from util.browser_util import get_all_ads_envs
from myProject.pharos import PharosScript

def test_pharos_on_all_active_browsers():
    """
    自动发现在 browser.txt 中所有已启动的浏览器，
    并对每一个浏览器执行Pharos脚本的初始化（连接钱包）流程。
    """
    print("--- 开始在所有已启动的浏览器上，批量测试Pharos脚本初始化 ---")

    # 1. 自动获取所有已启动并附加成功的浏览器环境
    print("步骤1: 正在查找并附加到所有已启动的浏览器...")
    active_envs = get_all_ads_envs()

    if not active_envs:
        print("\n[测试结束] 未从 resource/browser.txt 中找到任何已启动的浏览器。")
        print("请先在AdsPower中打开一个或多个在配置文件中列出的浏览器。")
        return

    print(f"\n成功附加到 {len(active_envs)} 个浏览器，准备逐一进行测试...")
    
    success_count = 0
    failure_count = 0

    # 2. 遍历所有已启动的环境，执行测试
    for i, ads_env in enumerate(active_envs):
        print(f"\n--- [{i+1}/{len(active_envs)}] 开始测试浏览器ID: {ads_env.user_id} ---")
        try:
            # PharosScript的__init__方法包含了所有初始化逻辑
            pharos_script = PharosScript(ads_env)
            
            print(f"[成功] 浏览器 {ads_env.user_id} 的Pharos脚本初始化成功！")
            success_count += 1
        except Exception as e:
            print(f"[失败] 浏览器 {ads_env.user_id} 在测试过程中遇到错误: {e}")
            failure_count += 1
            
    print("\n--- 所有测试执行完毕 ---")
    print(f"结果: {success_count} 个成功, {failure_count} 个失败。")
    print("浏览器将保持打开状态供您检查。")


if __name__ == '__main__':
    test_pharos_on_all_active_browsers()
