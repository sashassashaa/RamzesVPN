#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.main import VPNBot
from bot.config import CONFIG


def main():
    print("=" * 60)
    print("🚀 VPN BOT v3.0 - Мульти-серверный бот")
    print("=" * 60)
    print(f"📡 Бот: {CONFIG.BOT_TOKEN[:15]}...")
    print(f"👥 Админы: {CONFIG.ADMIN_IDS}")
    print("=" * 60)
    print()
    
    try:
        CONFIG.validate()
        os.makedirs('/opt/vpn_bot/data', exist_ok=True)
        os.makedirs('/opt/vpn_bot/logs', exist_ok=True)
        
        bot = VPNBot()
        bot.run()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()