import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo


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
    """
    从 Unsplash API 获取一张热门图片
    返回图片的下载 URL 和 ID
    """
    unsplash_access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    
    if not unsplash_access_key:
        print("❌ 未设置 UNSPLASH_ACCESS_KEY 环境变量")
        exit(1)
    
    # 获取热门图片
    url = "https://api.unsplash.com/photos/random"
    headers = {
        "Authorization": f"Client-ID {unsplash_access_key}"
    }
    params = {
        "orientation": "landscape",  # 横向图片
        "order_by": "popular"  # 按热门排序
    }
    
    print("📷 正在从 Unsplash 获取热门图片...")
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    
    if resp.status_code != 200:
        print(f"❌ 获取 Unsplash 图片失败: {resp.status_code}")
        print(resp.text)
        exit(1)
    
    try:
        data = resp.json()
    except Exception as e:
        print(f"❌ 解析 JSON 响应失败: {e}")
        exit(1)
    
    image_id = data["id"]
    download_url = data["urls"]["raw"]  # 获取原始质量图片
    photographer = data["user"]["name"]
    photo_url = data["links"]["html"]
    
    print(f"✅ 成功获取图片")
    print(f"   图片 ID: {image_id}")
    print(f"   摄影师: {photographer}")
    print(f"   链接: {photo_url}")
    
    return {
        "id": image_id,
        "url": download_url,
        "photographer": photographer,
        "photo_url": photo_url
    }


# ========== 下载图片 ==========
def download_image(image_url):
    """
    下载图片到内存
    返回图片的二进制数据和内容类型
    """
    print(f"⬇️  正在下载图片...")
    resp = requests.get(image_url, stream=True, timeout=60)
    
    if resp.status_code != 200:
        print(f"❌ 下载图片失败: {resp.status_code}")
        exit(1)
    
    image_data = resp.content
    content_type = resp.headers.get('Content-Type', 'image/jpeg')
    print(f"✅ 图片下载成功 ({len(image_data)} 字节, {content_type})")
    
    return image_data, content_type


# ========== 确保 OneDrive 目录存在 ==========
def ensure_onedrive_folder(access_token, folder_path):
    """
    确保 OneDrive 中的文件夹存在，如果不存在则创建
    folder_path: 例如 "Pictures/Unsplash"
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 分割路径并逐级创建
    path_parts = folder_path.split("/")
    current_path = ""
    
    for part in path_parts:
        parent_path = current_path if current_path else "root"
        current_path = f"{current_path}/{part}" if current_path else part
        
        # 检查文件夹是否存在
        check_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{current_path}"
        resp = requests.get(check_url, headers=headers, timeout=30)
        
        if resp.status_code == 404:
            # 文件夹不存在，创建它
            print(f"📁 创建文件夹: {current_path}")
            create_url = f"https://graph.microsoft.com/v1.0/me/drive/{parent_path}/children"
            if parent_path != "root":
                create_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{parent_path}:/children"
            
            data = {
                "name": part,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "rename"
            }
            
            create_resp = requests.post(create_url, headers=headers, json=data, timeout=30)
            
            if create_resp.status_code not in [200, 201]:
                # 如果是 409 冲突，说明文件夹可能在并发创建中已存在
                if create_resp.status_code == 409:
                    print(f"⚠️  文件夹可能已存在: {current_path}")
                else:
                    print(f"❌ 创建文件夹失败: {create_resp.status_code}")
                    print(create_resp.text)
                    exit(1)
            else:
                print(f"✅ 文件夹创建成功: {current_path}")
        elif resp.status_code == 200:
            print(f"✅ 文件夹已存在: {current_path}")
        else:
            print(f"❌ 检查文件夹失败: {resp.status_code}")
            print(resp.text)
            exit(1)


# ========== 上传图片到 OneDrive ==========
def upload_to_onedrive(access_token, image_data, image_info, content_type):
    """
    将图片上传到 OneDrive 的 Pictures/Unsplash 文件夹
    """
    # 根据 Content-Type 确定文件扩展名
    extension = '.jpg'  # 默认
    if 'png' in content_type.lower():
        extension = '.png'
    elif 'webp' in content_type.lower():
        extension = '.webp'
    elif 'gif' in content_type.lower():
        extension = '.gif'
    
    # 生成文件名：日期_图片ID.扩展名
    beijing_time = datetime.now(ZoneInfo("Asia/Shanghai"))
    filename = f"{beijing_time.strftime('%Y%m%d_%H%M%S')}_{image_info['id']}{extension}"
    
    # 确保目录存在
    ensure_onedrive_folder(access_token, "Pictures/Unsplash")
    
    # 上传图片
    upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/Pictures/Unsplash/{filename}:/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream"
    }
    
    print(f"⬆️  正在上传图片到 OneDrive: {filename}")
    resp = requests.put(upload_url, headers=headers, data=image_data, timeout=120)
    
    if resp.status_code not in [200, 201]:
        print(f"❌ 上传失败: {resp.status_code}")
        print(resp.text)
        exit(1)
    
    try:
        result = resp.json()
    except Exception as e:
        print(f"❌ 解析上传响应失败: {e}")
        exit(1)
    print(f"✅ 图片上传成功！")
    print(f"   文件名: {filename}")
    print(f"   路径: Pictures/Unsplash/{filename}")
    print(f"   大小: {result.get('size', 0)} 字节")
    print(f"   摄影师: {image_info['photographer']}")
    print(f"   Unsplash 链接: {image_info['photo_url']}")
    
    return result


# ========== 主函数 ==========
if __name__ == "__main__":
    print("🌅 开始执行 Unsplash 图片下载任务...")
    print(f"⏰ 北京时间: {datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取 Microsoft Graph access token
    access_token = get_access_token()
    
    # 从 Unsplash 获取热门图片
    image_info = get_unsplash_image()
    
    # 下载图片
    image_data, content_type = download_image(image_info["url"])
    
    # 上传到 OneDrive
    upload_to_onedrive(access_token, image_data, image_info, content_type)
    
    print("🎉 任务完成！")
