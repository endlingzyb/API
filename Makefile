# 定义常用的参数变量
# 包含了：密码文件、ARM64架构适配、Node环境镜像、开启复用
ARGS = --secret-file my.secrets --container-architecture linux/arm64 -P ubuntu-latest=node:20-bookworm --reuse

# 目标 1: 运行所有任务 (默认直接输入 make 就会跑这个)
all: all

# 目标 2: 生成日记 (输入 make note)
note:
	act -j create_notebook $(ARGS)

# 目标 3: 下载壁纸 (输入 make down)
down:
	act -j download_and_upload $(ARGS)

# 目标 4: 清理 Docker 容器 (输入 make clean)
# 当你觉得磁盘占用太大了，可以跑一下这个
clean:
	docker rm -f $$(docker ps -a -q --filter label=act-runner)