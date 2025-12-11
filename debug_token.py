import os
import requests
import json
from dotenv import load_dotenv

def test_token():
    print("🔍 开始 Token 诊断程序...")
    
    # 1. 加载 my.secrets 文件
    if os.path.exists('my.secrets'):
        load_dotenv('my.secrets')
        print("✅ 成功加载 my.secrets 文件")
    else:
        print("❌ 错误：未找到 my.secrets 文件！请确保它在当前目录下。")
        return

    # 2. 检查必要变量是否存在
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    refresh_token = os.getenv("GRAPH_REFRESH_TOKEN")
    tenant_id = os.getenv("TENANT_ID", "common")

    if not all([client_id, client_secret, refresh_token]):
        print("❌ 错误：my.secrets 文件中缺少必要变量（CLIENT_ID, CLIENT_SECRET 或 GRAPH_REFRESH_TOKEN）")
        return

    # 3. 尝试用 Refresh Token 换取 Access Token
    print("\n🔄 正在尝试向微软请求新的 Access Token...")
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "https://graph.microsoft.com/.default"
    }

    try:
        resp = requests.post(token_url, data=data, timeout=10)
        
        # 4. 分析结果
        if resp.status_code == 200:
            json_resp = resp.json()
            access_token = json_resp.get("access_token")
            print("\n🎉 认证成功！")
            print(f"✅ 获取到的 Access Token (前20位): {access_token[:20]}...")
            print(f"✅ 过期时间 (秒): {json_resp.get('expires_in')}")
            
            # 5. 进一步验证：尝试调用一下 /me 接口确保权限正常
            verify_permissions(access_token)
            
        else:
            print(f"\n❌ 认证失败！HTTP 状态码: {resp.status_code}")
            print("⚠️ 微软返回的错误详情：")
            print("-" * 30)
            print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            print("-" * 30)
            analyze_error(resp.json())

    except Exception as e:
        print(f"\n❌ 请求发生异常: {e}")

def verify_permissions(access_token):
    print("\n🕵️ 正在测试 API 权限 (读取个人资料)...")
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        me_resp = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, timeout=10)
        if me_resp.status_code == 200:
            profile = me_resp.json()
            print(f"✅ API 调用成功！你好，{profile.get('displayName')} ({profile.get('userPrincipalName')})")
        else:
            print(f"⚠️ API 调用失败 (状态码 {me_resp.status_code})。Token 有效但权限可能不足。")
            print(me_resp.text)
    except Exception as e:
        print(f"⚠️ API 测试异常: {e}")

def analyze_error(error_json):
    """简单的错误原因分析"""
    error_code = error_json.get("error")
    error_desc = error_json.get("error_description", "")
    
    print("\n💡 诊断建议：")
    if error_code == "invalid_grant":
        print("👉 Refresh Token 已失效、过期或被吊销。")
        print("   解决办法：请重新运行 'python get_refresh_token.py' 获取新的 Token。")
    elif error_code == "invalid_client":
        print("👉 Client Secret (密码) 错误或已过期。")
        print("   解决办法：去 Azure 后台检查你的客户端密码是否正确，注意不要有多余空格。")
    elif "AADSTS7000215" in error_desc:
        print("👉 Client Secret 格式错误。")
        print("   解决办法：确保 my.secrets 里的密码用双引号括起来，且没有转义字符。")
    else:
        print("👉 请根据上方具体的错误信息检查配置。")

if __name__ == "__main__":
    test_token()