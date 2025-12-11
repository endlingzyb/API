import os
import requests
import html
import time
import random
import json
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# ================= 配置区域 =================
DEFAULT_LAT = "39.9042"
DEFAULT_LON = "116.4074"

# ========== 工具函数：获取 access_token ==========
def get_access_token():
    if not os.environ.get("CLIENT_ID"):
        print("❌ [错误] 环境变量 CLIENT_ID 未找到")
        exit(1)
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
    try:
        resp = requests.post(token_url, data=data, timeout=10)
        if resp.status_code != 200:
            print(f"❌ 获取 access_token 失败: {resp.status_code}")
            exit(1)
        return resp.json()["access_token"]
    except Exception as e:
        print(f"❌ 获取 Token 异常: {e}")
        exit(1)

# ========== 数据获取 ==========
def get_weather():
    lat = os.environ.get("LATITUDE", DEFAULT_LAT)
    lon = os.environ.get("LONGITUDE", DEFAULT_LON)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "daily": "weather_code,temperature_2m_max,temperature_2m_min", "current_weather": "true", "timezone": "auto"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            daily = data.get("daily", {})
            current = data.get("current_weather", {})
            return {"temp_now": current.get("temperature"), "temp_max": daily.get("temperature_2m_max", ["-"])[0], "temp_min": daily.get("temperature_2m_min", ["-"])[0], "desc": "多云"}
    except Exception: pass
    return None

def get_hitokoto():
    try:
        resp = requests.get("https://v1.hitokoto.cn/?c=d&c=i&c=k", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return {"content": data.get("hitokoto"), "from": data.get("from")}
    except Exception: pass
    return {"content": "心系一处，守口如瓶。", "from": "Unknown"}

# ========== 核心逻辑：创建 SharePoint 页面 ==========
def create_sharepoint_page(access_token, image_url, weather_data, quote_data):
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    # 1. 查找站点
    target_site_name = os.environ.get("SHAREPOINT_SITE_NAME")
    site_id = None
    if target_site_name:
        print(f"🔍 搜索站点: '{target_site_name}'")
        search_resp = requests.get(f"https://graph.microsoft.com/v1.0/sites?search={target_site_name}", headers=headers)
        if search_resp.status_code == 200 and search_resp.json().get("value"):
            site_id = search_resp.json()["value"][0]["id"]
            print(f"✅ 锁定站点: {site_id}")
        else:
            print("❌ 没找到站点"); return
    else:
        print("⚠️ 使用 Root 站点")
        site_id = requests.get("https://graph.microsoft.com/v1.0/sites/root", headers=headers).json()["id"]

    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    page_name = f"Report{now.strftime('%Y%m%d%H%M')}.aspx"
    title_text = f"{now.strftime('%d日')} | 每日晨报"
    
    weather_html = f"<strong>{weather_data['temp_now']}°C</strong> ({weather_data['temp_min']}° ~ {weather_data['temp_max']}°)" if weather_data else "暂无数据"
    quote_html = f"“{html.escape(quote_data['content'])}” —— {html.escape(quote_data['from'])}"

    # 🟢 构造 HTML 内容
    content_html = f"""
    <h2>📅 今日概览</h2>
    <p>{weather_html}</p>
    <hr>
    <h3>💬 每日一言</h3>
    <p><em>{quote_html}</em></p>
    <hr>
    <h3>🎯 今日重点</h3>
    <ul>
        <li>[ ] 重要事项 1</li>
        <li>[ ] 重要事项 2</li>
        <li>[ ] 阅读 / 学习</li>
    </ul>
    """

    # 🟢 构造 Payload
    payload = {
        # 必须指定 OData 类型
        "@odata.type": "#microsoft.graph.sitePage",
        "name": page_name,
        "title": title_text,
        "pageLayout": "article",
        "titleArea": {
            "enableGradientEffect": True,
            "layout": "colorBlock",
            "showAuthor": True,
            "showPublishedDate": True
        },
        "canvasLayout": {
            "horizontalSections": [
                {
                    # 🔴 关键修复：必须是小写 'oneColumn'
                    "layout": "oneColumn", 
                    "id": "1",
                    "emphasis": "none",
                    "columns": [
                        {
                            "id": "1",
                            "width": 12,
                            "webparts": [
                                {
                                    # Text WebPart
                                    "id": "cbe7339d-2718-4d5f-952c-49520c8f6154", 
                                    "innerHtml": content_html
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    if image_url:
        payload["titleArea"]["imageWebUrl"] = image_url

    print("📝 正在发布 SharePoint 页面...")
    
    create_url = f"https://graph.microsoft.com/beta/sites/{site_id}/pages"
    resp = requests.post(create_url, headers=headers, json=payload)
    
    if resp.status_code in [200, 201]:
        print("✅ 页面创建成功！")
        
        # 发布
        page_item_id = resp.json()["id"]
        publish_url = f"https://graph.microsoft.com/beta/sites/{site_id}/pages/{page_item_id}/publish"
        requests.post(publish_url, headers=headers)
        
        pub_url = resp.json().get("webUrl")
        print("🚀 页面已发布！")
        print(f"🔗 链接: {pub_url}")
        
    else:
        print(f"❌ 创建失败: {resp.status_code}")
        print(f"🔍 错误详情: {resp.text}")

# ========== 图片获取 ==========
def get_today_image_url(access_token):
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        folder = "Pictures/Unsplash"
        encoded_path = requests.utils.quote(folder)
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_path}:/children"
        resp = requests.get(url, headers=headers, timeout=20)
        
        if resp.status_code == 200:
            files = resp.json().get("value", [])
            images = [f for f in files if f.get("file")]
            images.sort(key=lambda x: x["name"], reverse=True)
            
            beijing_now = datetime.now(ZoneInfo("Asia/Shanghai"))
            today_prefix = beijing_now.strftime("%Y%m%d")
            selected = next((img for img in images if img["name"].startswith(today_prefix)), images[0] if images else None)
            
            if selected:
                return selected.get("@microsoft.graph.downloadUrl")
    except Exception:
        pass
    return None

# ========== 主程序 ==========
if __name__ == "__main__":
    print("🚀 启动 SharePoint 生成器 (大小写修正版)...")
    time.sleep(random.randint(1, 3))
    try:
        token = get_access_token()
        weather = get_weather()
        quote = get_hitokoto()
        img_url = get_today_image_url(token)
        create_sharepoint_page(token, img_url, weather, quote)
    except Exception as e:
        print(f"❌ 脚本错误: {e}")
        exit(1)