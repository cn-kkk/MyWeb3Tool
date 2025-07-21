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
        pharos_tab = self.browser.get_tab(url=self.PHAROS_URL)
        if pharos_tab:
            LogUtil.info(self.user_id, f"找到已打开的Pharos页面，切换并刷新。")
            self.page = pharos_tab
            self.page.refresh()
            self.page.wait.load_start()
        else:
            LogUtil.info(self.user_id, f"未找到Pharos页面，新建标签页打开: {self.PHAROS_URL}")
            self.page = self.browser.new_tab(self.PHAROS_URL)

        # 步骤2: 最大化窗口
        # LogUtil.info(self.user_id, "步骤2: 最大化浏览器窗口。")
        # self.page.set.window.max()

        # 步骤3: 人性化等待和交互
        LogUtil.info(self.user_id, "步骤3: 等待页面加载并模拟交互...")
        AntiSybilDpUtil.human_long_wait(self.user_id)
        AntiSybilDpUtil.simulate_random_click(self.page, self.user_id)
        AntiSybilDpUtil.human_short_wait(self.user_id)

        # 步骤4: 解锁钱包
        LogUtil.info(self.user_id, "步骤4: 开始解锁钱包...")
        if not self.okx_util.open_and_unlock_drission(self.browser, self.user_id):
            error_msg = "解锁钱包失败，初始化终止。"
            LogUtil.error(self.user_id, error_msg)
            raise RuntimeError(error_msg)

        LogUtil.info(self.user_id, f"项目 '{self.project_name}' 初始化成功。")

    def task_check_in(self):
        """
        Pharos网页签到任务：自动查找并点击Check in按钮，然后刷新页面并验证状态。
        基于DrissionPage技术栈实现
        """
        LogUtil.info(self.user_id, "开始执行签到任务...")
        try:
            # 增加显式等待，确保页面完全加载
            self.page.wait.load_start()
            LogUtil.info(self.user_id, "页面加载完成，开始查找签到按钮...")

            # 查找 "Check in" 按钮
            checkin_btn = self.page.ele(
                'xpath://button[contains(text(), "Check in")]', timeout=20
            )

            # 如果找到 "Check in" 按钮，则执行签到
            if checkin_btn and checkin_btn.states.is_displayed:
                LogUtil.info(self.user_id, "签到按钮已找到，尝试点击...")
                checkin_btn.click()
                LogUtil.info(self.user_id, "已自动点击Check in签到按钮。")

                # 等待后端处理，然后刷新页面
                LogUtil.info(self.user_id, "等待2秒后刷新页面以确认状态...")
                AntiSybilDpUtil.human_short_wait(self.user_id)
                self.page.refresh()
                self.page.wait.load_start()
                LogUtil.info(self.user_id, "页面已刷新。")

            # 刷新后，验证按钮状态是否变为 "Checked"
            LogUtil.info(self.user_id, "验证签到状态...")
            checked_btn = self.page.ele(
                'xpath://button[contains(text(), "Checked")]', timeout=10
            )

            if checked_btn and checked_btn.states.is_displayed:
                LogUtil.info(self.user_id, "签到成功！按钮状态已更新为 'Checked'。")
                return True
            else:
                # 如果刷新后没找到 "Checked" 按钮，再检查一下 "Check in" 按钮是否还在
                checkin_still_exists = self.page.ele(
                    'xpath://button[contains(text(), "Check in")]', timeout=5
                )
                if checkin_still_exists:
                    LogUtil.warn(self.user_id, "签到失败，按钮状态未改变。")
                else:
                    LogUtil.warn(self.user_id, "未找到'Checked'按钮，状态未知，但'Check in'按钮已消失。")
                return False

        except Exception as e:
            # 捕获所有异常，包括查找 "Check in" 按钮超时
            # 如果超时，很可能意味着已经签到过了
            if "Timeout" in str(e):
                LogUtil.info(self.user_id, "未找到 'Check in' 按钮，检查是否已签到...")
                checked_btn = self.page.ele(
                    'xpath://button[contains(text(), "Checked")]', timeout=5
                )
                if checked_btn and checked_btn.states.is_displayed:
                    LogUtil.info(self.user_id, "任务已完成，按钮状态为 'Checked'。")
                    return True
            
            LogUtil.error(self.user_id, f"签到任务执行期间发生意外错误: {e}")
            return False

    def task_swap(self):
        """
        Pharos网页Swap任务：自动查找并点击Swap按钮
        基于DrissionPage技术栈实现
        """
        LogUtil.info(self.user_id, "开始执行Swap任务...")

        try:
            # 等待Swap按钮出现并可点击
            swap_btn = self.page.ele(
                'xpath://button[contains(@class, "beZyFg") and text()="Swap"]',
                timeout=15,
            )

            if not swap_btn:
                # 尝试其他可能的Swap按钮选择器
                swap_btn = self.page.ele(
                    'xpath://button[contains(text(), "Swap")]', timeout=5
                )

            if swap_btn:
                # 反女巫：点击前模拟随机操作
                LogUtil.info(self.user_id, "模拟随机点击...")
                AntiSybilDpUtil.simulate_random_click(self.page, self.user_id)
                LogUtil.info(self.user_id, "模拟短时间等待...")
                AntiSybilDpUtil.human_short_wait(self.user_id)

                # 点击Swap按钮
                swap_btn.click()
                LogUtil.info(self.user_id, "已自动点击Swap按钮，等待新页面加载...")

                # 等待页面加载
                LogUtil.info(self.user_id, "模拟长时间等待...")
                AntiSybilDpUtil.human_long_wait(self.user_id)

                # 检查是否成功跳转到Swap页面
                if (
                    "swap" in self.page.url.lower()
                    or "exchange" in self.page.url.lower()
                ):
                    LogUtil.info(self.user_id, "成功跳转到Swap页面")
                else:
                    LogUtil.info(self.user_id, "Swap按钮已点击，等待页面响应")

                return True
            else:
                LogUtil.warn(self.user_id, "未找到Swap按钮，可能页面结构变化")
                return False

        except Exception as e:
            LogUtil.error(self.user_id, f"Swap任务执行失败: {e}")
            return False

    def task_send_tokens(self):
        """
        执行发送代币任务：滚动页面，点击发送，选择金额，输入随机地址，确认发送。
        """
        LogUtil.info(self.user_id, "开始执行发送代币任务...")
        try:
            # 刷新页面并等待加载
            LogUtil.info(self.user_id, "刷新页面并等待加载...")
            self.page.refresh()
            self.page.wait.load_start()
            LogUtil.info(self.user_id, "页面加载完成。")

            # 确保页面元素加载完成，等待“Send”按钮出现
            LogUtil.info(self.user_id, "等待'Send'按钮出现...")
            send_button = self.page.wait.ele_displayed('xpath://button[text()="Send"]', timeout=20)
            if not send_button:
                LogUtil.warn(self.user_id, "未找到'Send'按钮或按钮不可见。")
                return False

            # 1. 使用JS滚动到页面35%的位置
            js_code = "window.scrollTo(0, document.body.scrollHeight * 0.35);"
            self.page.run_js(js_code)
            LogUtil.info(self.user_id, "已滚动到页面35%位置。")
            AntiSybilDpUtil.human_short_wait(self.user_id)

            # 2. 点击Send按钮
            send_button.click()
            LogUtil.info(self.user_id, "已点击'Send'按钮。")
            AntiSybilDpUtil.human_short_wait(self.user_id)

            # 3. 点击金额选项
            amount_option = self.page.ele('xpath://div[text()="0.001PHRS"]', timeout=15)
            if not amount_option or not amount_option.states.is_displayed:
                LogUtil.warn(self.user_id, "未找到'0.001PHRS'金额选项。")
                return False

            amount_option.click()
            LogUtil.info(self.user_id, "已选择'0.001PHRS'金额。")
            AntiSybilDpUtil.human_short_wait(self.user_id)

            # 4. 输入地址
            address_input = self.page.ele('xpath://input[@placeholder="Enter Address"]', timeout=10)
            if not address_input or not address_input.states.is_displayed:
                LogUtil.warn(self.user_id, "未找到地址输入框。")
                return False

            random_address = self.wallet_util.generate_random_evm_address()
            LogUtil.info(self.user_id, f"生成的随机EVM地址: {random_address}")

            address_input.input(random_address)
            LogUtil.info(self.user_id, "已将地址输入到输入框。")
            AntiSybilDpUtil.human_short_wait(self.user_id)

            # 5. 点击最终的“Send PHRS”按钮
            final_send_button = self.page.ele('xpath://button[text()="Send PHRS"]', timeout=10)
            if not final_send_button or not final_send_button.states.is_displayed:
                LogUtil.warn(self.user_id, "未找到最终的'Send PHRS'按钮。")
                return False
            
            final_send_button.click()
            AntiSybilDpUtil.human_long_wait(self.user_id)
            LogUtil.info(self.user_id, "已点击最终的'Send PHRS'按钮。")

            # 6. 处理钱包确认
            if not self.okx_util.confirm_transaction_drission(self.browser, self.user_id):
                LogUtil.error(self.user_id, "钱包交易确认失败。")
                return False
            
            LogUtil.info(self.user_id, "发送代币任务执行成功。")
            AntiSybilDpUtil.human_long_wait(self.user_id)
            return True

        except Exception as e:
            LogUtil.error(self.user_id, f"发送代币任务执行失败: {e}")
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