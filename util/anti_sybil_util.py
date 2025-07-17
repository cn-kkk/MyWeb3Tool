import random
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from util.log_util import LogUtil # 导入新的日志工具

class AntiSybilUtil:
    @staticmethod
    def simulate_mouse_move_and_slide(driver, area_selector='body', total_time=2.0, steps=10, env=None):
        """
        在当前页面区域内简单移动。
        """
        try:
            LogUtil.log(env, "开始简单鼠标滑动（无滚动）...")
            window_size = driver.get_window_size()
            maxLength = window_size['width']
            maxHeight = window_size['height']
            start_x = int(maxLength * 0.05)
            start_y = int(maxHeight * 0.15)
            end_x = int(maxLength * 0.12)
            end_y = int(maxHeight * 0.18)
            ActionChains(driver).move_by_offset(start_x, start_y).perform()
            time.sleep(total_time / steps)
            ActionChains(driver).move_by_offset(end_x - start_x, end_y - start_y).perform()
            time.sleep(total_time / steps)
            ActionChains(driver).move_by_offset(-end_x, -end_y).perform()
            LogUtil.log(env, f"鼠标滑动完成: ({start_x},{start_y}) -> ({end_x},{end_y})")
        except Exception as e:
            LogUtil.log(env, f"鼠标移动异常: {e}")

    @staticmethod
    def simulate_random_click(driver, area_selector='body', env=None):
        """
        在当前页面视口内，x在0~maxLength*0.15，y在maxHeight*0.1~maxHeight*0.2之间生成，然后点击。
        坐标为页面左上角绝对坐标。
        """
        try:
            LogUtil.log(env, "开始模拟随机点击（无滚动）...")
            window_size = driver.get_window_size()
            maxLength = window_size['width']
            maxHeight = window_size['height']
            x = int(random.uniform(0, maxLength * 0.15))
            y = int(random.uniform(maxHeight * 0.1, maxHeight * 0.2))
            body = driver.find_element(By.TAG_NAME, 'body')
            ActionChains(driver).move_to_element_with_offset(body, x, y).click().perform()
            LogUtil.log(env, f"随机点击完成: ({x},{y})")
        except Exception as e:
            LogUtil.log(env, f"随机点击异常: {e}")

    @staticmethod
    def simulate_scroll(driver, min_scroll=100, max_scroll=800, env=None):
        """
        从当前位置向下随机滚动，停0.5s后再滚动回原来的位置。
        """
        try:
            time.sleep(0.2)  # 等待页面稳定
            original_x = driver.execute_script("return window.scrollX;")
            original_y = driver.execute_script("return window.scrollY;")
            scroll_y = random.randint(min_scroll, max_scroll)
            LogUtil.log(env, f"开始滚动页面: {scroll_y}px (原始位置: {original_y})")
            driver.execute_script(f"window.scrollBy(0, {scroll_y});")
            time.sleep(0.5)
            driver.execute_script(f"window.scrollTo({original_x}, {original_y});")
            time.sleep(0.2)
            current_y = driver.execute_script("return window.scrollY;")
            LogUtil.log(env, f"已滚动回原始位置: {original_y}，当前scrollY: {current_y}")
        except Exception as e:
            LogUtil.log(env, f"滚动异常: {e}")

    @staticmethod
    def simulate_typing(driver, element, text, env=None):
        """
        模拟真人输入：逐字输入，10%概率中途停顿2s，10%概率全部删除重输。
        element: 可输入的WebElement
        text: 输入内容
        """
        try:
            LogUtil.log(env, f"开始模拟输入: {text}")
            if random.random() < 0.1:
                element.clear()
                for char in text:
                    element.send_keys(char)
                    time.sleep(random.uniform(0.08, 0.22))
                time.sleep(random.uniform(0.3, 0.7))
                element.send_keys(Keys.CONTROL, 'a')
                element.send_keys(Keys.BACKSPACE)
                time.sleep(random.uniform(0.2, 0.5))
                for char in text:
                    element.send_keys(char)
                    time.sleep(random.uniform(0.08, 0.22))
            else:
                for i, char in enumerate(text):
                    element.send_keys(char)
                    time.sleep(random.uniform(0.08, 0.22))
                    if i > 0 and random.random() < 0.1:
                        LogUtil.log(env, "输入中停顿2s...")
                        time.sleep(2)
            LogUtil.log(env, "输入完成")
        except Exception as e:
            LogUtil.log(env, f"输入模拟异常: {e}")

    @staticmethod
    def human_short_wait(env=None):
        t = random.uniform(2, 5)
        LogUtil.log(env, f"短等待 {t:.2f}s")
        time.sleep(t)
        return t

    @staticmethod
    def human_long_wait(env=None):
        t = random.uniform(10, 20)
        LogUtil.log(env, f"长等待 {t:.2f}s")
        time.sleep(t)
        return t

    @staticmethod
    def patch_webdriver_fingerprint(driver, env=None):
        """
        通过执行CDP命令，在页面加载前注入JS脚本，以修复和隐藏WebDriver的各种特征。
        """
        try:
            LogUtil.log(env, "开始修复WebDriver指纹特征...")
            
            js_script = """
            (function() {
                // 移除 navigator.webdriver 标志
                if (navigator.webdriver) {
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                }

                // 伪装 chrome.runtime 对象
                window.chrome = window.chrome || {};
                window.chrome.runtime = window.chrome.runtime || {};
                const original_runtime = window.chrome.runtime;
                window.chrome.runtime = new Proxy(original_runtime, {
                    get: function(target, prop, receiver) {
                        if (prop === 'id' || prop === 'onMessage' || prop === 'sendMessage') {
                            return; // 返回 undefined，隐藏敏感信息
                        }
                        return Reflect.get(target, prop, receiver);
                    }
                });

                // 伪装 navigator.plugins
                const original_plugins = navigator.plugins;
                if (original_plugins.length === 0 || Array.from(original_plugins).some(p => p.name.includes('WebDriver'))) {
                    const plugins_proxy = new Proxy(original_plugins, {
                        get: function(target, prop, receiver) {
                            if (prop === 'length') return 1;
                            if (prop === 'item' || typeof prop === 'symbol') return Reflect.get(target, prop, receiver);
                            return new Proxy({}, { get: () => 'Plugin' }); // 返回一个伪造的插件对象
                        }
                    });
                    Object.defineProperty(navigator, 'plugins', { get: () => plugins_proxy });
                }

                // 清理 ChromeDriver 在 window 对象上留下的痕迹
                // 例如 window.cdc_... 或 document.$cdc_...
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
            
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": js_script}
            )
            LogUtil.log(env, "WebDriver指纹特征修复完成")
        except Exception as e:
            LogUtil.log(env, f"WebDriver指纹特征修复异常: {e}")