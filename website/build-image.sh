#!/bin/bash
# LeetGPU Website - Docker 镜像构建脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
IMAGE_NAME="leetgpu/website"
VERSION=${VERSION:-"latest"}
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 打印标题
print_header() {
    echo ""
    echo "=========================================="
    echo "  🐳 LeetGPU Docker 镜像构建"
    echo "=========================================="
    echo ""
}

# 检查环境
check_environment() {
    print_info "检查构建环境..."
    
    # 检查是否在正确的目录
    if [ ! -f "app.py" ]; then
        print_error "请在 website 目录中运行此脚本"
        exit 1
    fi
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        print_info "请访问 https://www.docker.com/get-started"
        exit 1
    fi
    
    print_success "环境检查通过"
}

# 生成元数据
generate_metadata() {
    print_info "生成题目元数据..."
    
    if [ ! -f "challenges.json" ]; then
        python3 generate_challenge_metadata.py
        if [ $? -eq 0 ]; then
            print_success "元数据生成成功"
        else
            print_warning "元数据生成失败，将在容器启动时生成"
        fi
    else
        print_success "元数据文件已存在"
    fi
}

# 选择 Dockerfile
select_dockerfile() {
    echo ""
    print_info "选择构建类型:"
    echo "  1) 开发版 (Dockerfile)"
    echo "  2) 生产版 (Dockerfile.prod - 多阶段构建，优化大小)"
    echo ""
    
    read -p "请选择 [1-2] (默认: 2): " choice
    choice=${choice:-2}
    
    case $choice in
        1)
            DOCKERFILE="Dockerfile"
            TAG_SUFFIX=""
            print_info "使用开发版 Dockerfile"
            ;;
        2)
            DOCKERFILE="Dockerfile.prod"
            TAG_SUFFIX=""
            print_info "使用生产版 Dockerfile"
            ;;
        *)
            print_error "无效的选择"
            exit 1
            ;;
    esac
}

# 设置版本标签
set_version() {
    echo ""
    print_info "当前版本: ${VERSION}"
    read -p "是否修改版本号? [y/N]: " modify_version
    
    if [[ $modify_version =~ ^[Yy]$ ]]; then
        read -p "请输入新版本号: " new_version
        if [ ! -z "$new_version" ]; then
            VERSION=$new_version
        fi
    fi
    
    print_success "版本设置为: ${VERSION}"
}

# 构建镜像
build_image() {
    echo ""
    print_info "开始构建 Docker 镜像..."
    print_info "镜像名称: ${IMAGE_NAME}:${VERSION}${TAG_SUFFIX}"
    print_info "Git Commit: ${GIT_COMMIT}"
    print_info "构建时间: ${BUILD_DATE}"
    echo ""
    
    # 构建命令
    docker build \
        -f "${DOCKERFILE}" \
        -t "${IMAGE_NAME}:${VERSION}${TAG_SUFFIX}" \
        -t "${IMAGE_NAME}:latest${TAG_SUFFIX}" \
        --build-arg BUILD_DATE="${BUILD_DATE}" \
        --build-arg GIT_COMMIT="${GIT_COMMIT}" \
        --build-arg VERSION="${VERSION}" \
        .
    
    if [ $? -eq 0 ]; then
        print_success "镜像构建成功！"
    else
        print_error "镜像构建失败"
        exit 1
    fi
}

# 显示镜像信息
show_image_info() {
    echo ""
    print_info "镜像信息:"
    docker images | grep "${IMAGE_NAME}" | head -5
    
    echo ""
    print_info "镜像详情:"
    docker inspect "${IMAGE_NAME}:${VERSION}${TAG_SUFFIX}" --format='
    大小: {{.Size}}
    创建时间: {{.Created}}
    架构: {{.Architecture}}
    OS: {{.Os}}
    ' 2>/dev/null || print_warning "无法获取镜像详情"
}

# 测试镜像
test_image() {
    echo ""
    read -p "是否测试运行镜像? [y/N]: " test_run
    
    if [[ $test_run =~ ^[Yy]$ ]]; then
        print_info "启动测试容器..."
        
        # 停止并删除旧的测试容器
        docker rm -f leetgpu-test 2>/dev/null || true
        
        # 运行测试容器
        docker run -d \
            --name leetgpu-test \
            -p 5000:5000 \
            "${IMAGE_NAME}:${VERSION}${TAG_SUFFIX}"
        
        if [ $? -eq 0 ]; then
            print_success "测试容器已启动"
            print_info "访问地址: http://localhost:5000"
            print_info "查看日志: docker logs -f leetgpu-test"
            print_info "停止容器: docker stop leetgpu-test"
            print_info "删除容器: docker rm -f leetgpu-test"
            
            # 等待容器启动
            print_info "等待容器启动..."
            sleep 5
            
            # 健康检查
            if docker ps | grep -q leetgpu-test; then
                print_success "容器运行正常"
            else
                print_error "容器启动失败"
                docker logs leetgpu-test
            fi
        else
            print_error "测试容器启动失败"
        fi
    fi
}

# 保存镜像
save_image() {
    echo ""
    read -p "是否导出镜像为 tar 文件? [y/N]: " save_tar
    
    if [[ $save_tar =~ ^[Yy]$ ]]; then
        TARFILE="leetgpu-website-${VERSION}.tar"
        print_info "导出镜像到 ${TARFILE}..."
        
        docker save "${IMAGE_NAME}:${VERSION}${TAG_SUFFIX}" | gzip > "${TARFILE}.gz"
        
        if [ $? -eq 0 ]; then
            print_success "镜像已导出到 ${TARFILE}.gz"
            print_info "文件大小: $(du -h ${TARFILE}.gz | cut -f1)"
            print_info "加载镜像: docker load < ${TARFILE}.gz"
        else
            print_error "镜像导出失败"
        fi
    fi
}

# 推送镜像提示
push_info() {
    echo ""
    print_info "推送镜像到仓库:"
    echo "  docker push ${IMAGE_NAME}:${VERSION}${TAG_SUFFIX}"
    echo "  docker push ${IMAGE_NAME}:latest${TAG_SUFFIX}"
    echo ""
    print_info "或使用 push-image.sh 脚本进行推送"
}

# 主函数
main() {
    print_header
    check_environment
    generate_metadata
    select_dockerfile
    set_version
    build_image
    show_image_info
    test_image
    save_image
    push_info
    
    echo ""
    print_success "所有操作完成！"
    echo ""
}

# 运行主函数
main
