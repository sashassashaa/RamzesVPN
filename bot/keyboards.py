#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from bot.database import User


class Keyboards:
    def main(self, user: User) -> ReplyKeyboardMarkup:
        buttons = [
            ["🚀 Создать ключ", "📋 Мои ключи"],
            ["🔄 Переустановить", "🌍 Сменить локацию ключа"],
            ["📖 Помощь"]
        ]
        
        if user and user.is_admin:
            buttons.append(["👑 Админ-панель"])
        
        return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=buttons)
    
    def admin(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("➕ Добавить сервер", callback_data="admin_add_server")],
            [InlineKeyboardButton("📋 Список серверов", callback_data="admin_servers")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")]
        ])
    
    def cancel(self) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[[KeyboardButton("❌ Отмена")]]
        )
    
    def key_actions(self, email: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton("📋 Копировать", callback_data=f"copy_{email}"),
                InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{email}")
            ],
            [InlineKeyboardButton("🔄 Обновить", callback_data=f"renew_{email}")]
        ])