import os
import requests
import html
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# ========== 获取 access_token ==========
def get_access_token():
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

    return resp.json()["access_token"]

# ========== 创建 OneNote 页面 ==========
def create_page(access_token):
    def generate_title():
        return datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")

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

    page_content = f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>{title}</title>
    <meta name="created" content="{current_time.strftime('%Y-%m-%dT%H:%M:%S%z')}" />
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

# ========== 删除旧页面 ==========
def delete_old_pages(access_token):
    from zoneinfo import ZoneInfo
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 获取北京时间的“昨天”日期字符串
    beijing_tz = ZoneInfo("Asia/Shanghai")
    yesterday_str = (datetime.now(beijing_tz) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"🧹 正在删除标题为 '{yesterday_str}' 的页面...")
    
    pages_url = "https://graph.microsoft.com/v1.0/me/onenote/pages?$top=100"
    while pages_url:
        resp = requests.get(pages_url, headers=headers)
        if resp.status_code != 200:
            print("❌ 获取页面失败")
            print(resp.text)
            break

        data = resp.json()
        pages = data.get("value", [])

        for page in pages:
            title = page.get("title", "")
            if title == yesterday_str:
                page_id = page["id"]
                print(f"🗑 删除页面: {title} (ID: {page_id})")

                del_resp = requests.delete(
                    f"https://graph.microsoft.com/v1.0/me/onenote/pages/{page_id}",
                    headers=headers
                )
                if del_resp.status_code == 204:
                    print("✅ 删除成功")
                else:
                    print("❌ 删除失败", del_resp.status_code, del_resp.text)

        pages_url = data.get("@odata.nextLink", None)


# ========== 主函数 ==========
if __name__ == "__main__":
    token = get_access_token()
    create_page(token)
    delete_old_pages(token)
