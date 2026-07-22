#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from typing import Optional

from aiogram import types
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import CONFIG
from bot.database import UserRepository, ServerRepository, VPNKeyRepository
from bot.server_manager import ServerManager
from bot.ssh_installer import XUIInstaller, SSHConfig
from bot.keyboards import Keyboards

logger = logging.getLogger(__name__)


class Handlers:
    def __init__(self, user_repo: UserRepository, server_repo: ServerRepository,
                 key_repo: VPNKeyRepository, server_manager: ServerManager):
        self.user_repo = user_repo
        self.server_repo = server_repo
        self.key_repo = key_repo
        self.server_manager = server_manager
        self.keyboards = Keyboards()
        self._waiting_for = {}
    
    # ============ START ============
    
    async def cmd_start(self, message: types.Message):
        user = self.user_repo.create(
            message.from_user.id,
            message.from_user.username or '',
            message.from_user.first_name or '',
            message.from_user.last_name or ''
        )
        
        await message.reply(
            "🔐 <b>VPN Бот</b>\n\n"
            "Получите безопасный доступ в интернет.\n\n"
            "📌 <b>Доступные команды:</b>\n"
            "🚀 Создать ключ\n"
            "📋 Мои ключи\n"
            "🔄 Переустановить ключ\n"
            "🌍 Сменить локацию\n"
            "📖 Помощь",
            parse_mode=ParseMode.HTML,
            reply_markup=self.keyboards.main(user)
        )
    
    # ============ HELP ============
    
    async def cmd_help(self, message: types.Message):
        user = self.user_repo.get(message.from_user.id)
        
        await message.reply(
            "📖 <b>Инструкция</b>\n\n"
            "1️⃣ Нажмите <b>🚀 Создать ключ</b>\n"
            "2️⃣ Скопируйте VLESS ссылку\n"
            "3️⃣ Импортируйте в приложение\n\n"
            "<b>📱 Клиенты:</b>\n"
            "Android: v2rayNG, Hiddify\n"
            "iOS: Streisand, V2Box\n"
            "Windows: v2rayN, Nekoray",
            parse_mode=ParseMode.HTML,
            reply_markup=self.keyboards.main(user)
        )
    
    # ============ АДМИН: ДОБАВЛЕНИЕ СЕРВЕРА ============
    
    async def cmd_add_server(self, message: types.Message):
        user = self.user_repo.get(message.from_user.id)
        if not user or not user.is_admin:
            await message.reply("⛔ Доступ запрещен. Только для администраторов.")
            return
        
        await message.reply(
            "🔧 <b>Добавление нового сервера</b>\n\n"
            "Отправьте данные в формате:\n"
            "<code>IP:ПАРОЛЬ:НАЗВАНИЕ_ЛОКАЦИИ</code>\n\n"
            "Пример:\n"
            "<code>123.123.123.123:MyPass123:🇳🇱 Амстердам</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=self.keyboards.cancel()
        )
        self._waiting_for[message.from_user.id] = 'add_server'
    
    async def process_add_server(self, message: types.Message):
        user_id = message.from_user.id
        
        if user_id not in self._waiting_for or self._waiting_for[user_id] != 'add_server':
            return
        
        try:
            parts = message.text.split(':')
            if len(parts) != 3:
                await message.reply("❌ Неверный формат. Используйте: IP:ПАРОЛЬ:ЛОКАЦИЯ")
                return
            
            ip, password, location = parts
            
            existing = self.server_repo.get_by_location(location)
            if existing:
                await message.reply(f"❌ Локация '{location}' уже существует!")
                return
            
            status = await message.reply(f"🔄 Установка 3x-ui на {ip}...\n📍 Локация: {location}")
            
            ssh_config = SSHConfig(host=ip, password=password)
            installer = XUIInstaller(ssh_config)
            success, result = installer.install(54321)
            installer.close()
            
            if not success:
                await status.edit_text(f"❌ Ошибка установки:\n{result}")
                return
            
            server = self.server_repo.create(ip, password, location)
            if not server:
                await status.edit_text("❌ Ошибка сохранения сервера в БД")
                return
            
            servers = self.server_repo.get_all()
            if len(servers) == 1:
                self.server_repo.set_default(server.id)
            
            await status.edit_text(
                f"✅ <b>Сервер успешно добавлен!</b>\n\n"
                f"📍 Локация: {location}\n"
                f"🌐 IP: {ip}\n\n"
                f"Теперь пользователи могут создавать ключи на {location}!",
                parse_mode=ParseMode.HTML
            )
            
            del self._waiting_for[user_id]
            
        except Exception as e:
            await message.reply(f"❌ Ошибка: {str(e)}")
            logger.error(f"Ошибка добавления сервера: {e}")
    
    # ============ АДМИН: СПИСОК СЕРВЕРОВ ============
    
    async def cmd_servers(self, message: types.Message):
        user = self.user_repo.get(message.from_user.id)
        if not user or not user.is_admin:
            await message.reply("⛔ Доступ запрещен.")
            return
        
        servers = self.server_repo.get_all()
        
        if not servers:
            await message.reply("⚠️ Нет добавленных серверов.\nИспользуйте /add_server для добавления.")
            return
        
        text = "🌍 <b>Список серверов</b>\n\n"
        for s in servers:
            default = "⭐️ ДЕФОЛТНЫЙ" if s.is_default