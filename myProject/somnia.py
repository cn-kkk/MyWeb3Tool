from util.okx_wallet_util import OKXWalletUtil
from util.anti_sybil_dp_util import AntiSybilDpUtil
from util.log_util import log_util
from util.wallet_util import WalletUtil


class SomniaScript:
    """
    Somnia项目的脚本类。
    """

    project_name = "Somnia"
    SOMNIA_URL = "https://testnet.somnia.network/"

    def __init__(self, browser, user_id: str):
        self.browser = browser
        self.user_id = user_id
        self.okx_util = OKXWalletUtil()
        self.wallet_util = WalletUtil()

        log_util.info(self.user_id, f"开始初始化项目: {self.project_name}")

        # 步骤1: 注入反女巫脚本
        page_for_cdp = self.browser.get_tab() or self.browser.new_tab('about:blank')
        AntiSybilDpUtil.patch_webdriver_fingerprint(page_for_cdp)
        if not self.browser.get_tabs(url=self.SOMNIA_URL):
            page_for_cdp.close()

        # 步骤2: 获取或打开目标页面
        tabs = self.browser.get_tabs(url=self.SOMNIA_URL)
        if tabs:
            self.page = tabs[0]
            self.page.set.activate()
            self.page.refresh()
        else:
            self.page = self.browser.new_tab(self.SOMNIA_URL)
        self.page.wait.load_start()

        # 步骤3: 人性化交互
        AntiSybilDpUtil.human_long_wait()
        AntiSybilDpUtil.simulate_mouse_move(self.page)

        # 步骤4: 连接钱包
        log_util.info(self.user_id, "开始连接钱包...")
        # 查找所有名为Connect的按钮，并获取第一个可点击的
        connect_buttons = self.page.eles('text:Connect')
        clickable_button = next((btn for btn in connect_buttons if btn.states.is_clickable), None)

        # 如果没有找到，则尝试通过菜单按钮
        if not clickable_button:
            self.page.ele('css:.lucide-menu').parent('tag:button').click()
            AntiSybilDpUtil.human_brief_wait()
            connect_buttons = self.page.eles('text:Connect')
            clickable_button = next(btn for btn in connect_buttons if btn.states.is_clickable)

        clickable_button.click()
        AntiSybilDpUtil.human_short_wait()

        # 步骤5: 选择OKX钱包并确认
        log_util.info(self.user_id, "选择OKX钱包...")
        self.page.ele('text:OKX Wallet').click()
        AntiSybilDpUtil.human_short_wait()
        self.okx_util.confirm_transaction_drission(self.browser, self.user_id)

        log_util.info(self.user_id, f"项目 '{self.project_name}' 初始化成功。")


if __name__ == "__main__":
    print("SomniaScript 定义完成。请在您的主程序中实例化，或通过 SomniaScript_test.py 进行测试。")