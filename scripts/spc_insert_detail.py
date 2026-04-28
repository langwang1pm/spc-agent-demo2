"""
SPC 监控预警系统 - 模拟检验明细数据生成脚本
每分钟向 spc_agent_demo.qms_inspection_detail 插入一条模拟检验记录
"""

import random
import time
import argparse
from datetime import datetime, timezone

import psycopg as pg

# ===================== 数据库连接配置（腾讯云） =====================
DB_CONN = {
    "host": "sh-postgres-h3849b66.sql.tencentcdb.com",
    "port": 21656,
    "dbname": "icoastline",
    "user": "le_owner",
    "password": "PG^le=[2021)",
    "options": "-c search_path=spc_agent_demo,public",
}

# ===================== 固定字段（同一物料、同一工艺） =====================
MATERIAL_CODE = "MAT-001"
MATERIAL_NAME = "铝合金棒材"
INSPECTOR_CODE = "INSP-001"
CREATE_BY = "system"

# 检验值规格范围（经验值）
# measure_value_a：外径，LSL=18.5  USL=25.5  UCL=25.0  LCL=19.0
# measure_value_b：厚度，LSL=8.0   USL=12.0  UCL=11.8  LCL=8.2
# measure_value_c：硬度，LSL=60    USL=100   UCL=98    LCL=62
SPEC_A = {"lsl": 18.5, "usl": 25.5, "ucl": 25.0, "lcl": 19.0}
SPEC_B = {"lsl": 8.0,  "usl": 12.0, "ucl": 11.8, "lcl": 8.2}
SPEC_C = {"lsl": 60.0, "usl": 100.0, "ucl": 98.0, "lcl": 62.0}

# NG 阈值（超出规格限视为 NG）
NG_U_A = 25.5
NG_L_A = 18.5
NG_U_B = 12.0
NG_L_B = 8.0
NG_U_C = 100.0
NG_L_C = 60.0

# NG 概率 15%
NG_RATIO = 0.15


# ===================== 工具函数 =====================

def generate_inspection_no() -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rnd = random.randint(0, 999999)
    return f"INSP{ts}{rnd:06d}"


def generate_batch_no() -> str:
    ts = datetime.now().strftime("%Y%m%d")
    seq = random.randint(1, 999)
    return f"BAT{ts}{seq:03d}"


def generate_sample_seq(prev_seq: int | None) -> int:
    """样本序号，同一批次内顺序递增；换批次后重置为 1。"""
    if prev_seq is None or prev_seq >= 5:
        return 1
    return prev_seq + 1


def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def generate_measure_values() -> tuple[float, float, float, bool]:
    """
    生成三项检验值。

    规则：
    - 85% 概率：三项均在 UCL~LCL 控制限内 -> PASS
    - 15% 概率：随机 1~2 项超出规格限 -> NG
    - NG 时高/下限各半，超出幅度 0.1~0.8
    返回：(value_a, value_b, value_c, is_pass)
    """
    is_ng = random.random() < NG_RATIO

    if not is_ng:
        a = round(random.uniform(SPEC_A["lcl"] + 0.05, SPEC_A["ucl"] - 0.05), 4)
        b = round(random.uniform(SPEC_B["lcl"] + 0.05, SPEC_B["ucl"] - 0.05), 4)
        c = round(random.uniform(SPEC_C["lcl"] + 0.05, SPEC_C["ucl"] - 0.05), 4)
        return a, b, c, True

    # NG：随机选 1~2 项超限
    ng_fields = random.sample(["a", "b", "c"], k=random.randint(1, 2))
    a = round(random.uniform(SPEC_A["lcl"] + 0.05, SPEC_A["ucl"] - 0.05), 4)
    b = round(random.uniform(SPEC_B["lcl"] + 0.05, SPEC_B["ucl"] - 0.05), 4)
    c = round(random.uniform(SPEC_C["lcl"] + 0.05, SPEC_C["ucl"] - 0.05), 4)

    for field in ng_fields:
        direction = random.choice(["HIGH", "LOW"])
        if field == "a":
            delta = round(random.uniform(0.1, 0.8), 4)
            a = a + delta if direction == "HIGH" else a - delta
            a = clamp(a, NG_L_A - 1.0, NG_U_A + 1.0)
        elif field == "b":
            delta = round(random.uniform(0.05, 0.4), 4)
            b = b + delta if direction == "HIGH" else b - delta
            b = clamp(b, NG_L_B - 0.5, NG_U_B + 0.5)
        else:
            delta = round(random.uniform(1.0, 5.0), 4)
            c = c + delta if direction == "HIGH" else c - delta
            c = clamp(c, NG_L_C - 10.0, NG_U_C + 10.0)

    return round(a, 4), round(b, 4), round(c, 4), False


