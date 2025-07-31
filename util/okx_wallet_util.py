import os


# DrissionPage是可选依赖，只有在使用dp方法时才需要
try:
    from DrissionPage import ChromiumPage
    from .anti_sybil_dp_util import AntiSybilDpUtil
    from .log_util import log_util
except ImportError:
    ChromiumPage = None
    AntiSybilDpUtil = None
    log_util = None

class OKXWalletUtil:
    """
    OKX钱包工具类
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

    def confirm_transaction_drission(self, browser, user_id: str):
        """
        等待并处理OKX钱包的通用弹窗（如交易确认、连接请求等）。
        点了‘取消’直接抛出异常，未找到okx页面返回false。
        """
        wallet_page = None
        try:
            wallet_page = browser.latest_tab
            wallet_page.wait.load_start()

            if self.EXTENSION_ID not in wallet_page.url:
                log_util.warn(user_id,"未找到okx钱包页面。")
                return False

            # 循环处理，直到钱包页面关闭
            while wallet_page.tab_id in browser.tab_ids:
                # 优先处理“取消交易”弹窗，避免阻塞
                cancel_tx_button = wallet_page.ele('text:取消交易', timeout=1)
                if cancel_tx_button and cancel_tx_button.states.is_clickable:
                    cancel_tx_button.click()
                    AntiSybilDpUtil.human_short_wait()
                    continue  # 继续循环，检查页面是否关闭或有新弹窗

                action_button = wallet_page.ele(
                    'xpath://button[contains(., "确认") or contains(., "连接")]', timeout=5
                )
                if action_button and action_button.states.is_clickable:
                    action_button.click()
                    AntiSybilDpUtil.human_long_wait()
                    continue

                cancel_button = wallet_page.ele('text:取消', timeout=1)
                if cancel_button and cancel_button.states.is_clickable:
                    cancel_button.click()
                    raise Exception("钱包当前只能点击取消。")
                
                AntiSybilDpUtil.human_short_wait()
                if wallet_page.tab_id not in browser.tab_ids:
                    break
            
            return True

        except Exception as e:
            # 没有is_alive方法
            if wallet_page and wallet_page.tab_id in browser.tab_ids:
                wallet_page.close()
            # 将所有异常（包括自定义的）向上抛出，由调用者处理
            raise Exception(f"处理钱包弹窗时发生错误: {e}")
    
    def open_and_unlock_drission(self, browser, user_id: str):
        """
        使用 DrissionPage 打开并解锁OKX钱包。
        失败时直接抛出异常。
        """
        wallet_tab = None
        try:
            if not self.PASSWORD:
                raise Exception("未加载钱包密码，无法解锁")

            wallet_url = f"chrome-extension://{self.EXTENSION_ID}/popup.html"
            wallet_tab = browser.new_tab(url=wallet_url)
            wallet_tab.wait.load_start()
            AntiSybilDpUtil.human_short_wait()

            if wallet_tab.ele("text:发送", timeout=10):
                return

            password_input = wallet_tab.ele('tag:input@type=password', timeout=15)
            password_input.input(self.PASSWORD)
            AntiSybilDpUtil.human_short_wait()
            
            unlock_button = wallet_tab.ele('tag:button@type=submit')
            unlock_button.click()
            AntiSybilDpUtil.human_short_wait()

            # 解锁后，检查并处理可能出现的“取消交易”弹窗
            cancel_tx_button = wallet_tab.ele('text:取消交易', timeout=2)
            if cancel_tx_button and cancel_tx_button.states.is_clickable:
                cancel_tx_button.click()
                AntiSybilDpUtil.human_short_wait()

            if not wallet_tab.wait.ele_displayed('text:发送', timeout=10):
                 raise Exception("点击解锁后未能确认钱包已解锁。")

        except Exception as e:
            raise Exception(f"解锁钱包过程中失败: {e}")
        finally:
            if wallet_tab and wallet_tab.tab_id in browser.tab_ids:
                wallet_tab.close()

    def click_OKX_in_selector(self, browser, page: ChromiumPage, user_id: str):
        """
        在钱包选择弹窗中选择OKX钱包，并处理后续的连接确认。
        失败时直接抛出异常。
        """
        okx_wallet_button = page.ele(
            'xpath://div[text()="OKX Wallet"]/parent::div/parent::div',
            timeout=15
        )
        if not (okx_wallet_button and okx_wallet_button.states.is_displayed):
            raise Exception("在DApp页面找不到 OKX Wallet 选项。")

        okx_wallet_button.run_js("this.click();")
        AntiSybilDpUtil.human_long_wait()
        self.confirm_transaction_drission(browser, user_id)