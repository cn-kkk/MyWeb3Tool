from DrissionPage import ChromiumOptions, WebPage
import random
import os

# 导入Socks5相关的类
from util.socks5_util import Socks5Proxy, Socks5Util

class FingerprintUtil:
    """
    一个工具类，用于创建带有伪造指纹信息的DrissionPage浏览器对象。
    """

    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ]
        self.screen_resolutions = ["1920,1080", "1600,900", "1440,900", "1366,768"]
        self.hardware_concurrency = ["8", "12", "16"]
        self.socks5_util = Socks5Util()
        
        self.injector_script = ""
        try:
            util_dir = os.path.dirname(os.path.abspath(__file__))
            js_path = os.path.join(util_dir, "config", "fingerprint_injector.js")
            if os.path.exists(js_path):
                with open(js_path, 'r', encoding='utf-8') as f:
                    self.injector_script = f.read()
            else:
                print(f"[FingerprintUtil] Warning: Injector script not found at {js_path}")
        except Exception as e:
            print(f"[FingerprintUtil] Error reading injector script: {e}")

    def create_browser(self, 
                       proxy: Socks5Proxy = None, 
                       headless: bool = True, 
                       fingerprint_config: dict = None) -> WebPage:
        """
        创建并返回一个配置了指纹信息的WebPage对象。
        """
        co = ChromiumOptions()
        fp = fingerprint_config or {}

        # 1. 基础指纹配置
        user_agent = fp.get('user_agent', random.choice(self.user_agents))
        resolution = fp.get('resolution', random.choice(self.screen_resolutions))
        hardware = fp.get('hardware', random.choice(self.hardware_concurrency))
        language = "zh-CN,zh;q=0.9,en;q=0.8"

        co.set_user_agent(user_agent)
        co.add_arg(f'--window-size={resolution}')
        co.add_arg(f'--hardware-concurrency={hardware}')
        co.add_arg(f'--lang=zh-CN')

        # 2. 设置代理
        if proxy:
            proxy_url = self.socks5_util.get_proxy_url(proxy)
            co.set_proxy(proxy_url)

        # 3. 进阶指纹设置
        co.add_arg("--disable-plugins-discovery")
        co.add_arg("--use-gl=desktop")

        # 4. 隐私保护设置
        co.set_pref(key='intl.accept_languages', value=language)
        co.set_pref(key='credentials_enable_service', value=False)
        co.set_pref(key='profile.password_manager_enabled', value=False)
        co.set_pref(key='enable_do_not_track', value=True)
        co.set_pref(key='media.peerconnection.enabled', value=False)
        co.set_pref(key='profile.default_content_setting_values.geolocation', value=2)

        # 5. 设置无头模式
        co.set_headless(headless)

        # 6. 创建页面
        page = WebPage(chromium_options=co)

        # 7. 注入高级指纹伪造脚本
        if self.injector_script:
            try:
                page.run_cdp('Page.addScriptToEvaluateOnNewDocument', source=self.injector_script)
            except Exception as e:
                print(f"[FingerprintUtil] Failed to inject script: {e}")

        return page
