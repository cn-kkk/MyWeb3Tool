"""
.. deprecated:: 1.0.0
    This module is deprecated and will be removed in a future version.
    Its functionality has been replaced by `util.ads_browser_util` which uses DrissionPage.

This module contains the old Selenium-based implementation for browser automation.
"""
import warnings

warnings.warn(
    "The 'browser_util' module is deprecated. Use 'ads_browser_util' instead.",
    DeprecationWarning,
    stacklevel=2
)

import requests
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from util.anti_sybil_util import AntiSybilUtil
from config import BROWSER_CONFIG_FILE, API_ENDPOINTS, API_HEADER_KEY, API_URL_VALID_PREFIXES

BROWSER_USERID_FILE = BROWSER_CONFIG_FILE

def get_api_config():
    """从browser.txt读取API配置"""
    api_base = ""  # 默认空值
    
    if os.path.exists(BROWSER_USERID_FILE):
        try:
            with open(BROWSER_USERID_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) >= 1:
                    api_base = lines[0].strip()
        except Exception as e:
            print(f"[ERROR] 读取API配置失败: {e}")
    
    # 验证API地址格式
    if not api_base or not api_base.startswith(API_URL_VALID_PREFIXES):
        print(f"[WARN] API地址格式不正确或为空: {api_base}")
        return ""
    
    return api_base

def get_headers():
    """获取请求头"""
    return {}  # 不需要API key

class AdsEnv:
    def __init__(self, user_id, driver):
        self.user_id = user_id
        self.driver = driver
    def __repr__(self):
        return f"AdsEnv(user_id={self.user_id})"

