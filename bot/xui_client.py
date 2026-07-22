#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class XUIClientConfig:
    host: str
    port: int
    username: str
    password: str
    vless_port: int = 443
    vless_limit_ip: int = 2
    vless_flow: str = 'xtls-rprx-vision'
    vless_sni: str = 'apple.com'
    vless_fp: str = 'chrome'


class XUIClient:
    def __init__(self, config: XUIClientConfig):
        self.config = config
        self.base_url = f"http://{config.host}:{config.port}"
        self.session = requests.Session()
        self._inbounds = None
        self._is_logged = False
    
    def login(self) -> bool:
        try:
            resp = self.session.post(
                f"{self.base_url}/login",
                json={'username': self.config.username, 'password': self.config.password},
                timeout=5
            )
            if resp.json().get('success'):
                self._is_logged = True
                logger.info(f"✅ Авторизация в 3x-ui ({self.config.host})")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка авторизации: {e}")
            return False
    
    @property
    def inbounds(self) -> list:
        if self._inbounds is None:
            if not self._is_logged:
                self.login()
            try:
                resp = self.session.get(f"{self.base_url}/panel/api/inbounds/list/", timeout=5)
                self._inbounds = resp.json().get('obj', [])
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки inbound: {e}")
                self._inbounds = []
        return self._inbounds
    
    def _get_vless_inbound(self) -> Optional[Dict]:
        for inbound in self.inbounds:
            if inbound.get('protocol') == 'vless':
                return inbound
        return None
    
    def create_client(self, email: str, days: int = 30) -> Tuple[bool, str]:
        inbound = self._get_vless_inbound()
        if not inbound:
            return False, "VLESS протокол не настроен"
        
        expiry = datetime.now() + timedelta(days=days)
        expiry_timestamp = int(expiry.timestamp() * 1000)
        
        client_data = {
            "id": inbound['id'],
            "settings": json.dumps({
                "clients": [{
                    "email": email,
                    "limitIp": self.config.vless_limit_ip,
                    "enable": True,
                    "totalGB": 0,
                    "expiryTime": expiry_timestamp,
                    "flow": self.config.vless_flow
                }]
            })
        }
        
        try:
            resp = self.session.post(
                f"{self.base_url}/panel/api/inbounds/addClient",
                json=client_data,
                timeout=10
            )
            result = resp.json()
            
            if result.get('success'):
                link = self._generate_link(email, inbound)
                logger.info(f"✅ Клиент {email} создан до {expiry}")
                return True, link
            else:
                error = result.get('msg', 'Неизвестная ошибка')
                logger.error(f"❌ Ошибка создания: {error}")
                return False, error
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False, str(e)
    
    def delete_client(self, email: str) -> bool:
        inbound = self._get_vless_inbound()
        if not inbound:
            return False
        
        try:
            resp = self.session.post(
                f"{self.base_url}/panel/api/inbounds/{inbound['id']}/delClient/{email}",
                timeout=5
            )
            return resp.json().get('success', False)
        except Exception as e:
            logger.error(f"❌ Ошибка удаления: {e}")
            return False
    
    def _generate_link(self, email: str, inbound: Dict) -> str:
        try:
            settings = json.loads(inbound.get('settings', '{}'))
            stream = json.loads(inbound.get('streamSettings', '{}'))
            reality = stream.get('realitySettings', {})
            public_key = reality.get('settings', {}).get('publicKey', '')
            
            if not public_key:
                clients = settings.get('clients', [])
                if clients and 'publicKey' in clients[0]:
                    public_key = clients[0]['publicKey']
            
            return (
                f"vless://{email}@{self.config.host}:{self.config.vless_port}"
                f"?type=tcp&security=reality&pbk={public_key}"
                f"&fp={self.config.vless_fp}&sni={self.config.vless_sni}"
                f"&flow={self.config.vless_flow}&sid=ffffffffff"
                f"#{email}"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ссылки: {e}")
            return f"vless://{email}@{self.config.host}:{self.config.vless_port}?security=reality#{email}"