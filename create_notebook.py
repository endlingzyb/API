from msal import ConfidentialClientApplication
from requests_oauthlib import OAuth2Session
import requests
import json
import os
import random

# 进一步扩展后的词库
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

# 生成标题的函数
def generate_title():
    return random.choice(titles) + ' ' + random.choice(nouns)

# 生成诗句的函数
def generate_verse():
    noun = random.choice(nouns)
    verb = random.choice(verbs)
    adjective = random.choice(adjectives)
    
    verse = f"{adjective}的{noun}在{verb}中"
    
    return verse

page_content = """
<!DOCTYPE html>
<html>
<head>
    <title>""" + generate_title() + """</title>
</head>
<body>
    <h1>""" + generate_verse() + """</h1>
</body>
</html>
"""

# 通过环境变量获取 Microsoft Graph API 的凭证信息
client_id = os.environ.get('CLIENT_ID')
client_secret = os.environ.get('CLIENT_SECRET')
tenant_id = os.environ.get('TENANT_ID')

# 创建 ConfidentailClientApplication 对象
app = ConfidentialClientApplication(client_id, authority='https://login.microsoftonline.com/' + tenant_id, client_credential=client_secret)

# 获取访问令牌
result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
access_token = result['access_token']

# 使用访问令牌调用 Microsoft Graph API 创建 OneNote 笔记本

url = "https://graph.microsoft.com/v1.0/users/546342df-31bf-447f-8771-ccd71708539f/onenote/sections/1-fb339352-9c74-4f0b-b885-d4ddf8dd9178/pages"
url_me = "https://graph.microsoft.com/v1.0/users/renew@zhouyb.site"

headers = {
    'Authorization': 'Bearer ' + access_token,
    'Content-Type': 'application/xhtml+xml'
}

response = requests.get(url_me, headers=headers)
print(response.json())

response = requests.get(url_me+"/onenote/notebooks", headers=headers)
print(response.json())

response = requests.get(url_me+"/onenote/sections", headers=headers)
print(response.json())

response = requests.get(url_me+"/onenote/pages", headers=headers)
print(response.json())

response = requests.post(url, headers=headers, data=page_content)

# 打印创建笔记本的返回结果
print(response.json())
