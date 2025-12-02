import os
import requests
from datetime import datetime
import urllib.parse  # 新增：用于 URL 编码
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# ========== 获取 access_token ==========
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

    resp = requests.post(token_url, data=data, timeout=30)
    if resp.status_code != 200:
        print("❌ 获取 access_token 失败")
        print(resp.text)
        exit(1)

    return resp.json()["access_token"]


# ========== 从 Unsplash 获取热门图片 ==========
def get_unsplash_image():
    unsplash_access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not unsplash_access_key:
        print("❌ 未设置 UNSPLASH_ACCESS_KEY")
        exit(1)
    
    url = "https://api.unsplash.com/photos/random"
    headers = {"Authorization": f"Client-ID {unsplash_access_key}"}
    params = {"orientation": "landscape", "order_by": "popular"}
    
    print("📷 正在从 Unsplash 获取热门图片...")
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    
    if resp.status_code != 200:
        print(f"❌ 获取 Unsplash 图片失败: {resp.status_code}")
        exit(1)
    
    data = resp.json()
    return {
        "id": data["id"],
        "url": data["urls"]["raw"],
        "photographer": data["user"]["name"],
        "photo_url": data["links"]["html"]
    }


# ========== 下载图片 ==========
def download_image(image_url):
    print(f"⬇️  正在下载图片...")
    resp = requests.get(image_url, stream=True, timeout=60)
    if resp.status_code != 200:
        print(f"❌ 下载图片失败: {resp.status_code}")
        exit(1)
    return resp.content, resp.headers.get('Content-Type', 'image/jpeg')


# ========== 确保 OneDrive 目录存在 (修正版) ==========
def ensure_onedrive_folder(access_token, folder_path):
    """
    确保 OneDrive 中的文件夹存在，如果不存在则创建
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 分割路径
    path_parts = [p for p in folder_path.split("/") if p] # 过滤空字符串
    current_path = ""
    
    for part in path_parts:
        # 逻辑：parent_path 用于构建创建 API，current_path 用于构建检查 API
        parent_path = current_path
        current_path = f"{current_path}/{part}" if current_path else part
        
        # 1. 检查是否存在 (URL Encode)
        encoded_path = urllib.parse.quote(current_path)
        check_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_path}"
        
        resp = requests.get(check_url, headers=headers, timeout=30)
        
        if resp.status_code == 200:
            # 已存在，跳过
            continue
        elif resp.status_code == 404:
            # 2. 不存在，执行创建
            print(f"📁 创建文件夹: {current_path}")
            
            # 构建 Parent URL
            if not parent_path:
                # 在根目录创建
                create_url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
            else:
                # 在子目录创建 (注意 parent_path 也要 encode)
                encoded_parent = urllib.parse.quote(parent_path)
                create_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_parent}:/children"
            
            # 使用 'fail' 避免竞态条件产生重名文件夹 (Unsplash 1)
            data = {
                "name": part,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "fail" 
            }
            
            create_resp = requests.post(create_url, headers=headers, json=data, timeout=30)
            
            if create_resp.status_code == 409:
                print(f"ℹ️  文件夹刚刚被创建 (并发): {current_path}")
            elif create_resp.status_code not in [200, 201]:
                print(f"❌ 创建文件夹失败: {create_resp.status_code} - {create_resp.text}")
                exit(1)
            else:
                print(f"✅ 文件夹创建成功")
        else:
            print(f"❌ 检查文件夹异常: {resp.status_code} - {resp.text}")
            exit(1)


# ========== 上传图片到 OneDrive (修正版) ==========
def upload_to_onedrive(access_token, image_data, image_info, content_type):
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
    
    # 构建上传 URL (注意 Encode)
    full_path = f"{target_folder}/{filename}"
    encoded_full_path = urllib.parse.quote(full_path)
    upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_full_path}:/content"
    
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
    
    print(f"✅ 上传完成: {full_path}")


if __name__ == "__main__":
    print(f"⏰ {datetime.now(ZoneInfo('Asia/Shanghai'))}")
    token = get_access_token()
    img = get_unsplash_image()
    data, ctype = download_image(img["url"])
    upload_to_onedrive(token, data, img, ctype)
    print("🎉 任务结束")
