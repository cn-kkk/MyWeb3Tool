import random
import time
from datetime import datetime
from util.anti_sybil_dp_util import AntiSybilDpUtil
from util.log_util import log_util
from annotation.task_annotation import task_annotation
from util.okx_wallet_util import OKXWalletUtil


class WardenScript:
    """
    Warden Protocol项目的脚本类。
    """

    project_name = "Warden"
    WARDEN_URL = "https://app.wardenprotocol.org/earn"
    WARDEN_AI_CHAT_URL = "https://app.wardenprotocol.org/dashboard"

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

            # 步骤2: 获取Warden主页的页面对象
            tabs = self.browser.get_tabs(url=self.WARDEN_URL)
            if tabs:
                self.page = tabs[0]
                self.page.set.activate()
                self.page.refresh()
            else:
                self.page = self.browser.new_tab(self.WARDEN_URL)

            # 步骤3: 等待页面加载并检查是否需要重新登录
            self.page.wait.load_start()
            AntiSybilDpUtil.human_long_wait()
            
            # 新增逻辑：检查URL是否为认证页面
            if "auth" in self.page.url:
                self.okx_util.click_OKX_in_selector(self.browser, self.page, self.user_id)
                AntiSybilDpUtil.human_long_wait()
                # 重新验证URL是否已离开auth页面
                if "auth" in self.page.url:
                    raise Exception("尝试重新登录后，页面仍停留在认证页，初始化失败。")

            # 步骤4: 执行常规的人性化操作
            AntiSybilDpUtil.simulate_random_click(self.page, self.user_id)
            AntiSybilDpUtil.human_brief_wait()
            AntiSybilDpUtil.simulate_mouse_move(self.page)

            log_util.info(self.user_id, f"任务成功: 项目 '{self.project_name}' 初始化成功")
        except Exception as e:
            log_util.error(self.user_id, f"异常: 项目 '{self.project_name}' 初始化失败: {e}")
            raise

    @task_annotation.once_per_day
    def warden_task_chat_with_ai(self):
        """
        与AI聊天任务：直接打开AI聊天页面，输入并发送消息。
        """
        log_util.info(self.user_id, f"任务开始: {self.project_name} - AI Chat")
        chat_page = None
        try:
            # 步骤1: 获取AI聊天页面的页面对象
            tabs = self.browser.get_tabs(url=self.WARDEN_AI_CHAT_URL)
            if tabs:
                chat_page = tabs[0]
                chat_page.set.activate()
                chat_page.refresh()
            else:
                chat_page = self.browser.new_tab(self.WARDEN_AI_CHAT_URL)

            AntiSybilDpUtil.human_short_wait()

            # 新增逻辑：检查URL是否为认证页面
            if "auth" in chat_page.url:
                self.okx_util.click_OKX_in_selector(self.browser, chat_page, self.user_id)
                AntiSybilDpUtil.human_long_wait()

            # 步骤2: 生成并输入消息
            today = datetime.now()
            date_str = today.strftime('%Y年%m月%d日')
            weekday = today.isoweekday()
            message = f"今天是{date_str}，我今天要赚{weekday}个sol"

            # 通过ID精确定位输入框并输入
            input_box = chat_page.ele('#chat', timeout=20)
            input_box.input(message)
            AntiSybilDpUtil.human_brief_wait()
            
            # 模拟回车发送
            chat_page.actions.key_down('enter').key_up('enter')
            AntiSybilDpUtil.human_long_wait()  # 等待AI响应

            log_util.info(self.user_id, f"任务成功: {self.project_name} - AI Chat")
            return True

        except Exception as e:
            log_util.error(self.user_id, f"异常: {self.project_name} - AI Chat 任务执行失败: {e}", exc_info=True)
            return False
        finally:
            if chat_page and chat_page.tab_id in self.browser.tab_ids:
                chat_page.close()

    @task_annotation.once_per_day
    def warden_task_play_game(self):
        """
        玩游戏任务：进行赛车游戏。
        """
        log_util.info(self.user_id, f"任务开始: {self.project_name} - Play Game")
        try:
            # 步骤1: 获取Warden主页的页面对象
            tabs = self.browser.get_tabs(url=self.WARDEN_URL)
            if tabs:
                self.page = tabs[0]
                self.page.set.activate()
                self.page.refresh()
            else:
                self.page = self.browser.new_tab(self.WARDEN_URL)

            AntiSybilDpUtil.human_short_wait()

            # 新增逻辑：检查URL是否为认证页面
            if "auth" in self.page.url:
                self.okx_util.click_OKX_in_selector(self.browser, self.page, self.user_id)
                AntiSybilDpUtil.human_short_wait()
                # 认证完会回到dashboard页面，再次跳转回earn页面
                self.page = self.browser.new_tab(self.WARDEN_URL)
                AntiSybilDpUtil.human_short_wait()

            # 步骤2: 滚动并点击游戏入口
            self.page.scroll.down(800)
            AntiSybilDpUtil.human_short_wait()
            game_entry = self.page.ele('text:HODL the Wheel', timeout=10)

            if game_entry:
                game_entry.click()
                AntiSybilDpUtil.human_short_wait()
            else:
                raise Exception("未能找到'HODL the Wheel'游戏入口元素。")

            # 步骤3: 点击“START GAME”按钮
            AntiSybilDpUtil.human_short_wait()
            start_game_btn = self.page.ele('text:START GAME', timeout=10)
            if start_game_btn:
                start_game_btn.click()
                AntiSybilDpUtil.human_short_wait()
            else:
                raise Exception("未能找到'START GAME'按钮。")

            # 步骤4: 玩游戏
            for _ in range(10):
                key = random.choice(['a', 'd'])
                self.page.actions.key_down(key)
                time.sleep(0.2)
                self.page.actions.key_up(key)
                time.sleep(1)

            time.sleep(60)
            self.page.refresh()
            log_util.info(self.user_id, f"任务成功: {self.project_name} - Play Game")
            return True

        except Exception as e:
            log_util.error(self.user_id, f"异常: {self.project_name} - Play Game 任务执行失败: {e}", exc_info=True)
            return False


if __name__ == "__main__":
    # 这个脚本现在是一个库，不应该被直接运行。
    print(
        "WardenScript 定义完成。请在您的主程序中实例化，或通过 wardenScript_test.py 进行测试。"
    )
