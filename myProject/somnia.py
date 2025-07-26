import time
from util.okx_wallet_util import OKXWalletUtil

class SomniaScript:
    """
    使用Selenium原生流程执行Somnia任务的脚本。
    """
    project_name = "Somnia"
    SOMNIA_URL = "https://testnet.somnia.network/"

    def __init__(self, ads_env):
        """
        初始化任务，自动完成钱包解锁和断开连接。
        """
        self.ads_env = ads_env
        self.driver = ads_env.driver
        self.okx_util = OKXWalletUtil()
        self._initialize_session()

    def _initialize_session(self):
        """
        执行核心初始化操作。
        """