import webbrowser
import http.server
import socketserver
import urllib.parse
import requests
import sys
import time
import threading
import os
from dotenv import load_dotenv

# ================= 配置区域 =================
# 1. 尝试加载 my.secrets 文件
if os.path.exists('my.secrets'):
    load_dotenv('my.secrets')
    print("✅ 已加载 my.secrets 文件")
else:
    print("⚠️ 未找到 my.secrets 文件，将使用手动输入或系统环境变量")

# 2. 从环境变量(secrets)中获取，如果没有则留空，稍后会要求手动输入
CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
TENANT_ID = os.getenv("TENANT_ID", "common")  # 默认为 common

# 3. 端口必须与 Azure 注册的回调地址一致
PORT = 8000
REDIRECT_URI = f"http://localhost:{PORT}" 
# ===========================================

auth_code = None

class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        # 解析 URL 参数
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if 'code' in params:
            auth_code = params['code'][0]
            # 返回给浏览器一个成功的页面
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = """
            <html>
            <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                <h1 style="color: green;">授权成功！</h1>
                <p>已获取 Authorization Code。</p>
                <p>你可以关闭此窗口，回到终端查看 Refresh Token。</p>
                <script>window.close()</script>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(400)
            self.wfile.write(b"Error: No code found.")
            
    def log_message(self, format, *args):
        # 屏蔽多余的日志输出
        return

def start_server():
    # 启动本地服务器监听回调
    # 允许地址重用，防止报错 "Address already in use"
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("localhost", PORT), OAuthHandler) as httpd:
        while auth_code is None:
            httpd.handle_request()

def get_refresh_token(client_id, client_secret, tenant_id):
    global auth_code
    
    # 1. 构造授权 URL
    base_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": "offline_access User.Read Files.ReadWrite Notes.ReadWrite", # 自动加上了你需要的权限
        "state": "12345"
    }
    auth_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    print(f"\n🚀 正在打开默认浏览器进行登录...\n如果未打开，请手动访问: \n{auth_url}\n")
    
    # 2. 启动本地监听并在浏览器打开
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(1)
    webbrowser.open(auth_url)

    # 3. 等待用户登录并获取 Code
    print(f"⏳ 正在监听 http://localhost:{PORT} 等待回调...")
    while auth_code is None:
        time.sleep(1)
    
    print("✅ 获取到 Authorization Code!")

    # 4. 使用 Code 换取 Refresh Token
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "scope": "offline_access User.Read Files.ReadWrite Notes.ReadWrite",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "client_secret": client_secret
    }
    
    print("🔄 正在向微软请求 Token...")
    response = requests.post(token_url, data=data)
    json_resp = response.json()
    
    if 'refresh_token' in json_resp:
        print("\n" + "="*60)
        print("🎉 成功获取 GRAPH_REFRESH_TOKEN (请复制下方内容):")
        print("="*60)
        print(f"\n{json_resp['refresh_token']}\n")
        print("="*60)
        print("💡 提示：请将此 Token 填入 my.secrets 文件和 GitHub Secrets 中。")
    else:
        print("\n❌ 获取失败，错误信息：")
        print(json_resp)

if __name__ == "__main__":
    print("--- Microsoft Graph API Refresh Token 获取助手 ---")
    
    # 优先使用 secrets 里的值，如果没有则提示输入
    c_id = CLIENT_ID if CLIENT_ID else input("请输入 Client ID (应用程序ID): ").strip()
    c_secret = CLIENT_SECRET if CLIENT_SECRET else input("请输入 Client Secret (客户端密码): ").strip()
    t_id = TENANT_ID if TENANT_ID else input("请输入 Tenant ID (直接回车默认为 common): ").strip() or "common"
    
    if not c_id or not c_secret:
        print("❌ 错误：必须提供 Client ID 和 Client Secret")
        sys.exit(1)

    get_refresh_token(c_id, c_secret, t_id)
    input("\n按回车键退出...")