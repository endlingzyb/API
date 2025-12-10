import os
import requests
import html
import time
import random
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# ================= 配置区域 =================
# 默认坐标（北京），如果你想改，可以在 Github Secrets 里设置 LATITUDE 和 LONGITUDE
DEFAULT_LAT = "39.9042"
DEFAULT_LON = "116.4074"

# ========== 工具函数：获取 access_token ==========
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

# ========== 数据获取：今日天气 (Open-Meteo 免费 API) ==========
def get_weather():
    lat = os.environ.get("LATITUDE", DEFAULT_LAT)
    lon = os.environ.get("LONGITUDE", DEFAULT_LON)
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset",
        "current_weather": "true",
        "timezone": "auto"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            daily = data.get("daily", {})
            current = data.get("current_weather", {})
            
            # WMO 天气代码映射
            wmo_code = current.get("weathercode", 0)
            weather_desc = "晴朗"
            if wmo_code in [1, 2, 3]: weather_desc = "多云"
            elif wmo_code in [45, 48]: weather_desc = "雾"
            elif 51 <= wmo_code <= 67: weather_desc = "雨"
            elif 71 <= wmo_code <= 77: weather_desc = "雪"
            elif wmo_code >= 80: weather_desc = "阵雨/雷雨"

            return {
                "temp_now": current.get("temperature"),
                "temp_max": daily.get("temperature_2m_max", ["-"])[0],
                "temp_min": daily.get("temperature_2m_min", ["-"])[0],
                "desc": weather_desc,
                "wind": current.get("windspeed")
            }
    except Exception as e:
        print(f"⚠️ 获取天气失败: {e}")
    
    return None

# ========== 数据获取：每日一言 (Hitokoto) ==========
def get_hitokoto():
    try:
        # 获取动画、文学、哲学类的句子
        resp = requests.get("https://v1.hitokoto.cn/?c=d&c=i&c=k", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "content": data.get("hitokoto"),
                "from": data.get("from")
            }
    except Exception:
        pass
    return {"content": "今天也是充满希望的一天。", "from": "Unknown"}

