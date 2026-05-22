#!/bin/bash
# Linux/Mac 一键部署脚本
# Windows 用户请使用 deploy.bat

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 颜色 ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

# ── 检查依赖 ──
check_deps() {
    local missing=0

    if ! command -v docker &>/dev/null; then
        error "Docker 未安装，请先安装 Docker Desktop"
        missing=1
    elif ! docker info &>/dev/null 2>&1; then
        error "Docker 未运行，请启动 Docker Desktop"
        missing=1
    fi

    if ! command -v docker compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
        error "docker compose 不可用"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        exit 1
    fi

    info "Docker 环境检查通过"
}

# ── 菜单 ──
show_menu() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  PDF Service — 一键部署管理"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  1) 首次部署 (构建镜像 + 启动)"
    echo "  2) 启动服务"
    echo "  3) 停止服务"
    echo "  4) 重启服务"
    echo "  5) 查看状态"
    echo "  6) 查看日志 (Ctrl+C 退出)"
    echo "  7) 更新后重建"
    echo "  8) 彻底清理 (容器+镜像+数据)"
    echo "  9) 测试截图"
    echo "  0) 退出"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -n "请选择 [0-9]: "
    read -r choice
    echo ""
}

action_deploy() {
    warn "停止旧容器 (如果存在) ..."
    docker compose down 2>/dev/null || true
    warn "构建镜像 (首次约 8-15 分钟) ..."
    docker compose build
    info "启动服务 ..."
    docker compose up -d
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  部署完成!"
    echo "  服务地址: http://127.0.0.1:8911"
    echo "  健康检查: http://127.0.0.1:8911/api/health"
    echo "  输出目录: pdf-service-output/"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

action_start()   { docker compose up -d; }
action_stop()    { docker compose down; }
action_restart() { docker compose restart; }
action_status()  { docker compose ps; }
action_logs()    { docker compose logs -f; }

action_rebuild() {
    docker compose down
    docker compose build --no-cache
    docker compose up -d
    info "重建完成!"
}

action_remove() {
    read -r -p "确认删除容器和镜像? [y/N]: " confirm
    if [[ "$confirm" =~ ^[Yy] ]]; then
        docker compose down --rmi all -v
        info "已清理完成"
    fi
}

action_test() {
    if ! curl -sf http://127.0.0.1:8911/api/health >/dev/null 2>&1; then
        error "服务未运行，请先执行 1) 首次部署"
        return
    fi
    info "正在测试截图 ..."
    curl -s -X POST http://127.0.0.1:8911/api/render \
        -H "Content-Type: application/json" \
        -d '{"url":"https://www.baidu.com","output_type":"png","output_filename":"test-screenshot.png"}' | python3 -m json.tool 2>/dev/null || \
    curl -s -X POST http://127.0.0.1:8911/api/render \
        -H "Content-Type: application/json" \
        -d '{"url":"https://www.baidu.com","output_type":"png","output_filename":"test-screenshot.png"}'
    echo ""
    warn "等待渲染完成... (通常 15-30 秒)"
    echo "截图保存在: pdf-service-output/"
    sleep 20
    ls -lh pdf-service-output/test-screenshot* 2>/dev/null || true
}

# ── 主循环 ──
check_deps

while true; do
    show_menu
    case $choice in
        1)  action_deploy ;;
        2)  action_start ;;
        3)  action_stop ;;
        4)  action_restart ;;
        5)  action_status ;;
        6)  action_logs ;;
        7)  action_rebuild ;;
        8)  action_remove ;;
        9)  action_test ;;
        0)  echo "感谢使用!"; exit 0 ;;
        *)  warn "无效选项，请重试" ;;
    esac
    echo ""
done
