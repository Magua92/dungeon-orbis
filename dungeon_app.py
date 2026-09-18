# -*- coding: utf-8 -*-
"""App Flask separata da chronicle.py: minigioco di esplorazione (dungeon roguelite)
per i personaggi delle fazioni di Orbis Terrarum. Persistenza propria (SQLite),
nessuna scrittura su factions.json — i risultati vanno applicati a mano dal Master
dopo aver letto il riepilogo (anche mandato su Discord via webhook, se configurato)."""
import os
import datetime
from flask import Flask, request, session, redirect, url_for, render_template

import db
import engine
import game_data as gd

try:
    import requests
except ImportError:
    requests = None

app = Flask(__name__)
app.jinja_env.globals["ROOMS_PER_RUN"] = gd.ROOMS_PER_RUN
app.secret_key = os.environ.get("DUNGEON_SECRET_KEY", "cambia-questa-chiave-in-produzione")

# Config: incolla qui l'URL del webhook Discord dedicato (o lascialo vuoto per disattivare l'invio)
DISCORD_WEBHOOK_URL = os.environ.get("DUNGEON_DISCORD_WEBHOOK", "")

# Password semplice per la pagina di amministrazione (sblocco turno). Cambiala.
ADMIN_PASSWORD = os.environ.get("DUNGEON_ADMIN_PASSWORD", "cambiami")

db.init_db()


def send_discord_summary(text):
    if not DISCORD_WEBHOOK_URL or not requests:
        return
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": text}, timeout=8)
    except Exception:
        pass  # un fallimento nell'invio non deve mai far crollare la run del giocatore


def _run():
    return session.get("run")


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        faction = request.form.get("faction", "").strip()
        name = request.form.get("name", "").strip()
        if not faction or not name:
            return render_template("home.html", error="Inserisci sia la fazione che il nome del personaggio.")
        char = db.get_character(faction, name)
        if not char:
            session["pending_char"] = {"faction": faction, "name": name}
            return redirect(url_for("choose_class"))
        if db.is_run_locked(faction, name):
            return render_template("locked.html", faction=faction, name=name)
        return redirect(url_for("prepare", faction=faction, name=name))
    return render_template("home.html", error=None)


@app.route("/choose_class", methods=["GET", "POST"])
def choose_class():
    pending = session.get("pending_char")
    if not pending:
        return redirect(url_for("home"))
    if request.method == "POST":
        char_class = request.form.get("char_class")
        if char_class not in gd.CLASSES:
            return render_template("choose_class.html", classes=gd.CLASSES, error="Scegli una classe valida.")
        db.create_character(pending["faction"], pending["name"], char_class)
        session.pop("pending_char", None)
        return redirect(url_for("prepare", faction=pending["faction"], name=pending["name"]))
    return render_template("choose_class.html", classes=gd.CLASSES, error=None)


@app.route("/prepare")
def prepare():
    faction = request.args.get("faction")
    name = request.args.get("name")
    char = db.get_character(faction, name)
    if not char:
        return redirect(url_for("home"))
    if db.is_run_locked(faction, name):
        return render_template("locked.html", faction=faction, name=name)
    level = engine.level_from_xp(char["xp"])
    owned = db.get_owned_equipment(faction, name)
    abilities = engine.unlocked_abilities(char["class"], level)
    uses_loadout = engine.uses_loadout(char["class"])
    active_abilities = abilities
    entourage_bonus_map = {a["key"]: a["grants_extra_entourage"] for a in abilities if a.get("grants_extra_entourage")}
    has_strumenti = any(a["key"] == "strumenti_del_mestiere" for a in abilities)
    owned_ids = {o["item_id"] for o in owned}
    return render_template(
        "prepare.html", faction=faction, name=name, char_class=char["class"], level=level,
        xp=char["xp"], entourage_types=gd.ENTOURAGE_TYPES, max_pick=gd.ENTOURAGE_MAX_PICK,
        owned=owned, items=gd.ITEMS, abilities=abilities, error=None,
        uses_loadout=uses_loadout, active_abilities=active_abilities,
        ability_loadout_size=gd.ABILITY_LOADOUT_SIZE, entourage_bonus_map=entourage_bonus_map,
        has_strumenti=has_strumenti, owned_ids=owned_ids,
    )


