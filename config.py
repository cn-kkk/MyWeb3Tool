"""
配置文件 - 集中管理所有配置项
"""

import os

# 应用配置
APP_NAME = "S1mpleWeb3Tool"
APP_VERSION = "1.0.0"

# 目录配置
RESOURCE_DIR = "resource"
LOGS_DIR = "logs"

# 文件路径配置
BROWSER_CONFIG_FILE = os.path.join(RESOURCE_DIR, "browser.txt")
WALLET_CONFIG_FILE = os.path.join(RESOURCE_DIR, "wallet.txt")
SOCKS5_CONFIG_FILE = os.path.join(RESOURCE_DIR, "socks5.txt")

# API配置
API_ENDPOINTS = {
    "browser_active": "/browser/active",
    "browser_stop": "/browser/stop"
}
API_HEADER_KEY = "X-API-KEY"

# 数据格式配置
DATA_SEPARATOR = "----"

# UI配置
UI_FONTS = {
    "default": "Microsoft YaHei",
    "monospace": "Consolas"
}

# 日志配置
LOG_FILENAME_PREFIX = "myTool"
LOG_FILENAME_FORMAT = "{prefix}_{timestamp}.log"

# 验证配置
API_URL_VALID_PREFIXES = ("http://",) 