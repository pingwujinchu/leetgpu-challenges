# LeetGPU 在线测试网站

一个支持多种GPU型号的GPU编程在线测试平台，基于LeetGPU挑战题库构建。

## 🌟 功能特点

- **多种GPU型号支持**: 支持NVIDIA、AMD、Intel、Apple等主流GPU厂商
- **难度分级**: 简单、中等、困难三个难度等级，共54道挑战题目
- **随机测验**: 可根据难度和题目数量生成个性化测验
- **实时筛选**: 支持按难度、关键词搜索题目
- **现代化UI**: 响应式设计，深色主题，流畅的用户体验
- **多框架支持**: CUDA、PyTorch、Triton、Mojo等多种GPU编程框架

## 📊 题目统计

- **简单**: 15题
- **中等**: 32题
- **困难**: 7题
- **总计**: 54题

## 🚀 快速开始

### 1. 安装依赖

```bash
cd website
pip install -r requirements.txt
```

### 2. 生成题目元数据

```bash
python generate_challenge_metadata.py
```

这将扫描所有挑战题目并生成 `challenges.json` 文件。

### 3. 启动Web服务器

```bash
python app.py
```

服务器将在 `http://localhost:5000` 启动。

### 4. 访问网站

在浏览器中打开 `http://localhost:5000`，开始使用！

## 📁 项目结构

```
website/
├── app.py                          # Flask后端应用
├── generate_challenge_metadata.py  # 题目元数据生成脚本
├── challenges.json                 # 题目元数据（自动生成）
├── requirements.txt                # Python依赖
├── README.md                       # 项目说明
├── templates/                      # HTML模板
│   ├── index.html                 # 主页（题库列表）
│   ├── quiz.html                  # 测验页面
│   └── challenge.html             # 题目详情页
└── static/                         # 静态资源
    ├── style.css                  # 样式表
    ├── script.js                  # 主页脚本
    └── quiz.js                    # 测验脚本
```

## 🎮 GPU型号支持

### NVIDIA
- RTX 4090, RTX 4080, RTX 3090, RTX 3080
- A100, H100, V100, T4

### AMD
- MI300X, MI250X
- RX 7900 XTX, RX 6900 XT

### Intel
- Data Center GPU Max 1550
- Arc A770

### Apple
- M3 Max
- M2 Ultra

## 🔧 API端点

### 获取所有题目
```
GET /api/challenges?difficulty=<easy|medium|hard>&search=<keyword>
```

### 获取题目详情
```
GET /api/challenge/<challenge_id>
```

### 生成随机测验
```
GET /api/quiz/generate?difficulty=<all|easy|medium|hard>&count=<number>
```

### 获取统计信息
```
GET /api/stats
```

### 获取GPU型号列表
```
GET /api/gpu-models
```

## 🎯 使用场景

1. **学习GPU编程**: 浏览题库，选择合适难度的题目学习
2. **技能评估**: 使用随机测验功能评估自己的GPU编程水平
3. **面试准备**: 系统化学习各类GPU编程算法和优化技巧
4. **教学辅助**: 教师可用于课程作业和考试

## 🛠️ 技术栈

- **后端**: Python Flask
- **前端**: HTML5, CSS3, Vanilla JavaScript
- **数据**: JSON格式存储
- **设计**: 响应式设计，深色主题

## 📝 许可证

本项目基于 LeetGPU 题库构建，遵循 CC BY-NC-ND 4.0 许可证。

© 2025 AlphaGPU, LLC. 禁止商业使用、重新分发或衍生使用。

## 🤝 贡献

欢迎提交问题和改进建议！

## 📧 联系方式

如有问题或建议，请访问 [LeetGPU.com](https://leetgpu.com)
