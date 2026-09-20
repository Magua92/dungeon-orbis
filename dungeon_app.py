# -*- coding: utf-8 -*-
"""App Flask separata da chronicle.py: minigioco di esplorazione (dungeon roguelite)
per i personaggi delle fazioni di Orbis Terrarum. Persistenza propria (SQLite),
nessuna scrittura su factions.json — i risultati vanno applicati a mano dal Master
dopo aver letto il riepilogo (anche mandato su Discord via webhook, se configurato)."""
import os
import datetime
import random
from werkzeug.utils import secure_filename
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
app.jinja_env.globals["CLASS_PASSIVES"] = gd.CLASS_PASSIVES
app.jinja_env.globals["ENTOURAGE_TYPES"] = gd.ENTOURAGE_TYPES
app.jinja_env.globals["format_item_effects"] = gd.format_item_effects
app.jinja_env.filters["logclass"] = lambda line: log_line_class(line)
app.secret_key = os.environ.get("DUNGEON_SECRET_KEY", "cambia-questa-chiave-in-produzione")
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024  # 3 MB, guardia contro upload enormi

# Ritratti dei personaggi (caricati dai giocatori): salvati qui, un file per personaggio.
PORTRAIT_DIR = os.path.join(app.static_folder, "portraits")
os.makedirs(PORTRAIT_DIR, exist_ok=True)
ALLOWED_PORTRAIT_EXT = {"png", "jpg", "jpeg", "webp"}

# Ritratti dei mostri (preparati a mano da Amedeo): static/monsters/<slug_nome>.png|jpg|webp
MONSTER_PORTRAIT_DIR = os.path.join(app.static_folder, "monsters")


def _portrait_filename(faction, name, ext):
    slug = secure_filename(("%s_%s" % (faction, name)).lower().replace(" ", "_"))
    return "%s.%s" % (slug, ext)


def _portrait_url(faction, name, filename):
    """URL del ritratto di un personaggio, con parametro anti-cache basato sulla data
    di modifica del file, oppure None se non ne ha ancora caricato uno."""
    if not filename:
        return None
    path = os.path.join(PORTRAIT_DIR, filename)
    if not os.path.exists(path):
        return None
    return url_for("static", filename="portraits/" + filename) + "?v=%d" % int(os.path.getmtime(path))


def _monster_portrait_url(enemy_name):
    """Cerca static/monsters/<slug>.{png,jpg,jpeg,webp}; se non lo trova, il template
    ricade sull'emoji del pool come faceva finora."""
    slug = gd.slugify(enemy_name)
    for ext in ALLOWED_PORTRAIT_EXT:
        rel = "monsters/%s.%s" % (slug, ext)
        if os.path.exists(os.path.join(app.static_folder, rel)):
            return url_for("static", filename=rel)
    return None

# Config: incolla qui l'URL del webhook Discord dedicato (o lascialo vuoto per disattivare l'invio)
DISCORD_WEBHOOK_URL = os.environ.get("DUNGEON_DISCORD_WEBHOOK", "")
# Webhook separato per il canale Arena, cosi' le sfide PvP non si mischiano ai
# riepiloghi delle spedizioni normali.
ARENA_DISCORD_WEBHOOK_URL = os.environ.get("DUNGEON_ARENA_DISCORD_WEBHOOK", "")
# Webhook per il canale della Gilda degli Avventurieri (donazioni di fine spedizione).
GUILD_DISCORD_WEBHOOK_URL = os.environ.get("DUNGEON_GUILD_DISCORD_WEBHOOK", "")

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


def send_arena_discord(text):
    if not ARENA_DISCORD_WEBHOOK_URL or not requests:
        return
    try:
        requests.post(ARENA_DISCORD_WEBHOOK_URL, json={"content": text}, timeout=8)
    except Exception:
        pass


def send_guild_discord(text):
    if not GUILD_DISCORD_WEBHOOK_URL or not requests:
        return
    try:
        requests.post(GUILD_DISCORD_WEBHOOK_URL, json={"content": text}, timeout=8)
    except Exception:
        pass


