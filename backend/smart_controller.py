import threading
import os
import importlib.util
import inspect
import queue
import copy
from time import sleep

from backend.dispatcher import Dispatcher
from util.log_util import log_util
from config import AppConfig
from util.socks5_util import Socks5Util
from util.wallet_util import WalletUtil
from annotation.task_annotation import task_annotation  # 打包时包含注解模块

class SmartController:
    """
    智能控制器，作为系统的统一入口。
    """
    def __init__(self):
        self.log = log_util
        self.projects_map = {}
        self.interrupt_event = threading.Event()
        self.result_queue = queue.Queue()
        self.dispatcher = None  # 持有调度器实例

        # 用于存储实时任务状态
        self.current_task_status = {}
        self.status_lock = threading.Lock() # 防止后端更新的时候前端来读到脏数据
        self.result_processor_thread = None
        self.completed_task_count = 0

    def discover_projects(self):
        """扫描、加载并解析所有项目脚本，返回UI友好的数据结构。"""
        self.projects_map.clear()
        project_dir = AppConfig.MY_PROJECT_DIR
        if not os.path.exists(project_dir):
            self.log.warn("智能控制器", f"项目目录 '{project_dir}' 不存在。")
            return []

        discovered_projects = []
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
                                project_name = getattr(obj, "project_name", name).capitalize()
                                self.projects_map[project_name] = obj

                                # 1. 获取项目描述
                                project_desc = getattr(obj, "project_desc", None)
                                if not project_desc:
                                    project_desc = inspect.getdoc(obj)
                                project_desc = (project_desc or "没有提供项目描述").strip()

                                # 2. 通过方法名中的 `_task_` 发现任务
                                tasks = []
                                for method_name in dir(obj):
                                    if "_task_" in method_name:
                                        method_obj = getattr(obj, method_name)
                                        if inspect.isfunction(method_obj):
                                            limit = getattr(method_obj, '_task_limit', None) or getattr(method_obj, '_task_annotation', None)
                                            tasks.append({
                                                "name": method_name,
                                                "desc": (inspect.getdoc(method_obj) or "没有提供任务描述").strip(),
                                                "limit": limit
                                            })

                                discovered_projects.append({
                                    "project_name": project_name,
                                    "project_desc": project_desc,
                                    "tasks": tasks
                                })

                except Exception as e:
                    self.log.error("智能控制器", f"加载或解析项目脚本 {fname} 失败: {e}", exc_info=True)
        
        return discovered_projects

    def shutdown(self):
        """向所有工作线程和调度器发送中断信号。"""
        self.log.info("智能控制器", "接收到关闭信号，正在终止所有操作...")
        self.interrupt_event.set()
        if self.dispatcher:
            self.dispatcher.shutdown()
        
        # 等待结果处理线程结束
        if self.result_processor_thread and self.result_processor_thread.is_alive():
            self.log.info("智能控制器", "等待结果处理器完成最终处理...")
            self.result_processor_thread.join(timeout=5) # 设置超时以防万一

    def dispatch_sequence(self, sequence: list[dict], concurrent_browsers: int):
        """
        接收UI层的请求，创建并启动调度器来完成所有工作。
        """

        # 确保之前的任务已经完全终止
        if self.result_processor_thread and self.result_processor_thread.is_alive():
            self.log.warn("智能控制器", "检测到上一次的任务仍在运行，将先执行强制关闭。")
            self.shutdown()

        self.interrupt_event.clear()
        with self.status_lock:
            self.current_task_status.clear()
            self.completed_task_count = 0

        # 清空旧的结果队列
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break

        self.dispatcher = Dispatcher(
            sequence=sequence,
            concurrent_browsers=concurrent_browsers,
            projects_map=self.projects_map,
            result_queue=self.result_queue,
            interrupt_event=self.interrupt_event
        )

        # 启动结果处理线程
        self.result_processor_thread = threading.Thread(target=self._result_processor_loop, name="ResultProcessor")
        self.result_processor_thread.start()

        # 在后台线程中启动调度器，防止阻塞
        threading.Thread(target=self.dispatcher.execute, name="DispatcherThread").start()

        # 这里可以立即返回，或者根据需要返回一个任务ID等
        return {"status": "started"}

    def _result_processor_loop(self):
        """在一个独立的线程中运行，处理任务结果队列。"""
        self.log.info("结果处理器", "结果处理线程已启动。")

        total_tasks = self.dispatcher.total_task_count if self.dispatcher else 0
        self.log.info("结果处理器", f"启动时获取到的总任务数: {total_tasks}")
        if total_tasks == 0:
            self.log.info("结果处理器", "没有需要处理的任务，线程退出。")
            return

        while True:
            try:
                # 阻塞式获取，直到有结果或收到哨兵信号
                result = self.result_queue.get()

                # 检查是否是结束信号
                if result is None:
                    break

                result_data = result.to_dict()

                with self.status_lock:
                    if result.browser_id not in self.current_task_status:
                        self.current_task_status[result.browser_id] = []
                    self.current_task_status[result.browser_id].append(result_data)
                    self.completed_task_count += 1
                
                self.result_queue.task_done()

            except Exception as e:
                self.log.error("结果处理器", f"处理结果时发生未知错误: {e}", exc_info=True)

    def get_task_progress(self):
        """获取当前所有任务的执行状态。供前端轮询调用。"""
        with self.status_lock:
            # 返回一个深拷贝，防止在外部修改原始状态
            return copy.deepcopy(self.current_task_status)

    def get_execution_status(self):
        """获取任务执行的计数状态，并明确指示整个序列是否已完成。"""
        total_tasks = self.dispatcher.total_task_count if self.dispatcher else 0
        
        # 检查结果处理线程是否存在且仍在活动
        is_processing_alive = self.result_processor_thread and self.result_processor_thread.is_alive()
        
        with self.status_lock:
            is_truly_done = bool(self.dispatcher and not is_processing_alive and self.completed_task_count >= total_tasks)

            return {
                'completed': self.completed_task_count,
                'total': total_tasks,
                'is_done': is_truly_done
            }


    def get_ip_configs(self):
        return Socks5Util().read_proxies()

    def save_ip_configs(self, configs):
        self.log.info("智能控制器", f"正在保存 {len(configs)} 个 SOCKS5 代理配置...")
        return Socks5Util().save_socks5_config(configs)

    def get_wallet_configs(self):
        return WalletUtil().read_wallets()

    def save_wallet_configs(self, configs):
        self.log.info("智能控制器", f"正在保存 {len(configs)} 个钱包配置...")
        return WalletUtil().save_wallet_config(configs)

    def get_browser_configs(self):
        if os.path.exists(AppConfig.BROWSER_CONFIG_FILE):
            try:
                with open(AppConfig.BROWSER_CONFIG_FILE, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                self.log.error("智能控制器", f"读取浏览器配置失败: {e}", exc_info=True)
        return ""

    def save_browser_configs(self, content):
        self.log.info("智能控制器", "正在保存浏览器配置...")
        try:
            os.makedirs(os.path.dirname(AppConfig.BROWSER_CONFIG_FILE), exist_ok=True)
            with open(AppConfig.BROWSER_CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            lines = content.strip().split("\n")
            if len(lines) >= 1 and not lines[0].strip().startswith(AppConfig.API_URL_VALID_PREFIXES):
                self.log.warn("智能控制器", "浏览器配置已保存，但API URL格式似乎不正确。")
            sleep(0.1)
            return True
        except Exception as e:
            self.log.error("智能控制器", f"保存浏览器配置失败: {e}", exc_info=True)
            return False