from DrissionPage import ChromiumPage
from util.okx_wallet_util import OKXWalletUtil
from util.anti_sybil_dp_util import AntiSybilDpUtil
from util.log_util import log_util
from util.wallet_util import WalletUtil
from annotation.task_annotation import task_annotation


class PharosScript:
    """
    Pharos项目的脚本类。
    """

    project_name = "Pharos"
    PHAROS_URL = "https://testnet.pharosnetwork.xyz/experience"
    SWAP_URL = "https://testnet.zenithfinance.xyz/swap"

    def __init__(self, browser, user_id: str, window_height: int = 800):
        """
        项目级初始化。
        此方法负责打开项目页面、连接钱包以及执行必要的初始交互。
        假定钱包已在更高层级（Worker）被解锁。
        """
        self.browser = browser
        self.user_id = user_id
        self.okx_util = OKXWalletUtil()
        self.wallet_util = WalletUtil()
        self.window_height = window_height

        log_util.info(self.user_id, f"开始初始化项目: {self.project_name}")
        try:
            # 步骤1: 为浏览器实例注入反女巫检测脚本
            page_for_cdp = self.browser.get_tab()
            if not page_for_cdp:
                page_for_cdp = self.browser.new_tab('about:blank')
                AntiSybilDpUtil.patch_webdriver_fingerprint(page_for_cdp)
                page_for_cdp.close()
            else:
                AntiSybilDpUtil.patch_webdriver_fingerprint(page_for_cdp)

            # 步骤2: 获取Pharos主页的页面对象
            tabs = self.browser.get_tabs(url=self.PHAROS_URL)
            if tabs:
                self.page = tabs[0]
                self.page.set.activate()
                self.page.refresh()
            else:
                self.page = self.browser.new_tab(self.PHAROS_URL)
            self.page.wait.load_start()

            # 步骤3: 人性化等待和交互
            AntiSybilDpUtil.human_long_wait()
            AntiSybilDpUtil.simulate_random_click(self.page, self.user_id)
            AntiSybilDpUtil.human_brief_wait()
            AntiSybilDpUtil.simulate_mouse_move(self.page)
            
            # 步骤4: 连接钱包
            js_find_button = "const button = Array.from(document.querySelectorAll('button')).find(btn => btn.textContent.trim() === 'Connect Wallet' && btn.offsetParent !== null); return !!button;"
            if self.page.run_js(js_find_button):
                self.page.ele('xpath://button[normalize-space()="Connect Wallet"]').click()
                AntiSybilDpUtil.human_short_wait()

                def _select_okx_wallet():
                    """内部函数，用于处理复杂的钱包选择器逻辑，失败时会自己抛出异常。"""
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
                    possible_hosts = self.page.eles("xpath://*[contains(local-name(), 'modal')]")
                    for host in possible_hosts:
                        if host.states.is_displayed and self.page.run_js(js_find_and_click, host, "OKX Wallet"):
                            return
                    raise Exception("遍历所有弹窗未能找到并点击OKX Wallet。")

                # 调用内部函数选择OKX钱包
                _select_okx_wallet()
                AntiSybilDpUtil.human_short_wait()
                # 处理可选的"Continue"按钮
                js_click_continue = """
                const btn = document.querySelector('button.sc-fifgeu.donsIG');
                if (btn && btn.textContent.trim() === 'Continue') {
                  btn.click();
                }
                """
                self.page.run_js(js_click_continue)
                AntiSybilDpUtil.human_long_wait()

                self.okx_util.confirm_transaction_drission(self.browser, self.user_id)

            log_util.info(self.user_id, f"—————— 项目 '{self.project_name}' 初始化成功 ——————")
        except Exception as e:
            log_util.error(self.user_id, f"项目 '{self.project_name}' 初始化失败: {e}")
            raise

    @task_annotation.once_per_day
    def pharos_task_check_in(self):
        """
        签到任务：自动查找并点击Check in按钮，然后刷新页面并验证状态。
        """
        log_util.info(self.user_id, "开始执行签到任务...")
        try:
            # 任务开始前，获取或导航到Pharos主页
            tabs = self.browser.get_tabs(url=self.PHAROS_URL)
            if tabs:
                self.page = tabs[0]
                self.page.set.activate()
                self.page.refresh()
            else:
                self.page = self.browser.new_tab(self.PHAROS_URL)

            # 步骤1: 等待页面加载并查找 "Check in" 按钮
            self.page.wait.doc_loaded()
            AntiSybilDpUtil.human_short_wait()
            checkin_btn = self.page.ele(  # type: ignore
                'xpath://button[contains(text(), "Check in")]', timeout=20
            )

            # 步骤2: 如果找到按钮，则点击并刷新
            if checkin_btn and checkin_btn.states.is_displayed:
                checkin_btn.click()
                self.page.refresh()
                self.page.wait.load_start()

            # 步骤3: 验证按钮状态是否变为 "Checked"
            checked_btn = self.page.ele(  # type: ignore
                'xpath://button[contains(text(), "Checked")]', timeout=10
            )

            if checked_btn and checked_btn.states.is_displayed:
                log_util.info(self.user_id, "—————— 签到任务已成功完成 ——————")
                return True
            else:
                log_util.error(self.user_id, "签到任务失败：未找到'Checked'按钮，状态未知。")
                return False

        except Exception as e:
            # 捕获所有异常，包括查找 "Check in" 按钮超时
            # 如果超时，很可能意味着已经签到过了
            if "Timeout" in str(e):
                # 再次检查是否已签到
                checked_btn = self.page.ele(  # type: ignore
                    'xpath://button[contains(text(), "Checked")]', timeout=5
                )
                if checked_btn and checked_btn.states.is_displayed:
                    log_util.info(self.user_id, "—————— 签到任务已成功完成（之前已签到） ——————")
                    return True

            log_util.error(self.user_id, f"签到任务执行期间发生意外错误: {e}")
            return False

    def pharos_task_swap(self):
        """
        Swap任务：打开新页面，连接钱包，默认会swap0.005个PHRS到USDC，然后会swap回来。
        """
        log_util.info(self.user_id, "开始执行Swap任务...")
        swap_page = None
        try:
            # 步骤1: 打开新的SWAP_URL页面
            swap_page = self.browser.new_tab(self.SWAP_URL)

            # 步骤2: 人性化等待和页面刷新
            AntiSybilDpUtil.human_long_wait()
            swap_page.refresh()
            swap_page.wait.load_start()
            AntiSybilDpUtil.human_brief_wait()

            # 步骤3: 检查是否钱包连接
            connected_button = swap_page.ele('xpath://button[@data-testid="web3-status-connected"]', timeout=5) # type: ignore
            if not (connected_button and connected_button.states.is_displayed):
                # 如果未连接，则执行手动连接流程
                connect_btn = swap_page.ele( # type: ignore
                    'xpath://button[@data-testid="navbar-connect-wallet"]',
                    timeout=15
                )
                if connect_btn and connect_btn.states.is_displayed:
                    connect_btn.click()
                    AntiSybilDpUtil.human_short_wait()
                    if not self.okx_util.click_OKX_in_selector(self.browser, swap_page, self.user_id):
                        log_util.error(self.user_id, "Swap任务失败：执行OKX钱包连接流程失败。")
                        return False
                else:
                    # 两种按钮都找不到，则任务失败
                    log_util.error(self.user_id, "Swap任务失败：既未找到已连接的钱包按钮，也未找到'Connect'按钮。")
                    return False

            # 步骤4: 等待代币数量加载
            swap_page.wait.doc_loaded()
            AntiSybilDpUtil.human_short_wait()
            AntiSybilDpUtil.simulate_mouse_move(swap_page)

            # 步骤5: 模拟向下滚动，然后点击“Select token”按钮 (B Token)
            swap_page.scroll.down(300)
            AntiSybilDpUtil.human_short_wait()
            select_token_btn = swap_page.ele(
                'xpath://button[contains(@class, "open-currency-select-button") and .//span[text()="Select token"]]'
            ) # type: ignore
            if not (select_token_btn and select_token_btn.states.is_displayed):
                log_util.error(self.user_id, "Swap任务失败：未找到'Select token'按钮。")
                return False
            select_token_btn.click()
            AntiSybilDpUtil.human_short_wait()

            # 步骤6: 在弹窗中选择USDC
            usdc_option = swap_page.ele('xpath://div[@data-testid="common-base-USDC"]') # type: ignore
            if not (usdc_option and usdc_option.states.is_displayed):
                log_util.error(self.user_id, "Swap任务失败：未找到'USDC'选项。")
                return False
            usdc_option.click()
            AntiSybilDpUtil.human_short_wait()

            # 步骤7: 在PHRS输入框中输入金额
            amount_input = swap_page.wait.ele_displayed('xpath://input[@id="swap-currency-input"]', timeout=10)
            if not amount_input:
                log_util.error(self.user_id, "Swap任务失败：未找到金额输入框。")
                return False
            # 采用“点击->清空->输入”的终极策略来处理顽固输入框
            amount_input.click()
            AntiSybilDpUtil.human_brief_wait()
            amount_input.clear()
            AntiSybilDpUtil.human_brief_wait()
            random_amount_str = AntiSybilDpUtil.get_perturbation_number(0.006, 0.001)
            AntiSybilDpUtil.simulate_typing(swap_page, random_amount_str)

            # 步骤8: 等待兑换率计算完成
            swap_page.wait.doc_loaded()
            AntiSybilDpUtil.human_long_wait() # 使用长等待，给网页足够的时间返回汇率

            # 步骤9: 点击Swap按钮
            swap_btn = swap_page.ele('#swap-button') # type: ignore
            if not (swap_btn and swap_btn.states.is_clickable):
                log_util.error(self.user_id, "Swap任务失败：Swap按钮未出现或不可点击。")
                return False
            swap_btn.click()
            AntiSybilDpUtil.human_long_wait()

            # 步骤10: 在弹窗中点击 "Confirm Swap"
            confirm_swap_btn = swap_page.wait.ele_displayed('#confirm-swap-or-send', timeout=10)
            if not confirm_swap_btn:
                log_util.error(self.user_id, "Swap任务失败：未找到 'Confirm Swap' 按钮。")
                return False
            confirm_swap_btn.wait.clickable(timeout=10)
            confirm_swap_btn.click()
            AntiSybilDpUtil.human_long_wait()

            # 步骤11: 处理OKX钱包交易确认
            if not self.okx_util.confirm_transaction_drission(self.browser, self.user_id):
                log_util.error(self.user_id, "Swap任务失败：钱包交易确认失败。")
                return False
            AntiSybilDpUtil.human_huge_wait()
            AntiSybilDpUtil.simulate_mouse_move(swap_page)

            # 步骤12: 等待网页执行swap，然后通过点击空白处关闭swap成功的弹窗
            AntiSybilDpUtil.simulate_random_click(swap_page, self.user_id)
            self.page.wait.doc_loaded()

            # 步骤13: 点击对调按钮，然后将usdc换回PHRS，再次执行步骤7后面逻辑
            swap_currency_button = swap_page.ele('xpath://div[@data-testid="swap-currency-button"]')
            swap_currency_button.click()  # 点击按钮
            AntiSybilDpUtil.human_short_wait()

            max_btn = swap_page.wait.ele_displayed('@name=Swap Max Token Amount Selected', timeout=10)
            if max_btn:
                max_btn.click()
            else:
                amount_input.click()
                AntiSybilDpUtil.human_brief_wait()
                amount_input.clear()
                AntiSybilDpUtil.human_brief_wait()
                random_amount_str = AntiSybilDpUtil.get_perturbation_number(10, 2)
                AntiSybilDpUtil.simulate_typing(swap_page, random_amount_str)

            swap_page.wait.doc_loaded()
            AntiSybilDpUtil.human_long_wait()

            swap_btn.click()
            AntiSybilDpUtil.human_long_wait()

            new_confirm_swap_btn = swap_page.wait.ele_displayed('#confirm-swap-or-send', timeout=10)
            new_confirm_swap_btn.wait.clickable(timeout=10)
            new_confirm_swap_btn.click()
            AntiSybilDpUtil.human_long_wait()

            if not self.okx_util.confirm_transaction_drission(self.browser, self.user_id):
                log_util.error(self.user_id, "Swap任务失败：钱包交易确认失败。")
                return False
            AntiSybilDpUtil.human_huge_wait()

            log_util.info(self.user_id, "—————— Swap任务已成功完成 ——————")
            return True

        except Exception as e:
            log_util.error(self.user_id, f"Swap任务执行时发生意外错误: {e}")
            return False
        finally:
            # 任务结束后关闭页面
            if swap_page and swap_page.tab_id in self.browser.tab_ids:
                swap_page.close()

    def pharos_task_send_tokens(self):
        """
        发送代币任务：滚动页面，打开发送弹窗，输入随机地址，确认发送。
        """
        log_util.info(self.user_id, "开始执行发送代币任务...")
        try:
            # 任务开始前，获取或导航到Pharos主页
            tabs = self.browser.get_tabs(url=self.PHAROS_URL)
            if tabs:
                self.page = tabs[0]
                self.page.set.activate()
                self.page.refresh()
            else:
                self.page = self.browser.new_tab(self.PHAROS_URL)

            # 步骤1: 等待页面加载完成并查找'Send'按钮
            self.page.wait.doc_loaded()
            AntiSybilDpUtil.human_short_wait()
            AntiSybilDpUtil.simulate_mouse_move(self.page)
            send_button = self.page.wait.ele_displayed('xpath://button[text()="Send"]', timeout=20)
            if not send_button:
                log_util.error(self.user_id, "发送代币任务失败：未找到'Send'按钮。")
                return False

            # 步骤2: 滚动并点击Send按钮
            self.page.run_js("window.scrollTo(0, document.body.scrollHeight * 0.35);")
            AntiSybilDpUtil.human_short_wait()
            send_button.click()

            # 步骤3: 点击金额选项
            amount_option = self.page.ele('xpath://div[text()="0.001PHRS"]', timeout=15) # type: ignore
            if not amount_option or not amount_option.states.is_displayed:
                log_util.error(self.user_id, "发送代币任务失败：未找到'0.001PHRS'金额选项。")
                return False
            amount_option.click()

            # 步骤4: 输入随机地址
            address_input = self.page.ele('xpath://input[@placeholder="Enter Address"]', timeout=10) # type: ignore
            if not address_input or not address_input.states.is_displayed:
                log_util.error(self.user_id, "发送代币任务失败：未找到地址输入框。")
                return False
            random_address = self.wallet_util.generate_random_evm_address()
            address_input.input(random_address)
            AntiSybilDpUtil.human_short_wait()

            # 步骤5: 点击最终的“Send PHRS”按钮
            final_send_button = self.page.ele('xpath://button[text()="Send PHRS"]', timeout=10) # type: ignore
            if not final_send_button or not final_send_button.states.is_displayed:
                log_util.error(self.user_id, "发送代币任务失败：未找到'Send PHRS'按钮。")
                return False
            final_send_button.click()
            AntiSybilDpUtil.human_long_wait()

            # 步骤6: 处理钱包确认
            if not self.okx_util.confirm_transaction_drission(self.browser, self.user_id):
                log_util.error(self.user_id, "发送代币任务失败：钱包交易确认失败。")
                return False
            
            log_util.info(self.user_id, "—————— 发送代币任务已成功完成 ——————")
            AntiSybilDpUtil.human_long_wait()
            AntiSybilDpUtil.simulate_random_click(self.page, self.user_id)
            return True

        except Exception as e:
            log_util.error(self.user_id, f"发送代币任务执行时发生意外错误: {e}")
            return False


if __name__ == "__main__":
    # 这个脚本现在是一个库，不应该被直接运行。
    print(
        "PharosScript 定义完成。请在您的主程序中实例化，或通过 pharosScript_test.py 进行测试。"
    )