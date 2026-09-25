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
            portrait TEXT,
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
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS guild_contributions (
            faction TEXT NOT NULL,
            name TEXT NOT NULL,
            resources TEXT NOT NULL,   -- JSON: {"oro": 12, "gloria": 50, ...}
            boss_kills INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (faction, name)
        );
        CREATE TABLE IF NOT EXISTS arena_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faction_a TEXT NOT NULL,
            name_a TEXT NOT NULL,
            faction_b TEXT NOT NULL,
            name_b TEXT NOT NULL,
            status TEXT NOT NULL,          -- 'attesa_b' | 'in_corso' | 'concluso'
            turn TEXT,                     -- riservato per usi futuri, non usato dalla logica attuale
            round INTEGER NOT NULL DEFAULT 1,
            state_a TEXT,                  -- stato di combattimento del lato A, JSON
            state_b TEXT,                  -- stato di combattimento del lato B, JSON (NULL finche' B non si prepara)
            pending_action_a TEXT,         -- mossa scelta da A per il round corrente, in attesa di B
            pending_action_b TEXT,         -- mossa scelta da B per il round corrente, in attesa di A
            viewed_round_a INTEGER NOT NULL DEFAULT 0,  -- ultimo round che A ha effettivamente caricato/visto
            viewed_round_b INTEGER NOT NULL DEFAULT 0,  -- ultimo round che B ha effettivamente caricato/visto
            log TEXT,                      -- righe dell'ultimo round risolto, JSON
            winner TEXT,                   -- 'a' | 'b' | 'pareggio', solo se status='concluso'
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)
    conn.commit()
    # Migrazione: i DB creati prima di questa funzionalita' non hanno ancora la colonna.
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(characters)").fetchall()]
    if "portrait" not in cols:
        conn.execute("ALTER TABLE characters ADD COLUMN portrait TEXT")
        conn.commit()
    arena_cols = [r["name"] for r in conn.execute("PRAGMA table_info(arena_matches)").fetchall()]
    if "pending_action_a" not in arena_cols:
        conn.execute("ALTER TABLE arena_matches ADD COLUMN pending_action_a TEXT")
        conn.execute("ALTER TABLE arena_matches ADD COLUMN pending_action_b TEXT")
        conn.commit()
    if "viewed_round_a" not in arena_cols:
        conn.execute("ALTER TABLE arena_matches ADD COLUMN viewed_round_a INTEGER NOT NULL DEFAULT 0")
        conn.execute("ALTER TABLE arena_matches ADD COLUMN viewed_round_b INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()


def set_portrait(faction, name, filename):
    conn = get_conn()
    conn.execute("UPDATE characters SET portrait=? WHERE faction=? AND name=?", (filename, faction, name))
    conn.commit()
    conn.close()


def get_character(faction, name):
    conn = get_conn()
    row = conn.execute("SELECT * FROM characters WHERE faction=? AND name=?", (faction, name)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_characters():
    conn = get_conn()
    rows = conn.execute("SELECT faction, name, class, xp, portrait FROM characters ORDER BY faction, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_character(faction, name, char_class, xp):
    conn = get_conn()
    conn.execute("UPDATE characters SET class=?, xp=? WHERE faction=? AND name=?", (char_class, xp, faction, name))
    conn.commit()
    conn.close()


def delete_character(faction, name):
    conn = get_conn()
    conn.execute("DELETE FROM characters WHERE faction=? AND name=?", (faction, name))
    conn.execute("DELETE FROM equipment_owned WHERE faction=? AND name=?", (faction, name))
    conn.execute("DELETE FROM run_history WHERE faction=? AND name=?", (faction, name))
    conn.execute("DELETE FROM run_lock WHERE faction=? AND name=?", (faction, name))
    conn.commit()
    conn.close()


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
    if get_setting("unlimited_runs") == "1":
        return False
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


# ─── ARENA (duelli PvP asincroni) ────────────────────────────────────────
def create_arena_match(faction_a, name_a, faction_b, name_b, state_a, timestamp):
    """Crea la sfida con il lato A gia' preparato; il lato B resta NULL finche'
    non si prepara a sua volta (vedi set_arena_state_b)."""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO arena_matches (faction_a, name_a, faction_b, name_b, status, round, state_a, created_at, updated_at) "
        "VALUES (?,?,?,?, 'attesa_b', 1, ?, ?, ?)",
        (faction_a, name_a, faction_b, name_b, json.dumps(state_a, ensure_ascii=False), timestamp, timestamp)
    )
    conn.commit()
    match_id = cur.lastrowid
    conn.close()
    return match_id


def get_ongoing_arena_matches():
    """Duelli non ancora conclusi (in attesa o in corso), per il pannello admin."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM arena_matches WHERE status != 'concluso' ORDER BY created_at DESC").fetchall()
    conn.close()
    matches = []
    for row in rows:
        m = dict(row)
        m["state_a"] = json.loads(m["state_a"]) if m["state_a"] else None
        m["state_b"] = json.loads(m["state_b"]) if m["state_b"] else None
        m["log"] = json.loads(m["log"]) if m["log"] else []
        matches.append(m)
    return matches


def delete_arena_match(match_id):
    conn = get_conn()
    conn.execute("DELETE FROM arena_matches WHERE id=?", (match_id,))
    conn.commit()
    conn.close()


def get_arena_match(match_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM arena_matches WHERE id=?", (match_id,)).fetchone()
    conn.close()
    if not row:
        return None
    match = dict(row)
    match["state_a"] = json.loads(match["state_a"]) if match["state_a"] else None
    match["state_b"] = json.loads(match["state_b"]) if match["state_b"] else None
    match["log"] = json.loads(match["log"]) if match["log"] else []
    return match


def get_arena_matches_for(faction, name):
    """Tutte le sfide (in attesa, in corso o appena concluse) dove questo personaggio
    e' coinvolto, come sfidante o sfidato — piu' recenti prima."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM arena_matches WHERE (faction_a=? AND name_a=?) OR (faction_b=? AND name_b=?) "
        "ORDER BY updated_at DESC",
        (faction, name, faction, name)
    ).fetchall()
    conn.close()
    matches = []
    for row in rows:
        match = dict(row)
        match["state_a"] = json.loads(match["state_a"]) if match["state_a"] else None
        match["state_b"] = json.loads(match["state_b"]) if match["state_b"] else None
        match["log"] = json.loads(match["log"]) if match["log"] else []
        matches.append(match)
    return matches


def set_arena_state_b(match_id, state_b, start_log, first_turn, timestamp):
    """Il lato B si e' preparato: il duello passa a 'in_corso', con il log degli
    effetti "una tantum" di inizio duello (es. scudo del Novizio) e il turno
    impostato su chi muove per primo (deciso da start_arena_match, Arciere incluso)."""
    conn = get_conn()
    conn.execute(
        "UPDATE arena_matches SET state_b=?, status='in_corso', log=?, turn=?, updated_at=? WHERE id=?",
        (json.dumps(state_b, ensure_ascii=False), json.dumps(start_log, ensure_ascii=False), first_turn, timestamp, match_id)
    )
    conn.commit()
    conn.close()


def update_arena_match(match_id, timestamp, **fields):
    """Aggiorna uno o piu' campi (state_a, state_b, turn, round, log, status, winner).
    state_a/state_b/log vengono serializzati automaticamente se presenti."""
    for key in ("state_a", "state_b", "log"):
        if key in fields and fields[key] is not None:
            fields[key] = json.dumps(fields[key], ensure_ascii=False)
    fields["updated_at"] = timestamp
    columns = ", ".join("%s=?" % k for k in fields)
    conn = get_conn()
    conn.execute("UPDATE arena_matches SET %s WHERE id=?" % columns, (*fields.values(), match_id))
    conn.commit()
    conn.close()


# ─── GILDA DEGLI AVVENTURIERI (cassa comune, alimentata da donazioni volontarie) ──
# Nessuna iscrizione tracciata qui: chi fa parte della Gilda lo dichiara su Discord,
# tra i giocatori. Il gioco si limita a contare le donazioni quando arrivano, per
# personaggio, cosi' si puo' ricostruire sia il totale di fazione sia chi ha dato cosa.
def add_guild_contribution(faction, name, loot, boss_beaten, timestamp):
    conn = get_conn()
    row = conn.execute("SELECT resources, boss_kills FROM guild_contributions WHERE faction=? AND name=?",
                        (faction, name)).fetchone()
    resources = json.loads(row["resources"]) if row else {}
    boss_kills = row["boss_kills"] if row else 0
    for k, v in loot.items():
        resources[k] = resources.get(k, 0) + v
    if boss_beaten:
        boss_kills += 1
    conn.execute(
        "INSERT INTO guild_contributions (faction, name, resources, boss_kills, updated_at) VALUES (?,?,?,?,?) "
        "ON CONFLICT(faction, name) DO UPDATE SET resources=excluded.resources, boss_kills=excluded.boss_kills, updated_at=excluded.updated_at",
        (faction, name, json.dumps(resources, ensure_ascii=False), boss_kills, timestamp)
    )
    conn.commit()
    conn.close()


def reset_guild_treasury():
    conn = get_conn()
    conn.execute("DELETE FROM guild_contributions")
    conn.commit()
    conn.close()


def get_guild_leaderboard():
    """Una voce per fazione, ordinate per totale punti (risorse + gloria) discendente,
    ciascuna con l'elenco dei personaggi che hanno contribuito, ordinato allo stesso modo."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM guild_contributions").fetchall()
    conn.close()
    by_faction = {}
    for r in rows:
        resources = json.loads(r["resources"])
        entry = by_faction.setdefault(r["faction"], {"faction": r["faction"], "resources": {}, "boss_kills": 0, "members": []})
        for k, v in resources.items():
            entry["resources"][k] = entry["resources"].get(k, 0) + v
        entry["boss_kills"] += r["boss_kills"]
        entry["members"].append({"name": r["name"], "resources": resources, "boss_kills": r["boss_kills"],
                                  "total": sum(resources.values())})
    for entry in by_faction.values():
        entry["members"].sort(key=lambda m: m["total"], reverse=True)
        entry["gloria"] = entry["resources"].get("gloria", 0)
        entry["other_resources"] = {k: v for k, v in entry["resources"].items() if k != "gloria"}
        entry["total"] = sum(entry["resources"].values())
    return sorted(by_faction.values(), key=lambda e: e["total"], reverse=True)
