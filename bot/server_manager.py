#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime

from bot.database import ServerRepository, VPNKeyRepository
from bot.xui_client import XUIClient, XUIClientConfig

logger = logging.getLogger(__name__)


class ServerManager:
    def __init__(self, server_repo: ServerRepository, key_repo: VPNKeyRepository):
        self.server_repo = server_repo
        self.key_repo = key_repo
        self._clients_cache = {}
    
    def get_client(self, server_id: int) -> Optional[XUIClient]:
        server = self.server_repo.get_by_id(server_id)
        if not server:
            return None
        
        if server_id not in self._clients_cache:
            config = XUIClientConfig(
                host=server.ip,
                port=server.port,
                username=server.username,
                password=server.password
            )
            client = XUIClient(config)
            self._clients_cache[server_id] = client
        
        return self._clients_cache[server_id]
    
    def create_key(self, user_id: int, email: str, days: int = 30, location: str = None) -> Tuple[bool, str, Optional[str]]:
        if location:
            server = self.server_repo.get_by_location(location)
            if not server:
                return False, f"Локация '{location}' не найдена", None
        else:
            server = self.server_repo.get_default()
            if not server:
                return False, "Нет доступных серверов", None
        
        client = self.get_client(server.id)
        if not client or not client.login():
            return False, f"Ошибка подключения к серверу {server.location}", None
        
        success, result = client.create_client(email, days)
        if not success:
            return False, result, None
        
        key = self.key_repo.create(user_id, email, result, days, server.location)
        if not key:
            return False, "Ошибка сохранения в БД", None
        
        logger.info(f"✅ Ключ создан: {email} на {server.location}")
        return True, f"Ключ создан на {server.location}", result
    
    def delete_key(self, email: str) -> bool:
        key = self.key_repo.get_by_email(email)
        if not key:
            return False
        
        server = self.server_repo.get_by_id(key.server_id)
        if server:
            client = self.get_client(server.id)
            if client and client.login():
                client.delete_client(email)
        
        return self.key_repo.deactivate(email)