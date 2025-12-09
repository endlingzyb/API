import os
import requests
from datetime import datetime
import urllib.parse  # 用于 URL 编码
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# 定义一次获取的图片数量
IMAGE_COUNT = 5

# ==============================================================================
# 身份验证相关函数
# ==============================================================================

# ========== 获取 access_token (使用 refresh_token) ==========
def get_access_token():
    """
    使用存储在环境变量中的 refresh_token 交换新的 access_token，
    用于访问 Microsoft Graph API (OneDrive)。
    """
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

    resp = requests.post(token_url, data=data, timeout=30)
    if resp.status_code != 200:
        print("❌ 获取 access_token 失败")
        print(resp.text)
        exit(1)

    return resp.json()["access_token"]


# ==============================================================================
# Unsplash 数据获取函数 (关键修改)
# ==============================================================================

# ========== 从 Unsplash 获取随机壁纸 (5张) ==========
def get_unsplash_wallpapers():
    """
    从 Unsplash API 获取指定数量 (IMAGE_COUNT) 的【随机】横向壁纸。
    使用随机接口可以有效避免每天下载重复图片的问题。
    """
    unsplash_access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not unsplash_access_key:
        print("❌ 未设置 UNSPLASH_ACCESS_KEY")
        exit(1)
    
    # [修改点 1] 更改为 /photos/random 接口
    url = "https://api.unsplash.com/photos/random"
    headers = {"Authorization": f"Client-ID {unsplash_access_key}"}
    
    # [修改点 2] 参数调整
    params = {
        "count": IMAGE_COUNT,      # 随机接口使用 count 指定数量
        "query": "wallpaper",      # 依然限定为壁纸类
        "orientation": "landscape" # 限定横屏
        # 移除了 order_by，因为随机接口本身就是无序的
    }
    
    print(f"📷 正在从 Unsplash 随机抽取 {IMAGE_COUNT} 张壁纸...")
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    
    if resp.status_code != 200:
        print(f"❌ 获取 Unsplash 图片失败: {resp.status_code}")
        print(resp.text)
        exit(1)
    
    data_list = resp.json()
    
    # 解析并返回一个包含多个图片信息的列表
    image_list = []
    for data in data_list:
        image_list.append({
            "id": data["id"],
            # 使用 full 尺寸的 url，适合高分辨率壁纸
            "url": data["urls"]["full"], 
            "photographer": data["user"]["name"],
            "photo_url": data["links"]["html"]
        })
        
    return image_list


# ========== 下载图片 ==========
def download_image(image_url):
    """
    根据 URL 下载图片的二进制内容，并返回图片数据和 Content-Type。
    """
    print(f"⬇️  正在下载图片: {image_url[:50]}...")
    resp = requests.get(image_url, stream=True, timeout=60)
    if resp.status_code != 200:
        print(f"❌ 下载图片失败: {resp.status_code}")
        exit(1)
    return resp.content, resp.headers.get('Content-Type', 'image/jpeg')


# ==============================================================================
# OneDrive 操作函数
# ==============================================================================

# ========== 确保 OneDrive 目录存在 ==========
def ensure_onedrive_folder(access_token, folder_path):
    """
    确保 OneDrive 中的文件夹路径存在。如果路径中任一级文件夹不存在，则按顺序创建。
    注意：使用 URL 编码处理路径名中的特殊字符。
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 分割路径：例如 "Pictures/Unsplash" -> ["Pictures", "Unsplash"]
    path_parts = [p for p in folder_path.split("/") if p]
    current_path = ""
    
    # 逐级检查和创建文件夹
    for part in path_parts:
        parent_path = current_path
        current_path = f"{current_path}/{part}" if current_path else part
        
        # 1. 检查是否存在
        encoded_path = urllib.parse.quote(current_path)
        check_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_path}"
        
        resp = requests.get(check_url, headers=headers, timeout=30)
        
        if resp.status_code == 200:
            continue
        elif resp.status_code == 404:
            # 2. 不存在，执行创建
            print(f"📁 创建文件夹: {current_path}")
            
            if not parent_path:
                create_url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
            else:
                encoded_parent = urllib.parse.quote(parent_path)
                create_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_parent}:/children"
            
            data = {
                "name": part,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "fail" 
            }
            
            create_resp = requests.post(create_url, headers=headers, json=data, timeout=30)
            
            if create_resp.status_code == 409:
                print(f"ℹ️  文件夹刚刚被创建: {current_path}")
            elif create_resp.status_code not in [200, 201]:
                print(f"❌ 创建文件夹失败: {create_resp.status_code} - {create_resp.text}")
                exit(1)
            else:
                print(f"✅ 文件夹创建成功")
        else:
            print(f"❌ 检查文件夹异常: {resp.status_code} - {resp.text}")
            exit(1)


# ========== 上传图片到 OneDrive ==========
def upload_to_onedrive(access_token, image_data, image_info, content_type):
    """
    将图片二进制数据上传到 OneDrive 的指定文件夹 (Pictures/Unsplash)。
    """
    # 扩展名判断
    extension = '.jpg'
    if 'png' in content_type.lower(): extension = '.png'
    elif 'webp' in content_type.lower(): extension = '.webp'
    elif 'gif' in content_type.lower(): extension = '.gif'
    
    # 文件名
    beijing_time = datetime.now(ZoneInfo("Asia/Shanghai"))
    filename = f"{beijing_time.strftime('%Y%m%d_%H%M%S')}_{image_info['id']}{extension}"
    
    # 目标路径
    target_folder = "Pictures/Unsplash"
    ensure_onedrive_folder(access_token, target_folder)
    
    # 构建完整的 OneDrive 路径并进行 URL 编码
    full_path = f"{target_folder}/{filename}"
    encoded_full_path = urllib.parse.quote(full_path)
    
    # 上传 URL (conflictBehavior=rename 即使极小概率重名也会自动重命名)
    upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_full_path}:/content?@microsoft.graph.conflictBehavior=rename" 
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream" 
    }
    
    print(f"⬆️  正在上传: {filename}")
    resp = requests.put(upload_url, headers=headers, data=image_data, timeout=120)
    
    if resp.status_code not in [200, 201]:
        print(f"❌ 上传失败: {resp.status_code}")
        print(resp.text)
        exit(1)
    
    uploaded_name = resp.json().get('name', filename)
    print(f"✅ 上传完成: {target_folder}/{uploaded_name}")


# ==============================================================================
# 主执行逻辑
# ==============================================================================

if __name__ == "__main__":
    print(f"⏰ {datetime.now(ZoneInfo('Asia/Shanghai'))} - 🚀 开始获取和上传 {IMAGE_COUNT} 张随机壁纸")
    
    # 1. 获取认证 token
    token = get_access_token()
    
    # 2. 获取随机壁纸列表
    image_list = get_unsplash_wallpapers()
    
    # 3. 遍历列表，下载并上传每张图片
    for i, img in enumerate(image_list):
        print(f"\n--- 🏞️  处理第 {i + 1} / {len(image_list)} 张图片 (ID: {img['id']}) ---")
        
        try:
            # 下载图片
            data, ctype = download_image(img["url"])
            
            # 上传到 OneDrive
            upload_to_onedrive(token, data, img, ctype)
            
        except Exception as e:
            # 捕获异常，打印错误信息，然后继续处理下一张图片
            print(f"⚠️  处理图片 {img['id']} 时发生错误，跳过该图片: {e}")
            continue
            
    print("\n🎉 任务结束")
