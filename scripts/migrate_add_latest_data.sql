-- ============================================================
-- 迁移脚本：为 monitor_tasks 表添加 latest_data 字段
-- 日期: 2026-05-06
-- ============================================================

-- 添加 latest_data 字段（存储最新一次查询到的数据，一维数组）
ALTER TABLE spc_agent_demo.monitor_tasks
ADD COLUMN IF NOT EXISTS latest_data JSONB DEFAULT NULL;

-- 添加注释
COMMENT ON COLUMN spc_agent_demo.monitor_tasks.latest_data IS '最新一次查询到的数据，一维数组';

-- 验证
-- SELECT column_name, data_type, column_default, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_schema = 'spc_agent_demo' AND table_name = 'monitor_tasks'
-- ORDER BY ordinal_position;