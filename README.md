# PDF Service — 网页转 PDF / 截图 服务

基于 **Playwright 无头 Chromium** 的网页 PDF 生成与高清截图服务，封装为 **Docker 一键部署**。

## ✨ 功能特性

- 📄 **PDF 生成** — 网页直接转 PDF，文字可选中（非图片截屏）
- 🖼️ **多格式截图** — 支持 PNG / JPG / WebP 高清截图
- 📱 **移动端适配** — 可自定义视口宽度（默认 1920px，移动端可选 750px）
- 🔍 **高清渲染** — 支持缩放倍数（scale 2x/3x 等）
- 🌏 **中文渲染** — 内置 Noto CJK + 文泉驿中文字体
- 🔄 **后台服务** — FastAPI REST API，支持 JSON 请求
- 🐳 **一键部署** — Docker Compose 单命令启动，跨平台支持

## 📋 目录结构

```
pdf-service-docker/
├── Dockerfile                  # 三阶段构建 (Python + Node/Chromium + Final)
├── docker-compose.yml          # 服务编排
├── .dockerignore               # Docker 构建排除
├── pdf-service.py              # FastAPI 服务主程序
├── requirements.txt            # Python 依赖
├── package.json                # Playwright 依赖
├── package-lock.json           # npm 锁定文件
├── deploy.bat                  # Windows 一键部署脚本 (图形菜单)
├── deploy.sh                   # Linux/Mac 一键部署脚本
├── pdf-service-output/         # 生成文件输出目录
│   └── .gitkeep
└── README.md                   # 本文件
```

## 🚀 快速开始

### 前提条件

- **Docker Desktop** 4.x+ (Windows/Mac) 或 Docker Engine + Compose (Linux)
- 可用磁盘空间 ≥ 2 GB
- 网络畅通（构建时下载 Chromium ~300MB）

### Windows 用户（推荐）

1. 打开命令提示符或 PowerShell，进入项目目录：

```powershell
cd "C:\Users\Administrator\AppData\Local\hermes\hermes-agent\pdf-service-docker"
```

2. 双击运行 `deploy.bat`，按菜单提示操作：

```
┌──────────────────────────────────────────────────┐
│  请选择操作：                                    │
├──────────────────────────────────────────────────┤
│  1) 首次部署 (构建镜像 + 启动)                   │
│  2) 启动服务                                     │
│  3) 停止服务                                     │
│  4) 重启服务                                     │
│  5) 查看服务状态                                 │
│  6) 查看日志                                     │
│  7) 更新代码后重建                               │
│  8) 删除容器和镜像                               │
│  9) 测试截图                                     │
│  0) 退出                                         │
└──────────────────────────────────────────────────┘
```

3. 选择 **1) 首次部署**，等待构建完成（首次约 8-15 分钟，后续使用缓存秒级启动）。

### Linux / Mac 用户

```bash
cd pdf-service-docker/
chmod +x deploy.sh
./deploy.sh
```

### Docker Compose 直接启动

```bash
# 首次构建 + 启动
docker compose up -d --build

# 仅启动
docker compose up -d

# 停止
docker compose down

# 重建
docker compose build --no-cache && docker compose up -d --force-recreate
```

## 📡 API 接口

### 基本端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/render` | POST | 生成 PDF 或截图（主接口） |
| `/api/render/download/{filename}` | GET | 下载生成的文件 |
| `/api/health` | GET | 健康检查 |

### 请求格式

```
Content-Type: application/json
```

#### POST /api/render

**请求体：**

```json
{
  "url": "https://example.com/page",
  "output_type": "pdf",
  "output_filename": "my-report.pdf",
  "scale": 2.0,
  "width": 1920
}
```

**参数说明：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | string | 必填 | 目标网页 URL |
| `output_type` | string | `"pdf"` | 输出格式：`pdf` / `png` / `jpg` / `webp` |
| `output_filename` | string | 自动生成 | 输出文件名 |
| `scale` | number | `2.0` | 渲染缩放倍数（图片格式有效） |
| `width` | number | `1920` | 视口宽度（图片格式有效，移动端可选 750） |
| `wait_for_selector` | string | `""` | 等待某 CSS 选择器出现后再截图 |
| `wait_delay` | number | `1` | 页面加载后额外等待秒数 |

**成功响应：**

```json
{
  "success": true,
  "file_path": "pdf-service-output/my-report.pdf",
  "file_url": "/api/render/download/my-report.pdf",
  "file_size": 24680,
  "duration": 15.3,
  "error": ""
}
```

**失败响应：**

```json
{
  "success": false,
  "file_path": null,
  "file_url": null,
  "file_size": 0,
  "duration": 5.2,
  "error": "加载页面超时 (25秒)"
}
```

