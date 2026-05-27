"""
Web Page to PDF / Screenshot Service
使用 Playwright 无头浏览器将任意 URL 转换为 PDF 或图片。
Docker version — uses Node.js Playwright via subprocess.
"""
import os
import sys
import json
import uuid
import time
import hashlib
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# --- Configuration (Docker) ---
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/app/pdf-service-output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Aliyun OSS Configuration ---
OSS_ENABLED = os.environ.get("OSS_ENABLED", "false").lower() == "true"
OSS_ACCESS_KEY_ID = os.environ.get("OSS_ACCESS_KEY_ID", "")
OSS_ACCESS_KEY_SECRET = os.environ.get("OSS_ACCESS_KEY_SECRET", "")
OSS_BUCKET = os.environ.get("OSS_BUCKET", "")
OSS_ENDPOINT = os.environ.get("OSS_ENDPOINT", "oss-cn-shenzhen.aliyuncs.com")
OSS_PATH_PREFIX = os.environ.get("OSS_PATH_PREFIX", "lab/evaluation/export")

# Node.js and Playwright paths (Docker)
NODE_EXE = os.environ.get("NODE_EXE", "/usr/local/bin/node")
PLAYWRIGHT_DIR = os.environ.get("PLAYWRIGHT_DIR", "/usr/local/lib/node_modules/playwright")

# --- FastAPI App ---
app = FastAPI(
    title="Web Page PDF & Screenshot Service",
    version="3.2.0"
)


class OutputResponse(BaseModel):
    success: bool
    file_path: str = ""
    file_url: str = ""
    oss_url: str = ""
    file_size: int = 0
    duration: float = 0
    uploaded: bool = False
    error: str = ""


def upload_to_oss(local_file_path: str, oss_key: str, override_bucket: str = "", override_endpoint: str = "") -> Optional[str]:
    """Upload file to Aliyun OSS with public-read ACL, return accessible URL."""
    if not OSS_ENABLED or not OSS_ACCESS_KEY_ID:
        return None

    bucket = override_bucket or OSS_BUCKET
    endpoint = override_endpoint or OSS_ENDPOINT

    if not bucket or not endpoint:
        return None

    try:
        import requests
        import hmac
        import base64
        from datetime import datetime
        import hashlib as hl

        content_type = "application/octet-stream"
        if oss_key.endswith('.pdf'):
            content_type = "application/pdf"
        elif oss_key.endswith('.png'):
            content_type = "image/png"
        elif oss_key.endswith(('.jpg', '.jpeg')):
            content_type = "image/jpeg"
        elif oss_key.endswith('.webp'):
            content_type = "image/webp"

        # --- Step 1: Upload with public-read ACL ---
        date_str = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        canonicalized_resource = f"/{bucket}/{oss_key}"
        # Include x-oss-object-acl in signature for public-read
        acl_header = "x-oss-object-acl:public-read\n"
        string_to_sign = f"PUT\n\n{content_type}\n{date_str}\n{acl_header}{canonicalized_resource}"
        signature = base64.b64encode(
            hmac.new(OSS_ACCESS_KEY_SECRET.encode('utf-8'), string_to_sign.encode('utf-8'), hl.sha1).digest()
        ).decode('utf-8')

        url = f"https://{bucket}.{endpoint}/{oss_key}"
        headers = {
            "Host": f"{bucket}.{endpoint}",
            "Date": date_str,
            "Content-Type": content_type,
            "x-oss-object-acl": "public-read",
            "Authorization": f"OSS {OSS_ACCESS_KEY_ID}:{signature}",
        }

        with open(local_file_path, 'rb') as f:
            resp = requests.put(url, headers=headers, data=f, timeout=120)

        if resp.status_code not in (200, 204):
            print(f"OSS upload failed ({resp.status_code}): {resp.text[:200]}")
            return None

        # Public-read ACL set — return unsigned URL (directly accessible)
        public_url = f"https://{bucket}.{endpoint}/{oss_key}"
        print(f"OSS upload OK (public-read): {public_url}")
        return public_url

    except Exception as e:
        print(f"OSS upload error: {e}")
        import traceback
        traceback.print_exc()
        return None


