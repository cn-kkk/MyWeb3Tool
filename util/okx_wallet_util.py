import os
import time
import json
import pyautogui
import pyperclip

class OKXWalletUtil:
    """OKX钱包工具类（基于坐标点击）"""
    PASSWORD = None

    def __init__(self):
        self.password_file = "resource/okxPassword.txt"
        self.location_file = "resource/location.json"
        if OKXWalletUtil.PASSWORD is None:
            OKXWalletUtil.PASSWORD = self._load_password()

    def _load_password(self):
        if not os.path.exists(self.password_file):
            print(f"未找到密码文件: {self.password_file}")
            return None
        with open(self.password_file, 'r', encoding='utf-8') as f:
            pwd = f.readline().strip()
        if not pwd:
            print("密码文件为空")
            return None
        return pwd

    def connect_okx_wallet(self):
        """
        只点击一次坐标，等待5秒，然后输入密码，不做任何多余点击。
        """
        try:
            # 1. 读取坐标
            if not os.path.exists(self.location_file):
                print(f"未找到坐标配置文件: {self.location_file}")
                return False
            with open(self.location_file, 'r', encoding='utf-8') as f:
                loc = json.load(f)
            if 'okx_wallet_location' not in loc:
                print("location.json中未配置okx_wallet_location坐标")
                return False
            xy_str = loc['okx_wallet_location']
            if isinstance(xy_str, str):
                x, y = [int(i) for i in xy_str.split(',')]
            else:
                print("okx_wallet_location格式错误，必须是'2300,110'字符串")
                return False
            print(f"鼠标移动到OKX钱包图标坐标: ({x}, {y})，2秒后点击")
            pyautogui.moveTo(x, y, duration=0.5)
            time.sleep(2)
            pyautogui.click()
            print("已点击OKX钱包图标，等待5秒...")
            time.sleep(5)

            # 2. 输入密码（直接用静态常量）
            pwd = OKXWalletUtil.PASSWORD
            if not pwd:
                print("未获取到OKX钱包密码")
                return False

            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            pyperclip.copy(pwd)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            pyautogui.press('enter')
            print("已输入OKX钱包密码并尝试解锁")
            time.sleep(3)
            print("OKX钱包连接流程完成")
            return True
        except Exception as e:
            print(f"连接OKX钱包失败: {e}")
            return False

    def _get_okx_password(self):
        """从密码文件读取OKX钱包密码"""
        try:
            with open(self.password_file, 'r', encoding='utf-8') as f:
                for line in f:
                    pwd = line.strip()
                    if pwd:
                        return pwd
        except Exception as e:
            print(f"读取OKX钱包密码失败: {e}")
        return None 