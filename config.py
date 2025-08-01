"""
配置文件 - 集中管理所有配置项
"""
import sys
import os

def get_base_path():
    # 如果程序被打包（例如，通过 PyInstaller），则使用 sys._MEIPASS
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    # 否则，返回脚本所在的目录
    return os.path.dirname(os.path.abspath(__file__))

def get_application_path():
    # 如果程序被打包，返回可执行文件的目录
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # 否则，返回脚本所在的目录
    return os.path.dirname(os.path.abspath(__file__))

class AppConfig:
    """
    应用程序的所有配置项。
    通过类属性的方式提供静态访问。
    """
    # --- 核心路径配置 ---
    # BASE_DIR 用于访问打包到程序内部的资源（如 myProject）
    BASE_DIR = get_base_path()
    # APPLICATION_PATH 用于访问程序外部的资源（如 resource, logs）
    APPLICATION_PATH = get_application_path()

    # 应用配置
    APP_NAME = "S1mpleWeb3Tool"
    APP_VERSION = "1.0.0"

    # --- 目录配置 ---
    # 外部资源目录，位于 exe 文件同级
    RESOURCE_DIR = os.path.join(APPLICATION_PATH, "resource")
    LOGS_DIR = os.path.join(APPLICATION_PATH, "logs")
    # 内部资源目录，被打包进 exe
    MY_PROJECT_DIR = os.path.join(BASE_DIR, "myProject")


    # --- 文件路径配置 (现在都使用绝对路径) ---
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

    # 扩展配置
    OKX_EXTENSION_ID = "mcohilncbfahbmgdjkbpemcciiolgcge"

    @staticmethod
    def get_resource_path(relative_path):
        """
        获取外部资源（如配置文件）的绝对路径。
        """
        return os.path.join(AppConfig.RESOURCE_DIR, relative_path)