def render_page(
    url: str,
    output_path: str,
    output_type: str = "pdf",
    image_format: str = "png",
    scale: float = 2.0,
    width: int = 750,
    height: int = 0,
    format: str = "A4",
    landscape: bool = False,
    print_background: bool = True,
    margin: dict = None,
) -> dict:
    """Use Node.js Playwright to render URL to PDF or image."""
    if margin is None:
        margin = {"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"}

    is_pdf = output_type == "pdf"
    is_image = output_type in ("png", "jpg", "webp")
    actual_format = image_format if is_image else None
    actual_scale = scale if is_image else None

    # Use reasonable initial viewport height (1024) instead of 0
    # to avoid layout issues with vh/CSS/JS-dependent elements
    initial_height = height if height > 0 else 1024

    node_script = f"""
const {{ chromium }} = require('playwright');

(async () => {{
  const browser = await chromium.launch({{
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox',
           '--disable-gpu', '--disable-dev-shm-usage']
  }});

  const page = await browser.newPage({{
    viewport: {{ width: {width}, height: {initial_height}, deviceScaleFactor: {json.dumps(actual_scale) if actual_scale else 2.0} }},
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
  }});

  console.log('Loading:', {json.dumps(url)});
  await page.goto({json.dumps(url)}, {{ waitUntil: 'networkidle', timeout: 90000 }});

  // Wait for fonts + images to load, then short buffer for framework hydration
  try {{
    await page.waitForFunction(() => {{
      const fontsDone = !document.fonts || document.fonts.status === 'loaded';
      const imagesDone = Array.from(document.images).every(img => img.complete);
      return fontsDone && imagesDone;
    }}, {{ timeout: 15000 }});
  }} catch (e) {{
    console.log('Resource wait timeout, proceeding...');
  }}
  await page.waitForTimeout(2000);

  // Remove overflow constraints from structural containers,
  // but preserve text-truncation overflow (ellipsis / line-clamp)
  await page.evaluate(() => {{
    const all = document.querySelectorAll('*');
    all.forEach(el => {{
      const s = window.getComputedStyle(el);

      // Preserve text-truncation: text-overflow: ellipsis (single-line)
      // and -webkit-line-clamp (multi-line)
      const hasEllipsis = s.textOverflow === 'ellipsis';
      const hasLineClamp = s.webkitLineClamp !== 'none' && s.webkitLineClamp !== '0';
      if (hasEllipsis || hasLineClamp) {{
        return; // skip text-truncation elements
      }}

      if (s.overflow === 'hidden' || s.overflow === 'auto' || s.overflow === 'scroll' ||
          s.overflowY === 'hidden' || s.overflowY === 'auto' || s.overflowY === 'scroll') {{
        el.style.setProperty('overflow', 'visible', 'important');
        el.style.setProperty('overflow-y', 'visible', 'important');
      }}
      if (s.overflowX === 'hidden' || s.overflowX === 'auto' || s.overflowX === 'scroll') {{
        el.style.setProperty('overflow-x', 'visible', 'important');
      }}
    }});
    document.body.style.setProperty('overflow', 'visible', 'important');
    document.documentElement.style.setProperty('overflow', 'visible', 'important');
  }});

  // Wait for layout to stabilize after overflow removal (max 8s)
  let prevHeight = 0, stableCount = 0;
  for (let i = 0; i < 40; i++) {{
    await page.waitForTimeout(200);
    const h = await page.evaluate(() => document.body.scrollHeight);
    if (h === prevHeight && h > 0) {{
      stableCount++;
      if (stableCount >= 3) break; // stable for 600ms
    }} else {{
      stableCount = 0;
    }}
    prevHeight = h;
  }}

  const actualHeight = await page.evaluate(() => Math.max(
    document.body.scrollHeight, document.body.offsetHeight,
    document.documentElement.scrollHeight, document.documentElement.offsetHeight
  ));
  console.log('Content height:', actualHeight);

"""
    if is_pdf:
        node_script += f"""
  // Resize viewport to full content height for PDF capture
  const viewHeight = {height} > 0 ? {height} : Math.max(actualHeight, 6000);
  await page.setViewportSize({{ width: {width}, height: viewHeight }});

  // Wait for layout to stabilize after viewport resize (max 8s)
  let _ph = 0, _sc = 0;
  for (let i = 0; i < 40; i++) {{
    await page.waitForTimeout(200);
    const h = await page.evaluate(() => document.body.scrollHeight);
    if (h === _ph && h > 0) {{
      _sc++;
      if (_sc >= 3) break;
    }} else {{
      _sc = 0;
    }}
    _ph = h;
  }}

  await page.pdf({{
    path: {json.dumps(output_path)},
    format: {json.dumps(format)},
    landscape: {json.dumps(landscape)},
    printBackground: {json.dumps(print_background)},
    margin: {{
      top: {json.dumps(margin.get("top", "0mm"))},
      right: {json.dumps(margin.get("right", "0mm"))},
      bottom: {json.dumps(margin.get("bottom", "0mm"))},
      left: {json.dumps(margin.get("left", "0mm"))}
    }}
  }});
"""
    elif is_image:
        node_script += f"""
  await page.screenshot({{
    path: {json.dumps(output_path)},
    type: {json.dumps(actual_format)},
    fullPage: true
  }});
"""

    node_script += """
  await browser.close();
  process.exit(0);
})();
"""

    script_path = os.path.join("/tmp", f"render_{uuid.uuid4().hex[:8]}.js")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(node_script)

    start_time = time.time()
    output_path = os.path.abspath(output_path)

    try:
        env = os.environ.copy()
        env["NODE_PATH"] = PLAYWRIGHT_DIR + ":" + os.path.join(PLAYWRIGHT_DIR, "node_modules")
        result = subprocess.run(
            [NODE_EXE, script_path],
            cwd=PLAYWRIGHT_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=180
        )

        duration = time.time() - start_time
        if result.returncode != 0:
            raise Exception(f"Playwright error: {result.stderr[:500]}")

        if not os.path.exists(output_path):
            raise Exception(f"Output file not created at {output_path}")

        file_size = os.path.getsize(output_path)
        kind = "PDF" if is_pdf else "Screenshot"
        print(f"{kind} generated: {output_path} ({file_size / 1024:.1f} KB, {duration:.1f}s)")

        return {"success": True, "file_path": output_path, "file_size": file_size, "duration": round(duration, 2)}

    except subprocess.TimeoutExpired:
        raise Exception(f"Timeout after {time.time() - start_time:.0f}s")
    except Exception as e:
        raise Exception(f"Failed to render: {str(e)}")
    finally:
        try:
            os.remove(script_path)
        except:
            pass


