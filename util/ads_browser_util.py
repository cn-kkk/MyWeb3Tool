import requests
import os
import sys
import time

from DrissionPage import ChromiumPage, ChromiumOptions
from util.log_util import log_util
from config import AppConfig

# 将项目根目录添加到sys.path，以解决模块导入问题
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class DrissionPageEnv:
    """
    一个封装了DrissionPage浏览器对象和对应user_id的类。
    """

    def __init__(self, user_id, browser):
        self.user_id = user_id
        self.browser = browser

    def __repr__(self):
        return f"DrissionPageEnv(user_id={self.user_id})"


class AdsBrowserUtil:
    """
    一个专门用于连接和管理AdsPower浏览器实例的工具类 (基于DrissionPage)。
    这是一个“沉默”的工具，只在需要时提供浏览器对象，本身不产生非必要的日志。
    """

    @staticmethod
    def _get_api_config():
        """从browser.txt读取API配置"""
        api_base = ""
        browser_config_file = AppConfig.BROWSER_CONFIG_FILE
        if os.path.exists(browser_config_file):
            try:
                with open(browser_config_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if len(lines) >= 1:
                        api_base = lines[0].strip()
            except Exception as e:
                log_util.error(
                    "System", f"Failed to read API config from {browser_config_file}: {e}"
                )

        if not api_base or not api_base.startswith(AppConfig.API_URL_VALID_PREFIXES):
            log_util.warn(
                "System", f"API URL in {browser_config_file} is invalid or empty: {api_base}"
            )
            return ""

        return api_base

    @staticmethod
    def get_all_running_ads_browsers():
        """
        读取browser.txt，批量连接所有已启动的ads环境，返回DrissionPageEnv对象列表。
        这是一个静默操作，只记录错误和最终结果。
        """
        api_base = AdsBrowserUtil._get_api_config()

        if not api_base:
            log_util.error(
                "System", f"API URL not configured. Please set it in the first line of {AppConfig.BROWSER_CONFIG_FILE}"
            )
            return []

        user_ids = []
        browser_config_file = AppConfig.BROWSER_CONFIG_FILE
        if os.path.exists(browser_config_file):
            with open(browser_config_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 跳过第一行（API地址），从第二行开始读取user_id
                for line in lines[1:]:
                    uid = line.strip()
                    if uid:
                        user_ids.append(uid)
        else:
            log_util.error("AdsBrowserUtil", f"配置文件 {browser_config_file} 不存在。请在exe同目录下创建resource文件夹并添加该文件。")
            return []

        if not user_ids:
            log_util.warn(
                "System", f"No user_ids found in {browser_config_file}. Cannot connect to any browser."
            )
            return []

        envs = []
        active_endpoint = AppConfig.API_ENDPOINTS["browser_active"]

        for user_id in user_ids:
            try:
                # 在每个API请求前加入一个安全的等待，以避免触发频率限制
                time.sleep(0.5)

                full_api_url = (
                    f"{api_base.rstrip('/')}{active_endpoint}?user_id={user_id}"
                )

                resp = requests.get(
                    full_api_url, proxies={"http": None, "https": None}, timeout=10
                )
                resp.raise_for_status()
                data = resp.json()

                if data.get("code") == 0 and data.get("data", {}).get("ws", {}).get(
                    "selenium"
                ):
                    selenium_address = data["data"]["ws"]["selenium"]
                    co = ChromiumOptions().set_address(selenium_address)
                    # 连接到浏览器后，从返回的Page对象中获取其所属的Browser对象
                    page = ChromiumPage(co)
                    browser_object = page.browser
                    envs.append(DrissionPageEnv(user_id, browser_object))
                else:
                    api_msg = data.get("msg", "No message from API.")
                    log_util.warn(
                        user_id, f"找不到叫这个'{user_id}'的ads浏览器. API message: {api_msg}. 跳过处理."
                    )
            except requests.exceptions.RequestException as e:
                log_util.error(
                    user_id, f"ADS api连接失败，请检查是否启动ads客户端? Error: {e}"
                )
            except Exception as e:
                log_util.error(
                    user_id, f"连接'{user_id}'这个浏览器出现异常: {e}"
                )

        return envs

    @staticmethod
    def start_browser_if_not_running(user_id: str):
        """
        检查指定ID的浏览器是否正在运行，如果未运行，则尝试启动它。
        这是一个独立的、可复用的方法，专为未来的重构做准备。

        :param user_id: 要操作的浏览器user_id。
        :return: 如果浏览器最终处于运行状态，则返回其调试地址(selenium_ws)；否则返回None。
        """
        api_base = AdsBrowserUtil._get_api_config()
        if not api_base:
            log_util.error("AdsBrowserUtil", "API基础地址未配置，无法启动浏览器。")
            return None

        # 1. 检查浏览器当前状态
        active_endpoint = "/browser/active"
        active_url = f"{api_base.rstrip('/')}{active_endpoint}?user_id={user_id}"
        
        try:
            resp = requests.get(active_url, proxies={"http": None, "https": None}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 0 and data.get("data", {}).get("status") == "Active":
                return data["data"]["ws"]["selenium"]

        except requests.exceptions.RequestException as e:
            log_util.error("AdsBrowserUtil", f"检查浏览器 {user_id} 状态时API请求失败: {e}", exc_info=True)
            return None # API不通，无法继续

        # 2. 如果未运行，则启动浏览器
        time.sleep(0.2)
        start_endpoint = "/browser/start"
        start_url = f"{api_base.rstrip('/')}{start_endpoint}?user_id={user_id}"

        try:
            resp = requests.get(start_url, proxies={"http": None, "https": None}, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") == 0 and data.get("data", {}).get("ws", {}).get("selenium"):
                time.sleep(20) # 等待浏览器进程完全初始化
                return data["data"]["ws"]["selenium"]
            else:
                api_msg = data.get("msg", "无来自API的消息。")
                log_util.error("AdsBrowserUtil", f"启动浏览器 {user_id} 失败。API消息: {api_msg}")
                return None

        except requests.exceptions.RequestException as e:
            log_util.error("AdsBrowserUtil", f"启动浏览器 {user_id} 时API请求失败: {e}", exc_info=True)
            return None