def send_discord_embed(embed):
    if not DISCORD_WEBHOOK_URL or not requests:
        return
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=8)
    except Exception:
        pass  # un fallimento nell'invio non deve mai far crollare la run del giocatore


def build_expedition_report(run, xp_gained, loot, drop_names):
    """Costruisce sia l'embed Discord sia il testo mostrato nella pagina di fine
    spedizione, cosi' i due non possono disallinearsi: stessa storia, due formati."""
    faction, name, char_class, result = run["faction"], run["name"], run["class"], run["result"]
    special_boss = run.get("special_boss_fought")
    variants = gd.SPECIAL_BOSS_NARRATIVE.get(special_boss, {}).get(result) if special_boss else None
    if not variants:
        variants = gd.DISCORD_NARRATIVE.get(result, {}).get(char_class)
    if not variants:
        variants = [("Spedizione conclusa per {name}", "{name} torna a {faction}.")]
    title_tmpl, desc_tmpl = random.choice(variants)
    title = title_tmpl.format(name=name, faction=faction)
    description = desc_tmpl.format(name=name, faction=faction)

    fields = [
        {"name": "Stanze superate", "value": "%d/%d" % (run["room_index"], gd.ROOMS_PER_RUN), "inline": True},
        {"name": "Esperienza", "value": "%d PE" % xp_gained, "inline": True},
    ]
    if loot:
        fields.append({"name": "Bottino (donato alla Gilda)", "value": ", ".join("%d %s" % (v, k) for k, v in loot.items()), "inline": False})
    if drop_names:
        fields.append({"name": "Oggetti trovati", "value": ", ".join(drop_names), "inline": False})

    embed = {
        "title": title,
        "description": description,
        "color": gd.DISCORD_EMBED_COLORS.get(result, 0x808080),
        "fields": fields,
    }
    char = db.get_character(faction, name)
    if char and char.get("portrait"):
        portrait_path = os.path.join(PORTRAIT_DIR, char["portrait"])
        if os.path.exists(portrait_path):
            embed["thumbnail"] = {"url": url_for("static", filename="portraits/" + char["portrait"], _external=True)
                                   + "?v=%d" % int(os.path.getmtime(portrait_path))}

    summary_text = "%s\n\n%s\n\n" % (title, description)
    summary_text += "\n".join("%s: %s" % (f["name"], f["value"]) for f in fields)
    return embed, summary_text


def _run():
    return session.get("run")


@app.route("/", methods=["GET", "POST"])
def home():
    characters = db.get_all_characters()
    factions = sorted({c["faction"] for c in characters})
    char_by_faction = {}
    for c in characters:
        char_by_faction.setdefault(c["faction"], []).append(c["name"])
    for names in char_by_faction.values():
        names.sort()

    if request.method == "POST":
        faction = request.form.get("faction", "").strip()
        name = request.form.get("name", "").strip()
        if not faction or not name:
            return render_template("home.html", error="Inserisci sia la fazione che il nome del personaggio.", factions=factions, char_by_faction=char_by_faction)
        char = db.get_character(faction, name)
        if not char:
            session["pending_char"] = {"faction": faction, "name": name}
            return redirect(url_for("choose_class"))
        if db.is_run_locked(faction, name):
            return render_template("locked.html", faction=faction, name=name)
        return redirect(url_for("prepare", faction=faction, name=name))
    return render_template("home.html", error=None, factions=factions, char_by_faction=char_by_faction)


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


def log_line_class(line):
    """CSS class per colorare una riga del log fuori dal combattimento live (dove
    la colorazione e' gestita in JS): rosso per il sanguinamento, verde per il veleno,
    blu per la cura. Nessuna delle tre gioca un suono qui ne' nel combattimento live."""
    if line.startswith("Il sanguinamento ") or "ti ferisce in profondità: sanguini" in line or "la ferita sanguina" in line:
        return "log-bleed"
    if line.startswith("Il veleno ") or "inietta un veleno" in line:
        return "log-poison"
    if "recuperi" in line or "ti infonde" in line or "si riprende" in line:
        return "log-heal"
    return ""


