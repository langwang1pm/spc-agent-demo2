# SPC Agent - 数据模块调试记录

## 时间
2026-04-23

## 模块
数据源管理（数据输入）

## 后端 API 测试结果

| 接口 | 方法 | 路径 | 状态 | 备注 |
|------|------|------|------|------|
| 创建手动数据 | POST | /api/data/manual | ✅ 200 | |
| 上传文件数据 | POST | /api/data/file | ✅ 200 | 修复：name 从 query 改为 Form |
| 获取数据列表 | GET | /api/data/list | ✅ 200 | 返回 items[] + total |
| 获取单个数据源 | GET | /api/data/{id} | ✅ 200 | |
| 删除数据源 | DELETE | /api/data/{id} | ✅ 200 | |
| 系统对接 | POST | /api/data/system | 未测试 | 前端未实现 |

## 修复内容

### 1. 后端 data.py - 文件上传 name 参数
**问题**：`name: str` 是 FastAPI 默认 query 参数，前端用 FormData 传 `name` 字段无法接收

**修复**：将 `name: str` 改为 `name: str = Form(...)`，导入 `Form` from fastapi

```python
# 修改前
async def upload_file_data(name: str, file: UploadFile = File(...), ...):

# 修改后
async def upload_file_data(name: str = Form(...), file: UploadFile = File(...), ...):
```

### 2. 后端 models.py - 表创建到正确 schema（之前的修复）
所有模型加 `__table_args__ = {"schema": "spc_agent_demo"}`
所有 `ForeignKey` 加上 schema 前缀

## 前端数据流

- `manualData.values`（逗号分隔文本）→ `parseDataValues()` → `number[][]`
- POST `/data/manual` → `data_values: number[][]` → 后端 JSON 存储
- 成功后调用 `store.setDataSource()` + `performSPCAnalysis()`
- 文件上传：`handleFileUpload()` 拦截文件，设置 name + file，然后 POST `/data/file`

## 后续工作

- 前端 UI 自测：启动前端 dev server，测试手动输入 + 文件上传流程
- 系统对接（system）前端功能：可后续补充
