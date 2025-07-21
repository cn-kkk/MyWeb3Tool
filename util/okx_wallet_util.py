import os
import time
import warnings
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# DrissionPage是可选依赖，只有在使用dp方法时才需要
try:
    from DrissionPage import ChromiumPage
    from .anti_sybil_dp_util import AntiSybilDpUtil
    from .log_util import LogUtil
except ImportError:
    ChromiumPage = None
    AntiSybilDpUtil = None
    LogUtil = None

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
        .. deprecated:: 1.0.0
            This method is based on Selenium and is deprecated.
            Use :meth:`open_and_unlock_drission` instead.

        使用 driver.get() 或切换标签页，在OKX钱包插件页面解锁。
        标签页将保持打开状态，driver最终停留在钱包页面。
        """
        warnings.warn(
            "open_and_unlock is deprecated, use open_and_unlock_drission instead.",
            DeprecationWarning,
            stacklevel=2
        )
        if not self.PASSWORD:
            print("[ERROR] 未加载钱包密码，无法解锁")
            return False

        wallet_url_prefix = f"chrome-extension://{self.EXTENSION_ID}/popup.html"
        ext_id = self.EXTENSION_ID.lower()
        wallet_handle = None
        # 遍历所有窗口，切换后等待title非空，打印url和title，只要title或url包含'OKX Wallet'或插件ID就算钱包页面
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            # 等待title非空
            for _ in range(10):
                title = driver.title.strip().lower()
                if title:
                    break
                time.sleep(0.2)
            url = driver.current_url.strip().lower()
            print(f"[DEBUG] 检查窗口: {url} | title: {title}")
            if 'okx wallet' in title or wallet_url_prefix in url or ext_id in url:
                wallet_handle = handle
                print(f"[INFO] 命中钱包页面: {driver.current_url}")
                break
        # 没有则新开一个
        if not wallet_handle:
            driver.switch_to.new_window('tab')
            driver.get(wallet_url_prefix)
            print(f"[INFO] 新开标签页加载OKX钱包URL: {wallet_url_prefix}")
            time.sleep(5)  # 等待页面初步加载
            wallet_handle = driver.current_window_handle
        else:
            time.sleep(2)  # 已有页面也等一下

        # 解锁流程
        try:
            # 检查是否已经解锁
            send_button_xpath = "//*[text()='发送']"
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, send_button_xpath)))
            print("[INFO] 钱包已处于解锁状态。")
        except TimeoutException:
            print("[INFO] 钱包已锁定，开始执行解锁流程...")
            password_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type=\"password\"]'))
            )
            password_input.send_keys(self.PASSWORD)
            time.sleep(1)
            unlock_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            unlock_button.click()
            # 最终验证
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, send_button_xpath)))
            print("[SUCCESS] 成功解锁钱包。")
        # driver最终停留在钱包页面
        return True

    def choose_and_click_from_selector(self, driver, name, modal_tag=None, timeout=5):
        """
        .. deprecated:: 1.0.0
            This method is based on Selenium and is deprecated.
            DrissionPage can handle wallet selection pop-ups more robustly.

        更通用：自动推断modal标签
        :param driver: Selenium WebDriver实例
        :param name: 钱包名称（如"OKX Wallet"、"MetaMask"等）
        :param modal_tag: 钱包选择器弹窗的tag名，默认None自动推断
        :param timeout: 等待弹窗出现的超时时间（秒）
        :return: True表示点击成功，False表示未找到或���击失败
        """
        warnings.warn(
            "choose_and_click_from_selector is deprecated.",
            DeprecationWarning,
            stacklevel=2
        )
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
                    print("未自��检测到modal弹窗")
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
        .. deprecated:: 1.0.0
            This method is based on Selenium and is deprecated.
            DrissionPage handles wallet confirmation pop-ups automatically or via its own methods.

        用Selenium原生查找并点击'确认'或'连接'按钮，优先点击'确认'。
        :param driver: Selenium WebDriver实例，需已切换到OKX钱包插件窗口
        :param timeout: 查找超时时间（秒）
        :return: True表示点击成功，False表示未找到或点击失败
        """
        warnings.warn(
            "confirm_or_connect_native is deprecated.",
            DeprecationWarning,
            stacklevel=2
        )
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

    def disconnect_wallet(self, driver):
        """
        .. deprecated:: 1.0.0
            This method is based on Selenium and is deprecated.

        断开 OKX 钱包与 Dapp 的连接。假设 driver 已经切换到钱包插件页面。
        找到断开按钮并点击，成功返回 True，否则返回 False。
        """
        warnings.warn("disconnect_wallet is deprecated.", DeprecationWarning, stacklevel=2)
        try:
            # 直接查找断开按钮（假设唯一且可见）
            disconnect_btn = driver.find_element('css selector', '._disconnectIcon_utrae_60')
            disconnect_btn.click()
            return True
        except Exception:
            return False

    # --------------------------------------------------------------------
    # DrissionPage Methods
    # --------------------------------------------------------------------

    def confirm_transaction_drission(self, browser, user_id: str):
        """
        等待并处理OKX钱包的交易确认弹窗。
        :param browser: DrissionPage.ChromiumBrowser 对象
        :param user_id: 用于日志记录的浏览器标识
        :return: True表示成功, False表示失败
        """
        if ChromiumPage is None:
            raise ImportError("DrissionPage is not installed. Please install it to use this method.")
        
        wallet_page = None
        confirmed_at_least_once = False # 标志：是否至少点击过一次“确认”按钮
        try:
            LogUtil.info(user_id, "等待OKX钱包交易确认弹窗...")
            # 假设在调用此方法时，钱包确认弹窗（新标签页）已经出现
            # 尝试获取最新的标签页，并假定它是钱包弹窗
            wallet_page = browser.latest_tab
            wallet_page.wait.load_start() # 确保页面加载完成
            wallet_page.wait.load_start() # 确保页面加载完成

            # 调试日志：打印新标签页的URL和标题
            LogUtil.info(user_id, f"捕获到新标签页。URL: {wallet_page.url} | Title: {wallet_page.title}")

            if self.EXTENSION_ID not in wallet_page.url:
                LogUtil.error(user_id, "新标签页的URL与OKX钱包不匹配，操作终止。")
                wallet_page.close()
                return False

            LogUtil.info(user_id, f"已切换到钱包确认页面: {wallet_page.url}")

            # 持续循环，直到钱包页面关闭或操作完成
            while wallet_page.tab_id in browser.tab_ids:
                # 每次循环重新获取页面对象，确保是最新的状态
                wallet_page = browser.get_tab(wallet_page.tab_id)
                if wallet_page is None: # 页面可能在点击后立即关闭
                    LogUtil.info(user_id, "钱包确认流程完成，页面已关闭。")
                    return confirmed_at_least_once
                wallet_page.wait.load_start() # 确保页面加载完成

                LogUtil.info(user_id, "钱包页面仍在，尝试查找按钮...")

                confirm_button = wallet_page.ele('text:确认', timeout=1) # 短暂超时，快速检查
                cancel_button = wallet_page.ele('text:取消', timeout=1) # 短暂超时，快速检查

                if confirm_button and confirm_button.states.is_displayed and confirm_button.states.is_clickable:
                    LogUtil.info(user_id, f"成功找到并点击'确认'按钮，元素信息: {confirm_button.inner_html}")
                    confirm_button.click()
                    confirmed_at_least_once = True # 标记已点击过确认
                    AntiSybilDpUtil.human_short_wait(user_id) # 短暂等待页面响应
                    # 循环将继续，检查是否还有后续确认或页面是否关闭

                elif cancel_button and cancel_button.states.is_displayed and cancel_button.states.is_clickable:
                    LogUtil.info(user_id, f"找到并点击'取消'按钮，元素信息: {cancel_button.inner_html}")
                    cancel_button.click()
                    AntiSybilDpUtil.human_short_wait(user_id) # 短暂等待页面响应
                    LogUtil.info(user_id, "已点击钱包'取消'按钮，操作失败。")
                    # 确保钱包页面关闭
                    if wallet_page.tab_id in browser.tab_ids:
                        wallet_page.close()
                    return False # 用户取消，返回失败

                else:
                    # 既没有确认也没有取消，或者都不可点击，且页面仍在
                    page_html = wallet_page.html
                    
                    
                    AntiSybilDpUtil.human_short_wait(user_id) # 短暂等待，避免快速重试
                    # 如果页面仍在且无可用按钮，视为无法继续，返回失败
                    if wallet_page.tab_id in browser.tab_ids: 
                        LogUtil.error(user_id, "钱包页面持续无可用按钮，视为操作失败。")
                        wallet_page.close() # 强制关闭问题页面
                    return False # 无法继续，返回失败

            # 循环结束，说明钱包页面已关闭
            LogUtil.info(user_id, "钱包确认流程完成，页面已关闭。")
            return confirmed_at_least_once # 返回是否至少点击过一次确认

        except Exception as e:
            LogUtil.error(user_id, f"处理钱包交易确认时失败: {e}")
            # 确保如果出错，尝试关闭可能打开的钱包窗口
            if wallet_page and wallet_page.tab_id in browser.tab_ids:
                wallet_page.close()
            return False
    
    def open_and_unlock_drission(self, browser, user_id: str):
        """
        使用 DrissionPage 在新标签页中打开OKX钱包并解锁，完成后关闭钱包标签页。
        :param browser: DrissionPage.ChromiumBrowser 对象
        :param user_id: 用于日志记录的浏览器标识
        :return: True表示成功, False表示失败
        """
        if ChromiumPage is None:
            raise ImportError("DrissionPage is not installed. Please install it to use this method.")
        if not self.PASSWORD:
            LogUtil.error(user_id, "未加载钱包密码，无法解锁")
            return False

        wallet_url = f"chrome-extension://{self.EXTENSION_ID}/popup.html"
        wallet_tab = None
        try:
            LogUtil.info(user_id, f"在新标签页中打开OKX钱包")
            wallet_tab = browser.new_tab(url=wallet_url)
            
            # 增加等待，确保钱包页面加载稳定
            wallet_tab.wait.load_start()
            LogUtil.info(user_id, "钱包标签页已加载。")

            # 检查是否已解锁 (已解锁页面通常会包含“发送”按钮)
            if wallet_tab.ele("text:发送", timeout=5):
                LogUtil.info(user_id, "钱包已处于解锁状态。")
                return True

            LogUtil.info(user_id, "钱包已锁定，开始执行解锁流程...")
            
            password_input = wallet_tab.ele('tag:input@type=password', timeout=15)
            password_input.input(self.PASSWORD)
            
            AntiSybilDpUtil.human_short_wait()
            
            unlock_button = wallet_tab.ele('tag:button@type=submit')
            unlock_button.click()
            
            if wallet_tab.wait.ele_displayed('text:发送', timeout=10):
                LogUtil.info(user_id, "成功解锁钱包。")
                return True
            else:
                LogUtil.error(user_id, "点击解锁后未能确认钱包已解锁。")
                return False

        except Exception as e:
            LogUtil.error(user_id, f"解锁钱包过程中失败: {e}")
            return False
        finally:
            # 无论成功失败，都尝试关闭钱包标签页
            if wallet_tab:
                try:
                    LogUtil.info(user_id, "操作完成，短暂等待后关闭钱包标签页...")
                    AntiSybilDpUtil.human_short_wait()
                    wallet_tab.close()
                    LogUtil.info(user_id, "钱包标签页已关闭。")
                except Exception as e:
                    LogUtil.warn(user_id, f"关闭钱包标签页失败: {e}")


if __name__ == '__main__':
    print("OKXWalletUtil模块，提供 open_and_unlock(driver) 方法来解锁钱包。")