def sound_cues_from_log(log_lines, outcome=None):
    """Deduce quali effetti sonori generici far scattare in pagina, leggendo il testo
    del log dell'ultimo round/evento invece di dover tracciare un segnale dedicato in
    engine.py. Euristico ma sufficiente per un primo set di suoni per categoria."""
    text = " ".join(log_lines)
    cues = []
    if outcome == "vittoria":
        cues.append("victory")
    elif outcome in ("sconfitta_morte", "sconfitta_timore"):
        cues.append("defeat")
    if any(s in text for s in ("infliggi", "colpiscono per", "colpisce per", "danni al nemico", "danni fisici e", "danni al Timore del nemico", "critico")):
        cues.append("hit_dealt")
    # "sanguinamento"/"ti ferisce in profondità"/"perdi " non compaiono qui: sono
    # sanguinamento/veleno (niente suono, solo colore, vedi log_line_class) oppure gia'
    # coperti da "attacca la tua psiche" per i colpi reali al Timore.
    if any(s in text for s in ("Subisci", "attacca la tua psiche", "ti indebolisce")):
        cues.append("hit_taken")
    if any(s in text for s in ("recuperi", "ti infonde", "si riprende")):
        cues.append("heal")
    if any(s in text for s in ("scudo", "Scudo", "assorbe", "attutisce")):
        cues.append("shield")
    return cues


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
        portrait_url=_portrait_url(faction, name, char.get("portrait")),
    )


@app.route("/upload_portrait", methods=["POST"])
def upload_portrait():
    faction = request.form.get("faction")
    name = request.form.get("name")
    char = db.get_character(faction, name)
    if not char:
        return redirect(url_for("home"))
    file = request.files.get("portrait")
    if file and file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext in ALLOWED_PORTRAIT_EXT:
            # rimuove un eventuale ritratto precedente con estensione diversa, cosi' non
            # restano file orfani se il giocatore cambia formato tra un caricamento e l'altro
            for old_ext in ALLOWED_PORTRAIT_EXT:
                old_path = os.path.join(PORTRAIT_DIR, _portrait_filename(faction, name, old_ext))
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = _portrait_filename(faction, name, ext)
            file.save(os.path.join(PORTRAIT_DIR, filename))
            db.set_portrait(faction, name, filename)
    return redirect(url_for("prepare", faction=faction, name=name))


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
    run["portrait_url"] = _portrait_url(faction, name, char.get("portrait"))
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
        run["room_index"] = gd.ROOMS_PER_RUN
        run["log"] = ["Vie Segrete: abbandoni il percorso consueto per sentieri nascosti, e ti ritrovi già davanti alla tana del miniboss."]
        session["run"] = run
        return render_template("room_result.html", run=run, log=run["log"], room_finished=True,
                                sound_cues=sound_cues_from_log(run["log"]))


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
    engine.reset_shop_if_new_room(run)
    shop_log = run.get("shop_log")
    if shop_log:
        run["shop_log"] = None
        session["run"] = run

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
                            shop_used=run["shop_used"], shop_log=shop_log,
                            room_actions=room_actions, next_room_options=next_room_options)


@app.route("/shop_action", methods=["POST"])
def shop_action():
    run = _run()
    if not run or run.get("combat"):
        return redirect(url_for("room"))
    engine.reset_shop_if_new_room(run)
    action = request.form.get("action")
    if action == "incudine" and not run["shop_used"]["incudine"]:
        stat_choice = request.form.get("stat_choice", "dmg")
        run["shop_log"] = engine.resolve_incudine(run, stat_choice)
        run["shop_used"]["incudine"] = True
    elif action == "sacco_monete" and not run["shop_used"]["sacco_monete"]:
        run["shop_log"] = engine.resolve_sacco_monete(run)
        run["shop_used"]["sacco_monete"] = True
    session["run"] = run
    return redirect(url_for("room"))


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

    if room_type == "stanza_misteriosa":
        event_key = random.choice(list(gd.MYSTERY_EVENTS.keys()))
        run["mystery_event"] = event_key
        session["run"] = run
        return redirect(url_for("mystery_room"))

    if room_type == "fontana":
        log = engine.resolve_fontana(run)
    else:
        log = []

    run["log"] = log
    run["room_index"] += 1
    session["run"] = run
    return render_template("room_result.html", run=run, log=log, room_finished=True,
                            sound_cues=sound_cues_from_log(log))


