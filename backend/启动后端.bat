@echo off
chcp 65001 >nul
echo ========================================
echo    SPC Agent 后端启动脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 正在安装Python依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [2/3] 正在初始化数据库...
python init_db.py

echo.
echo [3/3] 正在启动后端服务...
echo.
echo 启动成功！
echo API地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause