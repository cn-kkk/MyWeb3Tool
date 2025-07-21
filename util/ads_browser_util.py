import requests
import os
import sys
import time

# 将项目根目录添加到sys.path，以解决模块导入问题
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from DrissionPage import ChromiumPage, ChromiumOptions
from util.log_util import LogUtil
import config


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
        browser_config_file = config.BROWSER_CONFIG_FILE
        if os.path.exists(browser_config_file):
            try:
                with open(browser_config_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if len(lines) >= 1:
                        api_base = lines[0].strip()
            except Exception as e:
                LogUtil.error(
                    "System", f"Failed to read API config from {browser_config_file}: {e}"
                )

        if not api_base or not api_base.startswith(config.API_URL_VALID_PREFIXES):
            LogUtil.warn(
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
            LogUtil.error(
                "System", f"API URL not configured. Please set it in the first line of {config.BROWSER_CONFIG_FILE}"
            )
            return []

        user_ids = []
        browser_config_file = config.BROWSER_CONFIG_FILE
        if os.path.exists(browser_config_file):
            with open(browser_config_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 跳过第一行（API地址），从第二行开始读取user_id
                for line in lines[1:]:
                    uid = line.strip()
                    if uid:
                        user_ids.append(uid)
        else:
            LogUtil.error("System", f"Browser config file not found: {browser_config_file}")
            return []

        if not user_ids:
            LogUtil.warn(
                "System", f"No user_ids found in {browser_config_file}. Cannot connect to any browser."
            )
            return []

        envs = []
        active_endpoint = config.API_ENDPOINTS["browser_active"]

        for user_id in user_ids:
            try:
                # 在每个API请求前加入一个安全的等待，以避免触发频率限制
                time.sleep(1.1)

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
                    LogUtil.warn(
                        user_id, f"Failed to get connection info for '{user_id}'. API message: {api_msg}. Skipping."
                    )
            except requests.exceptions.RequestException as e:
                LogUtil.error(
                    user_id, f"Could not connect to AdsPower API for user_id '{user_id}'. Is the local API running? Error: {e}"
                )
            except Exception as e:
                LogUtil.error(
                    user_id, f"An unexpected error occurred while connecting to browser '{user_id}': {e}"
                )

        return envs
