# LeetGPU 在线测试网站 - 使用指南

## 📋 项目概述

成功创建了一个功能完整的GPU编程在线测试网站，基于项目中的54道挑战题目，支持多种GPU型号选择和在线测验功能。

## ✨ 主要功能

### 1. 题库浏览
- **54道挑战题目**：涵盖简单(15题)、中等(32题)、困难(7题)三个难度级别
- **智能筛选**：支持按难度筛选和关键词搜索
- **详细信息**：每道题目包含完整的问题描述、要求和示例
- **框架支持**：显示每道题支持的编程框架(CUDA, PyTorch, Triton, Mojo等)

### 2. GPU型号支持
选择你的GPU型号，系统会显示详细的硬件信息：
- **NVIDIA**: RTX 4090, RTX 4080, RTX 3090, A100, H100, V100, T4等
- **AMD**: MI300X, MI250X, RX 7900 XTX, RX 6900 XT
- **Intel**: Data Center GPU Max 1550, Arc A770
- **Apple**: M3 Max, M2 Ultra

### 3. 随机测验
- **自定义难度**：选择全部、简单、中等或困难
- **自定义题数**：5-50题任意选择
- **实时计时**：记录答题用时
- **进度跟踪**：可视化导航，随时切换题目
- **理解度评估**：5级理解度自评系统
- **详细报告**：按难度统计，提供学习建议

### 4. 现代化界面
- **深色主题**：护眼的深色配色方案
- **响应式设计**：支持桌面和移动设备
- **流畅动画**：卡片悬停、页面切换等流畅效果
- **直观导航**：清晰的页面结构和导航

## 🚀 快速启动

### 方法一：Docker 部署（推荐生产环境）

```bash
cd website

# 方式 1: 一键部署
make deploy

# 方式 2: 使用 Docker Compose
docker-compose up -d

# 方式 3: 使用启动脚本
./docker-run.sh

# 方式 4: 手动构建和运行
./build-image.sh   # 构建镜像
docker run -d -p 5000:5000 --name leetgpu-website leetgpu/website:latest
```

**Docker 优势**:
- ✅ 环境隔离，无需安装 Python 依赖
- ✅ 一键部署，简化运维
- ✅ 跨平台支持（Linux/Mac/Windows）
- ✅ 易于扩展和迁移

详细 Docker 部署指南请查看 [DOCKER.md](website/DOCKER.md)

### 方法二：本地开发（推荐开发环境）

```bash
cd website

# 快速启动
./start.sh

# 或使用 Makefile
make quick
```

### 方法三：手动启动

```bash
# 1. 进入网站目录
cd website

# 2. 安装依赖
pip install -r requirements.txt

# 3. 生成题目元数据
python generate_challenge_metadata.py

# 4. 启动服务器
python app.py
```

### 访问网站

打开浏览器访问：`http://localhost:5000`

## 📂 项目结构

```
website/
├── app.py                          # Flask后端应用（主服务器）
├── generate_challenge_metadata.py  # 题目扫描脚本
├── challenges.json                 # 题目元数据（自动生成）
├── requirements.txt                # Python依赖
├── README.md                       # 详细文档
├── DOCKER.md                       # Docker完整部署指南
│
├── 启动脚本/
│   ├── start.sh                   # 快速启动脚本（本地）
│   ├── docker-run.sh              # Docker 快速启动
│   ├── build-image.sh             # Docker 镜像构建脚本
│   ├── push-image.sh              # Docker 镜像推送脚本
│   └── test-docker.sh             # Docker 测试脚本
│
├── Docker 配置/
│   ├── Dockerfile                 # 开发版 Dockerfile
│   ├── Dockerfile.prod            # 生产版 Dockerfile（多阶段构建）
│   ├── docker-compose.yml         # Docker Compose 配置
│   ├── .dockerignore              # Docker 忽略文件
│   ├── .env.example               # 环境变量示例
│   └── Makefile                   # 常用命令快捷方式
│
├── templates/                      # HTML模板
│   ├── index.html                 # 主页 - 题库列表
│   ├── quiz.html                  # 测验页面
│   └── challenge.html             # 题目详情页
│
└── static/                         # 静态资源
    ├── style.css                  # 主样式表（深色主题）
    ├── script.js                  # 主页交互逻辑
    └── quiz.js                    # 测验功能逻辑
```

## 🎯 使用场景

### 1. 学习GPU编程
浏览题库，从简单题目开始，逐步提升GPU编程能力。

### 2. 技能评估
使用随机测验功能，评估自己在不同难度下的掌握程度。

### 3. 面试准备
系统化学习各类GPU编程算法，包括：
- 基础操作（向量加法、矩阵乘法、转置）
- 图像处理（颜色反转、高斯模糊）
- 深度学习（ReLU、Softmax、注意力机制）
- 高级算法（FFT、K-means、排序）

### 4. 教学辅助
教师可用于：
- 课程作业布置
- 学生水平测试
- 进度跟踪

## 🔧 API接口

网站提供RESTful API，方便扩展：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/challenges` | GET | 获取题目列表（支持筛选） |
| `/api/challenge/<id>` | GET | 获取题目详情 |
| `/api/quiz/generate` | GET | 生成随机测验 |
| `/api/stats` | GET | 获取统计信息 |
| `/api/gpu-models` | GET | 获取GPU型号列表 |

### 示例：获取简单难度题目
```bash
curl "http://localhost:5000/api/challenges?difficulty=easy"
```

### 示例：搜索题目
```bash
curl "http://localhost:5000/api/challenges?search=matrix"
```

## 🎨 界面展示

### 主页
- 统计卡片：显示总题数和各难度题目数量
- GPU选择器：选择你的GPU型号
- 搜索和筛选：快速找到目标题目
- 题目网格：卡片式展示所有题目

### 测验页面
- 测验设置：选择难度和题目数量
- 题目展示：完整的题目内容
- 理解度评估：5级自评系统
- 进度导航：可视化进度和快速跳转
- 结果报告：详细的统计和学习建议

### 题目详情
- 题目描述：完整的问题说明
- 示例和约束：帮助理解题目要求
- 支持的框架：查看可用的编程框架

## 🛠️ 技术栈

- **后端**: Python 3.x + Flask 3.0
- **前端**: HTML5 + CSS3 + Vanilla JavaScript
- **数据格式**: JSON
- **设计**: 响应式 + 深色主题

## 📊 题目分类

### 简单题目 (15题)
- Vector Addition, Matrix Multiplication, Matrix Transpose
- Matrix Copy, Reverse Array, Color Inversion
- ReLU, Leaky ReLU, SiLU, SwiGLU
- 1D Convolution, Count Array Element等

### 中等题目 (32题)
- 2D Convolution, GEMM, Reduction, Softmax
- Batch Normalization, 2D Max Pooling
- Prefix Sum, Dot Product, Radix Sort
- K-Means Clustering等

### 困难题目 (7题)
- 3D Convolution, Multi-Head Attention
- Fast Fourier Transform, Linear Attention
- Causal Self-Attention, Multi-Agent Simulation

## 🔐 许可证

本项目基于LeetGPU题库构建，遵循 CC BY-NC-ND 4.0 许可证。
© 2025 AlphaGPU, LLC

## 📞 支持

如有问题或建议，请访问：
- 官网：https://leetgpu.com
- GitHub：查看 CONTRIBUTING.md

## 🎉 开始使用

现在你可以：
1. 运行 `cd website && ./start.sh` 启动网站
2. 在浏览器中访问 `http://localhost:5000`
3. 选择你的GPU型号
4. 开始浏览题目或进行测验！

祝你学习愉快！🚀
