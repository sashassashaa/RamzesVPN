#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paramiko
import time
import logging
from typing import Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SSHConfig:
    host: str
    port: int = 22
    username: str = 'root'
    password: str = ''
    timeout: int = 30


class XUIInstaller:
    def __init__(self, config: SSHConfig):
        self.config = config
        self.ssh = None
    
    def connect(self) -> bool:
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                timeout=self.config.timeout
            )
            logger.info(f"✅ SSH подключение к {self.config.host}")
            return True
        except Exception as e:
            logger.error(f"❌ SSH ошибка: {e}")
            return False
    
    def execute(self, command: str, timeout: int = 120) -> Tuple[str, str]:
        try:
            stdin, stdout, stderr = self.ssh.exec_command(command, timeout=timeout)
            out = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8')
            return out, err
        except Exception as e:
            return '', str(e)
    
    def install(self, xui_port: int = 54321) -> Tuple[bool, str]:
        if not self.connect():
            return False, "Ошибка подключения к серверу"
        
        commands = [
            ("Обновление системы", "apt-get update -y && apt-get upgrade -y"),
            ("Установка зависимостей", "apt-get install -y curl wget ufw socat"),
            ("Установка 3x-ui", "bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)"),
            (f"Настройка порта {xui_port}", f"/usr/local/x-ui/x-ui setting -port {xui_port}"),
            (f"Настройка пароля", f"/usr/local/x-ui/x-ui setting -username {self.config.username} -password {self.config.password}"),
            ("Открытие портов", f"ufw allow {xui_port}/tcp && ufw allow 443/tcp && ufw --force enable"),
            ("Автозапуск", "systemctl enable x-ui && systemctl restart x-ui"),
        ]
        
        for name, cmd in commands:
            logger.info(f"🔄 {name}...")
            out, err = self.execute(cmd)
            if err and 'error' in err.lower():
                logger.warning(f"⚠️ Ошибка в {name}: {err}")
        
        time.sleep(10)
        
        if self._check_panel_available(xui_port):
            return True, "3x-ui успешно установлен"
        else:
            return False, "Панель не отвечает после установки"
    
    def _check_panel_available(self, port: int) -> bool:
        try:
            import requests
            url = f"http://{self.config.host}:{port}/login"
            resp = requests.get(url, timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def close(self):
        if self.ssh:
            self.ssh.close()