def get_all_ads_envs():
    """
    读取adsBrowser.txt，批量attach所有已启动的ads环境，返回AdsEnv对象列表。
    """
    api_base = get_api_config()
    
    if not api_base:
        print(f"[ERROR] API地址未配置，请在browser.txt第一行设置API地址")
        return []
    
    headers = get_headers()
    
    user_ids = []
    if os.path.exists(BROWSER_USERID_FILE):
        with open(BROWSER_USERID_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # 跳过第一行（API地址），从第二行开始读取user_id
            for line in lines[1:]:
                uid = line.strip()
                if uid:
                    user_ids.append(uid)
    else:
        print(f"[ERROR] 未找到配置文件: {BROWSER_USERID_FILE}")
        return []
    
    envs = []
    for user_id in user_ids:
        try:
            resp = requests.get(f"{api_base}{API_ENDPOINTS['browser_active']}?user_id={user_id}", headers=headers, proxies={'http': None, 'https': None})
            data = resp.json()
            if data.get('code') == 0 and data.get('data', {}).get('ws', {}).get('selenium'):
                selenium_address = data['data']['ws']['selenium']
                webdriver_path = data['data']['webdriver']
                chrome_options = Options()
                chrome_options.add_experimental_option("debuggerAddress", selenium_address)
                # 检查是否存在crx插件，attach模式不支持动态加载插件
                crx_path = os.path.join('resource', 'okxwallet.crx')
                if os.path.exists(crx_path):
                    print(f"[INFO] 检测到OKX钱包插件: {crx_path}，attach模式下无法动态加载，仅新建driver时生效")

                service = Service(executable_path=webdriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # 在此注入JS以修复WebDriver指纹
                AntiSybilUtil.patch_webdriver_fingerprint(driver, env=user_id)

                envs.append(AdsEnv(user_id, driver))
                print(f"[INFO] 成功attach user_id={user_id}")
            else:
                print(f"[WARN] user_id={user_id} 未启动，跳过")
        except Exception as e:
            print(f"[ERROR] attach user_id={user_id} 失败: {e}")
    return envs

class AdsPowerUtil:
    @staticmethod
    def get_browser(user_id: str, api_base: str):
        """
        根据单个user_id启动或连接到一个AdsPower浏览器实例。
        返回一个Selenium WebDriver对象。
        """
        if not api_base:
            print(f"[ERROR] API地址未提供。")
            return None
        
        headers = get_headers()
        try:
            resp = requests.get(f"{api_base}{API_ENDPOINTS['browser_active']}?user_id={user_id}", headers=headers, proxies={'http': None, 'https': None})
            data = resp.json()
            if data.get('code') == 0 and data.get('data', {}).get('ws', {}).get('selenium'):
                selenium_address = data['data']['ws']['selenium']
                webdriver_path = data['data']['webdriver']
                
                chrome_options = Options()
                chrome_options.add_experimental_option("debuggerAddress", selenium_address)
                
                service = Service(executable_path=webdriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                
                AntiSybilUtil.patch_webdriver_fingerprint(driver, env=user_id)
                
                print(f"[INFO] 成功 attach user_id={user_id}")
                return driver
            else:
                print(f"[WARN] user_id={user_id} 未启动或API返回错误: {data.get('msg', 'N/A')}")
                return None
        except Exception as e:
            print(f"[ERROR] attach user_id={user_id} 失败: {e}")
            return None

    @staticmethod
    def get_userids_from_file():
        """从resource/browser.txt读取所有user_id（跳过第一行API配置）"""
        user_ids = []
        if os.path.exists(BROWSER_USERID_FILE):
            with open(BROWSER_USERID_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 跳过第一行（API地址），从第二行开始读取user_id
                for line in lines[1:]:
                    uid = line.strip()
                    if uid:
                        user_ids.append(uid)
        else:
            print(f"[ERROR] 未找到配置文件: {BROWSER_USERID_FILE}")
        return user_ids

    @staticmethod
    def save_browser_config(user_ids):
        """保存browser配置到文件（保留第一行API配置）"""
        try:
            os.makedirs(os.path.dirname(BROWSER_USERID_FILE), exist_ok=True)
            
            # 读取现有的API配置
            api_base = ""
            
            if os.path.exists(BROWSER_USERID_FILE):
                try:
                    with open(BROWSER_USERID_FILE, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if len(lines) >= 1:
                            api_base = lines[0].strip()
                except Exception as e:
                    print(f"[WARN] 读取现有API配置失败: {e}")
            
            # 写入文件：API配置 + user_ids
            with open(BROWSER_USERID_FILE, 'w', encoding='utf-8') as f:
                f.write(f"{api_base}\n")
                for user_id in user_ids:
                    if user_id.strip():  # 只保存非空行
                        f.write(f"{user_id.strip()}\n")
            print(f"成功保存 {len(user_ids)} 个browser user_id")
            return True
        except Exception as e:
            print(f"保存browser配置失败: {e}")
            return False

    @staticmethod
    def get_active_profiles(user_ids):
        """检测配置文件中的user_id哪些已启动，返回可操作的profile信息"""
        api_base = get_api_config()
        
        if not api_base:
            print(f"[ERROR] API地址未配置，请在browser.txt第一行设置API地址")
            return []
        
        headers = get_headers()
        
        running = []
        for user_id in user_ids:
            resp = requests.get(f"{api_base}{API_ENDPOINTS['browser_active']}?user_id={user_id}", headers=headers, proxies={'http': None, 'https': None})
            print(f"[DEBUG] {API_ENDPOINTS['browser_active']}?user_id={user_id} 状态码: {resp.status_code}, text: {repr(resp.text)}")
            try:
                data = resp.json()
            except Exception as e:
                print(f"[ERROR] 解析JSON失败: {e}")
                continue
            if data.get('code') == 0 and data.get('data', {}).get('ws', {}).get('selenium'):
                running.append({
                    'user_id': user_id,
                    'selenium_address': data['data']['ws']['selenium'],
                    'webdriver_path': data['data']['webdriver']
                })
        return running

    @staticmethod
    def stop_browser(user_id):
        """关闭指定user_id的AdsPower指纹浏览器实例"""
        api_base = get_api_config()
        
        if not api_base:
            print(f"[ERROR] API地址未配置，请在browser.txt第一行设置API地址")
            return False
        
        headers = get_headers()
        
        resp = requests.get(f"{api_base}{API_ENDPOINTS['browser_stop']}?user_id={user_id}", headers=headers)
        print(f"[DEBUG] {API_ENDPOINTS['browser_stop']}?user_id={user_id} 状态码: {resp.status_code}, text: {repr(resp.text)}")
        try:
            data = resp.json()
        except Exception as e:
            print(f"[ERROR] 解析JSON失败: {e}")
            return False
        if data.get('code') == 0:
            print(f"user_id={user_id} 浏览器已关闭")
            return True
        else:
            print(f"user_id={user_id} 关闭浏览器失败: {data}")
            return False

    @staticmethod
    def open_url_with_selenium(selenium_address, webdriver_path, url, max_retries=3):
        """使用Selenium连接端口并打开URL，带重试机制"""
        for attempt in range(max_retries):
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.chrome.service import Service
                print(f"尝试连接Selenium (第{attempt + 1}次)...")
                chrome_options = Options()
                chrome_options.add_experimental_option("debuggerAddress", selenium_address)
                service = Service(executable_path=webdriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.get(url)
                print(f"已通过Selenium打开: {url}")
                time.sleep(3)
                return True
            except Exception as e:
                print(f"Selenium连接失败 (第{attempt + 1}次): {e}")
                if attempt < max_retries - 1:
                    print(f"等待5秒后重试...")
                    time.sleep(5)
                else:
                    print("所有重试都失败了")
                    return False

if __name__ == "__main__":
    from util.okx_wallet_util import OKXWalletUtil

    # 1. 获取所有已启动的浏览器环境
    ads_envs = get_all_ads_envs()
    
    if not ads_envs:
        print("未发现任何已启动的浏览器环境，程序退出。")
    else:
        # 2. 初始化钱包工具
        okx_util = OKXWalletUtil()
        if not okx_util.PASSWORD:
            print("[FATAL] 无法加载钱包密码，请检查 resource/okxPassword.txt 文件。程序退出。")
        else:
            # 3. 遍历所有环境，解锁钱包
            for env in ads_envs:
                print(f"--- 开始操作 User ID: {env.user_id} ---")
                
                # 解锁钱包
                success = okx_util.unlock(env.driver)
                
                if success:
                    print(f"User ID: {env.user_id} 的钱包解锁成功。")
                else:
                    print(f"[FAILED] User ID: {env.user_id} 的钱包解锁失败。")
                
                print("操作完成，浏览器将保持打开状态供您验证。")
                
                # 4. 关闭浏览器 (已按要求注释掉)
                # AdsPowerUtil.stop_browser(env.user_id)
                
                print(f"--- User ID: {env.user_id} 操作结束 ---\n")