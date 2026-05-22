# PDF & Screenshot Service

基于 **Playwright 无头 Chromium** 的网页转 PDF/截图服务，Docker 一键部署，支持阿里云 OSS 自动上传。

[![Docker](https://img.shields.io/badge/Docker-✓-2496ED?logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.50-2EAD33?logo=playwright)](https://playwright.dev/)

---

## 快速开始

```bash
git clone https://github.com/puyuntiancheng/pdf-service.git
cd pdf-service
cp .env.example .env    # 编辑 .env 填入 OSS 密钥
docker compose up -d
curl http://127.0.0.1:8912/api/health
```

---

## API

### `POST /api/render` — 生成 PDF 或截图

```json
{
  "url": "https://example.com/page",
  "output_type": "png",
  "width": 750,
  "scale": 2
}
```

**响应：**
```json
{
  "success": true,
  "uploaded": true,
  "oss_url": "https://bucket.oss-cn-shenzhen.aliyuncs.com/lab/evaluation/export/xxx.png",
  "file_path": "",
  "file_size": 1103483,
  "duration": 17.51
}
```

### 参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `url` | string | **必填** | 目标网页 URL |
| `output_type` | string | `pdf` | `pdf` / `png` / `jpg` / `webp` |
| `width` | int | `750` | 视口宽度（px），移动端用 750 |
| `height` | int | `0` | 视口高度，0=自动完整内容高度 |
| `scale` | float | `2.0` | 缩放倍数，图片格式有效 |
| `format` | string | `A4` | PDF 纸张：A3/A4/Letter/Legal |
| `landscape` | bool | `false` | PDF 横向 |
| `print_background` | bool | `true` | 渲染背景 |
| `margin` | object | `{}` | PDF 边距 `{"top":"10mm"}` |
| `oss_enabled` | bool | `false` | 覆盖全局 OSS 开关 |
| `oss_path` | string | 自动 | OSS 对象路径 |

### 其他端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/render/download/{file}` | GET | 下载生成的文件 |

### curl 示例

```bash
# 截图
curl -X POST http://127.0.0.1:8912/api/render \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","output_type":"png","width":750,"scale":2}'

# PDF
curl -X POST http://127.0.0.1:8912/api/render \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","output_type":"pdf","format":"A4"}'

# OSS 上传
curl -X POST http://127.0.0.1:8912/api/render \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","oss_enabled":true,"oss_path":"reports/r.pdf"}'
```

---

## 阿里云 OSS

### .env 配置

```env
OSS_ENABLED=true
OSS_ACCESS_KEY_ID=LTAI5xxxxxxxxxxxx
OSS_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
OSS_BUCKET=your-bucket
OSS_ENDPOINT=oss-cn-shenzhen.aliyuncs.com
OSS_PATH_PREFIX=lab/evaluation/export
```

- 上传时设置 **public-read ACL**，返回 URL 可直接访问，无需签名
- 上传成功后自动删除本地临时文件，防止磁盘写满

---

## 部署

| 命令 | 说明 |
|------|------|
| `docker compose up -d` | 启动 |
| `docker compose up -d --build` | 构建+启动 |
| `docker compose down` | 停止 |
| `docker compose logs -f` | 日志 |

端口 `8912`（改 `docker-compose.yml` 中 `ports` 即可换端口）

---

## 技术栈

| 组件 | 说明 |
|------|------|
| Python 3.12 + FastAPI + Uvicorn | REST API |
| Node.js 18 + Playwright 1.50 | 无头浏览器 |
| Chromium + 文泉驿字体 | 渲染引擎，支持中文 |
| Docker 多阶段构建 | 镜像 ~600MB |

---

## 项目结构

```
├── pdf-service.py         # 主服务（渲染 + OSS 上传）
├── Dockerfile             # 三阶段构建
├── docker-compose.yml     # 端口 8912
├── .env.example           # OSS 配置模板
├── .gitignore
├── requirements.txt
├── package.json
├── deploy.bat / deploy.sh
├── pdf-service-output/
└── README.md
```

---

## 故障排查

| 问题 | 解决 |
|------|------|
| 端口占用 | `netstat -ano \| findstr :8912` |
| 中文方块 | Dockerfile 已含中文字体 |
| OSS 403 | 检查 `.env` 中 AK/SK/Bucket |
| 截图空白 | URL 可能需要登录 / JS 未执行完 |
