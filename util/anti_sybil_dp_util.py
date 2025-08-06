import time
import random
import json

from DrissionPage import ChromiumPage
from util.log_util import log_util


class AntiSybilDpUtil:
    """
    用于DrissionPage的防女巫工具类，提供人性化的操作。
    所有方法都应该是静态的，并且在适用时接受一个页面对象作为第一个参数。
    """

    @staticmethod
    def get_perturbation_number(center_value: float, deviation_value: float) -> str:
        """
        生成一个在 [中心值-偏差, 中心值+偏差] 范围内的随机数，并格式化为字符串。
        小数位数会比偏差值的小数位数多一位，以模拟真实世界的不精确输入。
        """
        # 1. 生成随机浮点数
        random_value = random.uniform(center_value - deviation_value, center_value + deviation_value)

        # 2. 自动计算所需的小数位数
        deviation_str = str(deviation_value)
        if '.' in deviation_str:
            # 如果偏差值是小数，则精度为其小数位数+1
            precision = len(deviation_str.split('.')[1]) + 1
        else:
            # 如果偏差值是整数，则精度为1
            precision = 1
        
        # 3. 格式化并返回字符串
        return f"{random_value:.{precision}f}"

    @staticmethod
    def human_brief_wait():
        """
        1s内等待
        """
        delay = random.uniform(0.5, 1)
        time.sleep(delay)

    @staticmethod
    def human_short_wait():
        """
        人性化的短等待，模拟思考或网络延迟。
        """
        delay = random.uniform(3, 5)
        time.sleep(delay)

    @staticmethod
    def human_long_wait():
        """
        人性化的长等待，用于等待页面加载。
        """
        delay = random.uniform(8.0, 12.0)
        time.sleep(delay)

    @staticmethod
    def human_huge_wait():
        """
        超长等待，一般用于比较卡的项目交互。
        """
        delay = random.uniform(13.0, 20.0)
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
            log_util.error("anti_sybil", f"simulate_scroll时发生意外错误: {e}")

    @staticmethod
    def simulate_mouse_move(page: ChromiumPage):
        """
        在页面内模拟几次无意义的鼠标移动。
        """
        try:
            # 在执行任何操作前，先等待页面加载稳定
            page.wait.load_start()

            width, height = page.rect.viewport_size
            
            for _ in range(random.randint(1, 3)):
                # 确保坐标在视口范围内，并留出边距
                x = random.randint(100, width - 100 if width > 200 else width)
                y = random.randint(100, height - 100 if height > 200 else height)
                # DrissionPage的actions是即时执行的，不需要 .perform()
                page.actions.move_to((x, y), duration=random.uniform(0.3, 0.8))
                time.sleep(random.uniform(0.2, 0.5))
        except Exception as e:
            log_util.error("anti_sybil", f"simulate_mouse_move时发生意外错误: {e}")

    @staticmethod
    def simulate_random_click(page, user_id: str = "anti_sybil"):
        """
        在页面视口的左上角区域内模拟一次安全的随机点击。
        该方法会检查目标坐标，避免点击到可交互的元素。
        """
        try:
            if not page:
                log_util.warn(user_id, "simulate_random_click收到了一个空的page对象，已跳过。")
                return

            # 混淆后的JS脚本，判断坐标处是否能交互
            # 深度混淆后的JS脚本，避免出现关键字
            js_is_safe_to_click = """
            return (function(x, y) {
                const _d = window['docu' + 'ment'];
                const _w = window;
                const _p = 'poin' + 'ter';
                const _el = _d['elementF' + 'romPoint'](x, y);
                if (!_el) {
                    return true;
                }
                const _s = 'a,bu' + 'tton,in' + 'put,sel' + 'ect,[on' + 'click]';
                const _style = _w['getComp' + 'utedStyle'](_el);
                if (_el['clo' + 'sest'](_s) || _style['cur' + 'sor'] === _p) {
                    return false;
                }
                return true;
            })(arguments[0], arguments[1]);
            """

            width, height = page.rect.viewport_size

            # 尝试最多5次以找到一个安全的点击位置
            for i in range(5):
                x = random.randint(0, int(width * 0.15))
                y = random.randint(int(height * 0.1), int(height * 0.2))

                # 调用JS进行安全检查
                if page.run_js(js_is_safe_to_click, x, y):
                    log_util.info(user_id, f"找到安全点击坐标 (尝试 {i+1}/5): x={x}, y={y}")
                    page.actions.move_to(
                        (x, y), duration=random.uniform(0.2, 0.6)
                    ).click()
                    return  # 成功点击后退出

            log_util.warn(user_id, "尝试5次后未能找到安全的随机点击位置，已跳过本次点击。")

        except Exception as e:
            log_util.error(user_id, f"simulate_random_click时发生意外错误: {e}")

    @staticmethod
    def simulate_typing(page: ChromiumPage, text: str, user_id: str = "anti_sybil"):
        """
        模拟真人输入：在当前光标位置逐字输入，并增加随机退格重输和停顿。
        只能输入键盘有的按键，中文不行。
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
            log_util.error(user_id, f"simulate_typing时发生意外错误: {e}")

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
            log_util.error("anti_sybil", f"patch_webdriver_fingerprint时发生意外错误: {e}")


if __name__ == "__main__":
    # 这个文件是一个工具库，不应该被直接运行。
    print("AntiSybilDpUtil is a utility library and should not be run directly.")
    print("Please import its methods in your main script.")