# ========== 核心逻辑：生成精美 HTML 内容 ==========
def generate_page_content(image_url, weather_data, quote_data):
    # 时间格式化
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    date_str = now.strftime("%Y年%m月%d日")
    week_days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday_str = week_days[now.weekday()]
    
    # 天气 HTML
    weather_html = "暂无天气数据"
    if weather_data:
        weather_html = f"""
        <div style="font-size: 24px; font-weight: bold; color: #333;">{weather_data['temp_now']}°C</div>
        <div style="color: #666; margin-top: 5px;">
            {weather_data['desc']} | {weather_data['temp_min']}° ~ {weather_data['temp_max']}°
        </div>
        """

    # 图片 HTML
    img_html = ""
    if image_url:
        img_html = f"""
        <div style="margin: 20px 0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <img src="{html.escape(image_url)}" alt="Daily Wallpaper" style="width: 100%; display: block;" />
        </div>
        """

    # 组合整体 HTML (使用 Table 布局以兼容 OneNote)
    page_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{date_str} {weekday_str} | 每日晨报</title>
        <meta name="created" content="{now.strftime('%Y-%m-%dT%H:%M:%S%z')}" />
    </head>
    <body style="font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; color: #333; line-height: 1.6;">
        
        <h1 style="color: #2c3e50; border-bottom: 2px solid #eaeaea; padding-bottom: 10px;">
            📅 {date_str} <span style="font-size: 0.6em; color: #888; font-weight: normal;">{weekday_str}</span>
        </h1>

        <table border="0" width="100%" cellspacing="0" cellpadding="10" style="background-color: #f9f9f9; border-radius: 8px; margin-top: 15px;">
            <tr>
                <td width="40%" valign="top" style="border-right: 1px solid #eee;">
                    <div style="font-size: 14px; color: #888; margin-bottom: 5px;">今日天气</div>
                    {weather_html}
                </td>
                <td width="60%" valign="top">
                    <div style="font-size: 14px; color: #888; margin-bottom: 5px;">每日一言</div>
                    <div style="font-style: italic; color: #444; font-weight: 500;">“{html.escape(quote_data['content'])}”</div>
                    <div style="text-align: right; color: #999; font-size: 12px; margin-top: 8px;">—— {html.escape(quote_data['from'])}</div>
                </td>
            </tr>
        </table>

        <h3 style="margin-top: 25px; color: #2980b9;">🎯 今日重点 (Top Priorities)</h3>
        <p data-tag="to-do">重要事项 1</p>
        <p data-tag="to-do">重要事项 2</p>
        <p data-tag="to-do">阅读 / 学习</p>

        {img_html}

        <h3 style="margin-top: 20px; color: #7f8c8d;">📝 随记 (Notes)</h3>
        <p style="color: #aaa;">点击此处开始输入...</p>

    </body>
    </html>
    """
    return page_html, now

# ========== OneNote API 操作 ==========
def create_onenote_page(access_token, html_content, created_time):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "text/html"
    }
    
    # 查找或创建分区
    notebook_name = "MyNotes"
    section_name = created_time.strftime("%Y年%m月")
    
    # 简化逻辑：这里假设你之前的 helper 函数逻辑没问题
    # 为了代码整洁，直接内联简单的获取逻辑，如果项目很大建议保留 helper
    
    # 1. 获取所有笔记本找到 ID
    nb_resp = requests.get("https://graph.microsoft.com/v1.0/me/onenote/notebooks", headers=headers)
    nb_id = next((nb['id'] for nb in nb_resp.json().get('value', []) if nb['displayName'] == notebook_name), None)
    
    if not nb_id:
        # 创建笔记本
        print(f"创建笔记本: {notebook_name}")
        resp = requests.post("https://graph.microsoft.com/v1.0/me/onenote/notebooks", headers=headers, json={"displayName": notebook_name})
        nb_id = resp.json()['id']

    # 2. 获取/创建分区
    sec_resp = requests.get(f"https://graph.microsoft.com/v1.0/me/onenote/notebooks/{nb_id}/sections", headers=headers)
    sec_id = next((s['id'] for s in sec_resp.json().get('value', []) if s['displayName'] == section_name), None)
    
    if not sec_id:
        # 创建分区
        print(f"创建分区: {section_name}")
        resp = requests.post(f"https://graph.microsoft.com/v1.0/me/onenote/notebooks/{nb_id}/sections", headers=headers, json={"displayName": section_name})
        sec_id = resp.json()['id']

    # 3. 创建页面
    print("正在写入 OneNote 页面...")
    page_resp = requests.post(
        f"https://graph.microsoft.com/v1.0/me/onenote/sections/{sec_id}/pages",
        headers=headers,
        data=html_content.encode('utf-8')
    )
    
    if page_resp.status_code == 201:
        print(f"✅ 成功创建页面：{page_resp.json()['links']['oneNoteWebUrl']['href']}")
    else:
        print("❌ 创建页面失败", page_resp.text)

# ========== OneDrive 图片获取 (保留原有逻辑) ==========
def get_today_image(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    folder = "Pictures/Unsplash"
    encoded_path = requests.utils.quote(folder)
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_path}:/children"
    
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200: return None
    
    files = resp.json().get("value", [])
    # 筛选图片
    images = [f for f in files if f.get("file") and f["name"].lower().endswith(('.jpg', '.png'))]
    if not images: return None
    
    images.sort(key=lambda x: x["name"], reverse=True)
    
    # 找当天的
    beijing_now = datetime.now(ZoneInfo("Asia/Shanghai"))
    today_prefix = beijing_now.strftime("%Y%m%d")
    
    selected = next((img for img in images if img["name"].startswith(today_prefix)), images[0] if images else None)
    
    if selected:
        print(f"✅ 选中图片: {selected['name']}")
        return selected.get("@microsoft.graph.downloadUrl")
    return None

# ========== 主程序 ==========
if __name__ == "__main__":
    print("🚀 启动每日晨报生成器...")
    
    # 随机延迟，模拟人类操作习惯
    time.sleep(random.randint(5, 15))
    
    try:
        token = get_access_token()
        
        # 1. 并行准备数据
        weather = get_weather()
        quote = get_hitokoto()
        img_url = get_today_image(token)
        
        # 2. 生成 HTML 内容
        html_content, created_time = generate_page_content(img_url, weather, quote)
        
        # 3. 推送到 OneNote
        create_onenote_page(token, html_content, created_time)
        
    except Exception as e:
        print(f"❌ 脚本执行出错: {e}")
        exit(1)