@app.route("/mystery_room")
def mystery_room():
    run = _run()
    if not run or not run.get("mystery_event"):
        return redirect(url_for("room"))
    event = gd.MYSTERY_EVENTS[run["mystery_event"]]
    return render_template("mystery_room.html", run=run, event=event)


@app.route("/mystery_choice", methods=["POST"])
def mystery_choice():
    run = _run()
    if not run or not run.get("mystery_event"):
        return redirect(url_for("room"))
    event_key = run["mystery_event"]
    valid_choices = {c[0] for c in gd.MYSTERY_EVENTS[event_key]["options"]}
    choice_key = request.form.get("choice_key")
    if choice_key not in valid_choices:
        return redirect(url_for("mystery_room"))
    log = engine.resolve_mystery_event(run, event_key, choice_key)
    run["mystery_event"] = None
    run["log"] = log
    run["room_index"] += 1
    session["run"] = run
    return render_template("room_result.html", run=run, log=log, room_finished=True,
                            sound_cues=sound_cues_from_log(log))


@app.route("/combat")
def combat():
    run = _run()
    if not run or not run.get("combat"):
        return redirect(url_for("room"))
    actions = engine.all_combat_abilities(run)
    is_boss = run["combat"]["tier"] == "boss"
    return render_template("combat.html", run=run, actions=actions, is_boss=is_boss,
                            enemy_portrait_url=_monster_portrait_url(run["combat"]["name"]))


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
        return render_template("room_result.html", run=run, log=run["log"], room_finished=True,
                                sound_cues=sound_cues_from_log(run["log"]))

    if esito == "fuga":
        engine.cleanup_temp_mercenaries(run)
        run["room_index"] += 1
        session["run"] = run
        return render_template("room_result.html", run=run, log=run.get("log", []), room_finished=True,
                                sound_cues=sound_cues_from_log(run.get("log", [])))

    if esito == "salta_stanza":
        engine.cleanup_temp_mercenaries(run)
        run["room_index"] += 1
        session["run"] = run
        return render_template("room_result.html", run=run, log=run.get("log", []), room_finished=True,
                                sound_cues=sound_cues_from_log(run.get("log", [])))

    if esito in ("sconfitta_morte", "sconfitta_timore"):
        engine.cleanup_temp_mercenaries(run)
        run["finished"] = True
        run["result"] = esito
        session["run"] = run
        # Non si salta subito al riepilogo: si rimostra la schermata di combattimento
        # un'ultima volta (con l'animazione del round fatale), poi il JS reindirizza
        # da solo a fine sequenza, cosi' il giocatore fa in tempo a leggere cos'e' successo.
        return render_template("combat.html", run=run, actions=[], is_boss=is_boss,
                                enemy_portrait_url=_monster_portrait_url(run["combat"]["name"]),
                                defeat_pending=True)

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
    return render_template("combat.html", run=run, actions=actions, is_boss=True, is_miniboss_intro=True,
                            enemy_portrait_url=_monster_portrait_url(run["combat"]["name"]))


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

    gloria = 0
    if run["result"] == "vittoria":
        gloria = gd.GUILD_GLORIA_VALUES.get(run.get("special_boss_fought"), gd.GUILD_GLORIA_VALUES[None])

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
        "sconfitta_morte": "💥 Spedizione Fallita",
        "ritirata_bancarotta": "💰 Ritirata (Bancarotta)",
    }
    embed, summary = build_expedition_report(run, xp_gained, loot, drop_names)
    send_discord_embed(embed)

    session.pop("run", None)
    return render_template("run_end.html", run=run, loot=loot, drop_names=drop_names, xp_gained=xp_gained,
                            result_labels=result_labels, summary_text=summary, gloria=gloria,
                            sound_cues=sound_cues_from_log(run.get("log", []), outcome=run["result"]))


