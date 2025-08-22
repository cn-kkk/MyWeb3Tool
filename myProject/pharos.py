import time
from DrissionPage import ChromiumPage
from util.okx_wallet_util import OKXWalletUtil
from util.anti_sybil_dp_util import AntiSybilDpUtil
from util.log_util import log_util
from util.wallet_util import WalletUtil
from annotation.task_annotation import task_annotation
from datetime import datetime

class PharosScript:
    """
    Pharos项目的脚本类。
    """

    project_name = "Pharos"
    PHAROS_URL = "https://testnet.pharosnetwork.xyz/experience"
    ZENITH_SWAP_URL = "https://testnet.zenithfinance.xyz/swap"
    FARO_SWAP_URL = "https://faroswap.xyz/swap"
    NAME_URL = "https://test.pharosname.com/"
    CFD_URL = "https://app.brokex.trade/"

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
            self._handle_switch_network_popup(self.page)
            AntiSybilDpUtil.simulate_random_click(self.page, self.user_id)
            AntiSybilDpUtil.human_brief_wait()
            AntiSybilDpUtil.simulate_mouse_move(self.page)
            
            # 步骤4: 连接钱包
            connect_btn = self.page.ele('text:Connect Wallet', timeout=10)
            if connect_btn:
                connect_btn.click()
                AntiSybilDpUtil.human_short_wait()
                
                try:
                    self.okx_util.click_OKX_in_selector(self.browser, self.page, self.user_id)
                except Exception as e:
                    if "未找到任何OKX钱包页面" in str(e):
                        AntiSybilDpUtil.human_short_wait()
                        address_element = self.page.ele('xpath://span[starts-with(text(), "0x")]', timeout=5)
                        if not address_element:
                            raise e
                    else:
                        raise e
                AntiSybilDpUtil.human_short_wait()

                # 处理可选的"Continue"按钮

                continue_btn = self.page.ele('text:Continue', timeout=10)
                if continue_btn and continue_btn.states.is_clickable:
                    continue_btn.click()
                    AntiSybilDpUtil.human_long_wait()

                # 最终确认钱包连接
                self.okx_util.confirm_transaction_drission(self.browser, self.user_id)

        except Exception as e:
            log_util.error(self.user_id, f"项目 '{self.project_name}' 初始化失败: {e}", exc_info=True)
            raise

    def _handle_switch_network_popup(self, page: ChromiumPage):
        """
        检查并处理“切换网络”弹窗。
        """
        try:
            # 使用CSS选择器和文本内容定位按钮，增加查找的鲁棒性
            switch_button = page.ele('xpath://button[contains(text(), "Switch")]', timeout=10)
            if switch_button and switch_button.states.is_clickable:
                switch_button.click()
                AntiSybilDpUtil.human_short_wait()  # 等待弹窗消失或页面响应
        except Exception as e:
            # 如果查找或点击失败，只记录警告，不中断主流程
            log_util.warn(self.user_id, f"处理网络切换弹窗时出现非致命错误: {e}")

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
            AntiSybilDpUtil.human_short_wait()
            self._handle_switch_network_popup(self.page)
            self.page.wait.doc_loaded()
            checkin_btn = self.page.ele(  # type: ignore
                'xpath://button[contains(text(), "Check in")]', timeout=20
            )

            # 步骤2: 如果找到按钮，则点击并刷新
            if checkin_btn and checkin_btn.states.is_displayed:
                checkin_btn.click()
                AntiSybilDpUtil.human_short_wait()
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
                message = "签到后未找到'Checked'字样，请检查。"
                log_util.error(self.user_id, message)
                return message

        except Exception as e:
            # 捕获所有异常，包括查找 "Check in" 按钮超时
            # 如果超时，很可能意味着已经签到过了
            if "Timeout" in str(e):
                # 再次检查是否已签到
                checked_btn = self.page.ele(  # type: ignore
                    'xpath://button[contains(text(), "Checked")]', timeout=10
                )
                if checked_btn and checked_btn.states.is_displayed:
                    log_util.info(self.user_id, "—————— 签到任务已成功完成（之前已签到） ——————")
                    return True

            error_details = str(e).replace('\n', ' ')
            message = f"签到异常: {error_details}"
            log_util.error(self.user_id, message, exc_info=True)
            return message

    def pharos_task_zenith_swap(self):
        """
        Zenith Swap任务：默认会swap PHRS到USDC，然后会swap回来。
        """
        log_util.info(self.user_id, "开始执行Zenith Swap任务...")
        swap_page = None
        try:
            # 步骤1: 打开新的SWAP_URL页面
            swap_page = self.browser.new_tab(self.ZENITH_SWAP_URL)

            # 步骤2: 人性化等待和页面刷新
            AntiSybilDpUtil.human_long_wait()
            swap_page.refresh()
            swap_page.wait.load_start()
            AntiSybilDpUtil.human_short_wait()

            # 步骤3: 检查钱包是否已连接（新逻辑）
            # 优先查找页面上是否已有 "0x" 开头的地址，这是已连接的明确标志
            address_element = swap_page.ele('xpath://span[starts-with(text(), "0x")]', timeout=10)
            if not (address_element and address_element.states.is_displayed):
                # 如果未找到地址，则执行连接钱包的流程
                connect_btn = swap_page.ele(
                    'xpath://button[@data-testid="navbar-connect-wallet"]',
                    timeout=15
                )
                if connect_btn and connect_btn.states.is_displayed:
                    connect_btn.click()
                    AntiSybilDpUtil.human_short_wait()
                    if not self.okx_util.click_OKX_in_selector2(self.browser, swap_page, self.user_id):
                        message = "执行OKX钱包连接流程失败。"
                        log_util.error(self.user_id, message)
                        return message
                else:
                    # 如果连 "Connect" 按钮也找不到，说明页面可能有问题
                    message = "未找到钱包地址，也未找到'Connect'按钮，页面异常。"
                    log_util.error(self.user_id, message)
                    return message

            # 步骤4: 等待代币数量加载
            swap_page.wait.doc_loaded()
            AntiSybilDpUtil.human_short_wait()
            AntiSybilDpUtil.simulate_mouse_move(swap_page)

            # 步骤5: 模拟向下滚动，然后点击“Select token”按钮 (B Token)
            swap_page.scroll.down(300)
            AntiSybilDpUtil.human_short_wait()
            select_token_btn = swap_page.ele(
                'xpath://button[contains(@class, "open-currency-select-button") and .//span[text()="Select token"]]', timeout=10
            ) # type: ignore
            if not (select_token_btn and select_token_btn.states.is_displayed):
                message = "未找到'Select token'按钮。"
                log_util.error(self.user_id, message)
                return message
            select_token_btn.click()
            AntiSybilDpUtil.human_short_wait()

            # 步骤6: 在弹窗中选择USDC
            usdc_option = swap_page.ele('xpath://div[@data-testid="common-base-USDC"]', timeout=10) # type: ignore
            if not (usdc_option and usdc_option.states.is_displayed):
                message = "未找到'USDC'选项。"
                log_util.error(self.user_id, message)
                return message
            usdc_option.click()
            AntiSybilDpUtil.human_short_wait()

            # 步骤7: 在PHRS输入框中输入金额
            amount_input = swap_page.ele('xpath://input[@id="swap-currency-input"]', timeout=10)
            if not amount_input:
                message = "未找到金额输入框。"
                log_util.error(self.user_id, message)
                return message
            # 采用“点击->清空->输入”的终极策略来处理顽固输入框
            amount_input.click()
            AntiSybilDpUtil.human_brief_wait()
            amount_input.clear()
            AntiSybilDpUtil.human_brief_wait()
            random_amount_str = AntiSybilDpUtil.get_perturbation_number(0.006, 0.001)
            AntiSybilDpUtil.simulate_typing(swap_page, random_amount_str)

            # 步骤8: 等待兑换率计算完成
            swap_page.wait.doc_loaded()
            AntiSybilDpUtil.human_huge_wait() # 使用长等待，给网页足够的时间返回汇率

            # 步骤9: 点击Swap按钮
            swap_btn = swap_page.ele('#swap-button', timeout=30)
            if not (swap_btn and swap_btn.states.is_clickable):
                message = "未能等到Swap按钮出现。"
                log_util.error(self.user_id, message)
                return message
            swap_btn.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_long_wait()

            # 步骤10: 在弹窗中点击 "Confirm Swap" 
            confirm_swap_btn = swap_page.ele('#confirm-swap-or-send', timeout=30)
            if not confirm_swap_btn:
                message = "未能等到Confirm Swap按钮出现。"
                log_util.error(self.user_id, message)
                return message
            confirm_swap_btn.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_long_wait()

            # 步骤10.1: 增加“Try again”的重试逻辑
            for i in range(3):
                try_again_btn = swap_page.ele('text:Try again', timeout=5)
                if try_again_btn:
                    try_again_btn.click()
                    AntiSybilDpUtil.human_short_wait()
                else:
                    break
            else:
                # 如果循环3次都执行完了（即按钮一直存在），则任务失败
                message = "测试网拥堵，反复try again"
                log_util.error(self.user_id, message)
                return message

            # 步骤11: 处理OKX钱包交易确认
            confirmation_result =  self.okx_util.confirm_transaction_drission(self.browser, self.user_id)
            if isinstance(confirmation_result, str):
                return confirmation_result
            AntiSybilDpUtil.human_huge_wait()
            AntiSybilDpUtil.simulate_mouse_move(swap_page)

            # 步骤12: 等待网页执行swap，然后通过点击空白处关闭swap成功的弹窗
            AntiSybilDpUtil.simulate_random_click(swap_page, self.user_id)
            self.page.wait.doc_loaded()

            # 步骤13: 点击对调按钮，然后将usdc换回PHRS，再次执行步骤7后面逻辑
            swap_currency_button = swap_page.ele('xpath://div[@data-testid="swap-currency-button"]', timeout=10)
            swap_currency_button.click()  # 点击按钮
            AntiSybilDpUtil.human_short_wait()

            max_btn = swap_page.ele('@name=Swap Max Token Amount Selected', timeout=10)
            if max_btn:
                max_btn.click()
            else:
                new_amount_input = swap_page.ele('xpath://input[@id="swap-currency-input"]', timeout=10)
                new_amount_input.click()
                AntiSybilDpUtil.human_brief_wait()
                new_amount_input.clear()
                AntiSybilDpUtil.human_brief_wait()
                random_amount_str = AntiSybilDpUtil.get_perturbation_number(10, 2)
                AntiSybilDpUtil.simulate_typing(swap_page, random_amount_str)

            swap_page.wait.doc_loaded()
            AntiSybilDpUtil.human_long_wait()

            swap_btn2 = swap_page.ele('#swap-button', timeout=30)
            swap_btn2.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_huge_wait()

            new_confirm_swap_btn = swap_page.ele('#confirm-swap-or-send', timeout=30)
            new_confirm_swap_btn.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_long_wait()

            # 第二次Swap后的“Try again”重试逻辑
            for i in range(3):
                try_again_btn = swap_page.ele('text:Try again', timeout=5)
                if try_again_btn:
                    try_again_btn.click()
                    AntiSybilDpUtil.human_short_wait()
                else:
                    break
            else:
                # 如果循环3次都执行完了（即按钮一直存在），则任务失败
                message = "测试网拥堵，反复try again"
                log_util.error(self.user_id, message)
                return message

            confirmation_result =  self.okx_util.confirm_transaction_drission(self.browser, self.user_id)
            if isinstance(confirmation_result, str):
                return confirmation_result
            AntiSybilDpUtil.human_huge_wait()

            log_util.info(self.user_id, "—————— Swap任务已成功完成 ——————")
            return True

        except Exception as e:
            if "ElementNotFoundError" in e.__class__.__name__:
                message = "测试网卡顿，未找到目标按钮"
            else:
                error_details = str(e).replace('\n', ' ')
                message = f"Zenith Swap发生错误: {error_details}"
            log_util.error(self.user_id, message, exc_info=True)
            return message
        finally:
            # 任务结束后关闭页面
            if swap_page and swap_page.tab_id in self.browser.tab_ids:
                swap_page.close()

    def pharos_task_faro_swap(self):
        """
        Faro Swap任务：打开新页面，连接钱包，并将PHRS兑换为USDT。
        """
        log_util.info(self.user_id, "开始执行Faro Swap任务...")
        swap_page = None
        try:
            # 步骤1: 打开新的SWAP_URL页面
            swap_page = self.browser.new_tab(self.FARO_SWAP_URL)
            AntiSybilDpUtil.human_huge_wait()

            # 步骤2: 检查并连接钱包
            connected_button = swap_page.ele('xpath://button[contains(text(), "0x")]', timeout=5)
            pending_button = swap_page.ele('button:has-text("pending")', timeout=5)
            if not ((connected_button and connected_button.states.is_displayed) or (pending_button and pending_button.states.is_displayed)):
                connect_btn = swap_page.ele('xpath://button[contains(text(), "Connect a wallet")]', timeout=10)
                connect_btn.click()
                AntiSybilDpUtil.human_short_wait()
                self.okx_util.click_OKX_in_selector(self.browser, swap_page, self.user_id)

            swap_page.actions.key_down("Escape")
            time.sleep(0.1)
            swap_page.actions.key_up("Escape")

            # 步骤3: 确保要卖出的代币是 PHRS
            from_token_selector = swap_page.ele('xpath:(//div[contains(@class, "css-70qvj9")])[1]', timeout=10)
            current_from_token = from_token_selector.s_ele('xpath:./div[1]').text
            if current_from_token != "PHRS":
                from_token_selector.click()
                AntiSybilDpUtil.human_short_wait()
                phrs_option = swap_page.ele('xpath://div[text()="PHRS"]', timeout=10)
                phrs_option.click()
                AntiSybilDpUtil.human_short_wait()

            # 步骤4: 确保要接收的代币是 USDT
            to_token_selector = swap_page.ele('xpath:(//div[contains(@class, "css-70qvj9")])[2]', timeout=10)
            current_to_token = to_token_selector.s_ele('xpath:./div[1]').text
            if current_to_token != "USDT":
                to_token_selector.click()
                AntiSybilDpUtil.human_short_wait()
                usdt_option = swap_page.ele('xpath://div[text()="USDT"]', timeout=10)
                usdt_option.click()
                AntiSybilDpUtil.human_short_wait()

            # 步骤5: 输入要兑换的金额
            amount_input = swap_page.ele('css:input.css-1fkmsfz', timeout=10)
            amount_input.click()
            AntiSybilDpUtil.human_brief_wait()
            random_amount_str = AntiSybilDpUtil.get_perturbation_number(0.006, 0.001)
            AntiSybilDpUtil.simulate_typing(swap_page, random_amount_str)
            AntiSybilDpUtil.human_long_wait()

            # 步骤6: 点击 Review Swap 按钮 (在15秒内持续查找)
            review_button = swap_page.ele('xpath://button[@data-testid="swap-review-btn"]', timeout=30)
            if not review_button:
                message = "未能等到faro的'Review Swap'按钮出现。"
                log_util.error(self.user_id, message)
                return message
            review_button.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_short_wait()

            # 步骤7: 点击 Confirm Swap 按钮 (在15秒内持续查找)
            confirm_button = swap_page.ele("xpath://button[text()='Confirm swap']", timeout=30)
            if not confirm_button:
                message = "未能等到faro的'Confirm Swap'按钮出现。"
                log_util.error(self.user_id, message)
                return message
            confirm_button.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_long_wait()

            # 步骤8: 处理钱包交易确认
            self.okx_util.confirm_transaction_drission(self.browser, self.user_id)
            AntiSybilDpUtil.human_huge_wait()

            swap_page.actions.key_down("Escape")
            time.sleep(0.1)
            swap_page.actions.key_up("Escape")
            AntiSybilDpUtil.simulate_random_click(swap_page, self.user_id)

            # 步骤9: 点击代币对调按钮
            arrow_btn = swap_page.ele(
                'css:button:has(> svg[data-testid="ArrowBackIcon"])', timeout=10
            )
            arrow_btn.run_js("this.click()")
            AntiSybilDpUtil.human_short_wait()

            # 步骤10: 点击Max按钮
            max_button = swap_page.ele('xpath://button[normalize-space()="Max"]', timeout=10)
            max_button.click()
            AntiSybilDpUtil.human_short_wait()

            # 步骤11: 再次swap
            review_button = swap_page.ele('xpath://button[@data-testid="swap-review-btn"]', timeout=30)
            review_button.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_short_wait()

            confirm_button = swap_page.ele("xpath://button[text()='Confirm swap']", timeout=30)
            confirm_button.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_long_wait()

            self.okx_util.confirm_transaction_drission(self.browser, self.user_id)
            AntiSybilDpUtil.human_huge_wait()
            log_util.info(self.user_id, "—————— Faro Swap任务已成功完成 ——————")
            return True

        except Exception as e:
            if "ElementNotFoundError" in e.__class__.__name__:
                message = "测试网卡顿，未找到目标按钮"
            else:
                error_details = str(e).replace('\n', ' ')
                message = f"Faro Swap错误: {error_details}"
            log_util.error(self.user_id, message, exc_info=True)
            return message
        finally:
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
            self.page.wait.load_start()
            AntiSybilDpUtil.human_short_wait()
            self._handle_switch_network_popup(self.page)
            AntiSybilDpUtil.simulate_mouse_move(self.page)
            self.page.scroll.down(800)
            AntiSybilDpUtil.human_short_wait()
            send_button = self.page.ele('xpath://button[text()="Send"]', timeout=20)
            if not send_button:
                message = "发送代币任务失败：未找到'Send'按钮。"
                log_util.error(self.user_id, message)
                return message

            # 步骤2: 点击Send按钮
            self.page.actions.click(send_button)
            AntiSybilDpUtil.human_long_wait()
            # 步骤3: 点击金额选项
            amount_option = self.page.ele('xpath://div[text()="0.001PHRS"]', timeout=30) # type: ignore
            if not amount_option or not amount_option.states.is_displayed:
                message = "发送代币任务失败：未找到'0.001PHRS'金额选项。"
                log_util.error(self.user_id, message)
                return message
            amount_option.click()
            AntiSybilDpUtil.human_short_wait()
            self.page.wait.doc_loaded()
            # 步骤4: 输入随机地址
            address_input = self.page.ele('xpath://input[@placeholder="Enter Address"]', timeout=10) # type: ignore
            if not address_input or not address_input.states.is_displayed:
                message = "发送代币任务失败：未找到地址输入框。"
                log_util.error(self.user_id, message)
                return message
            random_address = self.wallet_util.generate_random_evm_address()
            address_input.input(random_address)
            AntiSybilDpUtil.human_long_wait()

            # 步骤5: 点击最终的“Send PHRS”按钮
            final_send_button = self.page.ele('xpath://button[text()="Send PHRS"]', timeout=10) # type: ignore
            if not final_send_button or not final_send_button.states.is_clickable:
                message = "发送代币任务失败：未找到'Send PHRS'按钮。"
                log_util.error(self.user_id, message)
                return message
            # 按钮在页面之外，又不能滚动去显示按钮，只能js
            final_send_button.run_js('this.click()')
            AntiSybilDpUtil.human_long_wait()

            # 步骤6: 处理钱包确认
            if not self.okx_util.confirm_transaction_drission(self.browser, self.user_id):
                message = "发送代币任务失败：钱包交易确认失败。"
                log_util.error(self.user_id, message)
                return message
            
            log_util.info(self.user_id, "—————— 发送代币任务已成功完成 ——————")
            AntiSybilDpUtil.human_long_wait()
            AntiSybilDpUtil.simulate_random_click(self.page, self.user_id)
            AntiSybilDpUtil.human_brief_wait()
            return True

        except Exception as e:
            error_details = str(e).replace('\n', ' ')
            message = f"发送代币错误: {error_details}"
            log_util.error(self.user_id, message, exc_info=True)
            return message

    def pharos_task_buy_web3_name(self):
        """
        购买Pharos的Web3用户名。
        """
        log_util.info(self.user_id, "开始执行购买Web3用户名任务...")
        name_page = None
        try:
            # 步骤1: 获取或打开NAME_URL页面
            tabs = self.browser.get_tabs(url=self.NAME_URL)
            if tabs:
                name_page = tabs[0]
                name_page.set.activate()
                name_page.refresh()
            else:
                name_page = self.browser.new_tab(self.NAME_URL)
            
            name_page.wait.load_start()
            AntiSybilDpUtil.human_short_wait()

            # 步骤2: 确保钱包已连接
            profile_element = name_page.ele('xpath://div[@data-testid="header-profile"]', timeout=10)
            if not profile_element:
                log_util.info(self.user_id, "钱包未连接，开始连接流程...")
                connect_btn = name_page.ele('xpath://*[text()="连接" or text()="Connect"]', timeout=10)
                if connect_btn:
                    connect_btn.click()
                    AntiSybilDpUtil.human_short_wait()
                    self.okx_util.click_OKX_in_selector(self.browser, name_page, self.user_id)
                    AntiSybilDpUtil.human_short_wait()
            
            # 步骤3: 循环查找可用用户名并注册
            name_page.scroll.down(80)
            name_input = name_page.ele('xpath://input[@id="thorin2"]', timeout=10)
            today = datetime.now()
            weekday = today.isoweekday()

            for i in range(5):  # 最多尝试5次
                # 生成并输入新名称
                user_name = WalletUtil.get_a_random_word() + str(weekday) + ".phrs"
                name_input.clear()
                AntiSybilDpUtil.simulate_typing(name_page, user_name, self.user_id)
                AntiSybilDpUtil.human_long_wait()

                # 等待异步验证结果
                unavailable_notice = name_page.ele('xpath://*[text()="不可用" or text()="Not Supported"] or text()="Unavailable"]', timeout=10)
                if unavailable_notice:
                    continue  # 名称不可用，直接开始下一次循环

                available_button = name_page.ele('xpath://*[text()="可注册" or text()="Available"]', timeout=10)
                if available_button:
                    available_button.click()
                    AntiSybilDpUtil.human_long_wait()
                    break

            # 步骤4: 修改时间
            name_page.scroll.down(150)
            AntiSybilDpUtil.human_brief_wait()
            w, h = name_page.rect.viewport_size
            name_page.actions.move_to((int(w * 0.4), int(h * 0.3)))
            AntiSybilDpUtil.human_brief_wait()
            date_choose_btn = name_page.ele("xpath://button[text()='Pick by date']", timeout=20)
            date_choose_btn.click()
            AntiSybilDpUtil.human_short_wait()
            calendar_input = name_page.ele('#calendar', timeout=10)
            calendar_input.click()
            AntiSybilDpUtil.human_short_wait()
            # 日历控件只能循环按方向键
            actions = name_page.actions
            for _ in range(55):
                actions.key_down('up')
                actions.key_up('up')
                time.sleep(0.08)
            AntiSybilDpUtil.human_short_wait()
            name_page.actions.key_down('enter').key_up('enter')
            AntiSybilDpUtil.human_short_wait()

            gas_text = name_page.ele('@data-testid=invoice-total').child('tag:div').text
            if not gas_text.startswith('0.0'):
                message = "gas费异常，大于0.1"
                return message

            # 步骤5: 准备购买域名
            name_page.scroll.to_bottom()
            AntiSybilDpUtil.human_short_wait()
            next_btn = name_page.ele('@data-testid=next-button', timeout=10)
            next_btn.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_short_wait()
            begin_btn = name_page.ele('xpath://button[contains(.,"Begin")]', timeout=10)
            begin_btn.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_short_wait()

            # 步骤6: okx交易
            open_wallet_btn = name_page.ele('@data-testid=transaction-modal-confirm-button', timeout=20)
            open_wallet_btn.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_short_wait()
            confirmation_result =  self.okx_util.confirm_transaction_drission(self.browser, self.user_id)
            if isinstance(confirmation_result, str):
                return confirmation_result

            # 步骤7: 交易失败
            recomplete_btn = name_page.ele('@data-testid=finish-button', timeout=65)
            if recomplete_btn and recomplete_btn.states.is_clickable:
                recomplete_btn.wait.clickable(timeout=20).click()
                AntiSybilDpUtil.human_short_wait()
                open_wallet_btn2 = name_page.ele('@data-testid=transaction-modal-confirm-button', timeout=20)
                open_wallet_btn2.wait.clickable(timeout=20).click()
                AntiSybilDpUtil.human_short_wait()
                confirmation_result2 = self.okx_util.confirm_transaction_drission(self.browser, self.user_id)
                if isinstance(confirmation_result2, str):
                    return confirmation_result2
            log_util.info(self.user_id, "—————— 购买Web3用户名任务成功 ——————")
            return True

        except Exception as e:
            error_details = str(e).replace('\n', ' ')
            message = f"购买Web3用户名任务执行时发生意外错误: {error_details}"
            log_util.error(self.user_id, message, exc_info=True)
            return message
        finally:
            if name_page and name_page.tab_id in self.browser.tab_ids:
                name_page.close()

    def pharos_task_cfd_trading(self):
        """
        不支持6开及以上！！！需要自己领水。
        """
        log_util.info(self.user_id, "开始执行cfd trading任务...")
        cfd_trading_page = None
        message = None
        try:
            # 步骤1: 获取或打开NAME_URL页面
            cfd_trading_page = self.browser.new_tab(self.CFD_URL)
            AntiSybilDpUtil.human_long_wait()
            if cfd_trading_page.ele('text:contains=Brokex Protocol is currently not available on mobile'):
                return False
            # 步骤2: 滚动页面
            scroll_container = cfd_trading_page.ele('.div-block-487', timeout=5)
            if scroll_container:
                scroll_container.scroll.to_bottom()
            AntiSybilDpUtil.human_short_wait()
            # 步骤3: 点击Open Position按钮
            execute_order_btn = cfd_trading_page.ele('xpath://*[@id="btnOpenPosition" and contains(text(), "Execute the order")]', timeout=10)
            if execute_order_btn and execute_order_btn.states.is_clickable:
                click_success = False
                # 点击交易对
                for _ in range(3):
                    try:
                        pair_buttons_div = cfd_trading_page.ele('#pair-buttons', timeout=5)
                        if pair_buttons_div:
                            first_pair_link = pair_buttons_div.ele('tag:a', timeout=5)
                            if first_pair_link and first_pair_link.states.is_clickable:
                                first_pair_link.wait.clickable(timeout=20).click()
                                AntiSybilDpUtil.human_short_wait()
                                click_success = True
                                break
                    except:
                        AntiSybilDpUtil.human_short_wait()
                        pass
                if not click_success:
                    return "尝试3次后仍无法点击交易对，任务失败。"
                
                execute_order_btn.wait.clickable(timeout=20).click()
                AntiSybilDpUtil.human_short_wait()
            # 点击 open position
            final_open_position_btn = cfd_trading_page.ele('xpath://*[@id="btnOpenPosition" and contains(text(), "Open Position")]', timeout=10)
            final_open_position_btn.wait.clickable(timeout=20).click()
            AntiSybilDpUtil.human_short_wait()

            # 步骤4: okx钱包确认
            if not self.okx_util.confirm_transaction_drission(self.browser, self.user_id):
                message = "cfd trading失败：钱包交易确认失败。"
                log_util.error(self.user_id, message)
                return message
            AntiSybilDpUtil.human_long_wait()
            return True
        except Exception as e:
            error_details = str(e).replace('\n', ' ')
            message = f"cfd trading发生错误: {error_details}"
            log_util.error(self.user_id, message, exc_info=True)
            return message
        finally:
            if cfd_trading_page and cfd_trading_page.tab_id in self.browser.tab_ids:
                cfd_trading_page.close()


if __name__ == "__main__":
    # 这个脚本现在是一个库，不应该被直接运行。
    print(
        "PharosScript 定义完成。请在您的主程序中实例化，或通过 pharosScript_test.py 进行测试。"
    )

