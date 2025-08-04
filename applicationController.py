import os
import importlib.util
from time import sleep

import inspect
import pyautogui
import time
import ctypes
import threading
import random
import itertools
from annotation.task_annotation import task_annotation
from concurrent.futures import ThreadPoolExecutor, wait
from util.log_util import log_util
from util.okx_wallet_util import OKXWalletUtil
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
        self.window_height = 0
        log_util.info("控制器", f"检测到逻辑分辨率: {self.screen_width}x{self.screen_height}, DPI缩放比例: {self.scale_factor}")

    def discover_projects(self):
        log_util.info("控制器", "正在扫描项目脚本...")
        self.projects = []
        project_dir = AppConfig.MY_PROJECT_DIR
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
        """将一批浏览器窗口以网格状排列在屏幕上。"""
        log_util.info("控制器", f"正在以网格形式排列 {len(page_envs_batch)} 个窗口。")

        taskbar_height = 80  # 任务栏的估计逻辑高度
        gap_y = 10          # 窗口之间的垂直逻辑间隙

        # 1. 基于pyautogui获取的逻辑分辨率计算窗口的逻辑尺寸和位置
        logical_width = self.screen_width // 2
        logical_height = (self.screen_height - taskbar_height) // 2
        self.window_height = logical_height # 保存逻辑高度，供业务脚本使用

        positions = [
            {"x": 0, "y": 0},
            {"x": logical_width, "y": 0},
            {"x": 0, "y": logical_height + gap_y},
            {"x": logical_width, "y": logical_height + gap_y}
        ]

        for i, page_env in enumerate(page_envs_batch):
            if i >= len(positions):
                continue
            
            pos = positions[i]
            browser = page_env.browser
            page = browser.get_tab()
            if not page:
                log_util.warn(page_env.user_id, "浏览器中没有活动的标签页，无法设置窗口大小。")
                continue

            # 2. 根据DPI缩放比例，将逻辑坐标和尺寸转换为API需要的实际值（通过除法）
            actual_x = int(pos["x"] / self.scale_factor)
            actual_y = int(pos["y"] / self.scale_factor)
            actual_width = int(logical_width / self.scale_factor)
            actual_height = int(logical_height / self.scale_factor)

            try:
                # 使用DrissionPage的API来恢复、设置大小和位置
                page.set.window.normal()
                time.sleep(0.1)
                page.set.window.size(width=actual_width, height=actual_height)
                time.sleep(0.1)
                page.set.window.location(x=actual_x, y=actual_y)
            except Exception as e:
                log_util.error(page_env.user_id, f"使用DrissionPage排列窗口时发生错误: {e}", exc_info=True)


    def initialize_app(self):
        self.discover_projects()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        log_util.info("控制器", f"线程池初始化完成，最大工作线程数={self.max_workers}。")
        log_util.info("控制器", "核心应用后端初始化完成。")

    def _browser_worker(self, page_env: DrissionPageEnv, sequence: list[dict]):
        """在单个浏览器环境中，按顺序执行指定的任务序列。"""

        # 线程级初始化：只执行一次的钱包解锁
        try:
            okx_util = OKXWalletUtil()
            okx_util.open_and_unlock_drission(page_env.browser, page_env.user_id)
            log_util.info(page_env.user_id, f"[线程-{page_env.user_id}] 钱包初始化解锁成功。")
        except Exception as e:
            log_util.error(page_env.user_id, f"[线程-{page_env.user_id}] 钱包初始化解锁失败，任务序列中止: {e}", exc_info=True)
            return

        # 项目级实例缓存，用于维护项目上下文
        script_instances = {}
        try:
            for task_definition in sequence:
                if self.interrupt_event.is_set():
                    log_util.warn(page_env.user_id, f"[线程-{page_env.user_id}] 检测到中断信号，任务序列已中止。")
                    break

                task_name = task_definition.get("task_name")
                if not task_name:
                    log_util.warn(page_env.user_id, f"[线程-{page_env.user_id}] 任务定义缺少 'task_name' 键: {task_definition}")
                    continue

                project_name_inferred = task_name.split('_task_')[0].capitalize()
                project_info = next((p for p in self.projects if p["project_name"].lower() == project_name_inferred.lower()), None)

                if not project_info:
                    log_util.warn(page_env.user_id, f"[线程-{page_env.user_id}] 无法从任务名 '{task_name}' 推断出有效项目。")
                    continue

                # 项目级上下文管理：如果需要，则初始化新项目实例
                if project_name_inferred not in script_instances:
                    log_util.info(page_env.user_id, f"[线程-{page_env.user_id}] 切换到新项目 '{project_name_inferred}'，正在执行项目级初始化...")
                    try:
                        project_class = project_info["class"]
                        script_instances[project_name_inferred] = project_class(browser=page_env.browser, user_id=page_env.user_id, window_height=self.window_height)
                    except Exception as e:
                        log_util.error(page_env.user_id, f"[线程-{page_name_inferred}] 项目 '{project_name_inferred}' 初始化失败: {e}", exc_info=True)
                        script_instances[project_name_inferred] = None
                        continue
                
                script_instance = script_instances.get(project_name_inferred)
                if script_instance is None:
                    log_util.warn(page_env.user_id, f"[线程-{page_env.user_id}] 因项目 '{project_name_inferred}' 初始化失败，跳过任务 '{task_name}'。")
                    continue

                task_method = getattr(script_instance, task_name, None)
                if not (task_method and callable(task_method)):
                    log_util.warn(page_env.user_id, f"[线程-{page_env.user_id}] 在 '{project_name_inferred}' 中未找到或无效的任务方法 '{task_name}'。")
                    continue

                # 任务级执行（无内部重复循环）
                try:
                    log_util.info(page_env.user_id, f"[线程-{page_env.user_id}] 开始执行任务 '{task_name}'...")
                    task_method()
                    log_util.info(page_env.user_id, f"[线程-{page_env.user_id}] 任务 '{task_name}' 成功完成。")
                except Exception as e:
                    log_util.error(page_env.user_id, f"[线程-{page_env.user_id}] 执行任务 '{task_name}' 时发生错误: {e}", exc_info=True)

            if not self.interrupt_event.is_set():
                log_util.info(page_env.user_id, f"[线程-{page_env.user_id}] 所有任务已成功完成。")
        except Exception as e:
            log_util.error(page_env.user_id, f"[线程-{page_env.user_id}] 执行任务序列期间发生严重错误: {e}", exc_info=True)

    def _generate_task_assignments(self, sequence: list[dict], num_browsers: int) -> list[list[dict]]:
        """
        为指定数量的浏览器生成最优的任务分配方案。
        从任务序列中得到m种执行顺序，然后分配给n个浏览器；m>n时不会重复
        """
        # 1. 根据 repetition 展开原始任务列表
        expanded_tasks = []
        for task_def in sequence:
            task_template = {k: v for k, v in task_def.items() if k != 'repetition'}
            task_template['repetition'] = 1
            expanded_tasks.extend([task_template] * task_def.get('repetition', 1))
        
        total_tasks = len(expanded_tasks)
        if total_tasks <= 1:
            return [expanded_tasks for _ in range(num_browsers)]

        # 2. 安全检查：如果任务总数过多，则退回至简单随机化，避免性能问题
        if total_tasks > 7:
            log_util.warn("控制器", f"任务总数 ({total_tasks}) 超过10，为避免性能问题，将采用简单随机化（允许碰撞）。")
            assignments = []
            for _ in range(num_browsers):
                shuffled_list = list(expanded_tasks)
                random.shuffle(shuffled_list)
                assignments.append(shuffled_list)
            return assignments

        # 3. 使用itertools.permutations生成所有唯一的排列组合
        # 通过将dict转换为tuple来实现hashable，以便放入set中去重
        task_tuples = [tuple(sorted(d.items())) for d in expanded_tasks]
        all_unique_permutations_as_tuples = list(set(itertools.permutations(task_tuples)))
        M = len(all_unique_permutations_as_tuples)
        log_util.info("控制器", f"为任务序列生成了 {M} 种独特的执行顺序。")

        # 4. 根据浏览器数量(N)和排列总数(M)决定分配策略
        N = num_browsers
        assignments_as_tuples = []
        if M == 0: return [[] for _ in range(N)]

        num_pools = N // M
        remainder = N % M
        
        for _ in range(num_pools):
            assignments_as_tuples.extend(all_unique_permutations_as_tuples)
        
        if remainder > 0:
            assignments_as_tuples.extend(random.sample(all_unique_permutations_as_tuples, remainder))

        # 5. 将元组转换回字典列表
        assignments = [[dict(t) for t in p] for p in assignments_as_tuples]

        # 6. 最终打乱，确保哪个浏览器拿到哪个序列是随机的
        random.shuffle(assignments)
        
        log_util.info("控制器", f"已为 {N} 个浏览器生成了独一无二或近似独一无二的任务分配方案。")
        return assignments

    def dispatch_sequence(self, sequence: list[dict]):
        """接收UI层的任务序列，并将其分发到多个浏览器实例中并行执行。"""
        log_util.info("控制器", f"接收到任务分发请求，序列长度: {len(sequence)}。")
        
        # 每次分发前，都重新获取最新的浏览器列表
        self.get_all_drission_pages()

        if not self.pages:
            log_util.warn("控制器", "没有可用的浏览器实例来分发任务。")
            return
        if not sequence:
            log_util.warn("控制器", "任务序列为空，无需分发。")
            return
        if not self.executor:
            log_util.warn("控制器", "线程池未初始化，无法分发任务。")
            return

        self.interrupt_event.clear()

        # 1. 预先计算好所有浏览器的任务分配方案
        task_assignments = self._generate_task_assignments(sequence, len(self.pages))

        # 2. 按批次将任务分发给浏览器
        page_chunks = [self.pages[i: i + self.max_workers] for i in range(0, len(self.pages), self.max_workers)]
        
        assignment_index = 0
        for i, chunk in enumerate(page_chunks):
            sleep(0.1)
            self.arrange_windows_as_grid(chunk)

            for page_env in chunk:
                try:
                    time.sleep(0.1)
                    
                    browser = page_env.browser
                    tabs = browser.get_tabs()
                    for tab in tabs[1:]:
                        tab.close()
                    time.sleep(0.1)

                except Exception as e:
                    log_util.error(page_env.user_id, f"清理标签页时出错: {e}", exc_info=True)

            time.sleep(2)

            futures = []
            for page_env in chunk:
                if assignment_index < len(task_assignments):
                    thread_sequence = task_assignments[assignment_index]
                    future = self.executor.submit(self._browser_worker, page_env, thread_sequence)
                    futures.append(future)
                    assignment_index += 1
            
            wait(futures)

            # 批次任务完成后，最小化所有相关窗口
            for page_env in chunk:
                try:
                    page = page_env.browser.get_tab()
                    if page:
                        page.set.window.mini()
                        time.sleep(0.1) # 短暂延时避免操作过快
                except Exception as e:
                    log_util.error(page_env.user_id, f"最小化窗口 {page_env.user_id} 时出错: {e}", exc_info=True)

            log_util.info("控制器", f"批次 {i + 1}/{len(page_chunks)} 已完成。")

            if i < len(page_chunks) - 1:
                time.sleep(2)
        log_util.info("控制器", "任务序列的所有批次已处理完毕。")

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
            sleep(0.1)
            # 刷新浏览器
            self.get_all_drission_pages()
            return True
        except Exception as e:
            log_util.error("控制器", f"保存浏览器配置失败: {e}", exc_info=True)
            return False

app_controller = ApplicationController()