@app.route("/donate_to_guild", methods=["POST"])
def donate_to_guild():
    """Unico modo per uscire dalla schermata di fine spedizione: il bottino di
    questa run (se presente) va alla cassa comune della Gilda, non alla fazione.
    Nessuna iscrizione da verificare qui: la Gilda vive su Discord, il gioco si
    limita a contare quello che arriva."""
    faction = request.form.get("faction")
    name = request.form.get("name")
    boss_beaten = request.form.get("boss_beaten") == "1"
    loot = {}
    for r in gd.RESOURCE_TYPES:
        try:
            v = int(request.form.get("loot_%s" % r, "0"))
        except ValueError:
            v = 0
        if v > 0:
            loot[r] = v
    try:
        gloria = int(request.form.get("gloria", "0"))
    except ValueError:
        gloria = 0
    if gloria > 0:
        loot["gloria"] = gloria
    timestamp = datetime.datetime.utcnow().isoformat()
    db.add_guild_contribution(faction, name, loot, boss_beaten, timestamp)

    parts = ", ".join("%d %s" % (v, k) for k, v in loot.items())
    leaderboard = db.get_guild_leaderboard()
    grand_total = sum(f["total"] for f in leaderboard)
    try:
        goal = int(db.get_setting("guild_goal", "300"))
    except (TypeError, ValueError):
        goal = 300

    lines = ["🏛️ **%s** (%s) dona alla Gilda: %s%s" % (
        name, faction, parts or "nessuna risorsa questa volta",
        " — 👑 boss battuto!" if boss_beaten else ""
    ), "", "**Traguardo: %d / %d**" % (grand_total, goal)]
    for f in leaderboard:
        lines.append("**%s** — %d" % (f["faction"], f["total"]))
        for m in f["members"]:
            lines.append("　• %s: %d" % (m["name"], m["total"]))
    send_guild_discord("\n".join(lines))
    send_guild_discord("\n".join(lines))
    return redirect(url_for("home"))


@app.route("/guild")
def guild_leaderboard():
    leaderboard = db.get_guild_leaderboard()
    try:
        goal = int(db.get_setting("guild_goal", "300"))
    except (TypeError, ValueError):
        goal = 300
    grand_total = sum(f["total"] for f in leaderboard)
    return render_template("guild.html", leaderboard=leaderboard, goal=goal, grand_total=grand_total)


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
            elif action == "edit_character":
                faction = request.form.get("faction", "")
                name = request.form.get("name", "")
                new_class = request.form.get("new_class", "")
                if db.get_character(faction, name) and new_class in gd.CLASSES:
                    try:
                        new_xp = max(0, int(request.form.get("new_xp", "0")))
                    except ValueError:
                        new_xp = 0
                    db.update_character(faction, name, new_class, new_xp)
            elif action == "delete_character":
                faction = request.form.get("faction", "")
                name = request.form.get("name", "")
                char = db.get_character(faction, name)
                if char:
                    if char.get("portrait"):
                        old_path = os.path.join(PORTRAIT_DIR, char["portrait"])
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    db.delete_character(faction, name)
            elif action == "toggle_unlimited":
                current = db.get_setting("unlimited_runs") == "1"
                db.set_setting("unlimited_runs", "0" if current else "1")
            elif action == "set_guild_goal":
                try:
                    nuovo_traguardo = max(1, int(request.form.get("guild_goal", "300")))
                except ValueError:
                    nuovo_traguardo = 300
                db.set_setting("guild_goal", str(nuovo_traguardo))
    locks = db.get_all_locks()
    characters = db.get_all_characters()
    for c in characters:
        c["level"] = engine.level_from_xp(c["xp"])
    unlimited_runs = db.get_setting("unlimited_runs") == "1"
    try:
        guild_goal = int(db.get_setting("guild_goal", "300"))
    except (TypeError, ValueError):
        guild_goal = 300
    return render_template("admin.html", locks=locks, characters=characters, classes=gd.CLASSES, error=error,
                            unlimited_runs=unlimited_runs, guild_goal=guild_goal)