@app.get("/")
def root():
    return {
        "service": "Web Page PDF & Screenshot Service",
        "version": "3.2.0",
        "endpoints": {
            "POST /api/render": "Render URL to PDF or Screenshot (JSON body)",
            "GET /api/render/download/{filename}": "Download generated file",
            "GET /api/health": "Health check"
        }
    }


@app.post("/api/render", response_model=OutputResponse)
async def create_output(request: Request):
    start_time = time.time()

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    def get_str(key, default=""):
        val = data.get(key, default)
        return val if val is not None else default
    def get_bool(key, default=False):
        val = data.get(key, default)
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val) if val is not None else default
    def get_float(key, default):
        try:
            return float(data.get(key, default))
        except:
            return default
    def get_int(key, default):
        try:
            return int(data.get(key, default))
        except:
            return default

    url = get_str("url")
    output_filename = get_str("output_filename")
    output_type = get_str("output_type", "pdf")
    image_format = get_str("image_format", "png")
    scale = get_float("scale", 2.0)
    width = get_int("width", 750)
    height = get_int("height", 0)
    pdf_format = get_str("format", "A4")
    landscape = get_bool("landscape")
    print_background = get_bool("print_background", True)
    margin = data.get("margin") or {"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"}

    oss_enabled_param = get_bool("oss_enabled")
    oss_path_param = get_str("oss_path")
    oss_override_bucket = get_str("oss_override_bucket")
    oss_override_endpoint = get_str("oss_override_endpoint")

    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must start with http:// or https://")

    # Build filename
    file_id = uuid.uuid4().hex[:12]
    safe_name = "".join(c for c in (output_filename or f"page_{file_id}") if c.isalnum() or c in "-_ ")
    ext_map = {"pdf": "pdf", "png": "png", "jpg": "jpg", "webp": "webp"}
    ext = ext_map.get(output_type, "pdf")
    filename = f"{safe_name}.{ext}"
    output_path = os.path.join(OUTPUT_DIR, filename)

    # OSS config
    effective_oss = oss_enabled_param or OSS_ENABLED
    effective_bucket = oss_override_bucket or OSS_BUCKET
    effective_endpoint = oss_override_endpoint or OSS_ENDPOINT

    auto_oss_path = oss_path_param
    if effective_oss and not auto_oss_path:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        h = hashlib.md5(url.encode()).hexdigest()[:8]
        auto_oss_path = f"{OSS_PATH_PREFIX}/{ts}_{h}.{ext}"

    try:
        result = render_page(
            url=url, output_path=output_path, output_type=output_type,
            image_format=image_format, scale=scale, width=width, height=height,
            format=pdf_format, landscape=landscape, print_background=print_background,
            margin=margin
        )

        oss_url = ""
        uploaded = False
        local_cleaned = False

        if effective_oss and auto_oss_path:
            oss_result = upload_to_oss(
                local_file_path=result["file_path"],
                oss_key=auto_oss_path,
                override_bucket=effective_bucket,
                override_endpoint=effective_endpoint
            )
            if oss_result:
                oss_url = oss_result
                uploaded = True
                try:
                    os.remove(result["file_path"])
                    local_cleaned = True
                except:
                    pass

        return OutputResponse(
            success=True,
            file_path=result["file_path"] if not local_cleaned else "",
            file_url=f"/api/render/download/{filename}" if not uploaded else "",
            oss_url=oss_url,
            file_size=result["file_size"],
            duration=result["duration"],
            uploaded=uploaded
        )

    except Exception as e:
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except:
            pass
        return OutputResponse(success=False, error=str(e), duration=round(time.time() - start_time, 2))


@app.get("/api/render/download/{filename}")
def download_file(filename: str):
    filename = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    ext = filename.rsplit(".", 1)[-1].lower()
    media_types = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}
    return FileResponse(path=file_path, filename=filename, media_type=media_types.get(ext, "application/octet-stream"))


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "output_dir": OUTPUT_DIR}


if __name__ == "__main__":
    print("=" * 60)
    print("  Web Page PDF & Screenshot Service (Docker)")
    print("=" * 60)
    print(f"  Port: 8912")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  OSS: {'enabled' if OSS_ENABLED else 'disabled'}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8912, log_level="info")
