class task_annotation:
    """
    一个用于存放所有任务相关注解（装饰器）的容器类。
    """

    @staticmethod
    def once_per_day(func):
        """
        注解，用于标记一个任务每天只能执行一次。
        它会给函数对象附加一个 '_task_limit' 属性。
        """
        setattr(func, '_task_limit', 'once_per_day')
        return func