# ─── ARENA (duelli PvP asincroni) ─────────────────────────────────────────
def _arena_faction_data():
    characters = db.get_all_characters()
    factions = sorted({c["faction"] for c in characters})
    char_by_faction = {}
    for c in characters:
        char_by_faction.setdefault(c["faction"], []).append(c["name"])
    for names in char_by_faction.values():
        names.sort()
    return factions, char_by_faction


def _arena_ability_choices(char_class):
    """Tutte le abilita' attive della classe (le passive sono sempre automatiche,
    non si equipaggiano): in arena sono selezionabili a prescindere dal livello,
    tranne quelle segnate 'solo_spedizioni' (pensate solo per il PvE)."""
    out = []
    for a in gd.CLASSES[char_class]["abilities"]:
        if a["type"] == "passiva":
            continue
        out.append(dict(a, solo_spedizioni=a["key"] in engine.ARENA_SOLO_SPEDIZIONI))
    return out


def _build_arena_state_from_form(faction, name, char):
    """Costruisce lo stato di combattimento arena di un lato a partire dai campi
    del form di preparazione — stessa logica di /start_run, ma senza il vincolo del
    livello sulle abilita' selezionabili (vedi _arena_ability_choices)."""
    level = engine.level_from_xp(char["xp"])
    choices = _arena_ability_choices(char["class"])
    selectable_keys = {a["key"] for a in choices if not a["solo_spedizioni"]}
    chosen = [k for k in request.form.getlist("abilities") if k in selectable_keys]
    equipped_abilities = chosen[: gd.ABILITY_LOADOUT_SIZE - 1] or list(selectable_keys)[: gd.ABILITY_LOADOUT_SIZE - 1]
    entourage_bonus = sum(a.get("grants_extra_entourage", 0) for a in choices if a["key"] in equipped_abilities)

    entourage = request.form.getlist("entourage")
    entourage = [e for e in entourage if e in gd.ENTOURAGE_TYPES][: gd.ENTOURAGE_MAX_PICK + entourage_bonus]

    owned_ids = {e["item_id"] for e in db.get_owned_equipment(faction, name)}
    has_strumenti = "strumenti_del_mestiere" in equipped_abilities
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

    state = engine.new_arena_state(faction, name, char["class"], level, entourage, equip_ids, equipped_abilities)
    state["portrait_url"] = _portrait_url(faction, name, char.get("portrait"))
    return state


def _arena_side(match, faction, name):
    if match["faction_a"] == faction and match["name_a"] == name:
        return "a"
    if match["faction_b"] == faction and match["name_b"] == name:
        return "b"
    return None


def _notify_arena_conclusion(match, winner):
    if winner == "pareggio":
        send_arena_discord("🤝 Il duello tra **%s** e **%s** finisce in pareggio!" % (match["name_a"], match["name_b"]))
        return
    vincitore = match["name_a"] if winner == "a" else match["name_b"]
    perdente_state = match["state_b"] if winner == "a" else match["state_a"]
    perdente_nome = match["name_b"] if winner == "a" else match["name_a"]
    modo = "si arrende" if perdente_state["leader"]["timore"] <= 0 else "cade"
    send_arena_discord("🏆 **%s** ha sconfitto **%s** in Arena! (%s %s)" % (vincitore, perdente_nome, perdente_nome, modo))


@app.route("/arena")
def arena_home():
    faction = request.args.get("faction")
    name = request.args.get("name")
    factions, char_by_faction = _arena_faction_data()

    if not faction or not name:
        return render_template("arena_home.html", factions=factions, char_by_faction=char_by_faction, identified=False)

    char = db.get_character(faction, name)
    if not char:
        return redirect(url_for("arena_home"))

    matches = db.get_arena_matches_for(faction, name)
    for m in matches:
        side = _arena_side(m, faction, name)
        opp_side = "b" if side == "a" else "a"
        m["my_side"] = side
        m["opponent_faction"] = m["faction_%s" % opp_side]
        m["opponent_name"] = m["name_%s" % opp_side]
        if m["status"] == "attesa_b":
            m["azione_richiesta"] = "Preparati per accettare la sfida" if side == "b" else "In attesa che l'avversario si prepari"
        elif m["status"] == "in_corso":
            m["azione_richiesta"] = "In attesa dell'avversario" if m.get("pending_action_%s" % side) else "Tocca a te!"
        else:
            m["azione_richiesta"] = "Vittoria!" if m.get("winner") == side else ("Pareggio" if m.get("winner") == "pareggio" else "Sconfitta")

    opponents_by_faction = {f: [n for n in ns if not (f == faction and n == name)] for f, ns in char_by_faction.items()}
    opponents_by_faction = {f: ns for f, ns in opponents_by_faction.items() if ns}

    return render_template(
        "arena_home.html", factions=factions, char_by_faction=char_by_faction, identified=True,
        faction=faction, name=name, char_class=char["class"], matches=matches,
        opponent_factions=sorted(opponents_by_faction.keys()), opponents_by_faction=opponents_by_faction,
    )


