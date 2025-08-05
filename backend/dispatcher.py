import threading
import time
import itertools
import random
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import pyautogui
from DrissionPage import ChromiumPage, ChromiumOptions

from util.ads_browser_util import AdsBrowserUtil
from util.log_util import log_util
from domain.task_result import TaskResult

def get_windows_dpi_scaling():
    """通过调用 Windows API 获取屏幕的 DPI 缩放比例。"""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        hdc = user32.GetDC(0)
        dpi_x = gdi32.GetDeviceCaps(hdc, 88)
        user32.ReleaseDC(0, hdc)
        return dpi_x / 96.0
    except Exception:
        return 1.0

class Dispatcher:
    """
    最终版的调度器，运行在主线程。
    它使用内置的ThreadPoolExecutor和信号量来管理并发。
    """
    def __init__(self, sequence, concurrent_browsers, projects_map, results_list, results_lock, interrupt_event):
        self.sequence = sequence
        self.concurrent_browsers = concurrent_browsers
        self.projects_map = projects_map
        self.scale_factor = get_windows_dpi_scaling()
        self.results_list = results_list
        self.results_lock = results_lock
        self.interrupt_event = interrupt_event
        self.log = log_util
        self.screen_width, self.screen_height = pyautogui.size()
        self.executor = ThreadPoolExecutor(max_workers=self.concurrent_browsers, thread_name_prefix='BrowserWorker')
        self.concurrency_semaphore = threading.Semaphore(self.concurrent_browsers)
        self.browser_ids = []
        self.assignments = []

    def _generate_all_assignments(self):
        """根据原始任务序列，生成所有分配方案。"""
        num_browsers = len(self.browser_ids)
        expanded_tasks = []
        for task_def in self.sequence:
            task_template = {k: v for k, v in task_def.items() if k != 'repetition'}
            task_template['repetition'] = 1
            expanded_tasks.extend([task_template] * task_def.get('repetition', 1))
        
        total_tasks = len(expanded_tasks)
        if not total_tasks: 
            self.assignments = [[] for _ in range(num_browsers)]
            return
        if total_tasks <= 1: 
            all_permutations = [expanded_tasks]
        elif total_tasks > 7:
            all_permutations = []
            for _ in range(100):
                shuffled_list = list(expanded_tasks)
                random.shuffle(shuffled_list)
                all_permutations.append(shuffled_list)
        else:
            task_tuples = [tuple(sorted(d.items())) for d in expanded_tasks]
            all_permutations_as_tuples = list(set(itertools.permutations(task_tuples)))
            all_permutations = [[dict(t) for t in p] for p in all_permutations_as_tuples]

        if not all_permutations: 
            self.assignments = [[] for _ in range(num_browsers)]
            return

        assignment_cycler = itertools.cycle(all_permutations)
        self.assignments = [next(assignment_cycler) for _ in range(num_browsers)]

    def _arrange_window(self, browser: ChromiumPage, worker_id: int):
        """根据总并发数和当前序号，动态计算并排列窗口。"""
        try:
            page = browser.new_tab()
            time.sleep(1)

            all_tabs = browser.get_tabs()
            if len(all_tabs) > 1:
                for tab in all_tabs:
                    if tab.tab_id != page.tab_id:
                        tab.close()
                time.sleep(0.5)

            if self.concurrent_browsers <= 2: cols, rows = 2, 1
            elif self.concurrent_browsers <= 4: cols, rows = 2, 2
            elif self.concurrent_browsers <= 6: cols, rows = 3, 2
            elif self.concurrent_browsers <= 8: cols, rows = 4, 2
            else: cols, rows = 4, 2

            taskbar_height = 80
            gap_x = 10
            gap_y = 10

            cell_width = (self.screen_width - (cols - 1) * gap_x) / cols
            cell_height = (self.screen_height - taskbar_height - (rows - 1) * gap_y) / rows

            row = worker_id // cols
            col = worker_id % cols

            logical_x = col * (cell_width + gap_x)
            logical_y = row * (cell_height + gap_y)

            actual_x = int(logical_x / self.scale_factor)
            actual_y = int(logical_y / self.scale_factor)
            actual_width = int(cell_width / self.scale_factor)
            actual_height = int(cell_height / self.scale_factor)

            for attempt in range(3):
                try:
                    page.set.activate()
                    time.sleep(0.5)
                    page.set.window.normal()
                    time.sleep(0.1)
                    page.set.window.size(width=actual_width, height=actual_height)
                    time.sleep(0.1)
                    page.set.window.location(x=actual_x, y=actual_y)
                    return
                except Exception:
                    if attempt >= 2:
                        self.log.error(f"调度器", f"排列窗口 {browser.address} 重试3次后仍然失败。", exc_info=True)
                    else:
                        time.sleep(1)

        except Exception as e:
            self.log.error(f"调度器", f"排列窗口时发生严重错误: {e}", exc_info=True)

    def _worker(self, browser, assignment, user_id):
        """包含原BrowserWorker核心逻辑的工作函数，由线程池执行。"""
        try:
            script_instances = {}
            for task in assignment:
                if self.interrupt_event.is_set():
                    break

                task_name = task.get("task_name")
                project_name_inferred = task_name.split('_task_')[0].capitalize()
                project_class = self.projects_map.get(project_name_inferred)

                if not project_class:
                    details = f"无法从任务名 '{task_name}' 推断出有效的项目类。"
                    result = TaskResult(user_id, task_name, "FAILURE", datetime.now(), details)
                else:
                    try:
                        if project_name_inferred not in script_instances:
                            script_instances[project_name_inferred] = project_class(browser=browser, user_id=user_id)
                        
                        script_instance = script_instances[project_name_inferred]
                        task_method = getattr(script_instance, task_name)
                        task_method()
                        result = TaskResult(user_id, task_name, "SUCCESS", datetime.now(), "任务成功完成。")
                    except Exception as e:
                        details = f"执行任务时发生异常: {e}\n{traceback.format_exc()}"
                        result = TaskResult(user_id, task_name, "FAILURE", datetime.now(), details)

                with self.results_lock:
                    self.results_list.append(result)

        except Exception as e:
            self.log.error(f"工作线程 {threading.get_ident()}", f"处理工作包 {user_id} 时发生严重错误: {e}", exc_info=True)
        finally:
            if browser: browser.quit()
            self.concurrency_semaphore.release()

    def execute(self):
        """调度器的主执行方法。"""
        self.browser_ids = AdsBrowserUtil.get_configured_user_ids()
        if not self.browser_ids:
            self.log.error("调度器", "未在配置文件中找到任何浏览器ID，调度中止。")
            return

        self._generate_all_assignments()

        for i, user_id in enumerate(self.browser_ids):
            if self.interrupt_event.is_set():
                break

            self.concurrency_semaphore.acquire()

            try:
                browser = AdsBrowserUtil.start_browser_if_not_running(user_id)
                if not browser: 
                    self.log.error("调度器", f"获取浏览器实例 {user_id} 失败，跳过。")
                    self.concurrency_semaphore.release()
                    continue

                self._arrange_window(browser, worker_id=i)
                
                assignment = self.assignments[i]
                
                self.executor.submit(self._worker, browser, assignment, user_id)
            
            except Exception as e:
                self.log.error(f"调度器", f"在主调度循环中处理 {user_id} 时发生严重错误: {e}", exc_info=True)
                self.concurrency_semaphore.release()
                continue
        
        self.executor.shutdown(wait=True)