#### GET /api/render/download/{filename}

直接下载生成的文件。

#### GET /api/health

```json
{
  "status": "healthy",
  "output_dir": "/app/pdf-service-output",
  "total_files": 19,
  "pdf_files": 15,
  "image_files": 4
}
```

### 使用示例

```bash
# 生成 PDF
curl -X POST http://127.0.0.1:8911/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "output_type": "pdf",
    "output_filename": "example.pdf"
  }'

# 生成高清 PNG 截图 (3倍缩放)
curl -X POST http://127.0.0.1:8911/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "output_type": "png",
    "output_filename": "example-3x.png",
    "scale": 3.0
  }'

# 移动端尺寸 JPG 截图
curl -X POST http://127.0.0.1:8911/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "output_type": "jpg",
    "output_filename": "mobile.jpg",
    "scale": 1.0,
    "width": 750
  }'

# 等待指定元素加载后截图
curl -X POST http://127.0.0.1:8911/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "output_type": "png",
    "output_filename": "loaded.png",
    "wait_for_selector": ".main-content",
    "wait_delay": 3
  }'

# 下载生成的文件
curl -O http://127.0.0.1:8911/api/render/download/example.pdf
```

## 🔧 配置说明

### Docker Compose 配置

```yaml
services:
  pdf-service:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pdf-service
    restart: unless-stopped
    ports:
      - "8911:8911"
    volumes:
      - ./pdf-service-output:/app/pdf-service-output
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8911/api/health"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3
```

### 修改端口

编辑 `docker-compose.yml`，将 `8911:8911` 改为其他端口，例如 `9000:8911`。

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OUTPUT_DIR` | `/app/pdf-service-output` | 输出文件目录 |
| `NODE_EXE` | `/usr/local/bin/node` | Node.js 路径 |
| `PORT` | `8911` | 服务端口 |
| `PLAYWRIGHT_BROWSERS_PATH` | `/root/.cache/ms-playwright` | Playwright 浏览器路径 |

## 🏗️ 架构设计

### 三阶段 Docker 构建

```
┌─────────────────────────────────────────────────────────┐
│  Stage 1: python-builder                                 │
│  ─────────────────────────────                           │
│  Python 3.12-slim + pip install (FastAPI, uvicorn...)   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Stage 2: playwright-base                                │
│  ─────────────────────────────                           │
│  Node.js 18 + Chromium 浏览器 + 系统依赖                  │
│  (阿里云镜像源加速)                                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Stage 3: Final Image                                    │
│  ─────────────────────────────                           │
│  Python 3.12-slim + Node.js + Chromium + PDF Service    │
│  非 root 用户运行 + 中文语言环境                           │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.12-slim | 服务运行时 |
| FastAPI | ≥0.104.0 | Web 框架 |
| Uvicorn | ≥0.24.0 | ASGI 服务器 |
| Node.js | 18 | Playwright 运行环境 |
| Playwright | 1.49.1 | 无头浏览器 |
| Chromium | 131.0.6778.33 | 渲染引擎 |
| 字体 | Noto CJK + 文泉驿 | 中文渲染 |

## 📊 性能说明

| 指标 | 值 |
|------|-----|
| 内存占用 | ~200-400 MB |
| 镜像大小 | ~600-700 MB |
| 单次 PDF 生成 | 10-30 秒 |
| 并发支持 | ~4 个并行任务（Chromium 限制） |

> 如需更高并发，可启动多个容器实例配合负载均衡。

## 🛠️ 故障排查

### 构建失败

| 问题 | 解决方案 |
|------|----------|
| Docker 未运行 | 启动 Docker Desktop |
| 磁盘空间不足 | 清理无用镜像：`docker system prune -a` |
| 网络超时 | 检查网络，Docker 已配置阿里云镜像源 |
| `--no-cache` 构建慢 | 首次构建正常慢，后续使用缓存很快 |

### 服务异常

| 问题 | 解决方案 |
|------|----------|
| 端口被占用 | `netstat -ano \| findstr :8911` 找出占用进程并终止 |
| 截图返回空白 | 检查 URL 是否需要登录/JS 执行，使用 `wait_for_selector` 等待 |
| 中文显示为方块 | Dockerfile 已内置中文字体，检查字体是否完整 |

### 容器日志

```bash
docker compose logs -f
```

## 📝 输出目录

生成的文件保存在 `pdf-service-output/` 目录，文件命名规则：

```
{output_filename}.{ext}
或
{uuid}.{timestamp}.{output_type}
```

例如：
- `my-report.pdf`
- `test-screenshotpng.png`
- `4a3b2c1d-20260521-143022.png`

## 📄 许可证

内部使用工具。
