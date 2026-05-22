@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ============================================================
echo   PDF Service — Docker 一键部署管理脚本
echo ============================================================
echo.

:menu
echo ┌──────────────────────────────────────────────────┐
echo │  请选择操作：                                    │
echo ├──────────────────────────────────────────────────┤
echo │  1) 首次部署 (构建镜像 + 启动)                   │
echo │  2) 启动服务                                     │
echo │  3) 停止服务                                     │
echo │  4) 重启服务                                     │
echo │  5) 查看服务状态                                 │
echo │  6) 查看日志                                     │
echo │  7) 更新代码后重建                               │
echo │  8) 删除容器和镜像                               │
echo │  9) 测试截图 (打开示例 URL)                     │
echo │  0) 退出                                         │
echo └──────────────────────────────────────────────────┘
echo.
set /p choice="请输入选项 [0-9]: "

if "%choice%"=="1" goto deploy
if "%choice%"=="2" goto start
if "%choice%"=="3" goto stop
if "%choice%"=="4" goto restart
if "%choice%"=="5" goto status
if "%choice%"=="6" goto logs
if "%choice%"=="7" goto rebuild
if "%choice%"=="8" goto remove
if "%choice%"=="9" goto test
if "%choice%"=="0" goto end
echo [!] 无效选项，请重试
echo.
goto menu

:deploy
echo.
echo [步骤 1/2] 停止旧容器 (如果存在) ...
docker compose down 2>nul
echo [步骤 2/2] 构建镜像 ...
echo    首次构建需要 8-15 分钟，请耐心等待 ...
docker compose build
if errorlevel 1 (
    echo.
    echo [!] 构建失败，请检查上面的错误信息
    echo     可能原因:
    echo       - Docker Desktop 未运行
    echo       - 网络不通畅 (阿里云镜像源)
    echo       - 磁盘空间不足 (需要 ~2GB)
    goto :eof
)
echo.
echo [启动服务] ...
docker compose up -d
echo.
echo ============================================================
echo   部署完成!
echo   服务地址: http://127.0.0.1:8911
echo   健康检查: http://127.0.0.1:8911/api/health
echo   输出目录: pdf-service-output\
echo ============================================================
echo.
timeout /t 3 /nobreak >nul
goto menu

:start
echo.
docker compose up -d
if errorlevel 1 ( echo [!] 启动失败 ); else ( echo 服务已启动 )
timeout /t 2 /nobreak >nul
goto menu

:stop
echo.
docker compose down
echo 服务已停止
timeout /t 2 /nobreak >nul
goto menu

:restart
echo.
docker compose restart
echo 服务已重启
timeout /t 2 /nobreak >nul
goto menu

:status
echo.
docker compose ps
timeout /t 3 /nobreak >nul
goto menu

:logs
echo.
echo 按 Ctrl+C 退出日志查看 ...
echo.
docker compose logs -f
goto menu

:rebuild
echo.
docker compose down
docker compose build --no-cache
docker compose up -d
echo.
echo 重建完成!
timeout /t 3 /nobreak >nul
goto menu

:remove
echo.
echo [警告] 这将删除容器、镜像和输出文件!
set /p confirm="确认删除? [y/N]: "
if /i not "%confirm%"=="y" ( goto menu )
docker compose down --rmi all -v 2>nul
echo 已清理完成
timeout /t 2 /nobreak >nul
goto menu

:test
echo.
echo 正在测试截图功能 ...
echo.
curl -s -X POST http://127.0.0.1:8911/api/render ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://www.baidu.com\",\"output_type\":\"png\",\"output_filename\":\"test-screenshot.png\"}" >nul 2>&1
if errorlevel 1 (
    echo [!] 服务未运行，请先执行 1) 首次部署
) else (
    echo [✓] 请求已发送
    echo     截图保存在: pdf-service-output\
    echo     等待渲染完成... (通常 15-30 秒)
    timeout /t 15 /nobreak >nul
    dir pdf-service-output\test-screenshot* 2>nul | findstr /i "test-screenshot"
)
timeout /t 3 /nobreak >nul
goto menu

:end
echo.
echo 感谢使用 PDF Service!
echo.
exit /b 0
