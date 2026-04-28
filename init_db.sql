-- ============================================================
-- spc_agent_demo 数据库初始化脚本
-- 数据库：icoastline（腾讯云 PostgreSQL）
-- ============================================================

-- -------------------- qms_inspection_detail --------------------
-- 检验明细记录表（单样本实测数据，用于SPC绘图与质量追溯）
-- ============================================================

-- 1. 创建表结构
CREATE TABLE IF NOT EXISTS spc_agent_demo.qms_inspection_detail (
    id                        BIGSERIAL PRIMARY KEY,
    inspection_no             VARCHAR(50) NOT NULL,
    sample_seq                INT        NOT NULL DEFAULT 1,
    material_code             VARCHAR(50) NOT NULL,
    material_name             VARCHAR(100) NOT NULL,
    batch_no                  VARCHAR(50) NOT NULL,
    inspection_type           VARCHAR(20) NOT NULL,
    measure_value_a           NUMERIC(12,4),
    measure_value_b           NUMERIC(12,4),
    measure_value_c           NUMERIC(12,4),
    inspector_code            VARCHAR(50),
    create_time               TIMESTAMPTZ(3) NOT NULL DEFAULT NOW(),
    create_by                 VARCHAR(50),
    update_time               TIMESTAMPTZ(3) NOT NULL DEFAULT NOW(),
    update_by                 VARCHAR(50),
    CONSTRAINT chk_det_insp_type CHECK (inspection_type IN ('IQC', 'IPQC', 'FQC', 'OQC'))
);

-- 2. 表与字段注释（PG 标准语法）
COMMENT ON TABLE spc_agent_demo.qms_inspection_detail IS '检验明细记录表（单样本实测数据，用于SPC绘图与质量追溯）';

COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.id                IS '主键ID，自增序列';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.inspection_no    IS '关联检验主表单号（保障批次-检验单-样本三级追溯）';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.sample_seq       IS '样本序号/组内抽样顺序（1,2,3...），SPC控制图时间轴与子组计算必需';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.material_code    IS '物料/产品编码';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.material_name    IS '物料/产品名称';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.batch_no         IS '生产/来料批次号';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.inspection_type  IS '检验类型：IQC(来料)/IPQC(过程)/FQC(最终)/OQC(出货)';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.measure_value_a  IS '检验项A实测值（如：外径/长度/电压等）';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.measure_value_b  IS '检验项B实测值（如：厚度/宽度/电流等）';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.measure_value_c  IS '检验项C实测值（如：硬度/温度/压力等）';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.inspector_code  IS '执行检验的检验员编码';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.create_time     IS '记录创建时间（带时区，毫秒精度）';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.create_by       IS '记录创建人账号';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.update_time     IS '记录最后更新时间（带时区，毫秒精度）';
COMMENT ON COLUMN spc_agent_demo.qms_inspection_detail.update_by       IS '记录最后更新人账号';

-- 3. 业务索引（针对QMS查询与SPC时序拉取优化）
CREATE INDEX IF NOT EXISTS idx_qms_det_insp_no    ON spc_agent_demo.qms_inspection_detail(inspection_no);
CREATE INDEX IF NOT EXISTS idx_qms_det_mat_batch  ON spc_agent_demo.qms_inspection_detail(material_code, batch_no);
CREATE INDEX IF NOT EXISTS idx_qms_det_spc_ts     ON spc_agent_demo.qms_inspection_detail(material_code, inspection_type, create_time DESC);
CREATE INDEX IF NOT EXISTS idx_qms_det_sample     ON spc_agent_demo.qms_inspection_detail(batch_no, sample_seq);
