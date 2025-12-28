#!/bin/bash
# LeetGPU - 显示 Docker 镜像详细信息

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "=========================================="
echo "  🐳 LeetGPU Docker 镜像信息"
echo "=========================================="
echo ""

# 检查是否有 leetgpu 镜像
if ! docker images | grep -q "leetgpu"; then
    echo -e "${YELLOW}⚠️  未找到 LeetGPU 镜像${NC}"
    echo ""
    echo "请先构建镜像："
    echo "  ./build-image.sh"
    echo "  或"
    echo "  make build-prod"
    exit 1
fi

# 显示镜像列表
echo -e "${BLUE}📋 镜像列表:${NC}"
echo ""
docker images | head -1
docker images | grep leetgpu
echo ""

# 选择镜像查看详情
IMAGE_TAG=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep leetgpu | head -1)

if [ -z "$IMAGE_TAG" ]; then
    echo "未找到镜像"
    exit 1
fi

echo -e "${BLUE}📊 镜像详细信息: ${GREEN}${IMAGE_TAG}${NC}"
echo ""

# 基本信息
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 基本信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker inspect ${IMAGE_TAG} --format='
镜像 ID:        {{.Id}}
创建时间:       {{.Created}}
大小:           {{.Size}} bytes (~'$(docker images ${IMAGE_TAG} --format "{{.Size}}")')
架构:           {{.Architecture}}
操作系统:       {{.Os}}
'

# 层信息
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 镜像层信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker history ${IMAGE_TAG} --no-trunc --format "table {{.CreatedBy}}\t{{.Size}}" | head -10

# 配置信息
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  配置信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker inspect ${IMAGE_TAG} --format='
工作目录:       {{.Config.WorkingDir}}
暴露端口:       {{range $key, $value := .Config.ExposedPorts}}{{$key}} {{end}}
入口点:         {{.Config.Entrypoint}}
命令:           {{.Config.Cmd}}
用户:           {{.Config.User}}
'

# 环境变量
echo "环境变量:"
docker inspect ${IMAGE_TAG} --format='{{range .Config.Env}}  - {{.}}
{{end}}'

# 标签
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏷️  标签信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
LABELS=$(docker inspect ${IMAGE_TAG} --format='{{range $key, $value := .Config.Labels}}{{$key}}={{$value}}
{{end}}')

if [ -z "$LABELS" ]; then
    echo "  (无标签)"
else
    echo "$LABELS" | sed 's/^/  /'
fi

# 健康检查
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💊 健康检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
HEALTHCHECK=$(docker inspect ${IMAGE_TAG} --format='{{.Config.Healthcheck}}')
if [ "$HEALTHCHECK" == "<nil>" ] || [ -z "$HEALTHCHECK" ]; then
    echo "  未配置健康检查"
else
    docker inspect ${IMAGE_TAG} --format='
测试命令:       {{.Config.Healthcheck.Test}}
检查间隔:       {{.Config.Healthcheck.Interval}}
超时时间:       {{.Config.Healthcheck.Timeout}}
重试次数:       {{.Config.Healthcheck.Retries}}
启动等待:       {{.Config.Healthcheck.StartPeriod}}
'
fi

# 使用建议
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 使用示例"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# 运行容器"
echo "docker run -d -p 5000:5000 --name leetgpu-website ${IMAGE_TAG}"
echo ""
echo "# 查看日志"
echo "docker logs -f leetgpu-website"
echo ""
echo "# 进入容器"
echo "docker exec -it leetgpu-website /bin/bash"
echo ""
echo "# 停止容器"
echo "docker stop leetgpu-website"
echo ""
echo "# 删除容器"
echo "docker rm leetgpu-website"
echo ""

# 大小对比
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📏 镜像大小对比"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "基础镜像 (python:3.11-slim):  ~130MB"
echo "LeetGPU 镜像:                 ~$(docker images ${IMAGE_TAG} --format "{{.Size}}")"
echo ""

# 推送信息
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 推送镜像"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "使用推送脚本（推荐）:"
echo "  ./push-image.sh"
echo ""
echo "手动推送到 Docker Hub:"
echo "  docker login"
echo "  docker tag ${IMAGE_TAG} username/leetgpu-website:latest"
echo "  docker push username/leetgpu-website:latest"
echo ""

echo "=========================================="
echo ""
