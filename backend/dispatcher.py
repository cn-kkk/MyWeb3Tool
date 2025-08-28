import threading
import time
import itertools
import random
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

import pyautogui
from DrissionPage import ChromiumPage, ChromiumOptions

from backend.message_store import message_store
from util.ads_browser_util import AdsBrowserUtil
from util.anti_sybil_dp_util import AntiSybilDpUtil
from util.log_util import log_util

from util.okx_wallet_util import OKXWalletUtil


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
    调度器，运行在主线程。
    它使用内置的ThreadPoolExecutor和信号量来管理并发。
    """

    def __init__(self, sequence, concurrent_browsers, projects_map, interrupt_event):
        self.sequence = sequence
        self.concurrent_browsers = concurrent_browsers
        self.projects_map = projects_map
        self.interrupt_event = interrupt_event
        self.log = log_util

        self.scale_factor = get_windows_dpi_scaling()
        self.screen_width, self.screen_height = pyautogui.size()

        self.executor = ThreadPoolExecutor(max_workers=self.concurrent_browsers, thread_name_prefix='BrowserWorker')
        self.concurrency_semaphore = threading.Semaphore(self.concurrent_browsers)

        self.job_list = []  # 用于存放所有工作任务定义
        self.total_task_count = 0  # 将在execute()方法中计算

    def _generate_job_list(self):
        """
        Generates a list of all jobs for all browsers based on the sequence.
        This implements the 'consolidate first, then shuffle' strategy.
        """
        work_by_browser = {}

        # 阶段1: 为每个浏览器合并任务
        for project_group in self.sequence:
            project_tasks = project_group.get('tasks', [])
            browser_ids_for_project = project_group.get('browser_ids', [])

            # 根据重复次数展开任务
            expanded_tasks = []
            for task in project_tasks:
                for _ in range(task.get('repetition', 1)):
                    expanded_tasks.append({'task_name': task['task_name']})
            
            if not expanded_tasks:
                continue

            # 将这些任务追加到每个浏览器的任务列表中
            for browser_id in browser_ids_for_project:
                if browser_id not in work_by_browser:
                    work_by_browser[browser_id] = []
                work_by_browser[browser_id].extend(expanded_tasks)

        # 阶段2: 为每个浏览器打乱任务顺序并生成最终工作列表
        self.job_list = []
        for browser_id, tasks in work_by_browser.items():
            random.shuffle(tasks)
            self.job_list.append({
                'user_id': browser_id,
                'tasks_to_run': tasks
            })
        
        # 生成最终列表后，计算总任务数
        self.total_task_count = sum(len(job['tasks_to_run']) for job in self.job_list)
        self.log.info("调度器", f"已生成 {len(self.job_list)} 个工作包，总任务数: {self.total_task_count}")

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
            try:
                thread_name = threading.current_thread().name
                worker_id = int(thread_name.split('_')[-1])
                self._arrange_window(browser, worker_id)

                # 在窗口排列（并创建了新页面）后，立即获取该页面并注入补丁
                AntiSybilDpUtil.human_brief_wait()
                page = browser.latest_tab
                if page:
                    AntiSybilDpUtil.patch_webdriver_fingerprint(page)
                    self.log.info(user_id, "已成功为工作页面注入反指纹补丁。")
                else:
                    raise Exception("排列窗口后未能获取页面，无法注入补丁。")

            except Exception as e:
                self.log.error(user_id, f"排列窗口或注入补丁失败: {e}", exc_info=True)
                return # 关键步骤失败，中止该worker

            try:
                okx_util = OKXWalletUtil()
                okx_util.open_and_unlock_drission(browser, user_id)
            except Exception as e:
                self.log.error(user_id, f"钱包初始化解锁失败，任务序列中止: {e}", exc_info=True)
                return

            script_instances = {}
            task_execution_counts = Counter()
            for task in assignment:
                if self.interrupt_event.is_set():
                    self.log.warn(user_id, "检测到中断信号，任务序列已中止。")
                    break

                original_task_name = task.get("task_name")
                
                # 按照前端的规则，为同一个任务的多次执行创建唯一键 (e.g., task_name_0, task_name_1)
                execution_index = task_execution_counts[original_task_name]
                unique_task_name = f"{original_task_name}_{execution_index}"
                task_execution_counts[original_task_name] += 1

                project_name_inferred = original_task_name.split('_task_')[0].capitalize()
                project_class = self.projects_map.get(project_name_inferred)

                # 立即将状态设置为执行中并更新UI
                task_details = {
                    'task_name': unique_task_name, # 直接使用唯一名称作为任务名
                    'status': 'EXECUTING',
                    'details': '任务正在执行...',
                    'timestamp': datetime.now().isoformat(timespec='milliseconds')
                }
                current_browser_tasks = message_store.getByTopicAndKey('tasks', user_id) or {}
                current_browser_tasks[unique_task_name] = task_details
                message_store.put('tasks', user_id, current_browser_tasks)

                try:
                    if not project_class:
                        task_details['status'] = "FAILURE"
                        task_details['details'] = f"无法从任务名 '{original_task_name}' 推断出有效的项目类。"
                    else:
                        if project_name_inferred not in script_instances:
                            script_instances[project_name_inferred] = project_class(browser=browser, user_id=user_id)

                        script_instance = script_instances[project_name_inferred]
                        # 注意：调用方法时仍使用原始名称
                        task_method = getattr(script_instance, original_task_name)
                        task_return_value = task_method()

                        if isinstance(task_return_value, str):
                            task_details['status'] = "FAILURE"
                            task_details['details'] = task_return_value
                        else:
                            task_details['status'] = "SUCCESS"
                            task_details['details'] = "任务成功完成。"

                except Exception as e:
                    task_details['status'] = "FAILURE"
                    task_details['details'] = f"{e.__class__.__name__}: {e}" if str(e) else e.__class__.__name__
                    self.log.error(user_id, f"任务 {unique_task_name} 发生异常: {traceback.format_exc()}")

                finally:
                    # 使用 finally 确保最终状态（成功或失败）一定会被更新
                    task_details['timestamp'] = datetime.now().isoformat(timespec='milliseconds')
                    current_browser_tasks = message_store.getByTopicAndKey('tasks', user_id) or {}
                    current_browser_tasks[unique_task_name] = task_details
                    message_store.put('tasks', user_id, current_browser_tasks)

        except Exception as e:
            self.log.error(user_id, f"处理工作包时发生严重错误: {e}", exc_info=True)
        finally:
            if browser:
                try:
                    browser.quit()
                except Exception as e:
                    self.log.error(user_id, f"关闭浏览器 {browser.address} 时发生异常: {e}", exc_info=True)

            self.concurrency_semaphore.release()
            self.log.info(user_id, "信号量已成功释放。")

    def shutdown(self):
        """设置中断事件并清空待处理任务以停止所有工作。"""
        self.log.info("调度器", "接收到关闭信号，正在终止所有任务...")
        self.interrupt_event.set()
        self.log.info("调度器", "清空所有待执行的任务分配。")
        self.job_list.clear()

    def execute(self):
        """Dispatcher's main execution method."""
        self.log.info("调度器", "开始生成工作分配...")
        self._generate_job_list()

        if not self.job_list:
            self.log.warn("调度器", "没有生成任何有效的工作任务，调度中止。")
            message_store.put('signals', 'completion', {'status': 'ALL_TASKS_COMPLETED'})
            return

        futures = []
        for job in self.job_list:
            if self.interrupt_event.is_set():
                self.log.info("调度器", "在分发任务前检测到中断信号，主调度循环终止。")
                break

            self.concurrency_semaphore.acquire()
            
            user_id = job['user_id']
            assignment = job['tasks_to_run']
            
            try:
                browser = AdsBrowserUtil.start_browser_if_not_running(user_id)
                if not browser:
                    self.log.error("调度器", f"获取浏览器实例 {user_id} 失败，跳过。")
                    self.concurrency_semaphore.release()
                    continue

                future = self.executor.submit(self._worker, browser, assignment, user_id)
                futures.append(future)

            except Exception as e:
                self.log.error(f"调度器", f"在主调度循环中处理 {user_id} 时发生严重错误: {e}", exc_info=True)
                self.concurrency_semaphore.release()
                continue

        if futures:
            from concurrent.futures import wait
            wait(futures)

        self.executor.shutdown(wait=True)
        message_store.put('signals', 'completion', {'status': 'ALL_TASKS_COMPLETED'})