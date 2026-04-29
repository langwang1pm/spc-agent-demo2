"""
系统对接数据查询服务
支持从外部系统（数据库/ERP/MES/PLC）获取数据
"""
import json
from typing import List, Dict, Any, Optional, Tuple
import psycopg
from psycopg.rows import dict_row


class SystemQueryError(Exception):
    """系统查询错误"""
    pass


def validate_connection_config(connection_config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    验证连接配置是否有效
    
    Args:
        connection_config: 连接配置字典
        
    Returns:
        (is_valid, error_message)
    """
    if not connection_config:
        return False, "连接配置为空"
    
    db_type = connection_config.get("DB_type")
    if not db_type:
        return False, "连接配置中缺少 DB_type 字段"
    
    # 目前仅支持 postgresql
    if db_type.lower() != "postgresql":
        return False, f"暂不支持的数据库类型: {db_type}，目前仅支持 postgresql"
    
    # 验证必要字段
    required_fields = ["host", "dbname", "user", "password"]
    missing_fields = [f for f in required_fields if not connection_config.get(f)]
    if missing_fields:
        return False, f"连接配置缺少必要字段: {', '.join(missing_fields)}"
    
    return True, ""


def build_connection_string(connection_config: Dict[str, Any]) -> str:
    """
    构建数据库连接字符串
    
    Args:
        connection_config: 连接配置字典
        
    Returns:
        PostgreSQL 连接字符串
    """
    host = connection_config["host"]
    port = connection_config.get("port", 5432)
    dbname = connection_config["dbname"]
    user = connection_config["user"]
    password = connection_config["password"]
    
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def query_postgresql(connection_config: Dict[str, Any], sql: str) -> Tuple[bool, List[float] | str]:
    """
    查询 PostgreSQL 数据库
    
    Args:
        connection_config: 连接配置
        sql: SQL 查询语句
        
    Returns:
        (success, data_or_error_message)
    """
    conn = None
    try:
        # 构建连接
        conn_str = build_connection_string(connection_config)
        conn = psycopg.connect(conn_str)
        
        # 执行查询
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        
        if not rows:
            return False, "SQL 查询结果为空，请检查查询语句"
        
        # 提取数值，支持单列或多列结果
        # 如果是单列，直接取值；如果是多列，取第一列
        values: List[float] = []
        for row in rows:
            if isinstance(row, (list, tuple)):
                val = row[0]
            else:
                val = row
            
            # 尝试转换为 float
            try:
                if val is not None:
                    values.append(float(val))
            except (ValueError, TypeError):
                # 跳过无法转换的值
                continue
        
        if not values:
            return False, "查询结果中未找到有效数值，请检查查询语句"
        
        return True, values
        
    except psycopg.OperationalError as e:
        return False, f"数据库连接失败: {str(e)}"
    except psycopg.ProgrammingError as e:
        return False, f"SQL 语法错误: {str(e)}"
    except Exception as e:
        return False, f"查询执行失败: {str(e)}"
    finally:
        if conn:
            conn.close()


def query_system_data(
    system_type: str,
    connection_config: Any,
    query_config: str
) -> Tuple[bool, List[float] | str]:
    """
    从外部系统查询数据
    
    Args:
        system_type: 系统类型 (DATABASE/ERP/MES/PLC)
        connection_config: 连接配置（可能是字符串或字典）
        query_config: 数据查询配置（SQL语句）
        
    Returns:
        (success, data_or_error_message)
    """
    # 1. 判断系统类型
    if system_type != "DATABASE":
        return False, f"系统类型 [{system_type}] 相关功能暂未开发，敬请期待"
    
    # 2. 解析连接配置
    if isinstance(connection_config, str):
        try:
            connection_config = json.loads(connection_config)
        except json.JSONDecodeError:
            return False, "连接配置 JSON 解析失败，请检查格式是否正确"
    
    if not isinstance(connection_config, dict):
        return False, "连接配置格式错误，应为 JSON 对象"
    
    # 3. 验证连接配置
    is_valid, error_msg = validate_connection_config(connection_config)
    if not is_valid:
        return False, error_msg
    
    # 4. 检查 DB_type
    db_type = connection_config.get("DB_type", "").lower()
    if db_type != "postgresql":
        return False, f"暂不支持的数据库类型: {db_type}，目前仅支持 postgresql"
    
    # 5. 执行查询
    sql = query_config.strip()
    if not sql:
        return False, "数据查询语句为空"
    
    return query_postgresql(connection_config, sql)


def get_system_data_values(
    system_type: str,
    connection_config: Any,
    query_config: str
) -> List[float]:
    """
    获取系统对接数据（简化接口，失败时抛出异常）
    
    Args:
        system_type: 系统类型
        connection_config: 连接配置
        query_config: 查询配置
        
    Returns:
        数据值列表
        
    Raises:
        SystemQueryError: 查询失败时抛出
    """
    success, result = query_system_data(system_type, connection_config, query_config)
    if not success:
        raise SystemQueryError(result)
    return result