@app.route("/arena/prepare")
def arena_prepare():
    faction = request.args.get("faction")
    name = request.args.get("name")
    char = db.get_character(faction, name)
    if not char:
        return redirect(url_for("arena_home"))

    match_id = request.args.get("match_id")
    if match_id:
        match = db.get_arena_match(int(match_id))
        if not match or match["status"] != "attesa_b" or match["faction_b"] != faction or match["name_b"] != name:
            return redirect(url_for("arena_home", faction=faction, name=name))
        opp_faction, opp_name = match["faction_a"], match["name_a"]
    else:
        opp_faction = request.args.get("opp_faction")
        opp_name = request.args.get("opp_name")
        opp = db.get_character(opp_faction, opp_name) if opp_faction and opp_name else None
        if not opp or (faction, name) == (opp_faction, opp_name):
            return redirect(url_for("arena_home", faction=faction, name=name))

    owned = db.get_owned_equipment(faction, name)
    return render_template(
        "arena_prepare.html", faction=faction, name=name, char_class=char["class"],
        level=engine.level_from_xp(char["xp"]), opp_faction=opp_faction, opp_name=opp_name,
        match_id=match_id, entourage_types=gd.ENTOURAGE_TYPES, max_pick=gd.ENTOURAGE_MAX_PICK,
        owned=owned, owned_ids={o["item_id"] for o in owned}, items=gd.ITEMS,
        abilities_all=_arena_ability_choices(char["class"]), ability_loadout_size=gd.ABILITY_LOADOUT_SIZE,
        portrait_url=_portrait_url(faction, name, char.get("portrait")),
    )


@app.route("/arena/prepare", methods=["POST"])
def arena_prepare_submit():
    faction = request.form.get("faction")
    name = request.form.get("name")
    char = db.get_character(faction, name)
    if not char:
        return redirect(url_for("arena_home"))
    state = _build_arena_state_from_form(faction, name, char)
    timestamp = datetime.datetime.utcnow().isoformat()

    match_id = request.form.get("match_id")
    if match_id:
        match = db.get_arena_match(int(match_id))
        if not match or match["status"] != "attesa_b" or match["faction_b"] != faction or match["name_b"] != name:
            return redirect(url_for("arena_home", faction=faction, name=name))
        start_log = engine.start_arena_match(match["state_a"], state)
        db.set_arena_state_b(match["id"], state, start_log, timestamp)
        send_arena_discord("⚔️ Il duello tra **%s** (%s) e **%s** (%s) è iniziato!" %
                            (match["name_a"], match["faction_a"], name, faction))
        return redirect(url_for("arena_match", match_id=match["id"], faction=faction, name=name))

    opp_faction = request.form.get("opp_faction")
    opp_name = request.form.get("opp_name")
    opp = db.get_character(opp_faction, opp_name)
    if not opp or (faction, name) == (opp_faction, opp_name):
        return redirect(url_for("arena_home", faction=faction, name=name))
    new_id = db.create_arena_match(faction, name, opp_faction, opp_name, state, timestamp)
    send_arena_discord("🗡️ **%s** (%s) ha sfidato **%s** (%s) in Arena!" % (name, faction, opp_name, opp_faction))
    return redirect(url_for("arena_match", match_id=new_id, faction=faction, name=name))


