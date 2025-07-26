import os
import sys
import threading
from datetime import datetime

# 将项目根目录添加到sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import LOGS_DIR, LOG_FILENAME_PREFIX, LOG_FILENAME_FORMAT

class LogUtil:
    """
    一个独立的、不依赖任何UI框架的日志工具类。
    负责将日志打印到控制台、写入文件，并通过回调函数通知所有订阅者。
    这是一个线程安全的单例。
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(LogUtil, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        with self._lock:
            if hasattr(self, '_initialized') and self._initialized:
                return
            
            self.ui_handlers = []
            self.log_buffer = []
            self.buffer_lock = threading.Lock()
            
            if not os.path.exists(LOGS_DIR):
                os.makedirs(LOGS_DIR)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_filename = os.path.join(LOGS_DIR, LOG_FILENAME_FORMAT.format(prefix=LOG_FILENAME_PREFIX, timestamp=timestamp))
            
            self.flush_interval = 3.0  # 写入间隔为3秒
            self.timer = None
            self.start_timer()
            
            self._initialized = True

    def add_ui_handler(self, handler):
        if handler not in self.ui_handlers:
            self.ui_handlers.append(handler)

    def _flush_buffer_to_file(self):
        with self.buffer_lock:
            if not self.log_buffer:
                return
            try:
                with open(self.log_filename, "a", encoding="utf-8") as f:
                    for msg in self.log_buffer:
                        f.write(msg + "\n")
                self.log_buffer.clear()
            except Exception as e:
                print(f"[CRITICAL] Failed to write to log file {self.log_filename}: {e}")
        # 重置定时器
        self.start_timer()

    def start_timer(self):
        # 确保旧的定时器被取消
        if self.timer and self.timer.is_alive():
            self.timer.cancel()
        self.timer = threading.Timer(self.flush_interval, self._flush_buffer_to_file)
        self.timer.daemon = True  # 设置为守护线程，以便主程序退出时它也会退出
        self.timer.start()

    def _log(self, level: str, user_id: str, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] [{level.upper()}] [{user_id}] {message}"
        
        # 1. 立即打印到控制台
        print(full_message)
        
        # 2. 添加到缓冲区
        with self.buffer_lock:
            self.log_buffer.append(full_message)
        
        # 3. 立即通知所有UI订阅者
        for handler in self.ui_handlers:
            try:
                handler(full_message)
            except Exception as e:
                print(f"[CRITICAL] UI Log handler {handler} failed: {e}")

    def info(self, user_id: str, message: str):
        self._log("info", user_id, message)

    def warn(self, user_id: str, message: str):
        self._log("warn", user_id, message)

    def error(self, user_id: str, message: str, exc_info=False):
        if exc_info:
            import traceback
            message += "\n" + traceback.format_exc()
        self._log("error", user_id, message)

    def shutdown(self):
        """在程序退出时调用，确保所有缓冲的日志都被写入。"""
        if self.timer and self.timer.is_alive():
            self.timer.cancel()
        self._flush_buffer_to_file()

# 创建一个全局唯一的日志实例
log_util = LogUtil()