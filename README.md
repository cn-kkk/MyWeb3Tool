# S1mpleWeb3Tool

一个功能丰富的Web3工具集，提供多种区块链操作功能。

## 功能特性

- 🔧 **配置管理** - IP配置和钱包配置
- 🔄 **Somnia** - Swap、Mint、转账功能
- 🌐 **Pharos** - Swap、Deposit、转账、域名功能
- 📝 **日志记录** - 详细的操作日志记录

## 安装和运行

### 方法一：直接运行Python脚本

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行应用程序：
```bash
python myToolApplication.py
```

### 方法二：打包成exe文件

1. 运行打包脚本：
```bash
python build_exe.py
```

2. 运行生成的exe文件：
```bash
S1mpleWeb3Tool.exe
```

## 项目结构

```
S1mpleWeb3Tool/
├── myToolApplication.py    # 主应用程序
├── build_exe.py           # 打包脚本
├── requirements.txt       # 依赖列表
├── util/                  # 工具模块
├── resource/              # 资源文件
└── logs/                  # 日志文件（自动生成）
```

## 界面说明

### 首页
- 欢迎界面，显示应用程序功能概览

### 配置
- **IP配置** - 管理代理IP设置
- **钱包配置** - 管理钱包相关配置

### Somnia
- **Swap** - 代币交换功能
- **Mint** - NFT铸造功能
- **转账** - 代币转账功能

### Pharos
- **Swap** - 代币交换功能
- **Deposit** - 存款功能
- **转账** - 代币转账功能
- **域名** - 域名管理功能

## 日志系统

应用程序会自动记录所有操作日志，日志文件保存在 `logs/` 目录下，文件名格式为 `myTool_YYYYMMDD_HHMMSS.log`。

## 开发说明

- 使用 PyQt5 构建图形界面
- 支持 Windows 平台
- 可打包成独立的 exe 文件

## 注意事项

- 首次运行时会自动创建日志目录
- 确保有足够的磁盘空间用于日志文件
- 建议在虚拟环境中运行以避免依赖冲突