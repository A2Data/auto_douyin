# Auto Douyin - 抖音自动上传MCP服务

独立的抖音视频自动上传工具，基于Playwright实现，支持自动登录、视频上传、定时发布等功能。

## 功能特性

- ✅ 自动登录抖音创作者中心
- ✅ 视频文件上传
- ✅ 自动填充标题和话题标签
- ✅ 定时发布功能
- ✅ 缩略图上传
- ✅ 地理位置设置
- ✅ 第三方平台同步
- ✅ Cookie管理
- ✅ 批量上传
- ✅ 完整的日志记录
- ✅ 配置文件管理

## 安装指南

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 安装Playwright浏览器驱动

```bash
playwright install chromium
```

### 3. 配置文件

复制并修改配置文件：

```bash
cp config.json config.json
```

编辑 `config.json` 文件，设置Chrome浏览器路径等配置。

## 快速开始

### 1. 登录账号

首先需要登录抖音账号并生成Cookie：

```bash
python main.py login --account your_account_name
```

这会打开浏览器，请手动完成登录，登录成功后点击调试器的"继续"按钮，Cookie将自动保存。

### 2. 上传单个视频

```bash
python main.py upload --account your_account_name --video ./videos/demo.mp4 --title "我的视频标题" --tags 科技 数码 教程
```

### 3. 定时发布

```bash
python main.py upload --account your_account_name --video ./videos/demo.mp4 --schedule "2024-01-15 18:00"
```

