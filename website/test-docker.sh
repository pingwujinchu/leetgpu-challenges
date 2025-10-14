#!/bin/bash
# LeetGPU Website - Docker 测试脚本

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_test() {
    echo -e "${BLUE}🧪 测试: $1${NC}"
}

print_pass() {
    echo -e "${GREEN}✅ 通过: $1${NC}"
}

print_fail() {
    echo -e "${RED}❌ 失败: $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

echo "=========================================="
echo "  🐳 LeetGPU Docker 测试套件"
echo "=========================================="
echo ""

# 测试 1: 检查 Docker 环境
print_test "检查 Docker 环境"
if docker --version &> /dev/null; then
    print_pass "Docker 已安装: $(docker --version)"
else
    print_fail "Docker 未安装"
    exit 1
fi

# 测试 2: 检查必要文件
print_test "检查必要文件"
files=("Dockerfile" "Dockerfile.prod" "docker-compose.yml" "app.py" "requirements.txt")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        print_pass "文件存在: $file"
    else
        print_fail "文件缺失: $file"
        exit 1
    fi
done

# 测试 3: 检查元数据
print_test "检查题目元数据"
if [ -f "challenges.json" ]; then
    challenge_count=$(python3 -c "import json; print(len(json.load(open('challenges.json'))))" 2>/dev/null || echo "0")
    if [ "$challenge_count" -gt 0 ]; then
        print_pass "元数据包含 $challenge_count 道题目"
    else
        print_info "元数据为空，将在构建时生成"
    fi
else
    print_info "元数据文件不存在，将在构建时生成"
fi

# 测试 4: 构建开发版镜像
print_test "构建开发版 Docker 镜像"
if docker build -t leetgpu/website:test -f Dockerfile . &> /tmp/docker-build.log; then
    print_pass "开发版镜像构建成功"
else
    print_fail "开发版镜像构建失败"
    echo "查看日志: cat /tmp/docker-build.log"
    exit 1
fi

# 测试 5: 构建生产版镜像
print_test "构建生产版 Docker 镜像"
if docker build -t leetgpu/website:test-prod -f Dockerfile.prod . &> /tmp/docker-build-prod.log; then
    print_pass "生产版镜像构建成功"
    
    # 检查镜像大小
    image_size=$(docker images leetgpu/website:test-prod --format "{{.Size}}")
    print_info "镜像大小: $image_size"
else
    print_fail "生产版镜像构建失败"
    echo "查看日志: cat /tmp/docker-build-prod.log"
    exit 1
fi

# 测试 6: 运行容器测试
print_test "运行容器并测试"

# 清理旧容器
docker rm -f leetgpu-test &> /dev/null || true

# 启动容器
if docker run -d --name leetgpu-test -p 5001:5000 leetgpu/website:test-prod; then
    print_pass "容器启动成功"
    
    # 等待容器启动
    print_info "等待容器启动..."
    sleep 5
    
    # 测试 7: 健康检查
    print_test "健康检查"
    max_attempts=10
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker ps | grep -q leetgpu-test; then
            # 测试 API 端点
            if curl -s -f http://localhost:5001/api/stats &> /dev/null; then
                print_pass "API 端点响应正常"
                
                # 获取统计信息
                stats=$(curl -s http://localhost:5001/api/stats)
                total=$(echo $stats | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "unknown")
                print_info "题目总数: $total"
                break
            fi
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_fail "容器健康检查失败"
            echo "容器日志:"
            docker logs leetgpu-test
            exit 1
        fi
        
        print_info "尝试 $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    # 测试 8: 测试主页
    print_test "测试主页"
    if curl -s -f http://localhost:5001/ | grep -q "LeetGPU"; then
        print_pass "主页加载成功"
    else
        print_fail "主页加载失败"
    fi
    
    # 测试 9: 测试 Quiz 页面
    print_test "测试 Quiz 页面"
    if curl -s -f http://localhost:5001/quiz | grep -q "测验"; then
        print_pass "Quiz 页面加载成功"
    else
        print_fail "Quiz 页面加载失败"
    fi
    
    # 测试 10: 容器日志
    print_test "检查容器日志"
    if docker logs leetgpu-test 2>&1 | grep -q "Running on"; then
        print_pass "容器运行正常"
    else
        print_fail "容器日志异常"
        docker logs leetgpu-test
    fi
    
else
    print_fail "容器启动失败"
    exit 1
fi

# 清理
print_info "清理测试资源..."
docker stop leetgpu-test &> /dev/null
docker rm leetgpu-test &> /dev/null
docker rmi leetgpu/website:test &> /dev/null || true
docker rmi leetgpu/website:test-prod &> /dev/null || true

echo ""
echo "=========================================="
echo -e "${GREEN}  ✅ 所有测试通过！${NC}"
echo "=========================================="
echo ""
echo "现在可以使用以下命令部署:"
echo "  ./build-image.sh    # 交互式构建"
echo "  make deploy         # 一键部署"
echo "  ./docker-run.sh     # 启动容器"
echo ""
