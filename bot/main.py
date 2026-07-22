#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import BotCommand

from bot.config import CONFIG
from bot.database import Database, UserRepository, ServerRepository, VPNKeyRepository
from bot.server_manager import ServerManager
from bot.handlers import Handlers
from bot.keyboards import Keyboards

logger = logging.getLogger(__name__)


class VPNBot:
    def __init__(self):
        self.bot = Bot(token=CONFIG.BOT_TOKEN)
        self.dp = Dispatcher(self.bot)
        
        # Инициализация репозиториев
        self.db = Database(CONFIG.DB_PATH)
        self.user_repo = UserRepository(self.db)
        self.server_repo = ServerRepository(self.db)
        self.key_repo = VPNKeyRepository(self.db)
        
        # Менеджер серверов
        self.server_manager = ServerManager(self.server_repo, self.key_repo)
        
        # Обработчики
        self.handlers = Handlers(
            user_repo=self.user_repo,
            server_repo=self.server_repo,
            key_repo=self.key_repo,
            server_manager=self.server_manager
        )
        
        # Клавиатуры
        self.keyboards = Keyboards()
        
        # Регистрация обработчиков
        self._register_handlers()
        self._register_callbacks()
    
    def _register_handlers(self):
        """Регистрация обработчиков сообщений"""
        
        # ===== АДМИН КОМАНДЫ =====
        self.dp.message_handler(commands=['add_server'])(self.handlers.cmd_add_server)
        self.dp.message_handler(commands=['servers'])(self.handlers.cmd_servers)
        self.dp.message_handler(commands=['delete_server'])(self.handlers.cmd_delete_server)
        self.dp.message_handler(commands=['set_default'])(self.handlers.cmd_set_default)
        
        # ===== ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ =====
        self.dp.message_handler(commands=['start'])(self.handlers.cmd_start)
        self.dp.message_handler(commands=['create'])(self.handlers.cmd_create_key)
        self.dp.message_handler(commands=['mykeys'])(self.handlers.cmd_my_keys)
        self.dp.message_handler(commands=['reinstall'])(self.handlers.cmd_reinstall)
        self.dp.message_handler(commands=['help'])(self.handlers.cmd_help)
        
        # ===== ТЕКСТОВЫЕ КОМАНДЫ (кнопки) =====
        self.dp.message_handler(lambda msg: msg.text == "🚀 Создать ключ")(self.handlers.cmd_create_key)
        self.dp.message_handler(lambda msg: msg.text == "📋 Мои ключи")(self.handlers.cmd_my_keys)
        self.dp.message_handler(lambda msg: msg.text == "🔄 Переустановить")(self.handlers.cmd_reinstall)
        self.dp.message_handler(lambda msg: msg.text == "📖 Помощь")(self.handlers.cmd_help)
        self.dp.message_handler(lambda msg: msg.text == "🌍 Сменить локацию ключа")(self.handlers.cmd_change_location)
        self.dp.message_handler(lambda msg: msg.text == "👑 Админ-панель")(self.handlers.cmd_admin_panel)
        
        # ===== ОБРАБОТКА ВВОДА =====
        self.dp.message_handler()(self.handlers.process_add_server)
    
    def _register_callbacks(self):
        """Регистрация callback запросов"""
        self.dp.callback_query_handler(lambda c: c.data.startswith('create_loc_'))(self.handlers.process_create_location)
        self.dp.callback_query_handler(lambda c: c.data == 'create_loc_default')(self.handlers.process_create_default)
        self.dp.callback_query_handler(lambda c: c.data == 'cancel_create')(self.handlers.process_cancel)
        self.dp.callback_query_handler(lambda c: c.data.startswith('change_loc_key_'))(self.handlers.process_change_location)
        self.dp.callback_query_handler(lambda c: c.data.startswith('move_key_'))(self.handlers.process_move_key)
        self.dp.callback_query_handler(lambda c: c.data == 'cancel_change_loc')(self.handlers.process_cancel)
        self.dp.callback_query_handler(lambda c: c.data == 'cancel_move')(self.handlers.process_cancel)
        
        # Админ callback
        self.dp.callback_query_handler(lambda c: c.data == 'admin_add_server')(self.handlers.cmd_add_server)
        self.dp.callback_query_handler(lambda c: c.data == 'admin_servers')(self.handlers.cmd_servers)
        self.dp.callback_query_handler(lambda c: c.data == 'admin_close')(self.handlers.process_cancel)
    
    def run(self):
        """Запуск бота"""
        logger.info("🚀 Запуск VPN бота...")
        
        # Установка команд
        commands = [
            BotCommand("start", "Главное меню"),
            BotCommand("create", "Создать ключ"),
            BotCommand("mykeys", "Мои ключи"),
            BotCommand("reinstall", "Переустановить ключ"),
            BotCommand("help", "Помощь"),
        ]
        
        async def set_commands():
            await self.bot.set_my_commands(commands)
        
        loop = asyncio.new_event_loop()
        loop.run_until_complete(set_commands())
        
        logger.info("✅ Бот готов к работе")
        executor.start_polling(self.dp, skip_updates=True)