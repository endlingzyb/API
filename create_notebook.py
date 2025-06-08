import os
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import html

# ========== 获取 access_token ==========
client_id = os.environ["CLIENT_ID"]
client_secret = os.environ["CLIENT_SECRET"]
tenant_id = os.environ["TENANT_ID"]
refresh_token = os.environ["GRAPH_REFRESH_TOKEN"]

token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
data = {
    "client_id": client_id,
    "client_secret": client_secret,
    "grant_type": "refresh_token",
    "refresh_token": refresh_token,
    "scope": "https://graph.microsoft.com/.default offline_access"
}

resp = requests.post(token_url, data=data)
if resp.status_code != 200:
    print("❌ 获取 access_token 失败")
    print(resp.text)
    exit(1)

access_token = resp.json()["access_token"]

# ========== 生成内容 ==========
def generate_title():
    return datetime.now().strftime("%Y-%m-%d")

def generate_joke():
    try:
        headers = {"Accept": "application/json"}
        resp = requests.get("https://icanhazdadjoke.com/", headers=headers)
        if resp.status_code == 200:
            return html.escape(resp.json()["joke"])
        else:
            return "加载笑话失败 🥲"
    except Exception:
        return "获取笑话异常 🥲"

title = generate_title()
joke = generate_joke()
current_time = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Shanghai"))

# ========== 构建页面内容 ==========
page_content = f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>{title}</title>
    <meta name="created" content="{current_time.strftime('%Y-%m-%dT%H:%M:%SZ')}" />
  </head>
  <body>
    <h1>{title}</h1>
    <p>{joke}</p>
    <img src="https://cataas.com/cat" alt="猫咪" />
  </body>
</html>"""

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/xhtml+xml"
}

# ========== 提交到 OneNote ==========
response = requests.post(
    "https://graph.microsoft.com/v1.0/me/onenote/pages",
    headers=headers,
    data=page_content
)

if response.status_code == 201:
    print("✅ 成功创建 OneNote 页面：")
    print(response.json()["links"]["oneNoteWebUrl"]["href"])
else:
    print("❌ 页面创建失败")
    print(response.status_code)
    print(response.text)
