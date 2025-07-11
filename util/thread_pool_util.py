import threading
from queue import Queue

class ThreadWithStack(threading.Thread):
    def __init__(self, task_queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_queue = task_queue
        self.stack = []  # 线程独立栈
        self.daemon = True

    def run(self):
        while True:
            func, args, kwargs = self.task_queue.get()
            try:
                # 任务函数可通过threading.current_thread().stack访问线程栈
                func(*args, **kwargs)
            except Exception as e:
                print(f"[ThreadPoolUtil] 线程异常: {e}")
            finally:
                self.task_queue.task_done()

class ThreadPoolUtil:
    def __init__(self, max_workers=6):
        self.task_queue = Queue()
        self.threads = []
        for _ in range(max_workers):
            t = ThreadWithStack(self.task_queue)
            t.start()
            self.threads.append(t)

    def submit(self, func, *args, **kwargs):
        """
        提交任务到线程池。func为同步阻塞函数。
        任务函数内可通过threading.current_thread().stack访问线程栈。
        """
        self.task_queue.put((func, args, kwargs))

    def wait_completion(self):
        """
        阻塞直到所有任务完成。
        """
        self.task_queue.join() 