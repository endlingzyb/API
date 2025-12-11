import os
import requests
import html
import time
import random
from datetime import datetime, timezone
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


# ========== 查询个人资料 ==========
def get_my_profile(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://graph.microsoft.com/v1.0/me"

    requests.get("https://graph.microsoft.com/v1.0/me/messages", headers=headers)
    requests.get("https://graph.microsoft.com/v1.0/me/events?$select=subject,body,bodyPreview,organizer,attendees,start,end,location", headers=headers)
    requests.get("https://graph.microsoft.com/v1.0/me/drive/root/children", headers=headers)
    requests.get("https://graph.microsoft.com/v1.0/sites/root", headers=headers)
    requests.get("https://graph.microsoft.com/v1.0/me/joinedTeams", headers=headers)
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        profile = resp.json()
        info = {
            "姓名": profile.get("displayName"),
            "邮箱": profile.get("mail") or profile.get("userPrincipalName"),
            "职位": profile.get("jobTitle"),
            "手机号": profile.get("mobilePhone"),
            "办公电话": ", ".join(profile.get("businessPhones", [])),
            "办公室": profile.get("officeLocation"),
        }

        print("👤 我的个人资料：")
        for k, v in info.items():
            print(f"{k}: {v}")

        return info
    else:
        print("❌ 获取个人资料失败")
        print(resp.status_code, resp.text)
        return {}


# ========== 获取或创建笔记本 ==========
def get_or_create_notebook(access_token, notebook_name="MyNotes"):
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 获取所有笔记本
    notebooks_url = "https://graph.microsoft.com/v1.0/me/onenote/notebooks"
    resp = requests.get(notebooks_url, headers=headers)
    
    if resp.status_code != 200:
        print("❌ 获取笔记本失败")
        print(resp.text)
        exit(1)
    
    notebooks = resp.json().get("value", [])
    
    # 查找现有笔记本
    for notebook in notebooks:
        if notebook.get("displayName") == notebook_name:
            print(f"✅ 找到笔记本: {notebook_name}")
            return notebook["id"]
    
    # 创建新笔记本
    print(f"📓 创建新笔记本: {notebook_name}")
    create_resp = requests.post(
        notebooks_url,
        headers=headers,
        json={"displayName": notebook_name}
    )
    
    if create_resp.status_code == 201:
        notebook_id = create_resp.json()["id"]
        print(f"✅ 笔记本创建成功: {notebook_id}")
        return notebook_id
    else:
        print("❌ 创建笔记本失败")
        print(create_resp.text)
        exit(1)


# ========== 获取或创建分区 ==========
def get_or_create_section(access_token, notebook_id, section_name):
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 获取笔记本的所有分区
    sections_url = f"https://graph.microsoft.com/v1.0/me/onenote/notebooks/{notebook_id}/sections"
    resp = requests.get(sections_url, headers=headers)
    
    if resp.status_code != 200:
        print("❌ 获取分区失败")
        print(resp.text)
        exit(1)
    
    sections = resp.json().get("value", [])
    
    # 查找现有分区
    for section in sections:
        if section.get("displayName") == section_name:
            print(f"✅ 找到分区: {section_name}")
            return section["id"]
    
    # 创建新分区
    print(f"📑 创建新分区: {section_name}")
    create_resp = requests.post(
        sections_url,
        headers=headers,
        json={"displayName": section_name}
    )
    
    if create_resp.status_code == 201:
        section_id = create_resp.json()["id"]
        print(f"✅ 分区创建成功: {section_id}")
        return section_id
    else:
        print("❌ 创建分区失败")
        print(create_resp.text)
        exit(1)


# ========== 获取 OneDrive 图片 ==========
def get_random_image_from_onedrive(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 获取 Pictures/Unsplash 目录下的文件
    folder_path = "Pictures/Unsplash"
    encoded_path = requests.utils.quote(folder_path)
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_path}:/children"
    
    resp = requests.get(url, headers=headers)
    
    if resp.status_code != 200:
        print(f"❌ 获取 OneDrive 图片失败: {resp.status_code}")
        print(resp.text)
        return None
    
    files = resp.json().get("value", [])
    
    # 过滤出图片文件
    image_files = [f for f in files if f.get("file") and any(f["name"].lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])]
    
    if not image_files:
        print("❌ OneDrive 中没有找到图片")
        return None
    
    # 按文件名排序（假设文件名以日期开头，如 YYYYMMDD_HHMMSS_xxx.jpg）
    image_files.sort(key=lambda x: x["name"], reverse=True)
    
    # 尝试获取当天的图片（文件名需以 YYYYMMDD 开头）
    beijing_time = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Shanghai"))
    today_str = beijing_time.strftime("%Y%m%d")
    
    # 尝试找到当天的图片
    today_image = None
    for img in image_files:
        if img["name"].startswith(today_str):
            today_image = img
            break
    
    # 如果找不到当天的图片，使用最新的图片
    selected_image = today_image if today_image else image_files[0]
    
    print(f"✅ 选择图片: {selected_image['name']}")
    
    # 获取图片的下载链接
    return selected_image.get("@microsoft.graph.downloadUrl")


# ========== 创建 OneNote 页面 ==========
def create_page(access_token, profile_info):
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

    # 获取北京时间
    current_time = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Shanghai"))
    
    # 页面标题格式：DD日HH:MM
    title = current_time.strftime("%d日%H:%M")
    
    # 月份分区名称：YYYY年MM月
    section_name = current_time.strftime("%Y年%m月")
    
    joke = generate_joke()
    
    # 获取或创建笔记本和分区
    notebook_id = get_or_create_notebook(access_token, "MyNotes")
    section_id = get_or_create_section(access_token, notebook_id, section_name)
    
    # 获取 OneDrive 图片
    image_url = get_random_image_from_onedrive(access_token)
    
    # 图片 HTML
    image_html = ""
    if image_url:
        image_html = f'<img src="{html.escape(image_url)}" alt="每日图片" />'
    else:
        image_html = '<p>未找到图片</p>'
    
    # 🔹 个人资料拼接成表格
    profile_html = ""
    if profile_info:
        profile_html += "<h2>个人资料</h2><table border='1' cellspacing='0' cellpadding='5'>"
        profile_html += "<tr><th>字段</th><th>内容</th></tr>"
        for k, v in profile_info.items():
            if v:
                profile_html += f"<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>"
        profile_html += "</table>"

    page_content = f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>{title}</title>
    <meta name="created" content="{current_time.strftime('%Y-%m-%dT%H:%M:%S%z')}" />
  </head>
  <body>
    <h1>{title}</h1>
    <p>{joke}</p>
    {image_html}
    {profile_html}
  </body>
</html>"""

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/xhtml+xml"
    }

    # 创建页面到指定分区
    response = requests.post(
        f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section_id}/pages",
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




# ========== 主函数 ==========
if __name__ == "__main__":
    # 🔹 随机延迟 5-30 秒
    delay = random.randint(5, 30)
    print(f"⏳ 随机延迟 {delay} 秒后开始执行...")
    time.sleep(delay)
    
    token = get_access_token()
    profile_info = get_my_profile(token)   # 获取个人资料
    create_page(token, profile_info)       # 创建页面时附带资料表格