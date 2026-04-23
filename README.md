# SPC Agent - 统计过程控制智能助手

基于飞书的 SPC（统计过程控制）智能分析系统，支持控制图生成、AI智能分析、异常监控和飞书告警通知。

## 📋 功能特性

### 核心功能
- **数据输入**：支持手动输入、Excel/CSV文件导入、数据库对接
- **SPC分析**：9种控制图类型（X̄-R、X̄-S、I-MR、p、np、c、u、直方图、趋势图）
- **统计结果**：自动计算样本数、均值、标准差、变异系数等8项指标
- **AI智能分析**：基于Dify平台提供智能化的过程分析和改进建议
- **异常监控**：后台定时监控任务，实时检测数据异常
- **飞书告警**：Webhook方式发送异常告警到飞书群

### 图表功能
- ECharts 高性能图表渲染
- 支持导出PNG图片
- 全屏查看模式
- 判异规则可视化

## 🛠 技术栈

### 后端
- **框架**: FastAPI + Python 3.14
- **数据库**: PostgreSQL
- **ORM**: SQLAlchemy
- **任务调度**: APScheduler
- **数据处理**: NumPy, Pandas
- **飞书集成**: lark-oapi

### 前端
- **框架**: Vue 3 + TypeScript
- **UI组件**: Ant Design Vue 4
- **图表**: ECharts 5
- **状态管理**: Pinia
- **构建工具**: Vite

## 📁 项目结构

```
spc-agent-demo/
├── backend/                    # FastAPI后端
│   ├── app/
│   │   ├── api/               # API路由
│   │   │   ├── data.py        # 数据输入
│   │   │   ├── analysis.py    # 分析配置
│   │   │   ├── monitor.py     # 监控任务
│   │   │   ├── spc.py         # SPC计算
│   │   │   └── settings.py    # 系统设置
│   │   ├── models/            # 数据库模型
│   │   ├── services/          # 业务逻辑
│   │   │   ├── spc.py         # SPC核心算法
│   │   │   ├── ai_agent.py    # AI分析服务
│   │   │   ├── monitor.py     # 监控调度
│   │   │   ├── feishu.py      # 飞书通知
│   │   │   └── export.py      # 导出服务
│   │   ├── schemas/           # Pydantic模型
│   │   └── core/              # 核心配置
│   ├── requirements.txt
│   ├── init_db.py
│   └── 启动后端.bat
│
├── frontend/                   # Vue3前端
│   ├── src/
│   │   ├── api/               # API封装
│   │   ├── components/        # 组件
│   │   ├── views/            # 页面
│   │   ├── stores/           # Pinia状态
│   │   ├── types/            # TypeScript类型
│   │   └── utils/            # 工具函数
│   ├── vite.config.ts
│   └── 启动前端.bat
│
├── README.md
└── requirements_summary.md
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
# 编辑 .env 文件，填入数据库和飞书配置

# 初始化数据库
python init_db.py

# 启动服务
python -m uvicorn app.main:app --reload --port 8000
```

### 3. 前端配置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 访问应用

- 前端地址: http://localhost:5173
- 后端API文档: http://localhost:8000/docs
- API测试界面: http://localhost:8000/redoc

## ⚙️ 配置说明

### 数据库配置

编辑 `backend/.env`:

```env
DATABASE_URL=postgresql://用户名:密码@主机:端口/数据库名
DATABASE_SCHEMA=spc_agent_demo
```

### 飞书配置

```env
FEISHU_APP_ID=飞书应用AppID
FEISHU_APP_SECRET=飞书应用AppSecret
FEISHU_WEBHOOK_URL=飞书群Webhook地址
```

### AI配置（Dify）

```env
DIFY_API_URL=https://api.dify.ai/v1
DIFY_API_KEY=你的Dify应用APIKey
```

## 📊 数据库表结构

| 表名 | 说明 |
|------|------|
| data_sources | 数据源表 |
| analysis_configs | 分析配置表 |
| monitor_tasks | 监控任务表 |
| anomaly_records | 异常记录表 |
| ai_analysis_records | AI分析记录表 |
| system_settings | 系统设置表 |

## 🔧 开发路线图

- [x] Phase 1: 基础框架搭建
- [ ] Phase 2: 数据输入模块
- [ ] Phase 3: SPC核心计算 & 图表
- [ ] Phase 4: AI分析 & 导出
- [ ] Phase 5: 监控 & 飞书集成
- [ ] Phase 6: Docker部署

## 📝 许可证

MIT License

## 🤝 联系方式

如有问题，请联系系统管理员。
