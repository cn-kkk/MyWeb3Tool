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
        等待并处理OKX钱包的交易确认弹窗，支持多次确认。
        :param browser: DrissionPage.ChromiumBrowser 对象
        :param user_id: 用于日志记录的浏览器标识
        :return: True表示成功, False表示失败
        """
        
        wallet_page = None
        try:
            LogUtil.info(user_id, "等待OKX钱包交易确认弹窗...")
            # 假设在调用此方法时，钱包确认弹窗（新标签页）已经出现
            # 尝试获取最新的标签页，并假定它是钱包弹窗
            wallet_page = browser.latest_tab
            wallet_page.wait.load_start()

            if self.EXTENSION_ID not in wallet_page.url:
                LogUtil.error(user_id, "新标签页的URL与OKX钱包不匹配，操作终止。")
                wallet_page.close()
                return False

            # 持续循环，直到钱包页面关闭
            while wallet_page.tab_id in browser.tab_ids:
                wallet_page = browser.get_tab(wallet_page.tab_id)
                if not wallet_page:
                    break # 页面已关闭，跳出循环

                wallet_page.wait.load_start()
                AntiSybilDpUtil.human_short_wait()

                confirm_button = wallet_page.ele('text:确认', timeout=2)
                if confirm_button and confirm_button.states.is_displayed and confirm_button.states.is_clickable:
                    LogUtil.info(user_id, "找到并点击'确认'按钮。")
                    confirm_button.click()
                    AntiSybilDpUtil.human_short_wait() # 等待页面响应
                    continue # 继续下一次循环，以处理可能的多次确认

                cancel_button = wallet_page.ele('text:取消', timeout=1)
                if cancel_button and cancel_button.states.is_displayed and cancel_button.states.is_clickable:
                    LogUtil.warn(user_id, "未找到'确认'按钮，找到并点击'取消'按钮。")
                    cancel_button.click()
                    AntiSybilDpUtil.human_short_wait() # 等待页面响应
                    continue # 继续下一次循环，可能下次有确认

                # 如果确认和取消都找不到，则认为出现问题
                LogUtil.error(user_id, "在钱包页面上既未找到'确认'也未找到'取消'按钮，操作失败。")
                wallet_page.close()
                return False

            # 循环正常结束，说明钱包页面已关闭，视为成功
            LogUtil.info(user_id, "钱包确认流程成功完成，页面已关闭。")
            return True

        except Exception as e:
            LogUtil.error(user_id, f"处理钱包交易确认时发生意外错误: {e}", exc_info=True)
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

        wallet_url = f"chrome-extension://{self.EXTENSION_ID}/popup.html"
        wallet_tab = None
        try:
            wallet_tab = browser.new_tab(url=wallet_url)
            # 增加等待，确保钱包页面加载稳定
            wallet_tab.wait.load_start()
            # 检查是否已解锁 (已解锁页面通常会包含“发送”按钮)
            if wallet_tab.ele("text:发送", timeout=10):
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
                    AntiSybilDpUtil.human_short_wait()
                    wallet_tab.close()
                except Exception as e:
                    LogUtil.warn(user_id, f"关闭钱包标签页时发生轻微错误: {e}")