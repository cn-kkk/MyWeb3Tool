import threading
from copy import deepcopy

class MessageStore:
    """
    一个单例的、线程安全的、基于主题的内存状态存储器。
    严格按照用户设计的API实现。
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._store = {}  # The actual data store is a dictionary
        return cls._instance

    def put(self, topic: str, key: str, value: any):
        """
        将一个键值对放入指定的主题下。
        如果key已存在，此方法会覆盖其旧值。
        """
        with self._lock:
            if topic not in self._store:
                self._store[topic] = {}
            self._store[topic][key] = value

    def getByTopic(self, topic: str) -> dict:
        """
        获取指定主题下的所有数据。
        返回一个深拷贝以防止外部修改内部状态。
        """
        with self._lock:
            return deepcopy(self._store.get(topic, {}))

    def getByTopicAndKey(self, topic: str, key: str) -> any:
        """
        获取指定主题下特定key的值。
        返回一个深拷贝以防止外部修改内部状态。
        """
        with self._lock:
            if topic in self._store:
                return deepcopy(self._store[topic].get(key))
            return None

    def clear_topic(self, topic: str):
        """清空一个主题下的所有数据，用于开始新的任务。"""

        with self._lock:
            if topic in self._store:
                self._store[topic].clear()

# 导出的单例实例
message_store = MessageStore()
