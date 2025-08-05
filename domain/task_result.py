from dataclasses import dataclass
from datetime import datetime

@dataclass
class TaskResult:
    """用于封装单个任务执行结果的数据类。"""
    browser_id: str
    task_name: str
    status: str  # e.g., 'SUCCESS', 'FAILURE'
    timestamp: datetime
    details: str
