import time
import pyautogui
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from util.okx_wallet_util import OKXWalletUtil
from util.log_util import LogUtil

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
        
        try:
            LogUtil.log(self.ads_env, "执行UI交互以获取焦点并取消浮窗...")
            pyautogui.click(x=500, y=500)
            time.sleep(0.5)
            pyautogui.press('esc')
            LogUtil.log(self.ads_env, "UI交互完成。")
        except Exception as e:
            LogUtil.log(self.ads_env, f"[WARN] UI交互失败（可忽略）: {e}")

        # 步骤4: 连接网站钱包
        LogUtil.log(self.ads_env, "步骤4: 开始连接网站钱包...")
        try:
            # 1. 点击 "Connect Wallet"
            connect_button_xpath = "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'connect wallet')]"
            connect_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, connect_button_xpath))
            )
            connect_button.click()
            LogUtil.log(self.ads_env, "已点击 'Connect Wallet' 按钮，等待5秒...")
            time.sleep(5)

            # 2. 在弹窗中点击 "OKX Wallet"
            pharos_window_handle = self.driver.current_window_handle
            
            okx_option_xpath = "//*[contains(text(), 'OKX Wallet')]"
            okx_option = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, okx_option_xpath))
            )
            ActionChains(self.driver).move_to_element(okx_option).click().perform()
            LogUtil.log(self.ads_env, "已通过ActionChains点击 'OKX Wallet' 选项，等待10秒...")
            time.sleep(10)

            # 3. 查找并切换到已存在的OKX钱包页面
            wallet_handle = None
            LogUtil.log(self.ads_env, "正在查找已打开的OKX钱包页面...")
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                if self.OKX_WALLET_EXTENSION_ID in self.driver.current_url:
                    wallet_handle = handle
                    LogUtil.log(self.ads_env, f"找到钱包页面: {self.driver.current_url}")
                    break
            
            if not wallet_handle:
                raise RuntimeError("无法在已打开的窗口中找到OKX钱包页面。")

            # 4. 在钱包页面上点击确认
            self.driver.switch_to.window(wallet_handle)
            LogUtil.log(self.ads_env, "已切换到OKX钱包页面。")

            confirm_button_xpath = "//button[text()='连接' or text()='确认']"
            confirm_button = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, confirm_button_xpath))
            )
            confirm_button.click()
            LogUtil.log(self.ads_env, "已在钱包页面点击'连接/确认'按钮。")

            # 5. 操作完成后，关闭钱包页面，切回主窗口
            LogUtil.log(self.ads_env, "关闭钱包页面...")
            self.driver.close()
            self.driver.switch_to.window(pharos_window_handle)
            LogUtil.log(self.ads_env, "已切回主窗口，等待最终验证...")
            
            address_xpath = "//button[contains(text(), '0x')]"
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, address_xpath))
            )
            LogUtil.log(self.ads_env, "[SUCCESS] 钱包连接成功！初始化完成。")

        except (TimeoutException, NoSuchElementException) as e:
            error_msg = f"连接钱包过程中失败: {e}"
            LogUtil.log(self.ads_env, f"[ERROR] {error_msg}")
            raise RuntimeError(error_msg)

    def task_check_in(self):
        pass

    def run(self):
        self.task_check_in()
        LogUtil.log(self.ads_env, f"项目 {self.project_name} 的所有任务已执行完毕。")

if __name__ == '__main__':
    print("PharosScript 定义完成。请在您的主程序中实例化并调用 .run() 方法。")