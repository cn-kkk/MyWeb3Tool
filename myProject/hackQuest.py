from util.anti_sybil_dp_util import AntiSybilDpUtil
from util.log_util import log_util
from util.okx_wallet_util import OKXWalletUtil
from annotation.task_annotation import task_annotation

class HackQuestScript:
    """
    HackQuest项目的脚本类。
    """

    project_name = "HackQuest"
    HACK_QUEST_URL = "https://www.hackquest.io/zh-cn/quest"

    def __init__(self, browser, user_id: str, window_height: int = 800):
        """
        项目级初始化。
        此方法负责打开项目页面并执行必要的初始交互。
        """
        self.browser = browser
        self.user_id = user_id
        self.window_height = window_height
        self.okx_util = OKXWalletUtil()

        try:
            # 步骤1: 为浏览器实例注入反女巫检测脚本
            page_for_cdp = self.browser.get_tab()
            if not page_for_cdp:
                page_for_cdp = self.browser.new_tab('about:blank')
                AntiSybilDpUtil.patch_webdriver_fingerprint(page_for_cdp)
                page_for_cdp.close()
            else:
                AntiSybilDpUtil.patch_webdriver_fingerprint(page_for_cdp)

            # 步骤2: 获取HackQuest主页的页面对象
            tabs = self.browser.get_tabs(url=self.HACK_QUEST_URL)
            if tabs:
                self.page = tabs[0]
                self.page.set.activate()
                self.page.refresh()
            else:
                self.page = self.browser.new_tab(self.HACK_QUEST_URL)

            # 步骤3: 等待页面加载并执行反女巫模拟真人操作
            self.page.wait.load_start()
            AntiSybilDpUtil.human_long_wait()
            AntiSybilDpUtil.simulate_random_click(self.page, self.user_id)
            AntiSybilDpUtil.human_brief_wait()
            AntiSybilDpUtil.simulate_mouse_move(self.page)

            log_util.info(self.user_id, f"任务成功: 项目 '{self.project_name}' 初始化成功")
        except Exception as e:
            log_util.error(self.user_id, f"异常: 项目 '{self.project_name}' 初始化失败: {e}")
            raise

    @task_annotation.once_per_day
    def hackquest_task_check_in(self):
        log_util.info(self.user_id, f"任务开始: {self.project_name} - 每日签到")
        try:
            quest_page = self.browser.get_tab(url=self.HACK_QUEST_URL)
            if not quest_page:
                quest_page = self.browser.new_tab(self.HACK_QUEST_URL)
                quest_page.wait.load_start()
                AntiSybilDpUtil.human_long_wait()

            # 步骤1: 使用“当前连续登录”作为锚点，定位到任务的div容器
            check_in_container = quest_page.ele('tag:div:text:当前连续登录', timeout=20)
            # 检查任务是否已经完成
            if "已领取" in check_in_container.text:
                return True

            # 步骤2: 在容器内部查找并点击“领取”按钮
            check_in_btn = check_in_container.ele('tag:button:text:领取')
            check_in_btn.click()

            # 步骤3: 刷新页面
            AntiSybilDpUtil.human_short_wait()
            quest_page.refresh()
            quest_page.wait.load_start()
            AntiSybilDpUtil.human_long_wait()
            re_check_container = quest_page.ele('tag:div:text:当前连续登录', timeout=20)
            if re_check_container and "已领取" in re_check_container.text:
                return True
            else:
                return False

        except Exception as e:
            error_details = str(e).replace('\n', ' ')
            message = f"异常: {self.project_name} - 每日签到失败: {error_details}"
            log_util.error(self.user_id, message, exc_info=True)
            return message


if __name__ == "__main__":
    # 这个脚本现在是一个库，不应该被直接运行。
    print(
        "HackQuest 定义完成。请在您的主程序中实例化，或通过相应测试脚本进行测试。"
    )
