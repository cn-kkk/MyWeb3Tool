import os
from dataclasses import dataclass
from typing import List, Dict
from config import AppConfig

# socks5ip的实体类
@dataclass
class Socks5Proxy:
    ip: str
    port: int
    username: str
    password: str
    
    def __str__(self):
        return f"{self.ip}:{self.port}"

# socks5工具类，包含读取和保存
class Socks5Util:
    def __init__(self, file_path: str = AppConfig.SOCKS5_CONFIG_FILE):
        self.file_path = file_path
    
    def read_proxies(self) -> List[Socks5Proxy]:
        proxies = []
        
        if not os.path.exists(self.file_path):
            print(f"警告: 文件 {self.file_path} 不存在")
            return proxies
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        # 解析格式: ip----port----username----password
                        parts = line.split(AppConfig.DATA_SEPARATOR)
                        if len(parts) != 4:
                            print(f"警告: 第{line_num}行格式错误: {line}")
                            continue
                        
                        ip, port_str, username, password = parts
                        port = int(port_str)
                        
                        proxy = Socks5Proxy(
                            ip=ip.strip(),
                            port=port,
                            username=username.strip(),
                            password=password.strip()
                        )
                        proxies.append(proxy)
                        
                    except ValueError as e:
                        print(f"警告: 第{line_num}行端口号格式错误: {line}")
                    except Exception as e:
                        print(f"警告: 第{line_num}行解析失败: {line}, 错误: {e}")
            
            print(f"成功读取 {len(proxies)} 个socks5代理")
            return proxies
            
        except Exception as e:
            print(f"读取文件失败: {e}")
            return proxies
    
    def get_proxy_url(self, proxy: Socks5Proxy) -> str:
        return f"socks5://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}"

    def save_socks5_config(self, configs: List[Dict[str, str]]) -> bool:
        """保存socks5配置"""
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                for config in configs:
                    line = f"{config['ip']}{AppConfig.DATA_SEPARATOR}{config['port']}{AppConfig.DATA_SEPARATOR}{config['username']}{AppConfig.DATA_SEPARATOR}{config['password']}\n"
                    f.write(line)
            return True
        except Exception as e:
            print(f"保存socks5配置失败: {e}")
            return False 