@app.route("/start_run", methods=["POST"])
def start_run():
    faction = request.form.get("faction")
    name = request.form.get("name")
    char = db.get_character(faction, name)
    if not char or db.is_run_locked(faction, name):
        return redirect(url_for("home"))
    level = engine.level_from_xp(char["xp"])

    equipped_abilities = None
    entourage_bonus = 0
    if engine.uses_loadout(char["class"]):
        unlocked_full = engine.unlocked_abilities(char["class"], level)
        unlocked_keys = {a["key"] for a in unlocked_full}
        unlocked = [a["key"] for a in unlocked_full]
        chosen = [k for k in request.form.getlist("abilities") if k in unlocked_keys]
        equipped_abilities = chosen[: gd.ABILITY_LOADOUT_SIZE - 1] or unlocked[: gd.ABILITY_LOADOUT_SIZE - 1]
        entourage_bonus = sum(a.get("grants_extra_entourage", 0) for a in unlocked_full if a["key"] in equipped_abilities)

    entourage = request.form.getlist("entourage")
    entourage = [e for e in entourage if e in gd.ENTOURAGE_TYPES][: gd.ENTOURAGE_MAX_PICK + entourage_bonus]

    owned_ids = {e["item_id"] for e in db.get_owned_equipment(faction, name)}
    has_strumenti = bool(equipped_abilities) and "strumenti_del_mestiere" in equipped_abilities
    slot_arma = request.form.get("slot_arma") or None
    slot_armatura = request.form.get("slot_armatura") or None
    slot_jolly = request.form.get("slot_jolly") or None
    equip_ids = []
    for item_id, expected_slot in ((slot_arma, "arma"), (slot_armatura, "armatura"), (slot_jolly, None)):
        if not item_id or item_id not in gd.ITEMS:
            continue
        consentito = item_id in owned_ids or (has_strumenti and gd.ITEMS[item_id]["rarity"] == "base")
        if consentito and (expected_slot is None or gd.ITEMS[item_id]["slot"] == expected_slot):
            equip_ids.append(item_id)

    run = engine.new_run_state(faction, name, char["class"], level, entourage, equip_ids, equipped_abilities)
    session["run"] = run
    return redirect(url_for("room"))


@app.route("/room_action", methods=["POST"])
def room_action():
    run = _run()
    if not run or run.get("combat"):
        return redirect(url_for("room"))
    ability_key = request.form.get("ability_key")
    char_class = run["class"]
    ability = next((a for a in gd.CLASSES[char_class]["abilities"]
                     if a["key"] == ability_key and a.get("room_action")), None)
    if not ability or ability_key not in run.get("equipped_abilities", []) or ability_key in run["used_once_abilities"]:
        return redirect(url_for("room"))
    run["used_once_abilities"].append(ability_key)

    if ability_key == "bancarotta":
        run["finished"] = True
        run["result"] = "ritirata_bancarotta"
        session["run"] = run
        return redirect(url_for("run_end"))

    if ability_key == "vie_segrete":
        run["room_index"] += 1
        run["log"] = ["Vie Segrete: eviti del tutto questa stanza, proseguendo per sentieri nascosti."]
        session["run"] = run
        return render_template("room_result.html", run=run, log=run["log"], room_finished=True)

    return redirect(url_for("room"))


@app.route("/room")
def room():
    run = _run()
    if not run:
        return redirect(url_for("home"))
    if run["finished"]:
        return redirect(url_for("run_end"))
    if run["room_index"] >= gd.ROOMS_PER_RUN:
        return redirect(url_for("miniboss"))
    options = run["rooms_plan"][run["room_index"]]

    room_actions = [a for a in gd.CLASSES[run["class"]]["abilities"]
                     if a.get("room_action") and a["key"] in run.get("equipped_abilities", [])
                     and a["key"] not in run["used_once_abilities"]]

    next_room_options = None
    if "mappatore_esperto" in run.get("equipped_abilities", []) and run["room_index"] + 1 < gd.ROOMS_PER_RUN:
        next_room_options = run["rooms_plan"][run["room_index"] + 1]

    return render_template("room.html", run=run, options=options, room_types=gd.ROOM_TYPES,
                            room_number=run["room_index"] + 1, total_rooms=gd.ROOMS_PER_RUN,
                            incudine_options=gd.INCUDINE_OPTIONS,
                            incudine_cost=engine.incudine_cost(run),
                            incudine_amount=engine.incudine_buff_amount(run),
                            sacco_monete_cost=engine.sacco_monete_cost(run),
                            room_actions=room_actions, next_room_options=next_room_options)


@app.route("/choose_room", methods=["POST"])
def choose_room():
    run = _run()
    if not run:
        return redirect(url_for("home"))
    room_type = request.form.get("room_type")
    options = run["rooms_plan"][run["room_index"]]
    if room_type not in options:
        return redirect(url_for("room"))

    if room_type == "battaglia":
        tier = run["room_index"] + 1
        engine.start_combat(run, tier)
        session["run"] = run
        return redirect(url_for("combat"))

    if room_type == "fontana":
        log = engine.resolve_fontana(run)
    elif room_type == "incudine":
        stat_choice = request.form.get("stat_choice", "dmg")
        log = engine.resolve_incudine(run, stat_choice)
    elif room_type == "sacco_monete":
        log = engine.resolve_sacco_monete(run)
    else:
        log = []

    run["log"] = log
    run["room_index"] += 1
    session["run"] = run
    return render_template("room_result.html", run=run, log=log, room_finished=True)


