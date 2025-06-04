import json
import os
from msal import PublicClientApplication

client_id = os.environ.get("CLIENT_ID")
tenant_id = os.environ.get("TENANT_ID", "common")

if not client_id:
    raise Exception("请设置 CLIENT_ID 环境变量")

app = PublicClientApplication(
    client_id=client_id,
    authority=f"https://login.microsoftonline.com/{tenant_id}"
)

scopes = ["offline_access", "User.Read", "Notes.ReadWrite"]

flow = app.initiate_device_flow(scopes=scopes)
if "user_code" not in flow:
    raise Exception("无法初始化设备码登录流程")

print("请在浏览器中打开以下链接并输入代码完成登录：")
print(flow["verification_uri"])
print("输入代码：", flow["user_code"])

result = app.acquire_token_by_device_flow(flow)

if "access_token" in result:
    print("\n✅ 登录成功。请将以下 refresh_token 保存到 GitHub Secrets：\n")
    print(json.dumps({
        "refresh_token": result["refresh_token"]
    }, indent=2))
else:
    print("❌ 登录失败：")
    print(json.dumps(result, indent=2))
