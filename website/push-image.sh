#!/bin/bash
# LeetGPU Website - Docker 镜像推送脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
IMAGE_NAME="leetgpu/website"
VERSION=${VERSION:-"latest"}

# 打印函数
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

print_header() {
    echo ""
    echo "=========================================="
    echo "  📤 LeetGPU Docker 镜像推送"
    echo "=========================================="
    echo ""
}

# 检查镜像是否存在
check_image() {
    print_info "检查本地镜像..."
    
    if docker images | grep -q "${IMAGE_NAME}"; then
        print_success "找到本地镜像"
        echo ""
        docker images | grep "${IMAGE_NAME}"
    else
        print_error "未找到镜像 ${IMAGE_NAME}"
        print_info "请先运行 build-image.sh 构建镜像"
        exit 1
    fi
}

# 选择仓库
select_registry() {
    echo ""
    print_info "选择推送的仓库:"
    echo "  1) Docker Hub (docker.io)"
    echo "  2) 阿里云容器镜像服务 (registry.cn-hangzhou.aliyuncs.com)"
    echo "  3) 腾讯云容器镜像服务 (ccr.ccs.tencentyun.com)"
    echo "  4) 华为云容器镜像服务 (swr.cn-north-4.myhuaweicloud.com)"
    echo "  5) GitHub Container Registry (ghcr.io)"
    echo "  6) 自定义仓库"
    echo ""
    
    read -p "请选择 [1-6] (默认: 1): " choice
    choice=${choice:-1}
    
    case $choice in
        1)
            REGISTRY=""
            REGISTRY_NAME="Docker Hub"
            ;;
        2)
            read -p "请输入阿里云命名空间: " namespace
            REGISTRY="registry.cn-hangzhou.aliyuncs.com/${namespace}"
            REGISTRY_NAME="阿里云"
            ;;
        3)
            read -p "请输入腾讯云命名空间: " namespace
            REGISTRY="ccr.ccs.tencentyun.com/${namespace}"
            REGISTRY_NAME="腾讯云"
            ;;
        4)
            read -p "请输入华为云组织名: " org
            REGISTRY="swr.cn-north-4.myhuaweicloud.com/${org}"
            REGISTRY_NAME="华为云"
            ;;
        5)
            read -p "请输入 GitHub 用户名/组织: " username
            REGISTRY="ghcr.io/${username}"
            REGISTRY_NAME="GitHub"
            ;;
        6)
            read -p "请输入仓库地址: " custom_registry
            REGISTRY="${custom_registry}"
            REGISTRY_NAME="自定义仓库"
            ;;
        *)
            print_error "无效的选择"
            exit 1
            ;;
    esac
    
    if [ ! -z "$REGISTRY" ]; then
        FULL_IMAGE_NAME="${REGISTRY}/website"
    else
        FULL_IMAGE_NAME="${IMAGE_NAME}"
    fi
    
    print_success "目标仓库: ${REGISTRY_NAME}"
    print_info "完整镜像名: ${FULL_IMAGE_NAME}"
}

# 登录仓库
login_registry() {
    echo ""
    read -p "是否需要登录仓库? [Y/n]: " need_login
    need_login=${need_login:-Y}
    
    if [[ $need_login =~ ^[Yy]$ ]]; then
        print_info "登录到 ${REGISTRY_NAME}..."
        
        if [ -z "$REGISTRY" ]; then
            docker login
        else
            docker login ${REGISTRY%%/*}
        fi
        
        if [ $? -eq 0 ]; then
            print_success "登录成功"
        else
            print_error "登录失败"
            exit 1
        fi
    fi
}

# 标记镜像
tag_image() {
    echo ""
    print_info "标记镜像..."
    
    # 获取所有需要推送的版本
    read -p "请输入要推送的版本 (用空格分隔，默认: latest): " versions
    versions=${versions:-"latest"}
    
    for ver in $versions; do
        print_info "标记: ${IMAGE_NAME}:${ver} -> ${FULL_IMAGE_NAME}:${ver}"
        docker tag "${IMAGE_NAME}:${ver}" "${FULL_IMAGE_NAME}:${ver}"
        
        if [ $? -eq 0 ]; then
            print_success "标记成功: ${ver}"
        else
            print_error "标记失败: ${ver}"
        fi
    done
}

# 推送镜像
push_image() {
    echo ""
    print_info "开始推送镜像..."
    
    for ver in $versions; do
        echo ""
        print_info "推送: ${FULL_IMAGE_NAME}:${ver}"
        
        docker push "${FULL_IMAGE_NAME}:${ver}"
        
        if [ $? -eq 0 ]; then
            print_success "推送成功: ${ver}"
        else
            print_error "推送失败: ${ver}"
            exit 1
        fi
    done
}

# 显示拉取命令
show_pull_command() {
    echo ""
    print_success "所有镜像推送成功！"
    echo ""
    print_info "拉取镜像命令:"
    for ver in $versions; do
        echo "  docker pull ${FULL_IMAGE_NAME}:${ver}"
    done
    echo ""
    print_info "运行容器:"
    echo "  docker run -d -p 5000:5000 ${FULL_IMAGE_NAME}:latest"
    echo ""
}

# 多架构构建（可选）
multi_arch_build() {
    echo ""
    read -p "是否构建多架构镜像 (amd64/arm64)? [y/N]: " multi_arch
    
    if [[ $multi_arch =~ ^[Yy]$ ]]; then
        print_info "构建多架构镜像..."
        print_warning "需要 Docker Buildx 支持"
        
        # 检查 buildx
        if ! docker buildx version &> /dev/null; then
            print_error "Docker Buildx 未安装"
            return
        fi
        
        # 创建 builder
        docker buildx create --name leetgpu-builder --use 2>/dev/null || docker buildx use leetgpu-builder
        
        # 构建并推送
        docker buildx build \
            --platform linux/amd64,linux/arm64 \
            -f Dockerfile.prod \
            -t "${FULL_IMAGE_NAME}:latest" \
            -t "${FULL_IMAGE_NAME}:${VERSION}" \
            --push \
            .
        
        if [ $? -eq 0 ]; then
            print_success "多架构镜像构建并推送成功"
        else
            print_error "多架构镜像构建失败"
        fi
    fi
}

# 主函数
main() {
    print_header
    check_image
    select_registry
    login_registry
    tag_image
    push_image
    show_pull_command
    multi_arch_build
    
    echo ""
    print_success "推送操作完成！"
    echo ""
}

# 运行主函数
main
