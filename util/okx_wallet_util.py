import os


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
            # 此处为启动时检查，控制台打印是合适的
            print(f"[ERROR] 未找到密码文件: {self.password_file}")
            return None
        with open(self.password_file, 'r', encoding='utf-8') as f:
            pwd = f.readline().strip()
        if not pwd:
            print(f"[WARN] 文件 {self.password_file} 为空")
            return None
        return pwd

    def confirm_transaction_drission(self, browser, user_id: str):
        """
        等待并处理OKX钱包的通用弹窗（如交易确认、连接请求等）。
        会自动寻找并点击“确认”或“连接”按钮。
        :param browser: DrissionPage.ChromiumBrowser 对象
        :param user_id: 用于日志记录的浏览器标识
        :return: True表示成功, False表示失败
        """
        
        wallet_page = None
        try:
            wallet_page = browser.latest_tab
            wallet_page.wait.load_start()

            if self.EXTENSION_ID not in wallet_page.url:
                LogUtil.error(user_id, f"OKX钱包操作失败：打开的页面不是钱包扩展。URL: {wallet_page.url}")
                if wallet_page:
                    wallet_page.close()
                return False

            # 循环处理，直到钱包页面关闭
            while wallet_page.is_alive:
                # 查找并点击主要操作按钮
                action_button = wallet_page.ele(
                    'xpath://button[contains(., "确认") or contains(., "连接")]', timeout=5 # type: ignore
                )
                if action_button and action_button.states.is_clickable:
                    action_button.click()
                    AntiSybilDpUtil.human_short_wait()
                    # 点击后继续循环，以应对多步确认
                    continue

                # 查找并点击取消按钮
                cancel_button = wallet_page.ele('text:取消', timeout=1) # type: ignore
                if cancel_button and cancel_button.states.is_clickable:
                    cancel_button.click()
                    AntiSybilDpUtil.human_short_wait()
                    continue
                
                # 如果页面仍然存在，但找不到任何可操作按钮，则可能已完成并等待关闭
                # 短暂等待后再次检查页面状态
                AntiSybilDpUtil.human_short_wait()
                if not wallet_page.is_alive:
                    break

            return True

        except Exception as e:
            # 只有在发生意外时才记录错误
            LogUtil.error(user_id, f"处理钱包弹窗时发生意外错误: {e}", exc_info=True)
            if wallet_page and wallet_page.is_alive:
                wallet_page.close()
            return False
    
    def open_and_unlock_drission(self, browser, user_id: str):
        """
        使用 DrissionPage 在新标签页中打开OKX钱包并解锁，完成后关闭钱包标签页。
        :param browser: DrissionPage.ChromiumBrowser 对象
        :param user_id: 用于日志记录的浏览器标识
        :return: True表示成功, False表示失败
        """

        wallet_url = f"chrome-extension://{self.EXTENSION_ID}/popup.html"
        wallet_tab = None
        try:
            wallet_tab = browser.new_tab(url=wallet_url)
            wallet_tab.wait.load_start()
            
            # 检查是否已解锁 (已解锁页面通常会包含“发送”按钮)
            if wallet_tab.ele("text:发送", timeout=10): # type: ignore
                wallet_tab.close()
                return True

            # 执行解锁流程
            password_input = wallet_tab.ele('tag:input@type=password', timeout=15) # type: ignore
            password_input.input(self.PASSWORD)
            AntiSybilDpUtil.human_short_wait()
            
            unlock_button = wallet_tab.ele('tag:button@type=submit') # type: ignore
            unlock_button.click()
            
            # 等待解锁成功标志
            if wallet_tab.wait.ele_displayed('text:发送', timeout=10):
                return True
            else:
                LogUtil.error(user_id, "点击解锁后未能确认钱包已解锁。")
                return False

        except Exception as e:
            LogUtil.error(user_id, f"解锁钱包过程中失败: {e}")
            return False
        finally:
            if wallet_tab and wallet_tab.is_alive:
                wallet_tab.close()

    def click_OKX_in_selector(self, browser, page: ChromiumPage, user_id: str):
        """
        在钱包选择弹窗中选择OKX钱包，并处理后续的连接确认。
        这是一个封装好的通用连接方法。
        """
        try:
            # 步骤1: 在DApp页面点击“OKX Wallet”选项
            okx_wallet_button = page.ele(  # type: ignore
                'xpath://div[text()="OKX Wallet"]/parent::div/parent::div',
                timeout=15
            )

            if okx_wallet_button and okx_wallet_button.states.is_displayed:
                okx_wallet_button.run_js("this.click();")
                AntiSybilDpUtil.human_long_wait()
                # 步骤2: 调用通用弹窗处理器来完成连接
                return self.confirm_transaction_drission(browser, user_id)
            else:
                # 此处是可预见的失败，不记录error，而是返回False，由业务层决定如何记录
                return False

        except Exception as e:
            LogUtil.error(user_id, f"点击 OKX Wallet 选项时发生意外错误: {e}")
            return False