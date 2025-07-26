import os
import importlib.util
import inspect
import pyautogui
import time
import ctypes
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from util.log_util import LogUtil
import config
from util.ads_browser_util import AdsBrowserUtil, DrissionPageEnv
from util.socks5_util import Socks5Util
from util.wallet_util import WalletUtil


def get_windows_dpi_scaling():
    """
    通过调用 Windows API 获取屏幕的 DPI 缩放比例。
    :return: float, DPI 缩放比例 (例如 1.0, 1.25, 1.5)
    """
    try:
        # 加载必要的库
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        
        # 获取屏幕的设备上下文
        hdc = user32.GetDC(0)
        
        # 获取水平方向的 DPI
        # 88 = LOGPIXELSX
        dpi_x = gdi32.GetDeviceCaps(hdc, 88)
        
        # 释放设备上下文
        user32.ReleaseDC(0, hdc)
        
        # Windows 的标准 DPI 是 96
        return dpi_x / 96.0
    except Exception:
        # 如果发生任何错误，返回默认值 1.0
        return 1.0


class ApplicationController:
    """
    应用程序后端控制器。
    负责应用程序启动时的所有后端逻辑，如加载配置、初始化浏览器连接、管理线程池和任务分发。
    """

    def __init__(self):
        """
        初始化控制器。
        """
        LogUtil.info("控制器", "正在初始化应用程序控制器...")
        self.config = config
        self.pages = []  # 存储所有获取到的 DrissionPage 页面对象
        self.projects = []  # 存储所有发现的项目脚本
        self.max_workers = 4
        self.executor = None
        self.interrupt_event = threading.Event()  # 中断信号
        self.screen_width, self.screen_height = pyautogui.size()
        self.scale_factor = get_windows_dpi_scaling()
        LogUtil.info(
            "控制器",
            f"检测到逻辑分辨率: {self.screen_width}x{self.screen_height}, DPI缩放比例: {self.scale_factor}"
        )
        LogUtil.info("控制器", "应用程序控制器初始化完成。")

    def discover_projects(self):
        """
        扫描myProject目录，加载所有脚本类及元信息。
        """
        LogUtil.info("控制器", "正在扫描项目脚本...")
        self.projects = []  # 重置项目列表
        project_dir = os.path.join(os.getcwd(), "myProject")
        if not os.path.exists(project_dir):
            LogUtil.warn(
                "控制器",
                f"项目目录 '{project_dir}' 不存在，将不会加载任何项目。"
            )
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
                                if project_name in existing_projects:
                                    continue  # 如果项目已存在，则跳过

                                tasks = []
                                for attr in dir(obj):
                                    if "task_" in attr:
                                        method = getattr(obj, attr)
                                        if callable(method):
                                            tasks.append(
                                                {
                                                    "name": attr,
                                                    "desc": method.__doc__ or "",
                                                }
                                            )
                                self.projects.append(
                                    {
                                        "project_name": project_name,
                                        "project_desc": getattr(
                                            obj, "project_desc", ""
                                        ),
                                        "tasks": tasks,
                                        "class": obj,  # 存储类对象本身
                                    }
                                )
                                existing_projects.add(project_name)
                                LogUtil.info(
                                    "控制器",
                                    f"发现项目: {project_name}"
                                )
                except Exception as e:
                    LogUtil.error(
                        "控制器",
                        f"加载项目脚本 {fname} 失败: {e}", exc_info=True
                    )
        LogUtil.info(
            "控制器",
            f"项目扫描完成。共发现 {len(self.projects)} 个项目。"
        )

    def get_all_drission_pages(self):
        """
        连接并获取所有正在运行的浏览器实例的 DrissionPage 对象。
        """
        LogUtil.info("控制器", "正在尝试连接所有运行中的浏览器实例...")
        try:
            self.pages = AdsBrowserUtil.get_all_running_ads_browsers()
            LogUtil.info(
                "控制器",
                f"成功连接到 {len(self.pages)} 个浏览器实例。"
            )
            return self.pages
        except Exception as e:
            LogUtil.error(
                "控制器",
                f"获取 DrissionPage 对象时发生错误: {e}",
                exc_info=True,
            )
            self.pages = []
            return self.pages

    def arrange_windows_as_grid(self, page_envs_batch):
        """
        将指定的一批浏览器窗口以2x2网格形式平铺在屏幕上。
        """
        LogUtil.info("控制器", f"正在以网格形式排列 {len(page_envs_batch)} 个窗口。")
        
        logical_width = int(self.screen_width / self.scale_factor)
        taskBar_height = 80
        logical_height = int(self.screen_height / self.scale_factor) - taskBar_height

        # 浏览器宽有一部分不可见，手动补偿
        width = logical_width // 2 + 15
        height = logical_height // 2

        positions = [
            {"x": 0, "y": 0, "width": width, "height": height},  # 左上
            {"x": width, "y": 0, "width": width, "height": height},  # 右上
            {"x": 0, "y": height + 20, "width": width, "height": height},  # 左下
            {"x": width, "y": height + 20, "width": width, "height": height},  # 右下
        ]

        for i, page_env in enumerate(page_envs_batch):
            if i < len(positions):
                pos = positions[i]
                try:
                    # 获取当前活动的标签页
                    target_page = page_env.browser.latest_tab
                    # 从标签页获取窗口设置器
                    window_setter = target_page.set.window
                    # 先将窗口恢复正常状态
                    window_setter.normal()
                    time.sleep(0.5) # 强制等待，确保窗口状态已更新
                    window_setter.size(width=pos["width"], height=pos["height"])
                    window_setter.location(x=pos["x"], y=pos["y"])

                except Exception as e:
                    LogUtil.error(
                        page_env.user_id,
                        f"为 user_id {page_env.user_id} 设置窗口边界失败: {e}"
                    )

    def initialize_app(self):
        """
        执行应用启动所需的核心后端初始化任务。
        """
        LogUtil.info("控制器", "核心应用后端初始化开始...")
        self.get_all_drission_pages()
        self.discover_projects()

        # 初始化线程池
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        LogUtil.info(
            "控制器",
            f"线程池初始化完成，最大工作线程数={self.max_workers}。"
        )

        LogUtil.info("控制器", "核心应用后端初始化完成。")

    def _browser_worker(
        self, page_env: DrissionPageEnv, project_name: str, tasks: list[dict]
    ):
        """
        在单个浏览器环境中，按顺序执行一系列任务的工人函数。
        """
        LogUtil.info(
            page_env.user_id,
            f"[线程-{page_env.user_id}] 开始处理任务序列。"
        )
        try:
            project_info = next(
                (p for p in self.projects if p["project_name"] == project_name), None
            )
            if not project_info:
                LogUtil.error(
                    page_env.user_id, f"[线程-{page_env.user_id}] 未找到项目 '{project_name}'。"
                )
                return

            project_class = project_info["class"]
            script_instance = project_class(browser=page_env.browser, user_id=page_env.user_id)

            # 外层循环，遍历任务定义
            for task_definition in tasks:
                if self.interrupt_event.is_set():
                    LogUtil.warn(
                        page_env.user_id,
                        f"[线程-{page_env.user_id}] 检测到中断信号，任务序列已中止。"
                    )
                    break

                task_name = task_definition.get("name")
                repetitions = task_definition.get("repetitions", 1)

                if not task_name:
                    LogUtil.error(page_env.user_id, f"[线程-{page_env.user_id}] 任务定义缺少 'name' 键: {task_definition}")
                    continue

                task_method = getattr(script_instance, task_name, None)
                if not (task_method and callable(task_method)):
                    LogUtil.error(
                        page_env.user_id,
                        f"[线程-{page_env.user_id}] 在 '{project_name}' 中未找到或无效的任务方法 '{task_name}'。"
                    )
                    continue # 跳过无效任务，继续下一个

                # 内层循环，根据 repetitions 执行
                for i in range(repetitions):
                    if self.interrupt_event.is_set():
                        LogUtil.warn(
                            page_env.user_id,
                            f"[线程-{page_env.user_id}] 检测到中断信号，任务 '{task_name}' 的剩余执行已取消。"
                        )
                        break # 中断内层循环
                    
                    LogUtil.info(
                        page_env.user_id, f"[线程-{page_env.user_id}] 开始执行任务 '{task_name}' (第 {i+1}/{repetitions} 次)..."
                    )
                    task_method()
                    LogUtil.info(
                        page_env.user_id, f"[线程-{page_env.user_id}] 任务 '{task_name}' (第 {i+1}/{repetitions} 次) 成功完成。"
                    )
            
            if not self.interrupt_event.is_set():
                LogUtil.info(page_env.user_id, f"[线程-{page_env.user_id}] 所有任务已成功完成。")

        except Exception as e:
            LogUtil.error(
                page_env.user_id,
                f"[线程-{page_env.user_id}] 执行任务序列期间发生严重错误: {e}",
                exc_info=True,
            )

    def dispatch_tasks(self, project_name: str, tasks: list[dict]):
        """
        将一个任务序列分配给所有可用的浏览器实例，采用分批处理模式。
        """
        LogUtil.info(
            "控制器",
            f"正在为项目 '{project_name}' 的所有浏览器分发任务序列: {tasks}。"
        )
        if not self.pages:
            LogUtil.warn("控制器", "没有可用的浏览器实例来分发任务。")
            return
        
        if not tasks:
            LogUtil.warn("控制器", "任务列表为空，无需分发。")
            return

        if not self.executor:
            LogUtil.error(
                "控制器", "线程池未初始化，无法分发任务。"
            )
            return
            
        self.interrupt_event.clear() # 重置中断信号，确保新任务可以开始

        # 将所有页面分块，每块的大小为最大工作线程数
        page_chunks = [
            self.pages[i : i + self.max_workers]
            for i in range(0, len(self.pages), self.max_workers)
        ]

        for i, chunk in enumerate(page_chunks):
            LogUtil.info(
                "控制器",
                f"正在处理批次 {i+1}/{len(page_chunks)}，包含 {len(chunk)} 个浏览器。"
            )

            # 1. 对当前批次的浏览器进行窗口布局
            self.arrange_windows_as_grid(chunk)

            # 2. 将当前批次的任务提交给线程池 (每个浏览器一个worker)
            futures = [
                self.executor.submit(
                    self._browser_worker, page_env, project_name, tasks
                )
                for page_env in chunk
            ]

            # 3. 等待当前批次的所有任务完成
            wait(futures)

            LogUtil.info("控制器", f"批次 {i+1}/{len(page_chunks)} 已完成。")

        LogUtil.info("控制器", f"项目 '{project_name}' 的任务序列 {tasks} 的所有批次已处理完毕。")

    def interrupt_tasks(self):
        """
        设置中断信号，通知所有正在运行的worker线程在完成当前任务后停止。
        """
        LogUtil.info("控制器", "接收到中断信号，将通知所有线程停止后续任务...")
        self.interrupt_event.set()

    def shutdown(self):
        """
        安全地关闭线程池，等待所有任务完成。
        """
        if self.executor:
            LogUtil.info("控制器", "正在关闭线程池...")
            self.executor.shutdown(wait=True)
            LogUtil.info("控制器", "线程池已关闭。")

    # --- 配置管理方法 ---
    def get_ip_configs(self):
        LogUtil.info("控制器", "正在加载 SOCKS5 代理配置...")
        return Socks5Util().read_proxies()

    def save_ip_configs(self, configs):
        LogUtil.info("控制器", f"正在保存 {len(configs)} 个 SOCKS5 代理配置...")
        return Socks5Util().save_socks5_config(configs)

    def get_wallet_configs(self):
        LogUtil.info("控制器", "正在加载钱包配置...")
        return WalletUtil().read_wallets()

    def save_wallet_configs(self, configs):
        LogUtil.info("控制器", f"正在保存 {len(configs)} 个钱包配置...")
        return WalletUtil().save_wallet_config(configs)

    def get_browser_configs(self):
        LogUtil.info("控制器", "正在加载浏览器配置...")
        if os.path.exists(config.BROWSER_CONFIG_FILE):
            try:
                with open(config.BROWSER_CONFIG_FILE, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                LogUtil.error("控制器", f"读取浏览器配置失败: {e}", exc_info=True)
        return ""

    def save_browser_configs(self, content):
        LogUtil.info("控制器", "正在保存浏览器配置...")
        try:
            os.makedirs(os.path.dirname(config.BROWSER_CONFIG_FILE), exist_ok=True)
            with open(config.BROWSER_CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            lines = content.strip().split("\n")
            if len(lines) >= 1 and not lines[0].strip().startswith(
                config.API_URL_VALID_PREFIXES
            ):
                LogUtil.warn(
                    "控制器", "浏览器配置已保存，但API URL格式似乎不正确。"
                )
            return True
        except Exception as e:
            LogUtil.error("控制器", f"保存浏览器配置失败: {e}", exc_info=True)
            return False


# 创建一个单例供UI层调用
app_controller = ApplicationController()


