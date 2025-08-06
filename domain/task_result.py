from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class TaskResult:
    """用于封装单个任务执行结果的数据类。"""
    browser_id: str
    task_name: str
    status: str  # e.g., 'SUCCESS', 'FAILURE'
    timestamp: datetime
    details: str

    def to_dict(self):
        """将TaskResult对象转换为可序列化为JSON的字典。"""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d
