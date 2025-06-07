import os
import requests
import random
from datetime import datetime

# ========== 诗句词库 ==========
titles = [
    "春日吟", "月下独行", "秋风送爽", "夏夜星空", 
    "冬雪寒梅", "晨曦初露", "夜雨潇潇", "孤舟远影",
    "山间清泉", "梦回故乡", "花间一壶酒", "月影摇曳",
    "云海苍茫", "湖边小憩", "风吹柳絮", "星辰大海"
]

nouns = [
    "花", "月", "风", "云", "星", 
    "山", "水", "雪", "鸟", "树",
    "海", "草", "路", "影", "梦",
    "琴", "酒", "灯", "影", "雨",
    "心", "情", "夜", "光", "沙",
    "露", "雾", "声", "歌", "舞"
]

verbs = [
    "吟", "舞", "飞", "落", "照", 
    "笑", "泪", "思", "望", "听",
    "追", "唱", "奔", "游", "藏",
    "漂", "摇", "飘", "闪", "舞",
    "吟唱", "徘徊", "漫步", "回忆", "倾诉",
    "凝视", "感受", "探索"
]

adjectives = [
    "静", "远", "清", "明", "孤", 
    "寒", "热", "柔", "烈", "暗",
    "幽", "淡", "甜", "苦", "浓",
    "苍", "绿", "红", "蓝", "古",
    "美丽的", "孤独的", "温暖的", 
    "神秘的","宁静的","灿烂的",
    "悠扬的","璀璨的","恬淡的"
]

def generate_title():
    return random.choice(titles) + " " + random.choice(nouns)

def generate_verse():
    noun1 = random.choice(nouns)
    verb1 = random.choice(verbs)
    adj1 = random.choice(adjectives)
    noun2 = random.choice(nouns)
    verb2 = random.choice(verbs)
    adj2 = random.choice(adjectives)
    noun3 = random.choice(nouns)
    verb3 = random.choice(verbs)
    adj3 = random.choice(adjectives)

    return f"""
        {noun1}{verb1}在{adj1}的{noun2},<br/>
        {noun2}{verb2}着{adj2}的{noun3},<br/>
        {adj3}的{noun3}在{verb3}中
    """

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

# ========== 构建页面内容 ==========
title = generate_title()
verse = generate_verse()
# 获取当前本地时间（含年月日、时分秒）
current_time = datetime.now()

page_content = f"""<!DOCTYPE html>
<html>
  <head>
    <title>{title}</title>
    <meta name="created" content="{{ current_time }}" />
  </head>
  <body>
    <h1>{title}</h1>
    <p>{verse}</p>
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
