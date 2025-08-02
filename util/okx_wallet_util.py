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
        如果钱包已解锁，则直接返回。
        如果需要解锁，则执行解锁操作并保持页面打开。
        失败时会尝试关闭页面并抛出异常。
        """
        wallet_tab = None
        try:
            if not self.PASSWORD:
                raise Exception("未加载钱包密码，无法解锁")

            wallet_url = f"chrome-extension://{self.EXTENSION_ID}/popup.html"
            wallet_tab = browser.new_tab(url=wallet_url)
            wallet_tab.wait.load_start()
            AntiSybilDpUtil.human_short_wait()

            # 使用 xpath 兼容简体“发送”和繁体“發送”
            send_button_xpath = 'xpath://*[contains(., "发送") or contains(., "發送")]'

            if wallet_tab.ele(send_button_xpath, timeout=10):
                log_util.info(user_id, "钱包已经是解锁状态")
                wallet_tab.close()
            else:
                password_input = wallet_tab.ele('tag:input@type=password', timeout=15)
                if password_input:
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

                cancel_button = wallet_tab.ele('text:取消', timeout=2)
                if cancel_button and cancel_tx_button.states.is_clickable:
                    cancel_button.click()
                    AntiSybilDpUtil.human_short_wait()

                if not wallet_tab.wait.ele_displayed(send_button_xpath, timeout=10):
                    log_util.warn(user_id, "未能确认钱包是否解锁，请手动确认。")

                if wallet_tab and wallet_tab.tab_id in browser.tab_ids:
                    wallet_tab.close()

        except Exception as e:
            # 发生任何异常时，尝试关闭标签页并向上抛出异常
            if wallet_tab and wallet_tab.tab_id in browser.tab_ids:
                wallet_tab.close()
            raise Exception(f"解锁钱包过程中失败: {e}")

    def click_OKX_in_selector(self, browser, page: ChromiumPage, user_id: str):
        """
        在钱包选择弹窗中，通过尝试多种策略智能查找并点击OKX钱包选项。
        """
        okx_button_found = False
        clicked_element = None

        # --- 策略1: 全局文本搜索 (DP原生，最高优先级) ---
        okx_text_element = page.ele('text:OKX Wallet', timeout=5)
        if okx_text_element:
            # 优先检查文本元素自身是否可点击 (处理父元素是“假”按钮的情况)
            if okx_text_element.states.is_clickable:
                clicked_element = okx_text_element
            else:
                # 如果文本自身不可点击，再查找其可点击的父按钮
                button = okx_text_element.parent('tag:button')
                if button and button.states.is_clickable:
                    clicked_element = button

        # --- 策略2: 在Modal宿主组件的Shadow Root中查找 (DP原生，第二优先级) ---
        if not clicked_element:
            modal_hosts = page.eles("xpath://*[contains(local-name(), 'modal')]")
            if modal_hosts:
                for host in modal_hosts:
                    if not host.states.is_displayed: continue
                    try:
                        shadow_root = host.shadow_root
                        okx_text_in_shadow = shadow_root.ele('text:OKX Wallet', timeout=2)
                        if okx_text_in_shadow:
                            # 同样采用“先内后外”的点击逻辑
                            if okx_text_in_shadow.states.is_clickable:
                                clicked_element = okx_text_in_shadow
                                break
                            else:
                                button = okx_text_in_shadow.parent('tag:button')
                                if button and button.states.is_clickable:
                                    clicked_element = button
                                    break
                    except Exception:
                        continue

        # --- 策略3: JS递归注入 ---
        if not clicked_element:
            log_util.info(user_id, "尝试策略 #3: JS递归搜索 (最后底牌)...")
            js_find_and_click = '''
            function findWalletAndClick(rootElement, walletName) {
                let foundNode = null;
                function traverse(node) {
                    if (!node || foundNode) return;
                    if (node.shadowRoot) { traverse(node.shadowRoot); }
                    if (!foundNode && node.childNodes) { node.childNodes.forEach(traverse); }
                    if (!foundNode && node.innerText && node.innerText.includes(walletName) && (node.tagName === 'BUTTON' || node.tagName === 'DIV' || node.onclick)) {
                        foundNode = node;
                        return;
                    }
                }
                traverse(rootElement.shadowRoot ? rootElement.shadowRoot : rootElement);
                if (foundNode) { foundNode.click(); return true; }
                return false;
            }
            return findWalletAndClick(arguments[0], arguments[1]);
            '''
            # 复用策略2找到的hosts，如果之前没找到，重新找一次
            if 'modal_hosts' not in locals():
                modal_hosts = page.eles("xpath://*[contains(local-name(), 'modal')]")

            if modal_hosts:
                for host in modal_hosts:
                    if host.states.is_displayed:
                        try:
                            if page.run_js(js_find_and_click, host, "OKX Wallet"):
                                log_util.info(user_id, "策略 #3 成功。")
                                okx_button_found = True # JS已点击，只需标记成功
                                break
                        except Exception:
                            continue

        # --- 最终执行或报错 ---
        if clicked_element:
            page.actions.click(clicked_element)
            okx_button_found = True

        if okx_button_found:
            AntiSybilDpUtil.human_long_wait()
            self.confirm_transaction_drission(browser, user_id)
        else:
            raise Exception("尝试所有策略后，仍未能找到可点击的OKX Wallet选项。")

    def click_OKX_in_selector2(self, browser, page: ChromiumPage, user_id: str):
        """
        使用js去点击的。
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