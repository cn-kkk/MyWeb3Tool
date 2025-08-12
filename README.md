# MyWeb3Tool

本软件是一个基于 **AdsPower** 和 **DrissionPage** 框架的Web3自动化工具。

## 前提条件

在使用本软件前，请确保满足以下条件：

1.  **启用AdsPower API**：您必须拥有AdsPower账号，并已开通API功能。
2.  **安装OKX钱包**：在所有需要运行脚本的AdsPower浏览器环境中，必须预先安装好OKX钱包插件。
3.  **统一钱包密码**：所有浏览器环境中的OKX钱包必须设置成同一个密码。
4.  **ADS浏览器有缓存**：每个浏览器都运行过一次项目

## 运行须知

修改okx密码配置和ads浏览器配置，然后选择运行的任务

### 配置管理

通过UI界面可以管理以下配置文件：

*   **浏览器配置** (`resource/browser.txt`):
    *   **第一行**: 您的AdsPower本地API地址 (例如 `http://127.0.0.1:50325`)。
    *   **后续每行**: 一个您要操作的AdsPower浏览器环境的用户ID (user_id)。

*   **OKX钱包密码** (`resource/okxPassword.txt`):
    *   在此文件中配置您的OKX钱包密码。
    *   此密码必须与您所有浏览器环境中OKX钱包的密码一致。
    
*   **SOCKS5 IP配置** (`resource/socks5.txt`):
    *   **当前状态**: 暂未使用。
    *   **未来规划**: 用于动态添加新的AdsPower环境，并使钱包相关的网络请求通过指定的代理IP进行。

*   **钱包配置** (`resource/wallets.txt`):
    *   **当前状态**: 暂未使用。
    *   **未来规划**: 用于执行链上钱包操作，如转账、合约交互等。

## 如何使用

### 对于开发者

    
    python myToolApplication.py
    

### 对于普通用户

您可以直接从本项目的 `GitHub Releases` 页面下载已打包好的 `.exe` 可执行文件，无需安装Python环境即可运行。

## PS
软件根目录下会新建logs文件夹里面存放日志
