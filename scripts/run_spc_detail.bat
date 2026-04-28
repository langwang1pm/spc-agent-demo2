@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   SPC 模拟检验明细数据生成器
echo ============================================================
echo.
echo   python spc_insert_detail.py            - 每60秒插入一条（默认 NG 15%%）
echo   python spc_insert_detail.py --once      - 插入一条后退出
echo   python spc_insert_detail.py -i 30       - 每30秒插入一条
echo.
echo   停止： Ctrl + C
echo ============================================================
echo.
python "%~dp0spc_insert_detail.py" %*
