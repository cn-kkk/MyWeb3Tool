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
            print(f"[WARN] 文件 {self.password_file} 为空")
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

    def choose_and_click_from_selector(self, driver, name, modal_tag=None, timeout=5):
        """
        更通用：自动推断modal标签
        :param driver: Selenium WebDriver实例
        :param name: 钱包名称（如"OKX Wallet"、"MetaMask"等）
        :param modal_tag: 钱包选择器弹窗的tag名，默认None自动推断
        :param timeout: 等待弹窗出现的超时时间（秒）
        :return: True表示点击成功，False表示未找到或点击失败
        """
        try:
            if modal_tag:
                # 用指定modal_tag
                modal = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, modal_tag))
                )
                modals = [modal]
            else:
                # 自动查找所有modal类自定义标签
                all_modals = driver.find_elements(By.XPATH, "//*[contains(local-name(), 'modal')]")
                modals = []
                for m in all_modals:
                    if m.is_displayed():
                        modals.append(m)
                if not modals:
                    print("未自动检测到modal弹窗")
                    return False

            for modal in modals:
                js = f'''
                function findWallet(root) {{
                    let results = [];
                    function traverse(node) {{
                        if (!node) return;
                        if (node.shadowRoot) {{
                            traverse(node.shadowRoot);
                        }}
                        if (node.childNodes) {{
                            node.childNodes.forEach(traverse);
                        }}
                        if (node.innerText && node.innerText.includes("{name}")) {{
                            results.push(node);
                        }}
                    }}
                    traverse(root.shadowRoot ? root.shadowRoot : root);
                    return results;
                }}
                return findWallet(arguments[0]);
                '''
                nodes = driver.execute_script(js, modal)
                if nodes:
                    driver.execute_script("arguments[0].click();", nodes[0])
                    print(f"已用JS点击shadowRoot下的钱包：{name}")
                    return True
            print(f"未找到可点击的钱包：{name}")
            return False
        except Exception as e:
            print(f"查找{name}或点击失败: {e}")
            return False


    def confirm_or_connect_native(self, driver, timeout=5):
        """
        用Selenium原生查找并点击'确认'或'连接'按钮，优先点击'确认'。
        :param driver: Selenium WebDriver实例，需已切换到OKX钱包插件窗口
        :param timeout: 查找超时时间（秒）
        :return: True表示点击成功，False表示未找到或点击失败
        """
        try:
            time.sleep(2)
            buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-testid="okd-button"]')
            confirm_btn = None
            connect_btn = None
            for btn in buttons:
                try:
                    text = btn.text.strip()
                    print(f"[DEBUG] OKX按钮text: {text}")
                    if "确认" in text:
                        confirm_btn = btn
                    elif "连接" in text:
                        connect_btn = btn
                except Exception as e:
                    print(f"[DEBUG] 获取按钮text异常: {e}")
            target_btn = confirm_btn or connect_btn
            if target_btn:
                WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(target_btn))
                target_btn.click()
                time.sleep(2)
                return True
            else:
                print("[WARN] 未找到'确认'或'连接'按钮")
                return False
        except Exception as e:
            print(f"[ERROR] Selenium点击OKX钱包确认/连接按钮失败: {e}")
            return False

if __name__ == '__main__':
    print("OKXWalletUtil模块，提供 open_and_unlock(driver) 方法来解锁钱包。")
