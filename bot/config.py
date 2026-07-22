#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from dataclasses import dataclass
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    ADMIN_IDS: List[int] = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
    SUPPORT_USERNAME: str = os.getenv('SUPPORT_USERNAME', 'support')
    DB_PATH: str = os.getenv('DB_PATH', '/opt/vpn_bot/data/database.db')
    
    VLESS_PORT: int = int(os.getenv('VLESS_PORT', 443))
    VLESS_LIMIT_IP: int = int(os.getenv('VLESS_LIMIT_IP', 2))
    VLESS_FLOW: str = os.getenv('VLESS_FLOW', 'xtls-rprx-vision')
    VLESS_SNI: str = os.getenv('VLESS_SNI', 'apple.com')
    VLESS_FP: str = os.getenv('VLESS_FP', 'chrome')
    
    PRICES: Dict[int, int] = {
        30: int(os.getenv('PRICE_1_MONTH', 149)),
        90: int(os.getenv('PRICE_3_MONTH', 379)),
        180: int(os.getenv('PRICE_6_MONTH', 749)),
        365: int(os.getenv('PRICE_12_MONTH', 1349)),
    }
    
    @classmethod
    def validate(cls) -> bool:
        errors = []
        if not cls.BOT_TOKEN:
            errors.append("❌ BOT_TOKEN не установлен в .env")
        if not cls.ADMIN_IDS:
            errors.append("❌ ADMIN_IDS не установлен в .env")
        if errors:
            raise ValueError("\n".join(errors))
        return True


CONFIG = Config()