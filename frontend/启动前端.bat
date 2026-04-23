@echo off
chcp 65001 >nul
echo ========================================
echo    SPC Agent 前端启动脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] 正在安装依赖...
call npm install

echo.
echo [2/2] 正在启动开发服务器...
echo.
echo 启动成功！
echo 前端地址: http://localhost:5173
echo.

npm run dev

pause