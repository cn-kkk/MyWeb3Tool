import random
from util.anti_sybil_util import AntiSybilUtil
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import os

class PharosScript:
    project_name = "Pharos"
    PHAROS_URL = "https://testnet.pharosnetwork.xyz/experience"

    def __init__(self, ads_env):
        self.ads_env = ads_env
        self.driver = ads_env.driver

    def connect_wallet(self):
        """连接OKX钱包，自动点击Connect Wallet并选择OKX Wallet，自动输入密码解锁"""
        driver = self.driver
        # attach后自动切换到包含Pharos体验页的有效窗口
        try:
            handles = driver.window_handles
            for h in handles:
                driver.switch_to.window(h)
                if self.PHAROS_URL.split('//')[-1].split('/')[0] in driver.current_url:
                    AntiSybilUtil.log(self.ads_env, f"[调试] 已切换到有效Pharos窗口: {driver.current_url}")
                    break
        except Exception as e:
            AntiSybilUtil.log(self.ads_env, f"[调试] 切换窗口异常: {e}")
        driver.get(self.PHAROS_URL)
        AntiSybilUtil.log(self.ads_env, "访问Pharos体验页面")
        time.sleep(2)
        # 点击右上角Connect Wallet按钮
        try:
            connect_btn = driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'connect wallet')]")
            time.sleep(2)
            connect_btn.click()
            AntiSybilUtil.log(self.ads_env, "点击Connect Wallet按钮")
            time.sleep(2)
        except Exception as e:
            AntiSybilUtil.log(self.ads_env, f"未找到Connect Wallet按钮: {e}")
            return False
        # 用pyautogui图像识别查找OKX钱包选项并点击
        try:
            import pyautogui
            okx_img_path = os.path.join('ocr&irt', 'pharos_connect_wallet.png')
            AntiSybilUtil.log(self.ads_env, f"[调试] 开始图像识别: {okx_img_path}")
            # 检查文件是否存在
            if not os.path.exists(okx_img_path):
                AntiSybilUtil.log(self.ads_env, f"[调试] 图片文件不存在: {okx_img_path}")
                return False
            AntiSybilUtil.log(self.ads_env, f"[调试] 图片文件存在，开始识别")
            location = pyautogui.locateCenterOnScreen(okx_img_path, confidence=0.85)
            if location:
                pyautogui.moveTo(location.x, location.y, duration=0.3)
                time.sleep(0.5)
                pyautogui.click()
                AntiSybilUtil.log(self.ads_env, f"[调试] 成功点击OKX Wallet图标: {location}")
                time.sleep(2)
            else:
                AntiSybilUtil.log(self.ads_env, f"[调试] 未找到OKX Wallet图标: {okx_img_path}")
                return False
        except Exception as e:
            AntiSybilUtil.log(self.ads_env, f"[调试] 图像识别异常: {e}")
            AntiSybilUtil.log(self.ads_env, f"[调试] 图像识别异常详情: {str(e)}")
            return False
        # 切换到OKX钱包插件弹窗，自动输入密码解锁
        try:
            import pyperclip
            okx_pwd = None
            with open('resource/okxPassword.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    pwd = line.strip()
                    if pwd:
                        okx_pwd = pwd
                        break
            if not okx_pwd:
                AntiSybilUtil.log(self.ads_env, f"[调试] 未获取到OKX钱包密码")
                return False
            # 等待插件弹窗出现
            time.sleep(2)
            # 直接粘贴密码并回车（假设焦点已在密码框）
            pyperclip.copy(okx_pwd)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            pyautogui.press('enter')
            AntiSybilUtil.log(self.ads_env, "自动输入OKX钱包密码并解锁")
            time.sleep(2)
        except Exception as e:
            AntiSybilUtil.log(self.ads_env, f"自动解锁OKX钱包失败: {e}")
            return False
        return True

    def _get_wallet_password(self):
        """从wallet.txt读取第一个钱包密码"""
        try:
            with open("resource/wallet.txt", "r", encoding="utf-8") as f:
                for line in f:
                    pwd = line.strip()
                    if pwd:
                        return pwd
        except Exception as e:
            AntiSybilUtil.log(self.ads_env, f"读取钱包密码失败: {e}")
        return None

    def task_swap(self):
        """Pharos Swap 任务：在Pharos平台进行Swap操作。"""
        self.driver.get('https://pharos.xyz/swap')
        AntiSybilUtil.log(self.ads_env, "访问Pharos Swap页面")
        # TODO: 页面元素操作
        AntiSybilUtil.simulate_mouse_move_and_slide(self.driver, env=self.ads_env)

    def task_deposit(self):
        """Pharos Deposit 任务：在Pharos平台进行存款操作。"""
        self.driver.get('https://pharos.xyz/deposit')
        AntiSybilUtil.log(self.ads_env, "访问Pharos Deposit页面")
        # TODO: 页面元素操作
        AntiSybilUtil.simulate_random_click(self.driver, env=self.ads_env)

    def task_domain(self):
        """Pharos 域名任务：在Pharos平台进行域名相关操作。"""
        self.driver.get('https://pharos.xyz/domain')
        AntiSybilUtil.log(self.ads_env, "访问Pharos 域名页面")
        # TODO: 页面元素操作
        AntiSybilUtil.simulate_scroll(self.driver, env=self.ads_env)

    def run(self):
        """随机运行所有任务，每个任务后自动调用反女巫。"""
        tasks = [self.task_swap, self.task_deposit, self.task_domain]
        random.shuffle(tasks)
        for task in tasks:
            try:
                task()
                # 每个任务后随机调用反女巫
                anti_sybil_func = random.choice([
                    AntiSybilUtil.simulate_mouse_move_and_slide,
                    AntiSybilUtil.simulate_random_click,
                    AntiSybilUtil.simulate_scroll
                ])
                anti_sybil_func(self.driver, env=self.ads_env)
            except Exception as e:
                AntiSybilUtil.log(self.ads_env, f"任务{task.__name__}异常: {e}") 