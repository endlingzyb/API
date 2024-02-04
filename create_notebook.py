from msal import ConfidentialClientApplication
from requests_oauthlib import OAuth2Session
import requests
import json
import os
import random

def generate_random_str(randomlength=16):
  """
  生成一个指定长度的随机字符串
  """
  random_str =''
  base_str ='ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789'
  length =len(base_str) -1
  for i in range(randomlength):
    random_str +=base_str[random.randint(0, length)]
  return random_str


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
url = "https://graph.microsoft.com/v1.0/users/546342df-31bf-447f-8771-ccd71708539f/onenote/sections/1-045056de-adc7-4de0-9cb6-86ea0fed4d74/pages"
url_me = "https://graph.microsoft.com/v1.0/users/renew@zhouyb.site"

headers = {
    'Authorization': 'Bearer ' + access_token,
    'Content-Type': 'application/json'
}

response = requests.get(url_me, headers=headers)
print(response.json())

data = {
        "content":  "<!DOCTYPE html><html><head><title>" + generate_random_str(10) + "</title></head><body><p>" + generate_random_str(10) + "<i>formatted</i> <b>text</b>.</p></body></html>"
}
response = requests.post(url, headers=headers, data=json.dumps(data))

# 打印创建笔记本的返回结果
print(response.json())
