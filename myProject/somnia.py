import time
from util.okx_wallet_util import OKXWalletUtil
from util.log_util import LogUtil
from util.anti_sybil_util import AntiSybilUtil
from config import OKX_EXTENSION_ID

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
        LogUtil.log(self.ads_env, f"开始初始化项目: {self.project_name}")
        # 步骤1: 最大化窗口确保焦点
        try:
            LogUtil.log(self.ads_env, "步骤1: 尝试最大化浏览器窗口...")
            self.driver.maximize_window()
            time.sleep(1)
        except Exception:
            LogUtil.log(self.ads_env, f"[WARN] 窗口已是最大化，继续执行。")
        # 步骤2: 先解锁钱包，再断开连接
        LogUtil.log(self.ads_env, "步骤2: 解锁OKX钱包...")
        if not self.okx_util.open_and_unlock(self.driver):
            raise RuntimeError("钱包解锁失败，任务无法继续。")
        LogUtil.log(self.ads_env, "钱包解锁成功，切换到钱包页面准备断开连接...")
        # 再次确保driver在钱包页面
        wallet_url = f"chrome-extension://{self.okx_util.EXTENSION_ID}/popup.html"
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if wallet_url in self.driver.current_url:
                LogUtil.log(self.ads_env, f"[DEBUG] 已切换到OKX钱包插件页面: {self.driver.current_url}")
                break
        time.sleep(2)
        if not self.okx_util.disconnect_wallet(self.driver):
            LogUtil.log(self.ads_env, "[WARN] 未能自动断开钱包连接，可能已断开。")
        else:
            LogUtil.log(self.ads_env, "已自动断开钱包连接。")
        time.sleep(1)
