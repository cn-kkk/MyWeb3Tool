import random
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from util.log_util import LogUtil # 导入新的日志工具

class AntiSybilUtil:
    @staticmethod
    def simulate_mouse_move_and_slide(driver, area_selector='body', total_time=4.0, steps=40, env=None):
        """
        鼠标先移动到区域左上角的随机点，2s内随机函数滑动，再2s内随机函数滑动。
        """
        import math
        try:
            LogUtil.log(env, "开始模拟鼠标滑动...")
            area = driver.find_element(By.CSS_SELECTOR, area_selector)
            location = area.location
            size = area.size
            left = location['x']
            top = location['y']
            width = size['width']
            height = size['height']
            margin = 10
            # 随机初始点
            cur_x = left + random.randint(margin, width//4)
            cur_y = top + random.randint(margin, height//4)
            ActionChains(driver).move_to_element_with_offset(area, cur_x-left, cur_y-top).perform()
            LogUtil.log(env, f"鼠标已移动到初始点 ({cur_x},{cur_y})")
            # 第一段：2s内随机抛物线
            points1 = []
            ctrl1_x = cur_x + random.randint(30, 80)
            ctrl1_y = cur_y - random.randint(10, 40)
            end1_x = cur_x + random.randint(40, 120)
            end1_y = cur_y + random.randint(20, 60)
            for i in range(steps//2):
                t = i / (steps//2-1)
                x = int((1-t)**2*cur_x + 2*(1-t)*t*ctrl1_x + t**2*end1_x)
                y = int((1-t)**2*cur_y + 2*(1-t)*t*ctrl1_y + t**2*end1_y)
                points1.append((x, y))
            # 第二段：2s内另一随机抛物线
            ctrl2_x = end1_x + random.randint(30, 80)
            ctrl2_y = end1_y - random.randint(10, 40)
            end2_x = end1_x + random.randint(40, 120)
            end2_y = end1_y + random.randint(20, 60)
            points2 = []
            for i in range(steps//2):
                t = i / (steps//2-1)
                x = int((1-t)**2*end1_x + 2*(1-t)*t*ctrl2_x + t**2*end2_x)
                y = int((1-t)**2*end1_y + 2*(1-t)*t*ctrl2_y + t**2*end2_y)
                points2.append((x, y))
            # 合并轨迹，去重
            points = [points1[0]] + [pt for i, pt in enumerate(points1[1:], 1) if pt != points1[i-1]]
            points += [pt for i, pt in enumerate(points2, 0) if pt != points2[i-1]]
            # 分步滑动
            for i in range(1, len(points)):
                dx = points[i][0] - points[i-1][0]
                dy = points[i][1] - points[i-1][1]
                ActionChains(driver).move_by_offset(dx, dy).perform()
                time.sleep(total_time/steps)
            LogUtil.log(env, f"鼠标滑动完成，轨迹点数: {len(points)}")
        except Exception as e:
            LogUtil.log(env, f"鼠标移动异常: {e}")

    @staticmethod
    def simulate_random_click(driver, area_selector='body', env=None):
        """
        随机点击页面无关区域，确保坐标在可见区域内。
        """
        try:
            LogUtil.log(env, "开始模拟随机点击...")
            area = driver.find_element(By.CSS_SELECTOR, area_selector)
            location = area.location
            size = area.size
            margin = 10
            x = location['x'] + random.randint(margin, max(margin, size['width'] - margin - 1))
            y = location['y'] + random.randint(margin, max(margin, size['height'] - margin - 1))
            driver.execute_script(f"window.scrollTo({x-100}, {y-100});")
            ActionChains(driver).move_by_offset(x, y).click().perform()
            ActionChains(driver).move_by_offset(-x, -y).perform()
            LogUtil.log(env, f"随机点击完成: ({x},{y})")
        except Exception as e:
            LogUtil.log(env, f"随机点击异常: {e}")

    @staticmethod
    def simulate_scroll(driver, min_scroll=100, max_scroll=800, env=None):
        """
        随机滚动页面。
        """
        try:
            scroll_y = random.randint(min_scroll, max_scroll)
            LogUtil.log(env, f"开始滚动页面: {scroll_y}px")
            driver.execute_script(f"window.scrollBy(0, {scroll_y});")
            time.sleep(random.uniform(0.2, 0.8))
            LogUtil.log(env, "滚动完成")
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