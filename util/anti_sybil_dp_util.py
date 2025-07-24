import time
import random

from DrissionPage import ChromiumPage
from util.log_util import LogUtil


class AntiSybilDpUtil:
    """
    用于DrissionPage的防女巫工具类，提供人性化的操作。
    所有方法都应该是静态的，并且在适用时接受一个页面对象作为第一个参数。
    """

    @staticmethod
    def human_short_wait():
        """
        人性化的短等待，模拟思考或网络延迟。
        """
        delay = random.uniform(1.5, 3.5)
        time.sleep(delay)

    @staticmethod
    def human_long_wait():
        """
        人性化的长等待，用于等待页面加载或复杂操作。
        """
        delay = random.uniform(7.0, 12.0)
        time.sleep(delay)

    @staticmethod
    def simulate_scroll(page: ChromiumPage):
        """
        在页面上模拟一次自然的向下滚动，然后滚动回顶部。
        """
        try:
            scroll_distance = random.randint(300, 800)
            page.scroll.down(scroll_distance)
            AntiSybilDpUtil.human_short_wait()
            page.scroll.to_top()
        except Exception as e:
            LogUtil.error("anti_sybil", f"simulate_scroll时发生意外错误: {e}")

    @staticmethod
    def simulate_mouse_move(page: ChromiumPage):
        """
        在页面内模拟几次无意义的鼠标移动。
        """
        try:
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, page.size[0] - 100)
                y = random.randint(100, page.size[1] - 100)
                page.actions.move_to(
                    (x, y), duration=random.uniform(0.3, 0.8)
                ).perform()
                time.sleep(random.uniform(0.2, 0.5))
        except Exception as e:
            LogUtil.error("anti_sybil", f"simulate_mouse_move时发生意外错误: {e}")

    @staticmethod
    def simulate_random_click(page, user_id: str = "anti_sybil"):
        """
        在页面视口的左上角区域内模拟一次随机点击。
        """
        try:
            if not page:
                LogUtil.warn(user_id, "simulate_random_click收到了一个空的page对象，已跳过。")
                return

            # 使用JS获取视口大小，这是最可靠的方法
            width, height = page.run_js('return [window.innerWidth, window.innerHeight];')
            x = random.randint(0, int(width * 0.15))
            y = random.randint(int(height * 0.1), int(height * 0.2))
            LogUtil.info(user_id, f"simulate_random_click: x坐标{x}, y坐标{y}")
            page.actions.move_to(
                (x, y), duration=random.uniform(0.2, 0.6)
            ).click()
        except Exception as e:
            LogUtil.error(user_id, f"simulate_random_click时发生意外错误: {e}")

    @staticmethod
    def simulate_typing(page: ChromiumPage, text: str, user_id: str = "anti_sybil"):
        """
        模拟真人输入：在当前光标位置逐字输入，并增加随机停顿。
        有小概率会先输入一遍，然后删除，再重新输入，以模拟更真实的用户行为。
        """
        try:
            def _type_text_by_char(p, t):
                """辅助函数，用于执行逐字输入。"""
                for char in t:
                    p.actions.key_down(char).key_up(char)
                    time.sleep(random.uniform(0.08, 0.25))

            # 10%的概率触发“输入-删除-重输”的反女巫逻辑
            if random.random() < 0.1:
                # 第一次输入
                _type_text_by_char(page, text)
                AntiSybilDpUtil.human_short_wait()

                # 模拟退格键删除
                for _ in range(len(text) + 2):  # 多删几个以防万一
                    page.actions.key_down('backspace').key_up('backspace')
                    time.sleep(random.uniform(0.02, 0.05))
                AntiSybilDpUtil.human_short_wait()

            # 最终的、正确的输入 (无论是否触发了反女巫，都会执行这一步)
            _type_text_by_char(page, text)

        except Exception as e:
            LogUtil.error(user_id, f"simulate_typing时发生意外错误: {e}")

    @staticmethod
    def patch_webdriver_fingerprint(page: ChromiumPage):
        """
        通过执行CDP命令，在页面加载前注入JS脚本，以修复和隐藏WebDriver的各种特征。
        """
        if not ChromiumPage:
            return
        try:
            js_script = """
            (function() {
                if (navigator.webdriver) {
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                }
                window.chrome = window.chrome || {};
                window.chrome.runtime = window.chrome.runtime || {};
                const original_runtime = window.chrome.runtime;
                window.chrome.runtime = new Proxy(original_runtime, {
                    get: function(target, prop, receiver) {
                        if (prop === 'id' || prop === 'onMessage' || prop === 'sendMessage') {
                            return;
                        }
                        return Reflect.get(target, prop, receiver);
                    }
                });
                const original_plugins = navigator.plugins;
                if (original_plugins.length === 0 || Array.from(original_plugins).some(p => p.name.includes('WebDriver'))) {
                    const plugins_proxy = new Proxy(original_plugins, {
                        get: function(target, prop, receiver) {
                            if (prop === 'length') return 1;
                            if (prop === 'item' || typeof prop === 'symbol') return Reflect.get(target, prop, receiver);
                            return new Proxy({}, { get: () => 'Plugin' });
                        }
                    });
                    Object.defineProperty(navigator, 'plugins', { get: () => plugins_proxy });
                }
                const doc_keys = Object.keys(document);
                for (const key of doc_keys) {
                    if (key.startsWith('$cdc_') || key.startsWith('$wdc_')) {
                        delete document[key];
                    }
                }
                const win_keys = Object.keys(window);
                for (const key of win_keys) {
                    if (key.startsWith('cdc_')) {
                        delete window[key];
                    }
                }
            })();
            """
            page.run_cdp("Page.addScriptToEvaluateOnNewDocument", source=js_script)
        except Exception as e:
            LogUtil.error("anti_sybil", f"patch_webdriver_fingerprint时发生意外错误: {e}")


if __name__ == "__main__":
    # 这个文件是一个工具库，不应该被直接运行。
    print("AntiSybilDpUtil is a utility library and should not be run directly.")
    print("Please import its methods in your main script.")