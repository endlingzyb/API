# 纯净版配置：只保留密钥文件和复用参数
# 不指定架构，不指定镜像，完全交给 act 自动处理
ARGS = --secret-file my.secrets

# 目标 1: 运行所有任务
all: note down

# 目标 2: 生成日记
note:
	act -j create_notebook $(ARGS)

# 目标 2: 生成sharepoint页面
page:
	act -j create_sharepoint $(ARGS)

# 目标 3: 下载壁纸
down:
	act -j download_and_upload $(ARGS)

# 目标 4: 清理容器
clean:
	docker rm -f $$(docker ps -a -q --filter label=act-runner)