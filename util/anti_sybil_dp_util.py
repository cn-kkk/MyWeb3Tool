import time
import random

# DrissionPage是可选依赖，只有在使用时才需要
try:
    from DrissionPage import ChromiumPage, ChromiumElement
except ImportError:
    ChromiumPage = None
    ChromiumElement = None


class AntiSybilDpUtil:
    """
    用于DrissionPage的防女巫工具类，提供人性化的操作。
    所有方法都应该是静态的，并且在适用时接受一个页面对象作为第一个参数。
    """

    @staticmethod
    def human_short_wait(user_id: str = None):
        """
        人性化的短等待，模拟思考或网络延迟。
        """
        delay = random.uniform(1.5, 3.5)
        time.sleep(delay)

    @staticmethod
    def human_long_wait(user_id: str = None):
        """
        人性化的长等待，用于等待页面加载或复杂操作。
        """
        delay = random.uniform(7.0, 12.0)
        time.sleep(delay)

    @staticmethod
    def simulate_scroll(page: ChromiumPage, user_id: str = None):
        """
        在页面上模拟一次自然的向下滚动，然后滚动回顶部。
        """
        if not ChromiumPage:
            return
        try:
            scroll_distance = random.randint(300, 800)
            page.scroll.down(scroll_distance)
            AntiSybilDpUtil.human_short_wait(user_id)
            page.scroll.to_top()
        except Exception:
            # 作为非关键操作，静默失败
            pass

    @staticmethod
    def simulate_mouse_move(page: ChromiumPage, user_id: str = None):
        """
        在页面内模拟几次无意义的鼠标移动。
        """
        if not ChromiumPage:
            return
        try:
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, page.size[0] - 100)
                y = random.randint(100, page.size[1] - 100)
                page.actions.move_to(
                    (x, y), duration=random.uniform(0.3, 0.8)
                ).perform()
                time.sleep(random.uniform(0.2, 0.5))
        except Exception:
            # 静默失败
            pass

    @staticmethod
    def simulate_random_click(page: ChromiumPage, user_id: str = None):
        """
        在页面视口的左上角区域内模拟一次随机点击。
        """
        if not ChromiumPage:
            return
        try:
            width, height = page.size
            x = random.randint(0, int(width * 0.15))
            y = random.randint(int(height * 0.1), int(height * 0.2))
            page.actions.move_to(
                (x, y), duration=random.uniform(0.2, 0.6)
            ).click().perform()
        except Exception:
            # 静默失败
            pass

    @staticmethod
    def simulate_typing(element: ChromiumElement, text: str, user_id: str = None):
        """
        模拟真人输入：使用DrissionPage的by_word模式，并增加随机停顿。
        """
        if not ChromiumElement:
            return
        try:
            # 10%的概率完全重打一遍
            if random.random() < 0.1:
                element.input(text, by_word=True, interval=random.uniform(0.08, 0.2))
                AntiSybilDpUtil.human_short_wait(user_id)
                element.clear()
                AntiSybilDpUtil.human_short_wait(user_id)

            # 正常输入
            element.input(text, by_word=True, interval=random.uniform(0.1, 0.25))
        except Exception:
            # 模拟输入错误时静默失败
            pass

    @staticmethod
    def patch_webdriver_fingerprint(page: ChromiumPage, user_id: str = None):
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
        except Exception:
            # 修补指纹失败时静默失败
            pass


if __name__ == "__main__":
    # 这个文件是一个工具库，不应该被直接运行。
    print("AntiSybilDpUtil is a utility library and should not be run directly.")
    print("Please import its methods in your main script.")