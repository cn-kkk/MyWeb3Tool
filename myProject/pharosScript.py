import os
from DrissionPage import ChromiumPage
from util.okx_wallet_util import OKXWalletUtil
from util.anti_sybil_dp_util import AntiSybilDpUtil
from util.log_util import LogUtil
from util.wallet_util import WalletUtil


class PharosScript:
    """
    使用 DrissionPage 执行 Pharos 相关任务的脚本类。
    该类负责调用工具类来完成具体操作。
    """

    project_name = "Pharos"
    PHAROS_URL = "https://testnet.pharosnetwork.xyz/experience"
    SWAP_URL = "https://testnet.zenithfinance.xyz/swap"

    def __init__(self, browser, user_id: str):
        """
        初始化脚本，完成一系列准备工作。

        :param browser: 一个已经连接到浏览器的 DrissionPage.ChromiumBrowser 对象。
        :param user_id: 当前操作的浏览器 user_id，用于日志记录。
        """
        self.browser = browser
        self.user_id = user_id
        self.okx_util = OKXWalletUtil()
        self.wallet_util = WalletUtil()

        LogUtil.info(self.user_id, f"开始初始化项目: {self.project_name}")

        # 步骤1: 查找或创建项目标签页
        pharos_tab = None
        try:
            pharos_tab = self.browser.get_tab(url=self.PHAROS_URL)
        except Exception:
            # 找不到标签页是正常情况，下面会处理
            pass

        if pharos_tab:
            # 找到已打开的Pharos页面，切换并刷新
            self.page = pharos_tab
            self.page.refresh()
            self.page.wait.load_start()
        else:
            # 未找到Pharos页面，新建标签页打开
            self.page = self.browser.new_tab(self.PHAROS_URL)

        # 步骤2: 最大化窗口
        self.page.set.window.max()

        # 步骤3: 人性化等待和交互，并注入反指纹脚本
        AntiSybilDpUtil.human_long_wait()
        AntiSybilDpUtil.simulate_random_click(self.page)
        AntiSybilDpUtil.human_short_wait()
        AntiSybilDpUtil.patch_webdriver_fingerprint(self.page)

        # 步骤4: 解锁钱包
        LogUtil.info(self.user_id, "正在解锁钱包...")
        if not self.okx_util.open_and_unlock_drission(self.browser, self.user_id):
            error_msg = "解锁钱包失败，初始化终止。"
            LogUtil.error(self.user_id, error_msg)
            raise RuntimeError(error_msg)

        LogUtil.info(self.user_id, f"—————— 项目 '{self.project_name}' 初始化成功 ——————")

    def task_check_in(self):
        """
        Pharos网页签到任务：自动查找并点击Check in按钮，然后刷新页面并验证状态。
        基于DrissionPage技术栈实现
        """
        LogUtil.info(self.user_id, "开始执行签到任务...")
        try:
            # 步骤1: 等待页面加载并查找 "Check in" 按钮
            self.page.wait.load_start()
            checkin_btn = self.page.ele( # type: ignore
                'xpath://button[contains(text(), "Check in")]', timeout=20
            )

            # 步骤2: 如果找到按钮，则点击并刷新
            if checkin_btn and checkin_btn.states.is_displayed:
                checkin_btn.click()
                AntiSybilDpUtil.human_short_wait()
                self.page.refresh()
                self.page.wait.load_start()

            # 步骤3: 验证按钮状态是否变为 "Checked"
            checked_btn = self.page.ele( # type: ignore
                'xpath://button[contains(text(), "Checked")]', timeout=10
            )

            if checked_btn and checked_btn.states.is_displayed:
                LogUtil.info(self.user_id, "—————— 签到任务已成功完成 ——————")
                return True
            else:
                LogUtil.error(self.user_id, "签到任务失败：未找到'Checked'按钮，状态未知。")
                return False

        except Exception as e:
            # 捕获所有异常，包括查找 "Check in" 按钮超时
            # 如果超时，很可能意味着已经签到过了
            if "Timeout" in str(e):
                # 再次检查是否已签到
                checked_btn = self.page.ele( # type: ignore
                    'xpath://button[contains(text(), "Checked")]', timeout=5
                )
                if checked_btn and checked_btn.states.is_displayed:
                    LogUtil.info(self.user_id, "—————— 签到任务已成功完成（之前已签到） ——————")
                    return True
            
            LogUtil.error(self.user_id, f"签到任务执行期间发生意外错误: {e}")
            return False

    def task_swap(self):
        """
        重构后的Swap任务：打开新页面，连接钱包。
        """
        LogUtil.info(self.user_id, "开始执行Swap任务...")
        swap_page = None
        try:
            # 步骤1: 打开新的SWAP_URL页面
            swap_page = self.browser.new_tab(self.SWAP_URL)

            # 步骤2: 人性化等待和页面刷新
            AntiSybilDpUtil.human_long_wait()
            swap_page.refresh()
            swap_page.wait.load_start()
            AntiSybilDpUtil.human_short_wait()

            # 步骤3: 查找并点击 'Connect' 按钮
            connect_btn = swap_page.ele( # type: ignore
                'xpath://button[@data-testid="navbar-connect-wallet" and contains(text(), "Connect")]',
                timeout=20
            )

            if connect_btn and connect_btn.states.is_displayed:
                connect_btn.click()
                AntiSybilDpUtil.human_short_wait()

                # 步骤4: 调用OKX钱包工具类完成完整的连接流程
                if not self.okx_util.click_OKX_in_selector(self.browser, swap_page, self.user_id):
                    LogUtil.error(self.user_id, "Swap任务失败：执行OKX钱包连接流程失败。")
                    return False

                LogUtil.info(self.user_id, "—————— Swap任务已成功完成 ——————")
                return True
            else:
                LogUtil.error(self.user_id, "Swap任务失败：未找到'Connect'按钮。")
                return False

        except Exception as e:
            LogUtil.error(self.user_id, f"Swap任务执行时发生意外错误: {e}")
            return False
        finally:
            # 任务结束后可以考虑是否关闭swap_page
            if swap_page:
                swap_page.close()

    def task_send_tokens(self):
        """
        执行发送代币任务：滚动页面，点击发送，选择金额，输入随机地址，确认发送。
        """
        LogUtil.info(self.user_id, "开始执行发送代币任务...")
        try:
            # 步骤1: 刷新并等待'Send'按钮
            self.page.refresh()
            self.page.wait.load_start()
            send_button = self.page.wait.ele_displayed('xpath://button[text()="Send"]', timeout=20)
            if not send_button:
                LogUtil.error(self.user_id, "发送代币任务失败：未找到'Send'按钮。")
                return False

            # 步骤2: 滚动并点击Send按钮
            self.page.run_js("window.scrollTo(0, document.body.scrollHeight * 0.35);")
            AntiSybilDpUtil.human_short_wait()
            send_button.click()
            AntiSybilDpUtil.human_short_wait()

            # 步骤3: 点击金额选项
            amount_option = self.page.ele('xpath://div[text()="0.001PHRS"]', timeout=15) # type: ignore
            if not amount_option or not amount_option.states.is_displayed:
                LogUtil.error(self.user_id, "发送代币任务失败：未找到'0.001PHRS'金额选项。")
                return False
            amount_option.click()
            AntiSybilDpUtil.human_short_wait()

            # 步骤4: 输入随机地址
            address_input = self.page.ele('xpath://input[@placeholder="Enter Address"]', timeout=10) # type: ignore
            if not address_input or not address_input.states.is_displayed:
                LogUtil.error(self.user_id, "发送代币任务失败：未找到地址输入框。")
                return False
            random_address = self.wallet_util.generate_random_evm_address()
            address_input.input(random_address)
            AntiSybilDpUtil.human_short_wait()

            # 步骤5: 点击最终的“Send PHRS”按钮
            final_send_button = self.page.ele('xpath://button[text()="Send PHRS"]', timeout=10) # type: ignore
            if not final_send_button or not final_send_button.states.is_displayed:
                LogUtil.error(self.user_id, "发送代币任务失败：未找到'Send PHRS'按钮。")
                return False
            final_send_button.click()
            AntiSybilDpUtil.human_long_wait()

            # 步骤6: 处理钱包确认
            if not self.okx_util.confirm_transaction_drission(self.browser, self.user_id):
                LogUtil.error(self.user_id, "发送代币任务失败：钱包交易确认失败。")
                return False
            
            LogUtil.info(self.user_id, "—————— 发送代币任务已成功完成 ——————")
            AntiSybilDpUtil.human_long_wait()
            return True

        except Exception as e:
            LogUtil.error(self.user_id, f"发送代币任务执行时发生意外错误: {e}")
            return False

    def run(self):
        """
        运行所有任务的主方法
        """
        LogUtil.info(self.user_id, f"开始执行 {self.project_name} 的所有任务...")

        # 执行签到任务
        self.task_check_in()

        # 可以在这里添加更多任务
        # self.task_swap()

        LogUtil.info(self.user_id, f"项目 {self.project_name} 的所有任务已执行完毕。")


if __name__ == "__main__":
    # 这个脚本现在是一个库，不应该被直接运行。
    # 请运行 pharosScript_test.py 来进行测试。
    print(
        "PharosScript 定义完成。请在您的主程序中实例化，或通过 pharosScript_test.py 进行测试。"
    )