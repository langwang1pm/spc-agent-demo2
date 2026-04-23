"""
SPC数据输入相关API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models import DataSource, DataSourceType, SystemSourceType
from app.schemas import (
    DataSourceCreate,
    DataSourceResponse,
    ManualDataInput,
    ApiResponse
)
import shutil
import os
from pathlib import Path

router = APIRouter(prefix="/data", tags=["数据输入"])

# 文件上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/manual", response_model=ApiResponse)
async def create_manual_data(
    data: ManualDataInput,
    db: Session = Depends(get_db)
):
    """创建手动输入数据"""
    db_data = DataSource(
        name=data.name,
        source_type=DataSourceType.MANUAL,
        data_values=data.data_values
    )
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    
    return ApiResponse(
        success=True,
        message="数据添加成功",
        data={"id": db_data.id, "name": db_data.name}
    )


@router.post("/file", response_model=ApiResponse)
async def upload_file_data(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传文件数据（Excel/CSV）"""
    # 检查文件类型
    if not (file.filename.endswith('.xlsx') or 
            file.filename.endswith('.xls') or 
            file.filename.endswith('.csv')):
        raise HTTPException(status_code=400, detail="只支持Excel(.xlsx/.xls)或CSV文件")
    
    # 保存文件
    file_path = UPLOAD_DIR / f"{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 创建数据源记录
    db_data = DataSource(
        name=name,
        source_type=DataSourceType.FILE,
        file_name=file.filename,
        file_path=str(file_path)
    )
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    
    return ApiResponse(
        success=True,
        message="文件上传成功",
        data={"id": db_data.id, "name": db_data.name, "file_name": file.filename}
    )


@router.post("/system", response_model=ApiResponse)
async def create_system_data(
    data: DataSourceCreate,
    db: Session = Depends(get_db)
):
    """创建系统对接数据源"""
    if data.source_type != DataSourceType.SYSTEM:
        raise HTTPException(status_code=400, detail="数据源类型必须为system")
    
    db_data = DataSource(
        name=data.name,
        source_type=DataSourceType.SYSTEM,
        system_type=data.system_type,
        connection_config=data.connection_config,
        query_config=data.query_config
    )
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    
    return ApiResponse(
        success=True,
        message="系统对接配置创建成功",
        data={"id": db_data.id, "name": db_data.name}
    )


@router.get("/list", response_model=ApiResponse)
async def list_data_sources(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取数据源列表"""
    total = db.query(DataSource).count()
    data_sources = db.query(DataSource).order_by(
        DataSource.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return ApiResponse(
        success=True,
        data={
            "total": total,
            "items": [
                {
                    "id": ds.id,
                    "name": ds.name,
                    "source_type": ds.source_type.value,
                    "created_at": ds.created_at.isoformat() if ds.created_at else None
                }
                for ds in data_sources
            ]
        }
    )


@router.get("/{data_id}", response_model=ApiResponse)
async def get_data_source(
    data_id: int,
    db: Session = Depends(get_db)
):
    """获取单个数据源详情"""
    data_source = db.query(DataSource).filter(DataSource.id == data_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    
    return ApiResponse(
        success=True,
        data={
            "id": data_source.id,
            "name": data_source.name,
            "source_type": data_source.source_type.value,
            "data_values": data_source.data_values,
            "file_name": data_source.file_name,
            "file_path": data_source.file_path,
            "system_type": data_source.system_type.value if data_source.system_type else None,
            "connection_config": data_source.connection_config,
            "query_config": data_source.query_config,
            "created_at": data_source.created_at.isoformat() if data_source.created_at else None,
            "updated_at": data_source.updated_at.isoformat() if data_source.updated_at else None
        }
    )


@router.delete("/{data_id}", response_model=ApiResponse)
async def delete_data_source(
    data_id: int,
    db: Session = Depends(get_db)
):
    """删除数据源"""
    data_source = db.query(DataSource).filter(DataSource.id == data_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    
    # 删除关联文件
    if data_source.file_path and os.path.exists(data_source.file_path):
        os.remove(data_source.file_path)
    
    db.delete(data_source)
    db.commit()
    
    return ApiResponse(success=True, message="数据源删除成功")