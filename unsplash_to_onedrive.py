import os
import requests
from datetime import datetime
import urllib.parse  # 用于 URL 编码
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# ==============================================================================
# 全局常量定义
# ==============================================================================

# 每次获取的图片数量 (每种方向 3 张)
IMAGE_COUNT_PER_ORIENTATION = 3

# 目标分辨率定义 (2K)
RES_LANDSCAPE = "2560x1440" # 横版 2K (宽x高)
RES_PORTRAIT = "1440x2560"  # 竖版 2K (宽x高)

# 目标文件夹路径
BASE_FOLDER = "Pictures/Unsplash"
LANDSCAPE_FOLDER = f"{BASE_FOLDER}/Landscape"
PORTRAIT_FOLDER = f"{BASE_FOLDER}/Portrait"


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
# Unsplash 数据获取函数
# ==============================================================================

# ========== 从 Unsplash 获取指定方向和分辨率的壁纸 ==========
def get_unsplash_wallpapers_by_orientation(orientation, count):
    """
    从 Unsplash API 获取指定数量、方向和分辨率的壁纸。
    :param orientation: "landscape" (横版) 或 "portrait" (竖版)。
    :param count: 获取图片的数量。
    :return: 包含图片信息（含动态分辨率 URL）的列表。
    """
    unsplash_access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not unsplash_access_key:
        print("❌ 未设置 UNSPLASH_ACCESS_KEY")
        exit(1)
    
    # 确定分辨率
    res_str = RES_LANDSCAPE if orientation == "landscape" else RES_PORTRAIT
    width, height = res_str.split('x')
    
    url = "https://api.unsplash.com/photos"
    headers = {"Authorization": f"Client-ID {unsplash_access_key}"}
    
    # API 参数设置：
    params = {
        "per_page": count,        # 每次获取数量
        "order_by": "popular",    # 按热门排序
        "query": "wallpaper",     # 搜索关键词：壁纸
        "orientation": orientation # 明确指定方向 (landscape 或 portrait)
    }
    
    print(f"📷 正在从 Unsplash 获取 {count} 张热门{orientation}壁纸 (目标分辨率: {res_str})...")
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    
    if resp.status_code != 200:
        print(f"❌ 获取 Unsplash 图片失败: {resp.status_code}")
        print(resp.text)
        exit(1)
    
    data_list = resp.json()
    image_list = []
    
    for data in data_list:
        # 获取图片的基础 URL (使用 raw 尺寸，以方便动态修改参数)
        base_url = data["urls"]["raw"]
        
        # 动态调整 URL 以获取指定 2K 分辨率的图片
        # 拼接 w, h 和 fit=crop 参数确保图片尺寸精确到 2K
        # 注意：base_url 通常已有参数，所以用 & 连接
        dynamic_url = f"{base_url}&w={width}&h={height}&fit=crop"
        
        image_list.append({
            "id": data["id"],
            "url": dynamic_url, # 使用动态分辨率 URL
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
    该函数能处理多级目录 (如 Pictures/Unsplash/Landscape)。
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 分割路径：例如 "Pictures/Unsplash/Landscape" -> ["Pictures", "Unsplash", "Landscape"]
    path_parts = [p for p in folder_path.split("/") if p]
    current_path = ""
    
    for part in path_parts:
        parent_path = current_path
        current_path = f"{current_path}/{part}" if current_path else part
        
        # 1. 检查是否存在
        encoded_path = urllib.parse.quote(current_path)
        check_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{encoded_path}"
        
        resp = requests.get(check_url, headers=headers, timeout=30)
        
        if resp.status_code == 200:
            # 文件夹已存在
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
                print(f"ℹ️  文件夹刚刚被创建 (并发或竞态条件): {current_path}")
            elif create_resp.status_code not in [200, 201]:
                print(f"❌ 创建文件夹失败: {create_resp.status_code} - {create_resp.text}")
                exit(1)
            else:
                print(f"✅ 文件夹创建成功")
        else:
            print(f"❌ 检查文件夹异常: {resp.status_code} - {resp.text}")
            exit(1)


# ========== 上传图片到 OneDrive ==========
def upload_to_onedrive(access_token, image_data, image_info, content_type, target_folder):
    """
    将图片二进制数据上传到 OneDrive 的指定文件夹。
    :param target_folder: 上传的目标文件夹路径，例如 "Pictures/Unsplash/Landscape"。
    """
    # 扩展名判断
    extension = '.jpg'
    if 'png' in content_type.lower(): extension = '.png'
    elif 'webp' in content_type.lower(): extension = '.webp'
    elif 'gif' in content_type.lower(): extension = '.gif'
    
    # 文件名
    beijing_time = datetime.now(ZoneInfo("Asia/Shanghai"))
    filename = f"{beijing_time.strftime('%Y%m%d_%H%M%S')}_{image_info['id']}{extension}"
    
    # 确保目标路径存在
    ensure_onedrive_folder(access_token, target_folder)
    
    # 构建完整的 OneDrive 路径并进行 URL 编码
    full_path = f"{target_folder}/{filename}"
    encoded_full_path = urllib.parse.quote(full_path)
    
    # 上传 URL (使用 @microsoft.graph.conflictBehavior=rename 避免文件名冲突)
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
    
    total_files = IMAGE_COUNT_PER_ORIENTATION * 2
    print(f"⏰ {datetime.now(ZoneInfo('Asia/Shanghai'))} - 🚀 开始获取和上传共 {total_files} 张 2K 壁纸")
    
    # 1. 获取认证 token
    token = get_access_token()
    
    # 2. 定义任务列表 
    # (修正：使用正确的常量 IMAGE_COUNT_PER_ORIENTATION)
    tasks = [
        ("landscape", IMAGE_COUNT_PER_ORIENTATION, LANDSCAPE_FOLDER),
        ("portrait", IMAGE_COUNT_PER_ORIENTATION, PORTRAIT_FOLDER),
    ]
    
    total_processed = 0
    
    for orientation, count, target_folder in tasks:
        
        print(f"\n--- 🔄 开始处理 {orientation} ({count} 张) ---")
        
        # 2a. 获取壁纸列表
        image_list = get_unsplash_wallpapers_by_orientation(orientation, count)
        
        # 2b. 遍历列表，下载并上传每张图片
        for i, img in enumerate(image_list):
            total_processed += 1
            print(f"\n--- 🏞️  处理第 {total_processed} / {total_files} 张图片 (ID: {img['id']}) ---")
            
            try:
                # 下载图片
                data, ctype = download_image(img["url"])
                
                # 上传到 OneDrive，指定子文件夹
                upload_to_onedrive(token, data, img, ctype, target_folder)
                
            except Exception as e:
                # 捕获异常，打印错误信息，然后继续处理下一张图片
                print(f"⚠️  处理图片 {img['id']} 时发生错误，跳过该图片: {e}")
                continue
            
    print("\n🎉 任务结束")
