import threading
import os
import importlib.util
import inspect

from backend.dispatcher import Dispatcher
from util.log_util import log_util
from config import AppConfig

class SmartController:
    """
    最终版的、最简化的智能控制器，作为系统的统一入口。
    """
    def __init__(self):
        self.log = log_util
        self.projects_map = {}
        self.interrupt_event = threading.Event()
        self.task_results = []
        self.results_lock = threading.Lock()

    def discover_projects(self):
        """扫描并加载所有项目脚本。"""
        self.projects_map.clear()
        project_dir = AppConfig.MY_PROJECT_DIR
        if not os.path.exists(project_dir):
            self.log.warn("智能控制器", f"项目目录 '{project_dir}' 不存在。")
            return {}

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
                except Exception as e:
                    self.log.error("智能控制器", f"加载项目脚本 {fname} 失败: {e}", exc_info=True)
        return self.projects_map

    def interrupt_tasks(self):
        """向所有工作线程发送中断信号。"""
        self.log.info("智能控制器", "接收到中断信号，正在终止所有操作...")
        self.interrupt_event.set()

    def dispatch_sequence(self, sequence: list[dict], concurrent_browsers: int):
        """
        接收UI层的请求，创建并启动调度器来完成所有工作。
        """
        self.log.info("智能控制器", f"接收到执行任务请求。")
        
        self.task_results.clear()
        self.interrupt_event.clear()

        # 创建调度器实例，并把所有需要的资源和配置都交给他
        dispatcher = Dispatcher(
            sequence=sequence,
            concurrent_browsers=concurrent_browsers,
            projects_map=self.projects_map,
            results_list=self.task_results,
            results_lock=self.results_lock,
            interrupt_event=self.interrupt_event
        )

        # 命令调度器开始工作
        dispatcher.execute()

        self.log.info("智能控制器", "所有任务已执行完毕。")
        return self.task_results
