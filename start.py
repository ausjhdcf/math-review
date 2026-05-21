"""一键启动脚本 — 启动后端 + cpolar 穿透，显示公网地址"""
import subprocess, time, json, urllib.request, sys, os, signal

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("  数学复习助手 - 启动中...")
print("=" * 50)

# 启动 FastAPI
print("\n[1/2] 启动后端服务...")
server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
time.sleep(2)

# 启动 cpolar
print("[2/2] 启动公网穿透...")
cpolar = subprocess.Popen(
    ["./cpolar.exe", "http", "8000", "--log=stdout"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
time.sleep(8)

# 获取公网地址
for attempt in range(10):
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/http/in")
        with urllib.request.urlopen(req, timeout=3) as resp:
            html = resp.read().decode()
        marker = 'window.data = JSON.parse("'
        start = html.index(marker) + len(marker)
        end = html.index('");', start)
        raw = html[start:end]
        raw = raw.replace('\\"', '"').replace('\\\\', '\\')
        data = json.loads(raw)
        for t in data["UiState"]["Tunnels"]:
            if t["Name"] == "default":
                url = t["PublicUrl"]
                print("\n" + "=" * 50)
                print(f"\n  手机浏览器打开：\n\n  {url}\n")
                print("=" * 50)
                print("  按 Ctrl+C 停止服务")
                print("=" * 50)
                sys.stdout.flush()
                server.wait()
                sys.exit(0)
    except Exception:
        if attempt == 0:
            print("  (等待 cpolar 就绪...)")
        time.sleep(3)

print("\n  无法获取公网地址，请检查 cpolar 是否正常启动")
print("=" * 50)
server.terminate()
cpolar.terminate()
