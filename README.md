# PDF & Screenshot Service

基于 **Playwright 无头 Chromium** 的网页转 PDF/截图服务，Docker 一键部署，支持阿里云 OSS 自动上传。

[![Docker](https://img.shields.io/badge/Docker-✓-2496ED?logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.50-2EAD33?logo=playwright)](https://playwright.dev/)

---

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/puyuntiancheng/pdf-service.git
cd pdf-service

# 2. 配置 OSS（可选）
cp .env.example .env
# 编辑 .env 填入阿里云 OSS 密钥

# 3. 启动
docker compose up -d

# 4. 测试
curl http://127.0.0.1:8912/api/health
```

---

## API 接口

### `POST /api/render` — 生成 PDF 或截图

**请求：**
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
  "oss_url": "https://yun-campus-data-test.oss-cn-shenzhen.aliyuncs.com/lab/evaluation/export/20260522_xxxxx.png",
  "file_path": "",
  "file_size": 1103483,
  "duration": 17.51
}
```

### 参数说明

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `url` | string | **必填** | 目标网页 URL |
| `output_type` | string | `pdf` | `pdf` \| `png` \| `jpg` \| `webp` |
| `width` | int | `750` | 视口宽度（px），移动端用 750 |
| `height` | int | `0` | 视口高度，0 = 自动（完整内容高度） |
| `scale` | float | `2.0` | 缩放倍数，图片格式有效 |
| `format` | string | `A4` | PDF 纸张：`A3` \| `A4` \| `Letter` \| `Legal` |
| `landscape` | bool | `false` | PDF 横向打印 |
| `print_background` | bool | `true` | 渲染背景色/图 |
| `margin` | object | `{}` | PDF 边距，如 `{"top":"10mm"}` |
| `output_filename` | string | 自动 | 自定义文件名（不含扩展名） |
| `oss_enabled` | bool | `false` | 覆盖全局 OSS 开关 |
| `oss_path` | string | 自动 | OSS 对象路径，含文件名 |

### curl 示例

```bash
# 截图（PNG, 移动端宽度, 2x高清）
curl -X POST http://127.0.0.1:8912/api/render \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","output_type":"png","width":750,"scale":2}'

# 生成 PDF（A4, 带边距）
curl -X POST http://127.0.0.1:8912/api/render \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","output_type":"pdf","format":"A4","margin":{"top":"10mm","bottom":"10mm"}}'

# 上传到 OSS（OSS 已全局启用时可省略 oss_enabled）
curl -X POST http://127.0.0.1:8912/api/render \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","oss_enabled":true,"oss_path":"reports/report.pdf"}'
```

---

## 阿里云 OSS 配置

### .env 文件

```env
OSS_ENABLED=true
OSS_ACCESS_KEY_ID=LTAI5xxxxxxxxxxxx
OSS_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
OSS_BUCKET=your-bucket
OSS_ENDPOINT=oss-cn-shenzhen.aliyuncs.com
OSS_PATH_PREFIX=lab/evaluation/export
```

### 行为

- 上传时设置 `x-oss-object-acl: public-read`，返回的 URL **无需签名即可直接访问**
- 上传成功后自动删除本地临时文件，防止磁盘写满
- 不传 `oss_enabled` 时跟随全局 `.env` 配置

---

## 其他端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务信息、版本、参数速查 |
| `/api/render/download/{filename}` | GET | 下载生成的文件 |
| `/api/health` | GET | 健康检查 |

---

## 部署

| 命令 | 说明 |
|------|------|
| `docker compose up -d` | 启动 |
| `docker compose up -d --build` | 构建 + 启动 |
| `docker compose down` | 停止 |
| `docker compose logs -f` | 查看日志 |

**端口：** `8912`（修改 `docker-compose.yml` 中的 `ports` 即可更改）

---

## 技术栈

| 组件 | 说明 |
|------|------|
| Python 3.12 | 服务运行时 |
| FastAPI + Uvicorn | REST API |
| Node.js 18 + Playwright 1.50 | 无头浏览器渲染 |
| Chromium | 渲染引擎，支持中文（文泉驿字体） |
| Docker 多阶段构建 | 最终镜像 ~600MB |

---

## 文件夹结构

```
pdf-service/
├── pdf-service.py        # 主服务（FastAPI + Playwright 渲染 + OSS 上传）
├── Dockerfile            # 三阶段构建
├── docker-compose.yml    # 服务编排（端口 8912）
├── .env.example          # OSS 配置模板
├── .gitignore            # 排除 .env / 输出目录
├── requirements.txt      # Python 依赖
├── package.json          # Playwright 依赖
├── deploy.bat            # Windows 部署脚本
├── deploy.sh             # Linux/Mac 部署脚本
├── pdf-service-output/   # 输出目录（不提交）
└── README.md
```

---

## 故障排查

| 问题 | 解决 |
|------|------|
| 端口占用 | `netstat -ano \| findstr :8912` |
| 中文显示方块 | Dockerfile 已含中文字体，检查构建日志 |
| OSS 上传 403 | 检查 `.env` 中 AK/SK/Bucket 是否正确 |
| 截图空白 | URL 可能需要登录，或页面 JS 未执行完毕 |
| 容器启动失败 | `docker compose logs pdf-service` |
