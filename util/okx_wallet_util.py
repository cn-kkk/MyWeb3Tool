import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class OKXWalletUtil:
    """
    OKX钱包工具类 (基于Selenium)
    新版逻辑：只负责打开并解锁钱包，不再自动关闭。
    """
    PASSWORD = None
    EXTENSION_ID = 'mcohilncbfahbmgdjkbpemcciiolgcge'

    def __init__(self):
        self.password_file = "resource/okxPassword.txt"
        if OKXWalletUtil.PASSWORD is None:
            OKXWalletUtil.PASSWORD = self._load_password()

    def _load_password(self):
        """从 resource/okxPassword.txt 加载密码"""
        if not os.path.exists(self.password_file):
            print(f"[ERROR] 未找到密码文件: {self.password_file}")
            return None
        with open(self.password_file, 'r', encoding='utf-8') as f:
            pwd = f.readline().strip()
        if not pwd:
            print(f"[WARN] ���码文件 {self.password_file} 为空")
            return None
        return pwd

    def open_and_unlock(self, driver):
        """
        使用 driver.get() 在新标签页中打开OKX钱包并解锁。
        标签页将保持打开状态，以便后续操作。
        """
        if not self.PASSWORD:
            print("[ERROR] 未加载钱包密码，无法解锁")
            return False

        main_window_handle = driver.current_window_handle
        wallet_url = f"chrome-extension://{self.EXTENSION_ID}/popup.html"
        
        try:
            # 步骤1: 使用 driver.get() 打开新标签页
            driver.switch_to.new_window('tab')
            driver.get(wallet_url)
            print(f"已在新标签页中加载OKX钱包URL: {wallet_url}")
            time.sleep(5) # 等待页面初步加载

            # 步骤2: 检查是否已经解锁
            try:
                send_button_xpath = "//*[text()='发送']"
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, send_button_xpath)))
                print("[INFO] 钱包已处于解锁状态。")
            except TimeoutException:
                print("[INFO] 钱包已锁定，开始执行解锁流程...")
                # 执行解锁流程
                password_input = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
                )
                password_input.send_keys(self.PASSWORD)
                
                unlock_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
                unlock_button.click()
                
                # 最终验证
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, send_button_xpath)))
                print("[SUCCESS] 成功解锁钱包。")

            # 步骤3: 操作完成后，切回主窗口，但保持钱包标签页打开
            driver.switch_to.window(main_window_handle)
            print("钱包操作完成，已切回主窗口。钱包标签页保持打开。")
            return True

        except Exception as e:
            print(f"[ERROR] 打开并解锁OKX钱包时发生未知错误: {e}")
            # 如果出错，也尝试切回主窗口
            driver.switch_to.window(main_window_handle)
            return False

if __name__ == '__main__':
    print("OKXWalletUtil模块，提供 open_and_unlock(driver) 方法来解锁钱包。")
