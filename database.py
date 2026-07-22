#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import hashlib
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class User:
    id: int
    telegram_id: int
    username: str
    first_name: str
    last_name: str
    is_admin: bool
    is_banned: bool
    balance: float
    ref_code: str
    created_at: datetime


@dataclass
class Server:
    id: int
    ip: str
    port: int
    username: str
    password: str
    location: str
    is_active: bool
    is_default: bool
    max_users: int
    created_at: datetime


@dataclass
class VPNKey:
    id: int
    user_id: int
    email: str
    vless_link: str
    location: str
    server_id: int
    days: int
    is_active: bool
    expires_at: datetime
    created_at: datetime


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _cursor(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn.cursor()
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_db(self):
        with self._cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_admin BOOLEAN DEFAULT 0,
                    is_banned BOOLEAN DEFAULT 0,
                    balance REAL DEFAULT 0,
                    ref_code TEXT UNIQUE,
                    referrer_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    port INTEGER DEFAULT 54321,
                    username TEXT DEFAULT 'root',
                    password TEXT NOT NULL,
                    location TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    is_default BOOLEAN DEFAULT 0,
                    max_users INTEGER DEFAULT 500,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ip, location)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vpn_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    vless_link TEXT NOT NULL,
                    location TEXT,
                    server_id INTEGER,
                    days INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    traffic_used REAL DEFAULT 0,
                    traffic_limit REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (server_id) REFERENCES servers(id)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    days INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    payment_id TEXT UNIQUE,
                    provider TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)


class UserRepository:
    def __init__(self, db: Database):
        self.db = db
    
    def create(self, telegram_id: int, username: str = '', first_name: str = '', last_name: str = '') -> User:
        with self.db._cursor() as cur:
            cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?", (telegram_id,))
                return User(**dict(row))
            
            ref_code = hashlib.md5(f"{telegram_id}{secrets.token_hex(4)}".encode()).hexdigest()[:8]
            cur.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name, ref_code)
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, username[:50], first_name[:50], last_name[:50], ref_code))
            
            cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            return User(**dict(cur.fetchone()))
    
    def get(self, telegram_id: int) -> Optional[User]:
        with self.db._cursor() as cur:
            cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cur.fetchone()
            return User(**dict(row)) if row else None


class ServerRepository:
    def __init__(self, db: Database):
        self.db = db
    
    def create(self, ip: str, password: str, location: str, port: int = 54321, username: str = 'root') -> Optional[Server]:
        with self.db._cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO servers (ip, port, username, password, location, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (ip, port, username, password, location))
                cur.execute("SELECT * FROM servers WHERE ip = ? AND location = ?", (ip, location))
                row = cur.fetchone()
                return Server(**dict(row)) if row else None
            except sqlite3.IntegrityError:
                return None
    
    def get_all(self, active_only: bool = True) -> List[Server]:
        with self.db._cursor() as cur:
            query = "SELECT * FROM servers"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY is_default DESC, location"
            cur.execute(query)
            return [Server(**dict(row)) for row in cur.fetchall()]
    
    def get_by_id(self, server_id: int) -> Optional[Server]:
        with self.db._cursor() as cur:
            cur.execute("SELECT * FROM servers WHERE id = ? AND is_active = 1", (server_id,))
            row = cur.fetchone()
            return Server(**dict(row)) if row else None
    
    def get_by_location(self, location: str) -> Optional[Server]:
        with self.db._cursor() as cur:
            cur.execute("SELECT * FROM servers WHERE location = ? AND is_active = 1", (location,))
            row = cur.fetchone()
            return Server(**dict(row)) if row else None
    
    def get_default(self) -> Optional[Server]:
        with self.db._cursor() as cur:
            cur.execute("SELECT * FROM servers WHERE is_default = 1 AND is_active = 1")
            row = cur.fetchone()
            return Server(**dict(row)) if row else None
    
    def set_default(self, server_id: int) -> bool:
        with self.db._cursor() as cur:
            cur.execute("UPDATE servers SET is_default = 0")
            cur.execute("UPDATE servers SET is_default = 1 WHERE id = ?", (server_id,))
            return cur.rowcount > 0
    
    def delete(self, server_id: int) -> bool:
        with self.db._cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM vpn_keys WHERE server_id = ? AND is_active = 1", (server_id,))
            if cur.fetchone()[0] > 0:
                return False
            cur.execute("UPDATE servers SET is_active = 0 WHERE id = ?", (server_id,))
            return cur.rowcount > 0
    
    def get_locations(self) -> List[str]:
        return [s.location for s in self.get_all()]


class VPNKeyRepository:
    def __init__(self, db: Database):
        self.db = db
    
    def create(self, user_id: int, email: str, vless_link: str, days: int, location: str = None) -> Optional[VPNKey]:
        expires_at = datetime.now() + timedelta(days=days)
        with self.db._cursor() as cur:
            server_id = None
            if location:
                cur.execute("SELECT id FROM servers WHERE location = ? AND is_active = 1", (location,))
                row = cur.fetchone()
                if row:
                    server_id = row['id']
            
            cur.execute("""
                INSERT INTO vpn_keys (user_id, email, vless_link, location, server_id, days, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, email, vless_link, location, server_id, days, expires_at))
            
            cur.execute("SELECT * FROM vpn_keys WHERE email = ?", (email,))
            row = cur.fetchone()
            return VPNKey(**dict(row)) if row else None
    
    def get_by_user(self, user_id: int, active_only: bool = True) -> List[VPNKey]:
        with self.db._cursor() as cur:
            query = "SELECT * FROM vpn_keys WHERE user_id = ?"
            params = [user_id]
            if active_only:
                query += " AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP"
            query += " ORDER BY created_at DESC"
            cur.execute(query, params)
            return [VPNKey(**dict(row)) for row in cur.fetchall()]
    
    def get_by_email(self, email: str) -> Optional[VPNKey]:
        with self.db._cursor() as cur:
            cur.execute("SELECT * FROM vpn_keys WHERE email = ?", (email,))
            row = cur.fetchone()
            return VPNKey(**dict(row)) if row else None
    
    def deactivate(self, email: str) -> bool:
        with self.db._cursor() as cur:
            cur.execute("UPDATE vpn_keys SET is_active = 0 WHERE email = ?", (email,))
            return cur.rowcount > 0