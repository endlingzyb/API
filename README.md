# Microsoft 365 E5 自动续期 & Unsplash 壁纸同步

通过 GitHub Action 实现自动化调用 Microsoft Graph API 以保持 E5 开发者账户活跃，并集成 Unsplash 图片自动同步功能。

[官网 SDK 文档](https://docs.microsoft.com/zh-cn/graph/sdks/sdk-installation?view=graph-rest-1.0) | [Microsoft 365 开发人员计划](https://developer.microsoft.com/zh-cn/microsoft-365/dev-program)

-----

## 📋 前提条件

  * **已加入 Microsoft 365 开发人员计划**：[点击前往](https://developer.microsoft.com/zh-cn/microsoft-365/dev-program)

> **⚠️ 关于账号安全的建议**
>
> 由于需要储存密码，如果担心默认管理员账号安全性，建议新建一个**专用于设置自动续期的账户（小号）**。
>
> 1.  该小号需先设置为**全局管理员**以方便后续操作（直到完成所有“配置步骤”）。
> 2.  完成配置并测试运行成功后，可以在 E5-Office 控制面板取消该账号的全局管理员权限，自动续订脚本依然能正常运行。

-----

## 🛠️ 配置步骤

### 1\. 注册 Azure 应用

1.  登录到 **[Microsoft Azure Portal](https://portal.azure.com/)**。

2.  **注册新应用**并**新建客户端密码**。请参考下方截图操作。

      * **注意**：在此过程中，请务必记录下生成的 **`1` (Client ID)**、**`2` (Client Secret)** 和 **`3` (Tenant ID)**，后续步骤需要用到。

    ![image-20201220181608269](md_img/image-20201220181608269.png)
    
![image-20201220181906371](md_img/image-20201220181906371.png)
    
![image-20201220182210469](md_img/image-20201220182210469.png)
    
![image-20201220182857805](md_img/image-20201220182857805.png)
    
![image-20201220183358551](md_img/image-20201220183358551.png)
    
![image-20201220183519522](md_img/image-20201220183519522.png)
    
![image-20201220183623883](md_img/image-20201220183623883.png)
    
![image-20201220183801992](md_img/image-20201220183801992.png)
### 2\. 获取 GRAPH\_REFRESH\_TOKEN

为了支持无人值守运行，需要获取 Refresh Token。

#### 2.1 配置重定向 URI 和权限

1.  在应用的「**身份验证 (Authentication)**」页面，添加平台：
      * **类型**：Web
      * **重定向 URI**：`http://localhost`
      * **注意**：如果需要用户交互，请确保勾选“允许公共客户端流 (allow public client flows)”。
2.  在「**API 权限 (API Permissions)**」页面，添加权限：
      * `User.Read`
      * `offline_access` (**必须添加**，否则不会返回 refresh\_token)

#### 2.2 获取授权码 (Code)

在浏览器中构造并访问以下 URL（请替换 `{tenant_id}` 和 `{client_id}`）：

```text
https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?client_id={client_id}&response_type=code&redirect_uri=http://localhost&response_mode=query&scope=offline_access%20User.Read&state=12345
```

**参数说明：**

  * `client_id`: 你的应用注册里的应用程序(客户端) ID
  * `tenant_id`: 你的 Azure AD 目录(租户) ID
  * `redirect_uri`: 必须和应用注册里配置的一致 (例如 `http://localhost`)
  * `scope`: 必须包含 `offline_access` 才会返回 refresh\_token
  * `response_type=code`: 表示请求授权码

#### 2.3 登录并同意授权

1.  访问上述 URL 后，系统会跳转到微软登录页。
2.  输入账号密码，完成验证。如果是第一次登录，会弹出“同意授权”页面，点击**同意**。

#### 2.4 提取 Code

登录完成后，浏览器会跳转到类似以下的网址（显示无法访问是正常的）：

```text
http://localhost/?code=0.AAAA...snip...AA&state=12345&session_state=abcd-efgh
```

  * 复制 `code=` 之后的内容（即 `0.AAAA...` 这一长串）。
  * **注意**：此 Code 有效期极短，请尽快用于后续 Token 兑换（或填入 Secrets 供脚本第一次运行使用，具体视脚本逻辑而定）。

### 3\. 配置 GitHub Secrets

进入 GitHub 仓库的 `Settings` -\> `Secrets and variables` -\> `Actions`，添加以下 Secrets：

| Name | Value 说明 | 对应之前记录的编号 |
| :--- | :--- | :---: |
| **CLIENT\_ID** | 应用程序(客户端) ID | No. 1 |
| **CLIENT\_SECRET** | 证书和密码中的"客户端密码" | No. 2 |
| **TENANT\_ID** | 目录(租户) ID | No. 3 |
| **GRAPH\_REFRESH\_TOKEN** | 身份验证 Token (或上一步获取的 Code) | No. 4 |

> **⚠️ 权限设置提醒**
>
> 1.  确保 Secrets 添加正确，如上图所示：


### 4\. 启动运行

最后，你需要手动 **Star** 一下本仓库才会触发首次运行。

  * **测试方法**：Star 本仓库 -\> 取消 Star -\> 再次 Star（点两次）。

-----

## 🖼️ 附加功能：Unsplash 图片自动下载

### 功能说明

此功能会在每天 **北京时间早晨 10:06** 自动从 Unsplash API 获取一张热门图片，并上传到 OneDrive 的 `Pictures\Unsplash` 目录下。

### 配置步骤

#### 1\. 获取 Unsplash Access Key

1.  访问 [Unsplash Developers](https://unsplash.com/developers) 并注册账号。
2.  创建一个新的应用（Application）。
3.  复制生成的 **Access Key**。

#### 2\. 添加 GitHub Secret

在仓库的 `Settings` -\> `Secrets and variables` -\> `Actions` 中追加以下 Secret：

| Name | Value | 说明 |
| :--- | :--- | :--- |
| **UNSPLASH\_ACCESS\_KEY** | 你的 Unsplash Access Key | 用于访问 Unsplash API |

#### 3\. 工作流详情

  * **配置文件**：`.github/workflows/unsplash_to_onedrive.yml`
  * **执行时间**：每天北京时间 10:06 (UTC 02:06)
  * **脚本文件**：`unsplash_to_onedrive.py`
  * **保存路径**：OneDrive `/Pictures/Unsplash/`
  * **命名格式**：`YYYYMMDD_HHMMSS_图片ID.jpg`

#### 4\. 手动触发

配置完成后，你可以在 GitHub Actions 页面选中 `unsplash_to_onedrive` 工作流并手动触发以进行测试。

-----

## 🔗 参考链接

  * [GitHub Action YML 文件配置参考](https://github.com/moreant/auto-checkin-biliob)
  * [Microsoft Graph SDK - 邮件 API](https://docs.microsoft.com/zh-cn/graph/api/user-list-messages?view=graph-rest-1.0&tabs=http)
  * [Unsplash API 文档](https://unsplash.com/documentation)
