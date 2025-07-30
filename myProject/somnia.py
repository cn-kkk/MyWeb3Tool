from DrissionPage import ChromiumPage
from util.okx_wallet_util import OKXWalletUtil
from util.anti_sybil_dp_util import AntiSybilDpUtil
from util.log_util import log_util
from util.wallet_util import WalletUtil
from annotation.task_annotation import task_annotation


class SomniaScript:
    """
    Somnia项目的脚本类。
    """

    project_name = "Somnia"
    SOMNIA_URL = "https://testnet.somnia.network/"

    def __init__(self, browser, user_id: str):
        """
        项目级初始化。
        此方法负责打开项目页面、连接钱包以及执行必要的初始交互。
        假定钱包已在更高层级（Worker）被解锁。
        """
        self.browser = browser
        self.user_id = user_id
        self.okx_util = OKXWalletUtil()
        self.wallet_util = WalletUtil()

        log_util.info(self.user_id, f"开始初始化项目: {self.project_name}")
        try:
            # 步骤1: 为浏览器实例注入反女巫检测脚本
            page_for_cdp = self.browser.get_tab()
            if not page_for_cdp:
                # 如果没有任何标签页，创建一个临时的
                page_for_cdp = self.browser.new_tab('about:blank')
                AntiSybilDpUtil.patch_webdriver_fingerprint(page_for_cdp)
                page_for_cdp.close() # 用完即可关闭
            else:
                AntiSybilDpUtil.patch_webdriver_fingerprint(page_for_cdp)

            # 步骤2: 现在可以安全地获取目标页面了
            log_util.info(self.user_id, f"正在获取目标页面: {self.SOMNIA_URL}")
            try:
                somnia_tab = self.browser.get_tab(url=self.SOMNIA_URL)
            except Exception:
                somnia_tab = None

            if somnia_tab:
                self.page = somnia_tab
                self.page.refresh() # 刷新会触发已注入的脚本
            else:
                self.page = self.browser.new_tab(self.SOMNIA_URL) # 新建页面同样会触发
            self.page.wait.load_start()

            # 步骤3: 人性化等待和交互
            AntiSybilDpUtil.human_long_wait()
            AntiSybilDpUtil.simulate_random_click(self.page, self.user_id)
            AntiSybilDpUtil.human_brief_wait()
            AntiSybilDpUtil.simulate_mouse_move(self.page)

            # 步骤4: 侦察页面上的所有按钮，以进行最终调试
            log_util.info(self.user_id, "--- 开始终极侦察：查找页面上的所有按钮 ---")
            all_buttons = self.page.eles('@@button')
            log_util.info(self.user_id, f"侦察完毕，共在页面上发现 {len(all_buttons)} 个按钮。")

            if not all_buttons:
                raise Exception("页面上未发现任何按钮元素。")

            for i, btn in enumerate(all_buttons):
                try:
                    btn_text = btn.text
                    btn_html = btn.outer_html
                    log_util.info(self.user_id, f"--- 按钮 {i+1} ---")
                    log_util.info(self.user_id, f"  - 文本: {btn_text}")
                    log_util.info(self.user_id, f"  - HTML: {btn_html}")
                except Exception as e:
                    log_util.error(self.user_id, f"获取按钮 {i+1} 的信息时出错: {e}")
            
            raise Exception("侦察任务完成，请检查日志输出。")
        except Exception as e:
            log_util.error(self.user_id, f"项目 '{self.project_name}' 初始化失败: {e}")
            raise


if __name__ == "__main__":
    # 这个脚本现在是一个库，不应该被直接运行。
    print(
        "SomniaScript 定义完成。请在您的主程序中实例化，或通过 SomniaScript_test.py 进行测试。"
    )
