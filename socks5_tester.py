import requests
import time
from typing import List
from util.socks5_reader import Socks5Reader, Socks5Proxy


class Socks5Tester:
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.reader = Socks5Reader()
        self.test_url = "https://www.google.com"
    
    def test_proxy(self, proxy: Socks5Proxy) -> bool:
        proxy_url = self.reader.get_proxy_url(proxy)
        
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        try:
            print(f"正在测试代理: {proxy}")
            start_time = time.time()
            
            response = requests.get(
                self.test_url,
                proxies=proxies,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            if response.status_code == 200:
                print(f"✅ 成功! 代理 {proxy} 连接谷歌成功")
                print(f"   响应时间: {response_time}ms")
                print(f"   状态码: {response.status_code}")
                return True
            else:
                print(f"❌ 失败! 代理 {proxy} 连接谷歌失败")
                print(f"   状态码: {response.status_code}")
                return False
                
        except requests.exceptions.ProxyError as e:
            print(f"❌ 失败! 代理 {proxy} 连接错误: {e}")
            return False
        except requests.exceptions.Timeout as e:
            print(f"❌ 失败! 代理 {proxy} 连接超时: {e}")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"❌ 失败! 代理 {proxy} 连接失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 失败! 代理 {proxy} 未知错误: {e}")
            return False
    
    def test_all_proxies(self) -> None:
        print("=" * 60)
        print("开始测试Socks5代理连接谷歌")
        print("=" * 60)
        
        # 读取所有代理
        proxies = self.reader.read_proxies()
        
        if not proxies:
            print("没有找到可用的代理，请检查文件路径和格式")
            return
        
        print(f"找到 {len(proxies)} 个代理，开始测试...")
        print()
        
        # 统计结果
        success_count = 0
        fail_count = 0
        
        # 测试每个代理
        for i, proxy in enumerate(proxies, 1):
            print(f"[{i}/{len(proxies)}] ", end="")
            
            if self.test_proxy(proxy):
                success_count += 1
            else:
                fail_count += 1
            
            print("-" * 40)
            
            # 添加延迟避免请求过快
            if i < len(proxies):
                time.sleep(1)
        
        # 打印总结
        print("=" * 60)
        print("测试完成!")
        print(f"总代理数: {len(proxies)}")
        print(f"成功: {success_count}")
        print(f"失败: {fail_count}")
        print(f"成功率: {success_count/len(proxies)*100:.1f}%")
        print("=" * 60)


def main():
    tester = Socks5Tester(timeout=10)
    tester.test_all_proxies()


if __name__ == "__main__":
    main() 