import time
import pyautogui
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from util.okx_wallet_util import OKXWalletUtil
from util.log_util import LogUtil
from util.anti_sybil_util import AntiSybilUtil

class PharosScript:
    """
    使用新的Selenium原生流程执行Pharos任务的脚本。
    """
    project_name = "Pharos"
    PHAROS_URL = "https://testnet.pharosnetwork.xyz/experience"
    OKX_WALLET_EXTENSION_ID = "mcohilncbfahbmgdjkbpemcciiolgcge"

    def __init__(self, ads_env):
        """
        初始化任务，自动完成钱包解锁、页面打开和钱包连接。
        """
        self.ads_env = ads_env
        self.driver = ads_env.driver
        self.okx_util = OKXWalletUtil()
        
        self._initialize_session()

    def _initialize_session(self):
        """
        执行最核心、最直接的初始化操作。
        """
        LogUtil.log(self.ads_env, f"开始初始化项目: {self.project_name}")

        # 步骤1: 最大化窗口以确保焦点
        try:
            LogUtil.log(self.ads_env, "步骤1: 尝试最大化浏览器窗口...")
            self.driver.maximize_window()
            time.sleep(1)
        except Exception:
            LogUtil.log(self.ads_env, f"[WARN] 窗口已是最大化，继续执行。")

        # 步骤2: 解锁钱包
        LogUtil.log(self.ads_env, "步骤2: 解锁OKX钱包...")
        if not self.okx_util.open_and_unlock(self.driver):
            raise RuntimeError("钱包解锁失败，任务无法继续。")
        LogUtil.log(self.ads_env, "钱包解锁成功。")
        time.sleep(1)

        # 步骤3: 打开Pharos页面并取消浮窗
        LogUtil.log(self.ads_env, f"步骤3: 在新标签页中打开Pharos URL: {self.PHAROS_URL}")
        self.driver.switch_to.new_window('tab')
        self.driver.get(self.PHAROS_URL)
        LogUtil.log(self.ads_env, "页面加载完成，等待10秒...")
        time.sleep(10)
        # 反女巫：页面加载后模拟鼠标滑动
        AntiSybilUtil.simulate_mouse_move_and_slide(self.driver, area_selector='body', env=self.ads_env)
        try:
            LogUtil.log(self.ads_env, "执行UI交互以获取焦点并取消浮窗...")
            # 反女巫：随机点击
            AntiSybilUtil.simulate_random_click(self.driver, area_selector='body', env=self.ads_env)
            time.sleep(0.5)
            pyautogui.press('esc')
            LogUtil.log(self.ads_env, "UI交互完成。")
        except Exception as e:
            LogUtil.log(self.ads_env, f"[WARN] UI交互失败（可忽略）: {e}")

        # 步骤4: 连接网站钱包
        LogUtil.log(self.ads_env, "步骤4: 开始连接网站钱包...")
        try:
            # 反女巫：连接钱包前模拟滚动和短等待
            AntiSybilUtil.simulate_scroll(self.driver, env=self.ads_env)
            AntiSybilUtil.human_short_wait(env=self.ads_env)
            connect_button_xpath = "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'connect wallet')]"
            connect_wallet_found = False
            try:
                connect_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, connect_button_xpath))
                )
                connect_wallet_found = True
            except Exception:
                connect_wallet_found = False
            if connect_wallet_found:
                connect_button.click()
                LogUtil.log(self.ads_env, "已点击 'Connect Wallet' 按钮，等待5秒...")
                time.sleep(5)
                # AntiSybilUtil.simulate_mouse_move_and_slide(self.driver, area_selector='body', env=self.ads_env)
                # 2. 在弹窗中点击 "OKX Wallet"
                pharos_window_handle = self.driver.current_window_handle
                if not self.okx_util.choose_and_click_from_selector(self.driver, "OKX Wallet"):
                    raise RuntimeError("未能自动点击OKX Wallet，请检查钱包选择器结构！")
                LogUtil.log(self.ads_env, "已自动点击 'OKX Wallet' 选项，等待5秒...")
                time.sleep(5)
            # 反女巫：切换到钱包插件页面后模拟短等待
            pharos_window_handle = self.driver.current_window_handle
            wallet_handle = None
            found_url = None
            LogUtil.log(self.ads_env, "正在查找已打开的OKX钱包页面...")
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                if self.OKX_WALLET_EXTENSION_ID in self.driver.current_url:
                    wallet_handle = handle
                    found_url = self.driver.current_url
                    break
            if wallet_handle:
                LogUtil.log(self.ads_env, f"找到钱包页面: {found_url}")
            if not wallet_handle:
                raise RuntimeError("无法在已打开的窗口中找到OKX钱包页面。")
            AntiSybilUtil.human_short_wait(env=self.ads_env)
            # 调用工具类方法自动点击'连接'按钮
            if not self.okx_util.confirm_or_connect_native(self.driver):
                LogUtil.log(self.ads_env, "[WARN] 未能自动点击OKX钱包插件的'连接'按钮，已跳过。")
            LogUtil.log(self.ads_env, "已自动点击OKX钱包插件的'连接'按钮，等待5秒...")
            time.sleep(5)
            # 统一判断是否有Continue弹窗
            self.driver.switch_to.window(pharos_window_handle)
            try:
                continue_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue') or contains(@class, 'donsIG') ]"))
                )
                LogUtil.log(self.ads_env, "检测到Continue弹窗，自动点击...")
                time.sleep(2)
                continue_btn.click()
                time.sleep(5)
                # 再次切换到OKX钱包页面并点击连接
                self.driver.switch_to.window(wallet_handle)
                if not self.okx_util.confirm_or_connect_native(self.driver):
                    LogUtil.log(self.ads_env, "[WARN] [二次] 未能自动点击OKX钱包插件的'连接'按钮，已跳过。")
                LogUtil.log(self.ads_env, "[二次] 已自动点击OKX钱包插件的'连接'按钮，等待5秒...")
                time.sleep(5)
                self.driver.switch_to.window(pharos_window_handle)
                time.sleep(5)
            except Exception:
                LogUtil.log(self.ads_env, "未检测到Continue弹窗，无需处理。")
            LogUtil.log(self.ads_env, "已切换回Pharos主页面窗口。")

        except (TimeoutException, NoSuchElementException) as e:
            error_msg = f"连接钱包过程中失败: {e}"
            LogUtil.log(self.ads_env, f"[ERROR] {error_msg}")
            raise RuntimeError(error_msg)

    def task_check_in(self):
        """
        Pharos网页签到任务：自动查找并点击Check in按钮
        """
        try:
            checkin_btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Check in')]"))
            )
            checkin_btn.click()
            LogUtil.log(self.ads_env, "已自动点击Check in签到按钮")
            time.sleep(5)
            return True
        except Exception as e:
            LogUtil.log(self.ads_env, f"[ERROR] 签到按钮点击失败: {e}")
            return False

    def run(self):
        self.task_check_in()
        LogUtil.log(self.ads_env, f"项目 {self.project_name} 的所有任务已执行完毕。")

if __name__ == '__main__':
    print("PharosScript 定义完成。请在您的主程序中实例化并调用 .run() 方法。")