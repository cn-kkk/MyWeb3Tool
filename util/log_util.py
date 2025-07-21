import datetime
import threading
import sys
import io

# 强制将标准输出的编码设置为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class LogUtil:
    """
    提供分级日志记录的静态工具类。
    """

    _lock = threading.Lock()

    @staticmethod
    def _log(level, env, msg):
        """
        私有的核心日志记录方法。
        :param level: 日志级别 (e.g., "INFO", "ERROR").
        :param env: 环境对象 (如 ads_env) 或字符串标识。
        :param msg: 日志消息。
        """
        with LogUtil._lock:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            thread_name = threading.current_thread().name

            # 尝试获取user_id，如果env没有该属性，则将其本身转为字符串
            env_name = getattr(env, "user_id", str(env))

            print(f"[{now}] [{level:<5}] {env_name}—{thread_name}: {msg}")

    @staticmethod
    def info(env, msg):
        """记录一条INFO级别的日志。"""
        LogUtil._log("INFO", env, msg)

    @staticmethod
    def warn(env, msg):
        """记录一条WARN级别的日志。"""
        LogUtil._log("WARN", env, msg)

    @staticmethod
    def error(env, msg):
        """记录一条ERROR级别的日志。"""
        LogUtil._log("ERROR", env, msg)
