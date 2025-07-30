from datetime import datetime
from util.anti_sybil_dp_util import AntiSybilDpUtil
from util.log_util import log_util


class WardenScript:
    """
    Warden Protocol项目的脚本类。
    """

    project_name = "Warden"
    WARDEN_URL = "https://app.wardenprotocol.org/earn"
    WARDEN_AI_CHAT_URL = "https://app.wardenprotocol.org/dashboard"

    def __init__(self, browser, user_id: str):
        """
        项目级初始化。
        此方法负责打开项目页面并执行必要的初始交互。
        """
        self.browser = browser
        self.user_id = user_id

        log_util.info(self.user_id, f"任务开始: 初始化项目 {self.project_name}")
        try:
            # 步骤1: 为浏览器实例注入反女巫检测脚本
            page_for_cdp = self.browser.get_tab()
            if not page_for_cdp:
                page_for_cdp = self.browser.new_tab('about:blank')
                AntiSybilDpUtil.patch_webdriver_fingerprint(page_for_cdp)
                page_for_cdp.close()
            else:
                AntiSybilDpUtil.patch_webdriver_fingerprint(page_for_cdp)

            # 步骤2: 打开或激活WARDEN_URL页面
            try:
                self.page = self.browser.get_tab(url=self.WARDEN_URL)
                self.page.activate()
            except Exception:
                self.page = self.browser.new_tab(self.WARDEN_URL)

            # 步骤3: 等待页面加载完成
            self.page.wait.load_start()
            AntiSybilDpUtil.human_short_wait()
            AntiSybilDpUtil.simulate_random_click(self.page, self.user_id)
            AntiSybilDpUtil.human_brief_wait()
            AntiSybilDpUtil.simulate_mouse_move(self.page)

            log_util.info(self.user_id, f"任务成功: 项目 '{self.project_name}' 初始化成功")
        except Exception as e:
            log_util.error(self.user_id, f"异常: 项目 '{self.project_name}' 初始化失败: {e}")
            raise


    def warden_task_chat_with_ai(self):
        """
        与AI聊天任务：直接打开AI聊天页面，输入并发送消息。
        """
        log_util.info(self.user_id, f"任务开始: {self.project_name} - AI Chat")
        try:
            # 步骤1: 打开或激活AI聊天页面
            try:
                self.page = self.browser.get_tab(url=self.WARDEN_AI_CHAT_URL)
                self.page.activate()
            except Exception:
                self.page = self.browser.new_tab(self.WARDEN_AI_CHAT_URL)

            self.page.wait.load_start()
            AntiSybilDpUtil.human_short_wait()

            # 步骤2: 生成并输入消息
            today = datetime.now()
            date_str = today.strftime('%Y年%m月%d日')
            weekday = today.isoweekday()
            message = f"今天是{date_str}，我今天要赚{weekday}个sol"
            log_util.info(self.user_id, f"准备输入消息: {message}")

            # 通过ID精确定位输入框并输入
            input_box = self.page.ele('#chat', timeout=20)
            input_box.input(message)
            AntiSybilDpUtil.human_brief_wait()
            
            # 模拟回车发送
            self.page.actions.key_down('enter').key_up('enter')
            AntiSybilDpUtil.human_long_wait()  # 等待AI响应

            log_util.info(self.user_id, f"任务成功: {self.project_name} - AI Chat")
            return True

        except Exception as e:
            log_util.error(self.user_id, f"异常: {self.project_name} - AI Chat 任务执行失败: {e}")
            return False

    def warden_task_play_game(self):
        """
        玩游戏任务：进行赛车游戏。
        """
        log_util.info(self.user_id, f"任务开始: {self.project_name} - Play Game")
        try:
            # 步骤1: 打开或激活Warden主页面
            try:
                self.page = self.browser.get_tab(url=self.WARDEN_URL)
                self.page.activate()
            except Exception:
                self.page = self.browser.new_tab(self.WARDEN_URL)

            self.page.wait.load_start()
            AntiSybilDpUtil.human_long_wait()

            # 步骤2: 定位并点击游戏入口元素
            game_entry_selector = 'div[class*="bg-[linear-gradient(to_bottom,rgba(0,0,0,0)_0%,rgba(0,0,0,0.4)_97%)]"]'
            game_entry = self.page.ele(game_entry_selector, timeout=20)

            if game_entry:
                log_util.info(self.user_id, "游戏入口已找到，正在点击。")
                game_entry.click()
                AntiSybilDpUtil.human_brief_wait()
            else:
                raise Exception("未能找到游戏入口元素。")

            log_util.info(self.user_id, f"任务成功: {self.project_name} - Play Game")
            return True

        except Exception as e:
            log_util.error(self.user_id, f"异常: {self.project_name} - Play Game 任务执行失败: {e}")
            return False


if __name__ == "__main__":
    # 这个脚本现在是一个库，不应该被直接运行。
    print(
        "WardenScript 定义完成。请在您的主程序中实例化，或通过 wardenScript_test.py 进行测试。"
    )
