from msal import ConfidentialClientApplication
from requests_oauthlib import OAuth2Session
import requests
import json
import os

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
url = "https://graph.microsoft.com/v1.0/user/renew@zhouyb.site/notes/notebooks"
headers = {
    'Authorization': 'Bearer ' + access_token,
    'Content-Type': 'application/json'
}
data = {
    'displayName': 'add'
}
response = requests.post(url, headers=headers, data=json.dumps(data))

# 打印创建笔记本的返回结果

print(response.json())