def do_insert(
    inspection_no: str,
    sample_seq: int,
    val_a: float,
    val_b: float,
    val_c: float,
    batch_no: str,
) -> int | None:
    """插入一条检验明细记录，返回 id。"""
    now = datetime.now(timezone.utc)

    vals = (
        inspection_no,
        sample_seq,
        MATERIAL_CODE,
        MATERIAL_NAME,
        batch_no,
        "IQC",
        val_a,
        val_b,
        val_c,
        INSPECTOR_CODE,
        now,
        CREATE_BY,
        now,
        CREATE_BY,
    )

    query = """
    INSERT INTO qms_inspection_detail (
        inspection_no, sample_seq, material_code, material_name, batch_no,
        inspection_type, measure_value_a, measure_value_b, measure_value_c,
        inspector_code, create_time, create_by, update_time, update_by
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    RETURNING id;
    """

    conn = pg.connect(**DB_CONN)
    cur = conn.cursor()
    try:
        cur.execute(query, vals)
        row = cur.fetchone()
        conn.commit()
        inserted_id = int(row[0]) if row else None
    except Exception as e:
        conn.rollback()
        print(f"[DB ERROR] {e}")
        inserted_id = None
    finally:
        cur.close()
        conn.close()

    return inserted_id


# ===================== 主循环 =====================

def main():
    parser = argparse.ArgumentParser(description="SPC 模拟检验明细数据生成器")
    parser.add_argument("--interval", "-i", type=int, default=60,
                        help="插入间隔（秒），默认 60")
    parser.add_argument("--once", action="store_true",
                        help="插入一条后立即退出")
    args = parser.parse_args()

    print("=" * 60)
    print("  SPC Insert Detail Demo")
    print(f"  DB:     icoastline @ {DB_CONN['host']}:{DB_CONN['port']}")
    print(f"  Schema: spc_agent_demo")
    print(f"  Table:  qms_inspection_detail")
    print(f"  Material: {MATERIAL_CODE} - {MATERIAL_NAME}")
    print(f"  Val-A:  LSL={SPEC_A['lsl']}  USL={SPEC_A['usl']}  (外径mm)")
    print(f"  Val-B:  LSL={SPEC_B['lsl']}  USL={SPEC_B['usl']}  (厚度mm)")
    print(f"  Val-C:  LSL={SPEC_C['lsl']}  USL={SPEC_C['usl']}  (硬度HB)")
    print(f"  NG:     {NG_RATIO * 100:.0f}%")
    print(f"  Every:  {args.interval}s")
    print("=" * 60)

    counter = 0
    batch_no = generate_batch_no()
    batch_counter = 0
    prev_sample_seq = 0

    while True:
        counter += 1
        batch_counter += 1

        # 每 5 条样本换批次（sample_seq 1~5）
        if batch_counter > 5:
            batch_no = generate_batch_no()
            batch_counter = 1

        sample_seq = generate_sample_seq(prev_sample_seq)
        prev_sample_seq = sample_seq

        val_a, val_b, val_c, is_pass = generate_measure_values()
        inspection_no = generate_inspection_no()
        label = "PASS" if is_pass else "NG  "

        row_id = do_insert(inspection_no, sample_seq, val_a, val_b, val_c, batch_no)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if row_id is not None:
            print(
                f"[{ts}] #{counter:04d} | id={row_id} | {label}"
                f" | A={val_a:.4f} B={val_b:.4f} C={val_c:.2f}"
                f" | batch={batch_no} seq={sample_seq}"
            )
        else:
            print(f"[{ts}] #{counter:04d} | [FAIL] insert failed")

        if args.once:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()