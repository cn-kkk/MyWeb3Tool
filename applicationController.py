import os
import importlib.util

import inspect
import pyautogui
import time
import ctypes
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from util.log_util import log_util
from config import AppConfig
from util.ads_browser_util import AdsBrowserUtil, DrissionPageEnv
from util.socks5_util import Socks5Util
from util.wallet_util import WalletUtil


def get_windows_dpi_scaling():
    """
    通过调用 Windows API 获取屏幕的 DPI 缩放比例。
    :return: float, DPI 缩放比例 (例如 1.0, 1.25, 1.5)
    """
    try:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        hdc = user32.GetDC(0)
        dpi_x = gdi32.GetDeviceCaps(hdc, 88)
        user32.ReleaseDC(0, hdc)
        return dpi_x / 96.0
    except Exception:
        return 1.0


import win32gui
import win32con
import win32process


class ApplicationController:
    """
    应用程序后端控制器。
    """

    def __init__(self):
        log_util.info("控制器", "正在初始化应用程序控制器...")
        self.config = AppConfig
        self.pages = []
        self.projects = []
        self.max_workers = 4
        self.executor = None
        self.interrupt_event = threading.Event()
        self.screen_width, self.screen_height = pyautogui.size()
        self.scale_factor = get_windows_dpi_scaling()
        log_util.info("控制器", f"检测到逻辑分辨率: {self.screen_width}x{self.screen_height}, DPI缩放比例: {self.scale_factor}")

    def discover_projects(self):
        log_util.info("控制器", "正在扫描项目脚本...")
        self.projects = []
        project_dir = os.path.join(os.getcwd(), "myProject")
        if not os.path.exists(project_dir):
            log_util.warn("控制器", f"项目目录 '{project_dir}' 不存在，将不会加载任何项目。")
            return

        existing_projects = set()
        for fname in os.listdir(project_dir):
            if fname.endswith(".py") and not fname.startswith("_"):
                fpath = os.path.join(project_dir, fname)
                try:
                    spec = importlib.util.spec_from_file_location(fname[:-3], fpath)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if name.endswith("Script") and hasattr(obj, "project_name"):
                                project_name = getattr(obj, "project_name", name)
                                if project_name in existing_projects: continue
                                tasks = []
                                for attr in dir(obj):
                                    if "_task_" in attr:
                                        method = getattr(obj, attr)
                                        if callable(method):
                                            task_limit = getattr(method, '_task_limit', None)
                                            tasks.append({
                                                "name": attr, 
                                                "desc": method.__doc__ or "",
                                                "limit": task_limit
                                            })
                                self.projects.append({"project_name": project_name, "project_desc": getattr(obj, "project_desc", ""), "tasks": tasks, "class": obj})
                                existing_projects.add(project_name)
                                log_util.info("控制器", f"发现项目: {project_name}")
                except Exception as e:
                    log_util.error("控制器", f"加载项目脚本 {fname} 失败: {e}", exc_info=True)

    def get_all_drission_pages(self):
        log_util.info("控制器", "正在尝试连接所有运行中的浏览器实例...")
        try:
            self.pages = AdsBrowserUtil.get_all_running_ads_browsers()
            log_util.info("控制器", f"成功连接到 {len(self.pages)} 个浏览器实例。")
            return self.pages
        except Exception as e:
            log_util.error("控制器", f"获取 DrissionPage 对象时发生错误: {e}", exc_info=True)
            self.pages = []
            return self.pages

    def arrange_windows_as_grid(self, page_envs_batch):
        log_util.info("控制器", f"正在以网格形式排列 {len(page_envs_batch)} 个窗口。")

        # 直接计算win32gui需要的物理像素坐标
        taskbar_physical_height = int(60 * self.scale_factor) # 任务栏高度
        gap_physical_y = int(10 * self.scale_factor)
        
        width = int(self.screen_width // 2)
        height = int((self.screen_height - taskbar_physical_height) // 2)

        positions = [
            {"x": 0, "y": 0, "width": width, "height": height},
            {"x": width, "y": 0, "width": width, "height": height},
            {"x": 0, "y": height + gap_physical_y, "width": width, "height": height},
            {"x": width, "y": height + gap_physical_y, "width": width, "height": height}
        ]

        # 1. 获取所有可见窗口的句柄和标题
        all_windows = []
        def enum_windows_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    all_windows.append((hwnd, title))
        win32gui.EnumWindows(enum_windows_callback, None)

        # 2. 为每个浏览器实例寻找并排列窗口
        used_hwnds = set()
        last_valid_hwnd = None
        for i, page_env in enumerate(page_envs_batch):
            if i >= len(positions): continue
            pos = positions[i]
            found_hwnd = None

            try:
                # 获取部分标题，例如 "109"
                partial_title = page_env.browser.latest_tab.title
                
                # 遍历所有窗口，寻找最佳匹配
                for hwnd, full_title in all_windows:
                    if hwnd in used_hwnds: continue # 跳过已分配的窗口

                    # 智能匹配：必须同时包含部分标题和浏览器关键字
                    if partial_title in full_title and "SunBrowser" in full_title:
                        found_hwnd = hwnd
                        used_hwnds.add(hwnd) # 标记为已使用
                        break # 找到后立即停止搜索

                if found_hwnd:
                    # 采用分步、强健的序列来确保窗口被正确恢复、移动和置顶
                    win32gui.ShowWindow(found_hwnd, win32con.SW_SHOWNORMAL)
                    time.sleep(0.1) # 缩短等待时间，因为我们只移动，不抢焦点
                    win32gui.SetWindowPos(found_hwnd, win32con.HWND_TOPMOST, pos["x"], pos["y"], pos["width"], pos["height"], 0)
                    win32gui.SetWindowPos(found_hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                    last_valid_hwnd = found_hwnd # 记录最后一个有效窗口
                else:
                    log_util.warn(page_env.user_id, f"未能通过智能匹配找到标题包含 '{partial_title}' 和 'SunBrowser' 的窗口，已跳过排列。")

            except Exception as e:
                log_util.error(page_env.user_id, f"排列窗口时发生错误: {e}")
        
        # 3. 在所有窗口排列完成后，只激活最后一个窗口
        if last_valid_hwnd:
            try:
                win32gui.SetForegroundWindow(last_valid_hwnd)
            except Exception as e:
                log_util.error("控制器", f"激活最后一个窗口时出错: {e}")

    def initialize_app(self):
        self.get_all_drission_pages()
        self.discover_projects()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        log_util.info("控制器", f"线程池初始化完成，最大工作线程数={self.max_workers}。")
        log_util.info("控制器", "核心应用后端初始化完成。")

    def _browser_worker(self, page_env: DrissionPageEnv, sequence: list[dict]):
        log_util.info(page_env.user_id, f"[线程-{page_env.user_id}] 开始处理包含 {len(sequence)} 个任务的任务序列。")
        script_instances = {} # Cache for initialized script instances
        try:
            for task_definition in sequence:
                if self.interrupt_event.is_set():
                    log_util.warn(page_env.user_id, f"[线程-{page_env.user_id}] 检测到中断信号，任务序列已中止。")
                    break

                task_name = task_definition.get("task_name")
                repetition = task_definition.get("repetition", 1)

                if not task_name:
                    log_util.error(page_env.user_id, f"[线程-{page_env.user_id}] 任务定义缺少 'task_name' 键: {task_definition}")
                    continue

                # Infer project name from task name prefix
                project_name_inferred = task_name.split('_task_')[0].capitalize()
                project_info = next((p for p in self.projects if p["project_name"].lower() == project_name_inferred.lower()), None)

                if not project_info:
                    log_util.error(page_env.user_id, f"[线程-{page_env.user_id}] 无法从任务名 '{task_name}' 推断出有效项目。")
                    continue

                # Get or create script instance
                if project_name_inferred not in script_instances:
                    log_util.info(page_env.user_id, f"[线程-{page_env.user_id}] 首次遇到项目 '{project_name_inferred}'，正在初始化脚本...")
                    project_class = project_info["class"]
                    script_instances[project_name_inferred] = project_class(browser=page_env.browser, user_id=page_env.user_id)
                
                script_instance = script_instances[project_name_inferred]
                task_method = getattr(script_instance, task_name, None)

                if not (task_method and callable(task_method)):
                    log_util.error(page_env.user_id, f"[线程-{page_env.user_id}] 在 '{project_name_inferred}' 中未找到或无效的任务方法 '{task_name}'。")
                    continue

                for i in range(repetition):
                    if self.interrupt_event.is_set():
                        log_util.warn(page_env.user_id, f"[线程-{page_env.user_id}] 检测到中断信号，任务 '{task_name}' 的剩余执行已取消。")
                        break
                    log_util.info(page_env.user_id, f"[线程-{page_env.user_id}] 开始执行任务 '{task_name}' (第 {i+1}/{repetition} 次)...")
                    task_method()
                    log_util.info(page_env.user_id, f"[线程-{page_env.user_id}] 任务 '{task_name}' (第 {i+1}/{repetition} 次) 成功完成。")

            if not self.interrupt_event.is_set():
                log_util.info(page_env.user_id, f"[线程-{page_env.user_id}] 所有任务已成功完成。")
        except Exception as e:
            log_util.error(page_env.user_id, f"[线程-{page_env.user_id}] 执行任务序列期间发生严重错误: {e}", exc_info=True)

    def dispatch_sequence(self, sequence: list[dict]):
        log_util.info("控制器", f"正在为所有浏览器分发任务序列，序列长度: {len(sequence)}。")
        if not self.pages: 
            log_util.warn("控制器", "没有可用的浏览器实例来分发任务。")
            return
        if not sequence:
            log_util.warn("控制器", "任务序列为空，无需分发。")
            return
        if not self.executor: 
            log_util.error("控制器", "线程池未初始化，无法分发任务。")
            return

        self.interrupt_event.clear()
        page_chunks = [self.pages[i : i + self.max_workers] for i in range(0, len(self.pages), self.max_workers)]
        for i, chunk in enumerate(page_chunks):
            log_util.info("控制器", f"正在处理批次 {i+1}/{len(page_chunks)}，包含 {len(chunk)} 个浏览器。")
            self.arrange_windows_as_grid(chunk)
            futures = [self.executor.submit(self._browser_worker, page_env, sequence) for page_env in chunk]
            wait(futures)
            log_util.info("控制器", f"批次 {i+1}/{len(page_chunks)} 已完成。")
        log_util.info("控制器", f"任务序列的所有批次已处理完毕。")

    def interrupt_tasks(self):
        log_util.info("控制器", "接收到中断信号，将通知所有线程停止后续任务...")
        self.interrupt_event.set()

    def shutdown(self):
        if self.executor:
            log_util.info("控制器", "正在关闭线程池...")
            self.executor.shutdown(wait=True)
            log_util.info("控制器", "线程池已关闭。")

    def get_ip_configs(self):
        return Socks5Util().read_proxies()

    def save_ip_configs(self, configs):
        log_util.info("控制器", f"正在保存 {len(configs)} 个 SOCKS5 代理配置...")
        return Socks5Util().save_socks5_config(configs)

    def get_wallet_configs(self):
        return WalletUtil().read_wallets()

    def save_wallet_configs(self, configs):
        log_util.info("控制器", f"正在保存 {len(configs)} 个钱包配置...")
        return WalletUtil().save_wallet_config(configs)

    def get_browser_configs(self):
        if os.path.exists(AppConfig.BROWSER_CONFIG_FILE):
            try:
                with open(AppConfig.BROWSER_CONFIG_FILE, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                log_util.error("控制器", f"读取浏览器配置失败: {e}", exc_info=True)
        return ""

    def save_browser_configs(self, content):
        log_util.info("控制器", "正在保存浏览器配置...")
        try:
            os.makedirs(os.path.dirname(AppConfig.BROWSER_CONFIG_FILE), exist_ok=True)
            with open(AppConfig.BROWSER_CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            lines = content.strip().split("\n")
            if len(lines) >= 1 and not lines[0].strip().startswith(AppConfig.API_URL_VALID_PREFIXES):
                log_util.warn("控制器", "浏览器配置已保存，但API URL格式似乎不正确。")
            return True
        except Exception as e:
            log_util.error("控制器", f"保存浏览器配置失败: {e}", exc_info=True)
            return False

app_controller = ApplicationController()