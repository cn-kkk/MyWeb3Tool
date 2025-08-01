import os
import random
import secrets
from dataclasses import dataclass
from typing import List, Dict

from eth_account.hdaccount.mnemonic import Mnemonic

from config import AppConfig
from util.log_util import log_util
from eth_account import Account


@dataclass
class Wallet:
    private_key: str
    address: str


# 钱包工具类，包含读取和保存
class WalletUtil:
    def __init__(self, file_path: str = AppConfig.WALLET_CONFIG_FILE):
        self.file_path = file_path

    def read_wallets(self) -> List[Wallet]:
        wallets = []
        if not os.path.exists(self.file_path):
            log_util.warn("WalletUtil", f"配置文件 {self.file_path} 不存在。请在exe同目录下创建resource文件夹并添加该文件。")
            return wallets
        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(AppConfig.DATA_SEPARATOR)
                    if len(parts) != 2:
                        print(f"警告: 第{line_num}行格式错误: {line}")
                        continue
                    private_key, address = parts
                    wallets.append(
                        Wallet(private_key=private_key.strip(), address=address.strip())
                    )
            return wallets
        except Exception as e:
            print(f"读取文件失败: {e}")
            return wallets

    def save_wallet_config(self, configs: List[Dict[str, str]]) -> bool:
        """保存钱包配置"""
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                for config in configs:
                    line = (                        f"{config['privateKey']}{AppConfig.DATA_SEPARATOR}{config['address']}\n"                    )
                    f.write(line)
            return True
        except Exception as e:
            print(f"保存钱包配置失败: {e}")
            return False

    def generate_random_evm_address(self) -> str:
        """
        生成一个随机的EVM地址

        Returns:
            str: 生成的EVM地址
        """
        private_key = "0x" + secrets.token_hex(32)
        account = Account.from_key(private_key)
        return account.address

    @staticmethod
    def get_a_random_word() -> str:
        """
        从BIP-39英文词库中随机获取一个单词。

        Returns:
            str: 一个随机的英文单词。
        """
        word_list = Mnemonic("english").wordlist
        return random.choice(word_list)
