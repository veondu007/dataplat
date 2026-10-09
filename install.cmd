@echo off
rem ============================================================
rem  DataPlat 本地一键启动脚本（Windows / Docker Desktop）
rem  步骤：平台基础(PostgreSQL+Redis) -> Doris 2FE2BE -> API -> Web
rem  文档：docs/05-ops/本地配置与启动.md
rem ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo [1/4] 启动平台基础：PostgreSQL + Redis ...
docker compose -f deploy\docker-compose.yml up -d
if errorlevel 1 (
    echo [错误] 平台基础启动失败，请确认 Docker Desktop 已运行。
    pause & exit /b 1
)

echo [2/4] 启动 Doris 集群：2 FE + 2 BE（首次含 credit 测试库初始化）...
cd /d "%CD%\deploy\doris"
docker compose up -d
if errorlevel 1 (
    echo [错误] Doris 启动失败。
    cd /d "%~dp0"
    pause & exit /b 1
)

rem ---- 等待 BE Alive（最多约 6 分钟）----
echo 等待 BE 注册（首次需 1~3 分钟，如较久请先检查 vm.max_map_count）...
set /a tries=0
:wait_be
set /a tries+=1
if %tries% gtr 36 (
    echo [错误] 等待超时，BE 未就绪。请检查：
    echo   - wsl -d docker-desktop -u root -- sysctl -w vm.max_map_count=2000000
    echo   - docker compose -f deploy\doris\docker-compose.yml logs -f fe-1
    cd /d "%~dp0"
    pause & exit /b 1
)
for /f "skip=1 delims=" %%L in ('docker exec dataplat-doris-fe-1 mysql -uroot -P9030 -h127.0.0.1 -e "SHOW BACKENDS;" 2^>nul') do (
    echo %%L | findstr /i "true" >nul && goto be_ready
)
timeout /t 10 /nobreak >nul
goto wait_be
:be_ready
echo Doris BE 已全部 Alive。
cd /d "%~dp0"

echo [3/4] 启动 API：venv + 依赖 + 迁移 + uvicorn ...
cd /d "%CD%\apps\api"
if not exist .venv\Scripts\python.exe (
    echo 首次运行，创建虚拟环境并安装依赖（约 1~2 分钟）...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements-dev.txt
) else (
    call .venv\Scripts\activate.bat
)
python -m alembic upgrade head
cd /d "%~dp0"

echo [4/4] 启动 Web：npm install + vite dev ...
cd /d "%CD%\apps\web"
if not exist node_modules (
    npm install
)
cd /d "%~dp0"

echo.
echo ============================================================
echo  启动完成！请分别打开两个终端执行：
echo    API: cd apps\api ^&^& .venv\Scripts\activate ^&^& uvicorn app.main:app --reload --port 8000
echo    Web: cd apps\web ^&^& npm run dev
echo  控制台：http://localhost:5173   登录：admin / admin123
echo   API 文档：http://127.0.0.1:8000/docs
echo ============================================================
pause
