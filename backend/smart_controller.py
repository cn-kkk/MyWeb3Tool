import threading
import os
import importlib.util
import inspect
from time import sleep

from backend.dispatcher import Dispatcher
from backend.message_store import message_store
from util.log_util import log_util
from config import AppConfig
from util.socks5_util import Socks5Util
from util.wallet_util import WalletUtil
from annotation.task_annotation import task_annotation

class SmartController:
    """
    智能控制器，作为系统的统一入口。
    采用无状态设计，通过 message_store 与调度器解耦。
    """
    def __init__(self):
        self.log = log_util
        self.projects_map = {}
        self.interrupt_event = threading.Event()
        self.dispatcher = None  # 持有调度器实例

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

                                project_desc = getattr(obj, "project_desc", None) or inspect.getdoc(obj) or "没有提供项目描述"
                                project_desc = project_desc.strip()

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

    def dispatch_sequence(self, sequence: list[dict], concurrent_browsers: int):
        """
        接收UI层的请求，创建并启动调度器来完成所有工作。
        """
        # 检查是否有旧的调度线程仍在运行
        if self.dispatcher and any(t.name == "DispatcherThread" and t.is_alive() for t in threading.enumerate()):
            self.log.warn("智能控制器", "检测到上一次的任务仍在运行，将先执行强制关闭。")
            self.shutdown()

        self.interrupt_event.clear()
        
        # 清空上一次运行的数据
        message_store.clear_topic('tasks')
        message_store.clear_topic('signals')

        self.dispatcher = Dispatcher(
            sequence=sequence,
            concurrent_browsers=concurrent_browsers,
            projects_map=self.projects_map,
            interrupt_event=self.interrupt_event
        )

        threading.Thread(target=self.dispatcher.execute, name="DispatcherThread").start()
        return {"status": "started"}

    def get_task_progress(self) -> dict:
        """获取当前所有任务的执行状态。供前端轮询调用。"""
        return message_store.getByTopic('tasks')

    def get_execution_status(self) -> dict:
        """获取任务执行的计数状态，并明确指示整个序列是否已完成。"""
        total_tasks = self.dispatcher.total_task_count if self.dispatcher else 0
        
        tasks_data = message_store.getByTopic('tasks')
        completed_count = sum(len(tasks) for tasks in tasks_data.values())

        completion_signal = message_store.getByTopicAndKey('signals', 'completion')
        is_done = bool(completion_signal and completion_signal.get('status') == 'ALL_TASKS_COMPLETED')

        return {
            'completed': completed_count,
            'total': total_tasks,
            'is_done': is_done
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