@app.route("/arena/match/<int:match_id>")
def arena_match(match_id):
    faction = request.args.get("faction")
    name = request.args.get("name")
    match = db.get_arena_match(match_id)
    if not match:
        return redirect(url_for("arena_home", faction=faction, name=name))
    side = _arena_side(match, faction, name)
    if side is None:
        return redirect(url_for("arena_home", faction=faction, name=name))

    if match["status"] == "attesa_b":
        if side == "b":
            return redirect(url_for("arena_prepare", faction=faction, name=name, match_id=match_id))
        return render_template("arena_wait.html", match=match, faction=faction, name=name,
                                messaggio="In attesa che %s si prepari..." % match["name_b"])

    opp_side = "b" if side == "a" else "a"
    my_state = match["state_%s" % side]
    opp_state = match["state_%s" % opp_side]

    if match["status"] == "concluso":
        return render_template("arena_result.html", match=match, faction=faction, name=name, side=side,
                                my_state=my_state, opp_state=opp_state,
                                CLASS_PASSIVES=gd.CLASS_PASSIVES, ENTOURAGE_TYPES=gd.ENTOURAGE_TYPES)

    my_pending = match.get("pending_action_%s" % side)
    actions = engine.arena_available_actions(my_state)
    return render_template(
        "arena_combat.html", match=match, faction=faction, name=name, side=side,
        my_state=my_state, opp_state=opp_state, actions=actions, waiting=bool(my_pending),
        CLASS_PASSIVES=gd.CLASS_PASSIVES, ENTOURAGE_TYPES=gd.ENTOURAGE_TYPES,
    )


@app.route("/arena/match/<int:match_id>/act", methods=["POST"])
def arena_match_act(match_id):
    faction = request.form.get("faction")
    name = request.form.get("name")
    action_key = request.form.get("action_key", "attacco_fisico")
    match = db.get_arena_match(match_id)
    if not match or match["status"] != "in_corso":
        return redirect(url_for("arena_match", match_id=match_id, faction=faction, name=name))
    side = _arena_side(match, faction, name)
    if side is None:
        return redirect(url_for("arena_home", faction=faction, name=name))
    if match.get("pending_action_%s" % side):
        return redirect(url_for("arena_match", match_id=match_id, faction=faction, name=name))

    my_state = match["state_%s" % side]
    valid_keys = {a["key"] for a in engine.arena_available_actions(my_state) if a["available"]}
    if action_key not in valid_keys:
        return redirect(url_for("arena_match", match_id=match_id, faction=faction, name=name))

    timestamp = datetime.datetime.utcnow().isoformat()
    other_side = "b" if side == "a" else "a"
    other_pending = match.get("pending_action_%s" % other_side)

    if not other_pending:
        db.update_arena_match(match_id, timestamp, **{"pending_action_%s" % side: action_key})
        return redirect(url_for("arena_match", match_id=match_id, faction=faction, name=name))

    action_a = action_key if side == "a" else other_pending
    action_b = action_key if side == "b" else other_pending
    esito, log = engine.resolve_arena_round(match["state_a"], match["state_b"], action_a, action_b)
    fields = {
        "state_a": match["state_a"], "state_b": match["state_b"], "log": log,
        "round": match["round"] + 1, "pending_action_a": None, "pending_action_b": None,
    }
    if esito == "in_corso":
        db.update_arena_match(match_id, timestamp, **fields)
    else:
        winner = {"vittoria_a": "a", "vittoria_b": "b", "pareggio": "pareggio"}[esito]
        fields["status"] = "concluso"
        fields["winner"] = winner
        db.update_arena_match(match_id, timestamp, **fields)
        _notify_arena_conclusion(match, winner)
    return redirect(url_for("arena_match", match_id=match_id, faction=faction, name=name))


@app.route("/arena/match/<int:match_id>/status")
def arena_match_status(match_id):
    match = db.get_arena_match(match_id)
    if not match:
        return {"error": "not_found"}, 404
    return {"status": match["status"], "round": match["round"], "updated_at": match["updated_at"]}


if __name__ == "__main__":
    app.run(debug=True)
