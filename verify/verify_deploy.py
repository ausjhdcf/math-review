"""
验证4：部署走通
目标：创建一个最小 FastAPI 应用，部署到 Railway，手机浏览器验证
红线：代码→部署→访问链路全程通畅

使用方法：
  1. pip install fastapi uvicorn
  2. 本地测试:
     python verify_deploy.py
     # 浏览器打开 http://localhost:8000
  3. 部署到 Railway:
     # 确保项目根目录（study/）被 git init
     git init && git add . && git commit -m "init"
     # 在 Railway 中连接 GitHub 仓库，或使用 Railway CLI:
     # railway up
  4. 手机浏览器打开 Railway 给的公网地址

注意：
  此脚本是单文件部署验证。正式项目会拆分为多个文件。
  除了本脚本外，还需在同目录准备以下部署文件：
    - requirements.txt    ← 依赖列表
    - Procfile             ← Railway 启动命令（无扩展名）
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# 部署辅助：生成配套文件
# ============================================================

REQUIREMENTS_TXT = """fastapi==0.115.6
uvicorn==0.34.0
python-multipart==0.0.20
supabase==2.13.0
httpx==0.28.1
"""

PROCFILE = "web: uvicorn verify_deploy:app --host 0.0.0.0 --port $PORT"

RAILWAY_JSON = """{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn verify_deploy:app --host 0.0.0.0 --port $PORT"
  }
}
"""


def generate_deploy_files():
    """在同目录生成部署所需文件"""
    base = Path(__file__).parent

    req_file = base / "requirements.txt"
    if not req_file.exists():
        req_file.write_text(REQUIREMENTS_TXT, encoding="utf-8")
        print(f"  已生成: {req_file}")

    procfile = base / "Procfile"
    if not procfile.exists():
        procfile.write_text(PROCFILE, encoding="utf-8")
        print(f"  已生成: {procfile}")

    railway_config = base / "railway.json"
    if not railway_config.exists():
        railway_config.write_text(RAILWAY_JSON, encoding="utf-8")
        print(f"  已生成: {railway_config}")


# ============================================================
# 最小 FastAPI 应用
# ============================================================

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="数学复习助手 - 部署验证")
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    app = None  # FastAPI 未安装，仅能生成部署文件

DEPLOY_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>部署验证 - 考研数学复习助手</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
        }
        .card {
            background: white; border-radius: 16px; padding: 32px 24px;
            max-width: 400px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
        }
        h1 { font-size: 1.5em; margin-bottom: 8px; color: #333; }
        .status { display: inline-block; background: #10b981; color: white;
                  padding: 4px 16px; border-radius: 20px; font-size: 0.85em; margin: 12px 0; }
        .info { background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 16px 0;
                text-align: left; font-size: 0.9em; color: #666; line-height: 1.8; }
        .info span { color: #333; font-weight: 600; }
        .test-area {
            border: 2px dashed #ddd; border-radius: 12px; padding: 32px 16px;
            margin: 16px 0; color: #999; cursor: pointer; transition: all 0.2s;
        }
        .test-area:hover { border-color: #667eea; color: #667eea; }
        #upload-result { margin-top: 12px; font-size: 0.85em; color: #10b981; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📐 考研数学复习助手</h1>
        <div class="status">✅ 部署成功</div>

        <div class="info">
            <div><span>服务端时间:</span> {deploy_time}</div>
            <div><span>API 状态:</span> <span style="color:#10b981">正常</span></div>
            <div><span>Python:</span> {python_version}</div>
            <div><span>Host:</span> {host}</div>
        </div>

        <div class="test-area" onclick="document.getElementById('file-input').click()">
            📷 点击测试上传（正式版功能预览）
        </div>
        <input type="file" id="file-input" accept="image/*" style="display:none"
               onchange="testUpload(this)">
        <div id="upload-result"></div>

        <p style="font-size:0.75em;color:#bbb;margin-top:16px;">
            验证阶段 v0.1 · 后端服务正常运行
        </p>
    </div>

    <script>
        async function testUpload(input) {{
            const file = input.files[0];
            if (!file) return;
            const form = new FormData();
            form.append('file', file);
            try {{
                const resp = await fetch('/api/test-upload', {{ method:'POST', body:form }});
                const data = await resp.json();
                document.getElementById('upload-result').textContent =
                    `✓ 上传接口正常: ${{data.filename}} (${{data.size_kb}}KB)`;
            }} catch(e) {{
                document.getElementById('upload-result').textContent =
                    '✗ 上传失败: ' + e.message;
            }}
        }}
    </script>
</body>
</html>"""


if HAS_FASTAPI:

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        html = HTML_TEMPLATE
        html = html.replace("{deploy_time}", DEPLOY_TIME)
        html = html.replace("{python_version}", sys.version.split()[0])
        html = html.replace("{host}", request.client.host if request.client else "unknown")
        return html

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "time": datetime.now().isoformat(),
            "python": sys.version.split()[0],
        }

    @app.post("/api/test-upload")
    async def test_upload(request: Request):
        form = await request.form()
        file = form.get("file")
        if not file:
            return {"error": "未收到文件"}
        return {
            "filename": file.filename,
            "size_kb": round(file.size / 1024, 1),
            "received": True,
        }


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    generate_deploy_files()

    if not HAS_FASTAPI:
        print("=" * 60)
        print("  FastAPI 未安装，仅生成了部署文件")
        print("  要启动服务器请先执行: pip install fastapi uvicorn python-multipart")
        print("=" * 60)
        sys.exit(0)

    import uvicorn
    print("=" * 60)
    print("  部署验证服务器启动中...")
    print("  本地访问: http://localhost:8000")
    print("  健康检查: http://localhost:8000/api/health")
    print("  按 Ctrl+C 停止")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
