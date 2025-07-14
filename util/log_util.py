import datetime
import threading
import sys
import io

# 强制将标准输出的编码设置为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class LogUtil:
    @staticmethod
    def log(env, msg):
        """
        全局日志记录方法。
        :param env: 环境对象 (如 ads_env) 或字符串标识。
        :param msg: 日志消息。
        """
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        thread_name = threading.current_thread().name
        
        # 尝试获取user_id，如果env没有该属性，则将其本身转为字符串
        env_name = getattr(env, 'user_id', str(env))
        
        print(f"[{now}] {env_name}—{thread_name}: {msg}")