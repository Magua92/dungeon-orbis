# -*- coding: utf-8 -*-
"""Persistenza SQLite per il minigioco dungeon. Volutamente separato da chronicle.py:
questa app non legge/scrive mai factions.json."""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dungeon.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS characters (
            faction TEXT NOT NULL,
            name TEXT NOT NULL,
            class TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (faction, name)
        );
        CREATE TABLE IF NOT EXISTS equipment_owned (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faction TEXT NOT NULL,
            name TEXT NOT NULL,
            item_id TEXT NOT NULL,
            acquired_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS run_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faction TEXT NOT NULL,
            name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            result TEXT NOT NULL,
            rooms_cleared INTEGER NOT NULL,
            loot_json TEXT NOT NULL,
            xp_gained INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS run_lock (
            faction TEXT NOT NULL,
            name TEXT NOT NULL,
            PRIMARY KEY (faction, name)
        );
    """)
    conn.commit()
    conn.close()


def get_character(faction, name):
    conn = get_conn()
    row = conn.execute("SELECT * FROM characters WHERE faction=? AND name=?", (faction, name)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_characters():
    conn = get_conn()
    rows = conn.execute("SELECT faction, name, class FROM characters ORDER BY faction, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_character(faction, name, char_class):
    conn = get_conn()
    conn.execute("INSERT INTO characters (faction, name, class, xp) VALUES (?,?,?,0)", (faction, name, char_class))
    conn.commit()
    conn.close()


def add_xp(faction, name, amount):
    conn = get_conn()
    conn.execute("UPDATE characters SET xp = xp + ? WHERE faction=? AND name=?", (amount, faction, name))
    conn.commit()
    conn.close()


def get_owned_equipment(faction, name):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM equipment_owned WHERE faction=? AND name=?", (faction, name)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_equipment(faction, name, item_id, timestamp):
    conn = get_conn()
    conn.execute("INSERT INTO equipment_owned (faction, name, item_id, acquired_at) VALUES (?,?,?,?)",
                 (faction, name, item_id, timestamp))
    conn.commit()
    conn.close()


def is_run_locked(faction, name):
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM run_lock WHERE faction=? AND name=?", (faction, name)).fetchone()
    conn.close()
    return row is not None


def set_run_lock(faction, name):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO run_lock (faction, name) VALUES (?,?)", (faction, name))
    conn.commit()
    conn.close()


def clear_all_locks():
    conn = get_conn()
    conn.execute("DELETE FROM run_lock")
    conn.commit()
    conn.close()


def clear_lock(faction, name):
    conn = get_conn()
    conn.execute("DELETE FROM run_lock WHERE faction=? AND name=?", (faction, name))
    conn.commit()
    conn.close()


def save_run_history(faction, name, timestamp, result, rooms_cleared, loot, xp_gained):
    conn = get_conn()
    conn.execute(
        "INSERT INTO run_history (faction, name, timestamp, result, rooms_cleared, loot_json, xp_gained) VALUES (?,?,?,?,?,?,?)",
        (faction, name, timestamp, result, rooms_cleared, json.dumps(loot, ensure_ascii=False), xp_gained)
    )
    conn.commit()
    conn.close()


def get_all_locks():
    conn = get_conn()
    rows = conn.execute("SELECT faction, name FROM run_lock").fetchall()
    conn.close()
    return [dict(r) for r in rows]
