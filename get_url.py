"""Extract cpolar public URL from local API"""
import urllib.request, json

req = urllib.request.Request("http://127.0.0.1:4040/http/in")
with urllib.request.urlopen(req, timeout=3) as resp:
    html = resp.read().decode()

marker = 'window.data = JSON.parse("'
start = html.index(marker) + len(marker)
end = html.index('");', start)
raw = html[start:end]

# Unescape: cpolar embeds JSON as a JS string, so \" → " and \\ → \
raw = raw.replace('\\"', '"').replace('\\\\', '\\')

data = json.loads(raw)
for t in data["UiState"]["Tunnels"]:
    if t["Name"] == "default":
        print(t["PublicUrl"])