@app.route("/combat")
def combat():
    run = _run()
    if not run or not run.get("combat"):
        return redirect(url_for("room"))
    actions = engine.all_combat_abilities(run)
    is_boss = run["combat"]["tier"] == "boss"
    return render_template("combat.html", run=run, actions=actions, is_boss=is_boss)


@app.route("/combat/act", methods=["POST"])
def combat_act():
    run = _run()
    if not run or not run.get("combat"):
        return redirect(url_for("room"))
    action_key = request.form.get("action_key", "attacco_fisico")
    available_keys = {a["key"] for a in engine.available_combat_actions(run)}
    if action_key not in available_keys:
        return redirect(url_for("combat"))
    is_boss = run["combat"]["tier"] == "boss"
    esito = engine.resolve_combat_round(run, action_key)

    if esito == "in_corso":
        session["run"] = run
        return redirect(url_for("combat"))

    if esito == "vittoria":
        engine.cleanup_temp_mercenaries(run)
        loot_log, item_id = engine.roll_loot(run, is_boss)
        run["log"] = run.get("log", []) + loot_log
        if item_id:
            run.setdefault("pending_drops", []).append(item_id)
        run["combat"] = None
        if is_boss:
            run["finished"] = True
            run["result"] = "vittoria"
            session["run"] = run
            return redirect(url_for("run_end"))
        run["room_index"] += 1
        session["run"] = run
        return render_template("room_result.html", run=run, log=run["log"], room_finished=True)

    if esito == "fuga":
        engine.cleanup_temp_mercenaries(run)
        run["room_index"] += 1
        session["run"] = run
        return render_template("room_result.html", run=run, log=run.get("log", []), room_finished=True)

    if esito == "salta_stanza":
        engine.cleanup_temp_mercenaries(run)
        run["room_index"] += 1
        session["run"] = run
        return render_template("room_result.html", run=run, log=run.get("log", []), room_finished=True)

    if esito in ("sconfitta_morte", "sconfitta_timore"):
        engine.cleanup_temp_mercenaries(run)
        run["finished"] = True
        run["result"] = esito
        session["run"] = run
        return redirect(url_for("run_end"))

    session["run"] = run
    return redirect(url_for("combat"))


@app.route("/miniboss")
def miniboss():
    run = _run()
    if not run:
        return redirect(url_for("home"))
    if not run.get("combat"):
        engine.start_combat(run, "boss")
        session["run"] = run
    actions = engine.all_combat_abilities(run)
    return render_template("combat.html", run=run, actions=actions, is_boss=True, is_miniboss_intro=True)


@app.route("/run_end")
def run_end():
    run = _run()
    if not run or not run.get("finished"):
        return redirect(url_for("home"))

    faction, name = run["faction"], run["name"]
    xp_gained = engine.compute_xp_gain(run)

    loot = {}
    if run["result"] != "sconfitta_morte":
        loot = {k: v for k, v in run["treasure"].items() if v}
    else:
        loot = {}

    db.add_xp(faction, name, xp_gained)
    timestamp = datetime.datetime.utcnow().isoformat()
    drop_names = []
    if run["result"] != "sconfitta_morte":
        for item_id in run.get("pending_drops", []):
            db.add_equipment(faction, name, item_id, timestamp)
            drop_names.append(gd.ITEMS[item_id]["name"])

    db.save_run_history(faction, name, timestamp, run["result"], run["room_index"], loot, xp_gained)
    db.set_run_lock(faction, name)

    result_labels = {
        "vittoria": "🏆 Vittoria completa",
        "sconfitta_timore": "😰 Ritirata per Timore",
        "sconfitta_morte": "💀 Sconfitta",
        "ritirata_bancarotta": "💰 Ritirata (Bancarotta)",
    }
    loot_txt = ", ".join("%d %s" % (v, k) for k, v in loot.items()) if loot else "nessuno"
    drop_txt = (", oggetti trovati: " + ", ".join(drop_names)) if drop_names else ""
    summary = (
        "🗺️ **Spedizione conclusa** — %s (%s)\n"
        "Esito: %s — stanze superate: %d/%d\n"
        "Bottino: %s%s\n"
        "Esperienza guadagnata: %d PE"
    ) % (name, faction, result_labels.get(run["result"], run["result"]), run["room_index"], gd.ROOMS_PER_RUN,
         loot_txt, drop_txt, xp_gained)
    send_discord_summary(summary)

    session.pop("run", None)
    return render_template("run_end.html", run=run, loot=loot, drop_names=drop_names, xp_gained=xp_gained,
                            result_labels=result_labels, summary_text=summary)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    error = None
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw != ADMIN_PASSWORD:
            error = "Password errata."
        else:
            action = request.form.get("action")
            if action == "clear_all":
                db.clear_all_locks()
            elif action == "clear_one":
                db.clear_lock(request.form.get("faction", ""), request.form.get("name", ""))
    locks = db.get_all_locks()
    return render_template("admin.html", locks=locks, error=error)


if __name__ == "__main__":
    app.run(debug=True)
