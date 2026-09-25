# -*- coding: utf-8 -*-
"""Motore di gioco puro (nessuna dipendenza da Flask/sessione), cosi' e' testabile
in isolamento. Tutte le funzioni operano su un dizionario `run` passato esplicitamente
e ritornano/mutano quello stesso dizionario, piu' una lista di righe di log."""
import random
import game_data as gd

# Riga sentinella inserita nel log esattamente tra l'azione del leader e quella del
# nemico in un round: combat.html la intercetta per inserire una pausa netta fra le
# due animazioni/suoni invece di mostrarla come testo. Ogni template che stampa il log
# grezzo (room_result.html, il fallback noscript di combat.html) deve escluderla.
ROUND_BEAT_MARKER = "__BEAT__"


# ─── LIVELLI ──────────────────────────────────────────────────────────────
def level_from_xp(xp):
    lvl = 1 + xp // gd.XP_PER_LEVEL
    return min(lvl, gd.MAX_LEVEL)


def unlocked_abilities(char_class, level):
    abilities = gd.CLASSES[char_class]["abilities"]
    return [a for a in abilities if level >= a["lvl"]]


def uses_loadout(char_class):
    """True per le classi gia' ridisegnate col nuovo sistema (cooldown + equipaggio a slot),
    riconosciute dal fatto che almeno un'abilita' ha un campo 'cd'. Le classi non ancora
    ridisegnate continuano a funzionare con tutte le abilita' sbloccate sempre disponibili."""
    return any("cd" in a for a in gd.CLASSES[char_class]["abilities"])


def base_stats_for(char_class, level):
    base = gd.CLASS_BASE_STATS.get(char_class, {"pv": gd.BASE_PV, "timore": gd.BASE_TIMORE})
    growth = gd.CLASS_LEVEL_GROWTH.get(char_class, {"pv_per_level": 0, "timore_per_level": 0})
    extra_levels = level - 1
    pv = base["pv"] + growth["pv_per_level"] * extra_levels
    timore = base["timore"] + growth["timore_per_level"] * extra_levels
    return pv, timore


# ─── CREAZIONE STATO DI UNA RUN ──────────────────────────────────────────
def new_run_state(faction, name, char_class, level, entourage_types, equip_item_ids, equipped_abilities=None):
    armor = gd.BASE_ARMOR
    mres = gd.BASE_MRES
    dmg_bonus = 0
    iniziativa_bonus = 0
    flags = {}
    seen_items = set()
    for item_id in equip_item_ids:
        if not item_id or item_id in seen_items:
            continue
        seen_items.add(item_id)
        eff = gd.ITEMS[item_id]["effects"]
        armor += eff.get("armor", 0)
        mres += eff.get("mres", 0)
        dmg_bonus += eff.get("dmg", 0)
        iniziativa_bonus += eff.get("iniziativa", 0)
        for k, v in eff.items():
            if k not in ("armor", "mres", "dmg", "iniziativa"):
                flags[k] = v

    oro_iniziale = 0

    seguito = [{"type": t, "alive": True, "charges": gd.GUARDIANO_CHARGES if t == "guardiano" else None}
               for t in entourage_types]

    pv_max, timore_max = base_stats_for(char_class, level)

    if equipped_abilities is None:
        unlocked = unlocked_abilities(char_class, level)
        equipped_abilities = [a["key"] for a in unlocked[: gd.ABILITY_LOADOUT_SIZE - 1]]

    if "veterano_mille_battaglie" in equipped_abilities:
        armor += 2
        mres += 2
    if "protezione_arcana" in equipped_abilities:
        armor += 1
        mres += 3

    run = {
        "faction": faction, "name": name, "class": char_class, "level": level,
        "leader": {
            "pv": pv_max, "pv_max": pv_max,
            "timore": timore_max, "timore_max": timore_max,
            "armor": armor, "mres": mres, "dmg_bonus": dmg_bonus, "iniziativa_bonus": iniziativa_bonus,
        },
        "equip_flags": flags,
        "seguito": seguito,
        "treasure": {**{r: 0 for r in gd.RESOURCE_TYPES}, "oro": oro_iniziale},
        "room_index": 0,
        "rooms_plan": generate_rooms_plan(),
        "used_once_abilities": [],
        "ability_use_counts": {},
        "protezione_arcana_used": False,
        "omelia_salvezza_used": False,
        "equipped_abilities": equipped_abilities,
        "cooldowns": {},
        "temp_buffs": {"dmg": 0, "armor": 0, "mres": 0},
        "log": [],
        "combat": None,  # stato del combattimento in corso (se presente)
        "finished": False,
        "result": None,  # 'vittoria' | 'ritirata_timore' | 'ritirata_morte'
        "incudine_free_used": 0,  # Amministratore: "Abile nelle trattative"
        "special_boss_fought": None,  # boss speciale incontrato in questa run (es. "il_diaulo"), se presente
        "shop_used": {"incudine": False, "sacco_monete": False},  # una volta a stanza, si resetta cambiando stanza
        "shop_used_for_room_index": -1,  # a quale room_index si riferisce shop_used (per il reset pigro)
        "shop_log": None,  # feedback dell'ultimo acquisto, mostrato una volta sola in room.html
        "bonus_xp": 0,  # PE extra da eventi della Stanza Misteriosa, sommati a fine run
        "pending_effects": [],  # effetti (es. veleno) che scattano all'inizio del PROSSIMO combattimento
        "mystery_event": None,  # evento pescato per la Stanza Misteriosa, in attesa di una scelta
    }
    return run


# ─── GENERAZIONE STANZE ──────────────────────────────────────────────────
def reset_shop_if_new_room(run):
    """Forgia e Mercenario si possono usare una volta a stanza: quando si arriva
    davvero a una stanza nuova (non quando si ricarica la stessa dopo un acquisto),
    il contatore si azzera."""
    if run.get("shop_used_for_room_index") != run["room_index"]:
        run["shop_used"] = {"incudine": False, "sacco_monete": False}
        run["shop_used_for_room_index"] = run["room_index"]


def generate_rooms_plan():
    """Genera, per ognuna delle ROOMS_PER_RUN stanze, le opzioni tra cui scegliere per
    concludere la stanza. La Battaglia c'e' sempre; Fontana e Stanza Misteriosa
    compaiono ciascuna con la propria probabilita' indipendente (possono comparire
    insieme). Forgia e Mercenario non sono piu' "scelte della stanza": sono azioni
    sempre disponibili che non la concludono, gestite a parte (vedi /shop_action)."""
    plan = []
    for i in range(gd.ROOMS_PER_RUN):
        options = ["battaglia"]
        if i + 1 >= gd.FONTANA_MIN_ROOM and random.random() < gd.FONTANA_APPEARANCE_CHANCE:
            options.append("fontana")
        if random.random() < gd.MYSTERY_ROOM_CHANCE:
            options.append("stanza_misteriosa")
        random.shuffle(options)
        plan.append(options)
    return plan


# ─── ABILITA' DISPONIBILI IN COMBATTIMENTO ───────────────────────────────
def _attacco_fisico_desc(char_class):
    lo, hi = gd.CLASS_BASE_DMG.get(char_class, (gd.BASE_DMG_MIN, gd.BASE_DMG_MAX))
    extra = ""
    if char_class == "Esploratore":
        extra = "; guadagni +2 scudo fisico"
    return "%d-%d danni fisici%s." % (lo, hi, extra)


def all_combat_abilities(run):
    """Ritorna TUTTE le abilita' attive equipaggiate, comprese quelle attualmente non
    disponibili per cooldown o usi esauriti — con lo stato necessario a mostrarlo a schermo."""
    char_class = run["class"]
    result = [{"key": "attacco_fisico", "name": "Attacco Fisico", "type": "fisico",
               "desc": _attacco_fisico_desc(char_class), "available": True,
               "cd_remaining": None, "max_cd": None, "uses_left": None, "max_uses": None}]

    abilities = unlocked_abilities(char_class, run["level"])
    ability_by_key = {a["key"]: a for a in abilities}
    keys = run.get("equipped_abilities", []) if uses_loadout(char_class) else [a["key"] for a in abilities]

    for key in keys:
        a = ability_by_key.get(key)
        if not a or a["type"] == "passiva":
            continue
        entry = {"key": a["key"], "name": a["name"], "type": a["type"], "desc": a["desc"],
                 "cd_remaining": None, "max_cd": a.get("cd"), "uses_left": None, "max_uses": a.get("max_uses")}
        if a.get("once"):
            used = key in run["used_once_abilities"]
            entry["available"] = not used
            entry["max_uses"] = 1
            entry["uses_left"] = 0 if used else 1
        elif "max_uses" in a:
            used_count = run["ability_use_counts"].get(key, 0)
            entry["uses_left"] = a["max_uses"] - used_count
            entry["available"] = entry["uses_left"] > 0
        else:
            remaining = run["cooldowns"].get(key, 0)
            entry["cd_remaining"] = remaining
            entry["available"] = remaining <= 0
        result.append(entry)
    return result


def available_combat_actions(run):
    """Ritorna solo le azioni davvero selezionabili in questo momento (usata per validare
    l'azione scelta lato server)."""
    return [a for a in all_combat_abilities(run) if a.get("available", True)]


def has_ability(run, key):
    return any(a["key"] == key for a in unlocked_abilities(run["class"], run["level"]))


# ─── SEGUITO: ASSORBIMENTO DI UN COLPO FISICO ────────────────────────────
def _troop_falls(run, member, log):
    """Segna una truppa del Seguito come caduta e applica l'effetto passivo del
    Penitente, se presente nel Seguito (recupero di Timore per il leader). Va
    usata ovunque una truppa muoia, qualunque sia la causa."""
    member["alive"] = False
    if any(m["alive"] and m["type"] == "penitente" for m in run["seguito"]):
        bonus = gd.PENITENTE_TIMORE_BONUS
        run["leader"]["timore"] = min(run["leader"]["timore_max"], run["leader"]["timore"] + bonus)
        log.append("Penitente: il sacrificio non è vano, recuperi %d Timore." % bonus)


def _seguito_absorb(run, incoming_dmg, cavaliere_ward_chance=None):
    """Tenta di far assorbire il colpo fisico dal Seguito. Ritorna (assorbito: bool,
    danno_residuo_al_leader: int, righe_di_log: list). cavaliere_ward_chance permette
    di usare una percentuale diversa da quella di default (usata dall'Arena)."""
    log = []
    seg = run["seguito"]
    ward_chance = cavaliere_ward_chance if cavaliere_ward_chance is not None else gd.CAVALIERE_WARD_CHANCE

    def alive_of(t):
        return [m for m in seg if m["alive"] and m["type"] == t]

    # Cavaliere: possibilita' di annullare l'attacco senza consumare nessuno
    if alive_of("cavaliere") and random.random() < ward_chance:
        log.append("Un Cavaliere del Seguito para il colpo: l'attacco viene annullato.")
        return True, 0, log

    razionamento = False

    guardiani = alive_of("guardiano")
    if guardiani:
        m = guardiani[0]
        residuo = max(0, incoming_dmg - gd.GUARDIANO_REDUCTION)
        m["charges"] -= 1
        log.append("Il Guardiano assorbe parte del colpo (-%d danno)." % gd.GUARDIANO_REDUCTION)
        if m["charges"] <= 0:
            log.append("Il Guardiano, esausto, cade.")
            _troop_falls(run, m, log)
        return True, residuo, log

    membri = alive_of("fante")
    if membri:
        m = membri[0]
        survive = razionamento and random.random() < 0.5
        log.append("Fante assorbe il colpo interamente%s." % (" e resiste ancora!" if survive else ", e cade."))
        if not survive:
            _troop_falls(run, m, log)
        return True, 0, log

    mercenari = alive_of("mercenario")
    if mercenari:
        m = mercenari[0]
        _troop_falls(run, m, log)
        if random.random() < gd.MERCENARIO_SUCCESS_CHANCE:
            log.append("Il mercenario assorbe il colpo prima di fuggire.")
            return True, 0, log
        else:
            log.append("Il mercenario fugge senza proteggerti!")
            return False, incoming_dmg, log

    return False, incoming_dmg, log


# ─── COMBATTIMENTO ────────────────────────────────────────────────────────
def _interp_value(table_by_level, level):
    """Come _interp_dmg ma per un singolo valore (es. PV o Timore fissi di un boss
    speciale), interpolato linearmente tra i livelli-ancora piu' vicini."""
    keys = sorted(table_by_level.keys())
    if level <= keys[0]:
        return table_by_level[keys[0]]
    if level >= keys[-1]:
        return table_by_level[keys[-1]]
    lo = max(k for k in keys if k <= level)
    hi = min(k for k in keys if k >= level)
    if lo == hi:
        return table_by_level[lo]
    t = (level - lo) / (hi - lo)
    return round(table_by_level[lo] + (table_by_level[hi] - table_by_level[lo]) * t)


def start_combat(run, tier):
    """tier: 1..N per stanze normali, 'boss' per il miniboss."""
    level = run["level"]
    special_boss = None
    enemy_pv_value = None
    enemy_timore_value = None
    if tier == "boss":
        data = gd.get_boss_tier(gd.ROOMS_PER_RUN, level)
        if random.random() < gd.IL_DIAULO["spawn_chance"]:
            special_boss = "il_diaulo"
            name, icon = gd.IL_DIAULO["name"], gd.IL_DIAULO["icon"]
            archetype = "il_diaulo"
            enemy_armor, enemy_mres = gd.IL_DIAULO["armor"], gd.IL_DIAULO["mres"]
        elif random.random() < gd.UOMORSOMAIALE["spawn_chance"]:
            special_boss = "uomorsomaiale"
            spec = gd.UOMORSOMAIALE
            name, icon = spec["name"], spec["icon"]
            archetype = "uomorsomaiale"
            enemy_armor, enemy_mres = spec["armor"], spec["mres"]
            enemy_pv_value = _interp_value(spec["pv_table"], level)
            enemy_timore_value = _interp_value(spec["timore_table"], level)
        else:
            name, icon, archetype = random.choice(data["pool"])
            enemy_armor, enemy_mres = gd.enemy_defense(archetype, level)
    else:
        data = gd.get_enemy_tier(tier, level)
        name, icon, archetype = random.choice(data["pool"])
        enemy_armor, enemy_mres = gd.enemy_defense(archetype, level)
    if enemy_pv_value is None:
        enemy_pv_value = data["pv"]
    if enemy_timore_value is None:
        enemy_timore_value = data["pv"]  # comportamento generico: PV e Timore coincidono
    if tier == "boss":
        # sopravvive anche dopo che run["combat"] viene svuotato (vittoria) o quando si
        # arriva a run_end: serve per personalizzare il resoconto sul boss incontrato.
        run["special_boss_fought"] = special_boss
    run["cooldowns"] = {}  # i cooldown si resettano a ogni nuovo combattimento, non durano tutta la run
    run["combat"] = {
        "tier": tier, "name": name, "icon": icon, "archetype": archetype, "special_boss": special_boss,
        "dot_kind": gd.MONSTER_DOT_KIND.get(name, "sanguinamento"),
        "enemy_armor": enemy_armor, "enemy_mres": enemy_mres,
        "enemy_pv": enemy_pv_value, "enemy_pv_max": enemy_pv_value,
        "enemy_timore": enemy_timore_value, "enemy_timore_max": enemy_timore_value,
        "dmg": data["dmg"], "fear_chance": data["fear_chance"], "fear_dmg": data["fear_dmg"],
        "round": 1, "first_hit_taken": False, "first_fear_hit_taken": False, "negotiated_escape": False, "enemy_stunned": 0,
        "combat_armor_bonus": 0, "combat_mres_bonus": 0, "combat_dmg_bonus": 0,
        "shield_reduction": 0, "double_next_attack": False, "skip_attack": False,
        "colpo_arcano_stacks": 0, "shield_physical_pool": 0, "shield_timore_pool": 0,
        "enemy_slowed_turns": 0, "burn_turns": 0, "burn_dmg": 0,
        "evasion_turns": 0, "evasion_chance": 0.0,
        "raffica_potenziata": False, "enemy_weaken_turns": 0, "enemy_weaken_amount": 0,
        "enemy_buff_stat": None, "enemy_buff_turns": 0,
        "player_debuff_stat": None, "player_debuff_turns": 0,
        "player_bleed_turns": 0, "player_bleed_dmg": 0, "player_bleed_target": None, "player_bleed_kind": None,
        "enemy_bleed_turns": 0, "enemy_bleed_dmg": 0, "enemy_bleed_kind": None,
        "egida_triggered": False,
        "diaulo_signore_cd": 0,
        "uomorsomaiale_sventrare_cd": 0, "uomorsomaiale_ruggito_cd": 0,
        "player_dmg_debuff": 0, "player_dmg_debuff_turns": 0,
    }
    run["log"] = []
    if special_boss == "il_diaulo":
        run["log"].append("IL DIAULO emerge dalle ombre, e il tuo Timore trema solo a guardarlo.")
    if run.get("pending_effects"):
        for eff in run["pending_effects"]:
            if eff["type"] == "veleno":
                run["combat"]["player_bleed_turns"] = eff["turns"]
                run["combat"]["player_bleed_dmg"] = eff["dmg"]
                run["combat"]["player_bleed_target"] = "pv"
                run["combat"]["player_bleed_kind"] = "veleno"
                run["log"].append("Il veleno bevuto in precedenza si manifesta: perderai %d PV a turno per %d turni." % (eff["dmg"], eff["turns"]))
            elif eff["type"] == "dmg_debuff":
                run["combat"]["player_dmg_debuff"] = eff["amount"]
                run["combat"]["player_dmg_debuff_turns"] = eff["turns"]
                run["log"].append("Il rito incompiuto ti indebolisce: i tuoi colpi infliggeranno %d danni in meno per %d turni." % (eff["amount"], eff["turns"]))
        run["pending_effects"] = []
    novizi = [m for m in run["seguito"] if m["alive"] and m["type"] == "novizio"]
    if novizi:
        run["combat"]["shield_physical_pool"] += gd.NOVIZIO_SHIELD_PHYSICAL
        run["combat"]["shield_timore_pool"] += gd.NOVIZIO_SHIELD_TIMORE
        _troop_falls(run, novizi[0], run["log"])
        run["log"].append("Un Novizio si consuma per proteggerti: guadagni %d scudo Vita e %d scudo Timore." % (gd.NOVIZIO_SHIELD_PHYSICAL, gd.NOVIZIO_SHIELD_TIMORE))
    if tier == "boss" and run["class"] == "Esploratore":
        bonus_pv = round(run["leader"]["pv_max"] * 0.25)
        bonus_timore = round(run["leader"]["timore_max"] * 0.25)
        run["combat"]["shield_physical_pool"] += bonus_pv
        run["combat"]["shield_timore_pool"] += bonus_timore
        run["log"].append("Sforzo Adrenalinico: il pericolo ti acuisce i sensi — guadagni %d scudo Vita e %d scudo Timore." % (bonus_pv, bonus_timore))
    if has_ability(run, "fiuto"):
        run["log"].append("🧭 Fiuto: percepisci la presenza di %s %s prima ancora di vederlo." % (icon, name))
    run["log"].append("%s %s emerge dall'ombra." % (icon, name))


def _leader_dmg(run):
    lo, hi = gd.CLASS_BASE_DMG.get(run["class"], (gd.BASE_DMG_MIN, gd.BASE_DMG_MAX))
    base = random.randint(lo, hi)
    return base + run["leader"]["dmg_bonus"] + run["temp_buffs"]["dmg"] + run["combat"].get("combat_dmg_bonus", 0)


def _effective_defense(run, combat, stat):
    """Armatura o Res. Mentale effettive del leader in questo combattimento: base +
    oggetti/passive + bonus temporanei di combattimento, meno un eventuale debuff
    nemico attivo su quella specifica statistica."""
    base = run["leader"][stat] + run["temp_buffs"][stat] + combat.get("combat_%s_bonus" % stat, 0)
    if combat.get("player_debuff_stat") == stat and combat.get("player_debuff_turns", 0) > 0:
        base -= gd.ENEMY_DEBUFF_AMOUNT
    return max(0, base)


def _check_egida_trigger(run, combat, log):
    """Egida dell'Ultimo Bastione: la prima volta che la Vita scende sotto la soglia in
    questo combattimento, concede un bonus fisso e permanente all'Armatura per il resto
    dello scontro (non si riattiva se la Vita risale e ridiscende)."""
    bonus = run.get("equip_flags", {}).get("bonus_armor_sotto_quarto", 0)
    if not bonus or combat.get("egida_triggered"):
        return
    if run["leader"]["pv_max"] > 0 and run["leader"]["pv"] < run["leader"]["pv_max"] * gd.RADDOPPIO_SOTTO_QUARTO_SOGLIA:
        combat["egida_triggered"] = True
        combat["combat_armor_bonus"] = combat.get("combat_armor_bonus", 0) + bonus
        log.append("L'Egida dell'Ultimo Bastione risponde al pericolo: +%d Armatura per il resto dello scontro." % bonus)


def _maybe_reflect_fixed(run, combat, log):
    """Armatura del Sigillo Infranto: possibilita' fissa di riflettere una quantita'
    fissa di danno sul nemico ad ogni colpo fisico subito."""
    chance = run.get("equip_flags", {}).get("riflette_chance", 0)
    amount = run.get("equip_flags", {}).get("riflette_fisso", 0)
    if chance and amount and random.random() < chance:
        combat["enemy_pv"] -= amount
        log.append("La tua armatura riflette %d danni sul nemico." % amount)


def _special_boss_deal_damage(run, combat, log, phys, timore_amt):
    """Infligge danno di un boss speciale al leader con la stessa mitigazione (scudo di
    Formazione Difensiva, Scudo Magico, Armatura/Res. Mentale) usata per un attacco
    nemico normale — cosi' le loro mosse "grezze" (non il veleno/sanguinamento, che
    bypassano tutto di proposito) restano coerenti col resto del gioco."""
    if phys > 0:
        residuo = phys
        shield = combat.get("shield_reduction", 0)
        if shield and residuo > 0:
            residuo = max(0, residuo - shield)
            combat["shield_reduction"] = 0
            log.append("Lo scudo di Formazione Difensiva attutisce il colpo.")
        pool = combat.get("shield_physical_pool", 0)
        if pool and residuo > 0:
            assorbito = min(pool, residuo)
            residuo -= assorbito
            combat["shield_physical_pool"] -= assorbito
            log.append("Lo Scudo Magico assorbe %d danni fisici (%d rimasti nel serbatoio)." % (assorbito, combat["shield_physical_pool"]))
        final_armor = _effective_defense(run, combat, "armor")
        dmg_to_leader = max(1, residuo - final_armor) if residuo > 0 else 0
        if dmg_to_leader > 0:
            run["leader"]["pv"] -= dmg_to_leader
            log.append("Subisci %d danni fisici." % dmg_to_leader)
            _maybe_reflect_fixed(run, combat, log)
    if timore_amt > 0:
        residuo_t = timore_amt
        pool_t = combat.get("shield_timore_pool", 0)
        if pool_t and residuo_t > 0:
            assorbito_t = min(pool_t, residuo_t)
            residuo_t -= assorbito_t
            combat["shield_timore_pool"] -= assorbito_t
            log.append("Lo Scudo Magico assorbe %d danni al Timore (%d rimasti nel serbatoio)." % (assorbito_t, combat["shield_timore_pool"]))
        total_mres = _effective_defense(run, combat, "mres")
        timore_to_leader = max(1, residuo_t - total_mres) if residuo_t > 0 else 0
        if timore_to_leader > 0:
            run["leader"]["timore"] -= timore_to_leader
            log.append("Il tuo Timore scende di %d." % timore_to_leader)


def _il_diaulo_turn(run, combat, log):
    """Moveset dedicato di IL DIAULO, boss speciale (20% di comparire al posto del
    miniboss casuale). Sostituisce del tutto la logica generica (cura/buff/debuff/
    sanguinamento) quando e' lui il nemico attivo."""
    spec = gd.IL_DIAULO
    has_shield = combat.get("shield_physical_pool", 0) > 0 or combat.get("shield_timore_pool", 0) > 0

    if has_shield and combat.get("diaulo_signore_cd", 0) <= 0:
        removed_phys = combat.get("shield_physical_pool", 0)
        removed_timore = combat.get("shield_timore_pool", 0)
        combat["shield_physical_pool"] = 0
        combat["shield_timore_pool"] = 0
        combat["enemy_pv"] = min(combat["enemy_pv_max"], combat["enemy_pv"] + removed_phys)
        combat["enemy_timore"] = min(combat["enemy_timore_max"], combat["enemy_timore"] + removed_timore)
        combat["diaulo_signore_cd"] = 8
        log.append("Signore Oscuro: IL DIAULO dissolve i tuoi scudi (-%d Vita, -%d Timore) e ne assorbe l'energia, curandosene per lo stesso ammontare." % (removed_phys, removed_timore))
        return

    roll = random.random()
    if roll < spec["amico_rettiliani_chance"]:
        dmg = random.randint(*spec["amico_rettiliani_dmg"])
        timore_dmg = random.randint(*spec["amico_rettiliani_dmg_timore"])
        _special_boss_deal_damage(run, combat, log, dmg, timore_dmg)
        combat["player_bleed_turns"] = spec["veleno_turni"]
        combat["player_bleed_dmg"] = spec["veleno_dmg"]
        combat["player_bleed_target"] = "pv"
        combat["player_bleed_kind"] = "veleno"
        log.append("Amico dei Rettiliani: IL DIAULO inietta un veleno che drena %d PV a turno per %d turni (ignora armatura e scudi)." % (spec["veleno_dmg"], spec["veleno_turni"]))
        return
    elif roll < spec["amico_rettiliani_chance"] + spec["buttacettete_chance"]:
        dmg = random.randint(*spec["buttacettete_dmg"])
        contraccolpo = random.randint(*spec["buttacettete_contraccolpo"])
        log.append("Buttacettete: IL DIAULO carica e si schianta su di te.")
        _special_boss_deal_damage(run, combat, log, dmg, 0)
        combat["enemy_pv"] -= contraccolpo
        log.append("Lo schianto gli costa %d danni di contraccolpo." % contraccolpo)
        return
    else:
        dmg_timore = random.randint(*spec["dmg_timore_base"])
        eff_mres = max(0, _effective_defense(run, combat, "mres") - spec["penetrazione_mres"])
        pool_t = combat.get("shield_timore_pool", 0)
        residuo_t = dmg_timore
        if pool_t and residuo_t > 0:
            assorbito_t = min(pool_t, residuo_t)
            residuo_t -= assorbito_t
            combat["shield_timore_pool"] -= assorbito_t
            log.append("Lo Scudo Magico assorbe %d danni al Timore (%d rimasti nel serbatoio)." % (assorbito_t, combat["shield_timore_pool"]))
        finale = max(1, residuo_t - eff_mres) if residuo_t > 0 else 0
        if finale > 0:
            run["leader"]["timore"] -= finale
            log.append("IL DIAULO sussurra il tuo nome: perdi %d Timore (penetra %d Res. Mentale)." % (finale, spec["penetrazione_mres"]))


def _uomorsomaiale_turn(run, combat, log):
    """Moveset dedicato dell'Uomorsomaiale: sceglie a caso fra le mosse non in
    cooldown (nessuna percentuale fissa, a differenza di IL DIAULO)."""
    spec = gd.UOMORSOMAIALE
    disponibili = ["base"]
    if combat.get("uomorsomaiale_sventrare_cd", 0) <= 0:
        disponibili.append("sventrare")
    if combat.get("uomorsomaiale_ruggito_cd", 0) <= 0:
        disponibili.append("ruggito")
    mossa = random.choice(disponibili)

    if mossa == "sventrare":
        combat["uomorsomaiale_sventrare_cd"] = spec["sventrare_cd"]
        dmg = random.randint(*spec["sventrare_dmg"])
        log.append("Sventrare: l'Uomorsomaiale affonda le zanne.")
        _special_boss_deal_damage(run, combat, log, dmg, 0)
        if run.get("equip_flags", {}).get("immunita_sanguinamento"):
            log.append("L'Elmo del Primo Re di Karag-Duraz protegge dalla ferita: non sanguini.")
        else:
            combat["player_bleed_turns"] = spec["sventrare_bleed_turni"]
            combat["player_bleed_dmg"] = spec["sventrare_bleed_dmg"]
            combat["player_bleed_target"] = "pv"
            combat["player_bleed_kind"] = "sanguinamento"
            log.append("Sventrare: la ferita sanguina per %d PV a turno per %d turni." % (spec["sventrare_bleed_dmg"], spec["sventrare_bleed_turni"]))
        return

    if mossa == "ruggito":
        combat["uomorsomaiale_ruggito_cd"] = spec["ruggito_cd"]
        combat["player_dmg_debuff"] = spec["ruggito_riduzione"]
        combat["player_dmg_debuff_turns"] = spec["ruggito_turni"]
        log.append("Ruggito: l'Uomorsomaiale ruggisce, intimorendoti — i tuoi colpi infliggeranno %d danni in meno per %d turni." % (spec["ruggito_riduzione"], spec["ruggito_turni"]))
        return

    for i in range(spec["colpi_base"]):
        dmg = random.randint(*spec["dmg_base"])
        log.append("L'Uomorsomaiale attacca (colpo %d di %d)." % (i + 1, spec["colpi_base"]))
        _special_boss_deal_damage(run, combat, log, dmg, 0)


def _set_cooldown(run, ability_key):
    for a in gd.CLASSES[run["class"]]["abilities"]:
        if a["key"] == ability_key:
            run["cooldowns"][ability_key] = a.get("cd", 0)
            return


def _apply_ability_action(run, ability_key):
    """Applica l'effetto di un'abilita' attiva scelta dal giocatore per questo round.
    Ritorna (danno_fisico_al_nemico:int, danno_timore_al_nemico:int, righe_di_log:list, fuga:bool)."""
    log = []
    combat = run["combat"]
    if ability_key in ("negoziazione", "nebbia_illusoria"):
        run["used_once_abilities"].append(ability_key)
        combat["negotiated_escape"] = True
        verbo = "Le tue parole convincono il nemico a ritirarsi" if ability_key == "negoziazione" else "Sparisci nella nebbia, sottraendoti allo scontro"
        log.append("%s." % verbo)
        return 0, 0, log, True

    if ability_key == "martellata":
        _set_cooldown(run, ability_key)
        dmg = random.randint(3, 5) + run["leader"]["dmg_bonus"] + run["temp_buffs"]["dmg"]
        log.append("Martellata: infliggi %d danni." % dmg)
        if random.random() < 0.5:
            stordimento = random.randint(1, 2)
            combat["enemy_stunned"] = combat.get("enemy_stunned", 0) + stordimento
            log.append("Il colpo stordisce il nemico per %d turno/i!" % stordimento)
        return dmg, 0, log, False

    if ability_key == "formazione_difensiva":
        _set_cooldown(run, ability_key)
        combat["combat_armor_bonus"] += 1
        combat["shield_reduction"] += 3
        log.append("Formazione Difensiva: +1 Armatura fino a fine combattimento; il prossimo colpo subito sara' ridotto di 3.")
        return 0, 0, log, False

    if ability_key == "doppio_colpo":
        _set_cooldown(run, ability_key)
        d1 = _leader_dmg(run)
        d2 = _leader_dmg(run)
        log.append("Doppio Colpo: due attacchi infliggono %d e %d danni." % (d1, d2))
        return d1 + d2, 0, log, False

    if ability_key == "vita_al_fronte":
        _set_cooldown(run, ability_key)
        heal = run["leader"]["pv_max"] // 4
        run["leader"]["pv"] = min(run["leader"]["pv_max"], run["leader"]["pv"] + heal)
        log.append("Vita al Fronte: recuperi %d Vita." % heal)
        return 0, 0, log, False

    if ability_key == "grido_di_guerra":
        _set_cooldown(run, ability_key)
        combat["combat_dmg_bonus"] += 1
        combat["double_next_attack"] = True
        log.append("Grido di Guerra: non attacchi questo turno, ma il tuo prossimo colpo sara' piu' forte (+1 Danno, +40% danno al prossimo attacco).")
        return 0, 0, log, False

    if ability_key == "fine_stratega":
        run["ability_use_counts"][ability_key] = run["ability_use_counts"].get(ability_key, 0) + 1
        fallen = [m for m in run["seguito"] if not m["alive"]]
        for m in fallen:
            m["alive"] = True
            if m["type"] == "guardiano":
                m["charges"] = gd.GUARDIANO_CHARGES
        stat = random.choice(["dmg", "armor", "mres"])
        run["temp_buffs"][stat] = run["temp_buffs"].get(stat, 0) + 1
        label = {"dmg": "Danno", "armor": "Armatura", "mres": "Resistenza Mentale"}[stat]
        if fallen:
            log.append("Fine Stratega: %d membri del Seguito tornano in forze, e guadagni +1 %s per il resto della run." % (len(fallen), label))
        else:
            log.append("Fine Stratega: il Seguito e' gia' al completo, ma guadagni comunque +1 %s per il resto della run." % label)
        return 0, 0, log, False

    if ability_key == "manovra_a_tenaglia":
        run["used_once_abilities"].append(ability_key)
        vive = [m for m in run["seguito"] if m["alive"]]
        if not vive:
            log.append("Manovra a Tenaglia: non hai piu' truppe da sacrificare, il gesto resta vano.")
            return 0, 0, log, False
        dmg_totale = 0
        for m in vive:
            colpo = random.randint(8, 10)
            dmg_totale += colpo
            _troop_falls(run, m, log)
        log.append("Manovra a Tenaglia: sacrifichi %d membri del Seguito, infliggendo %d danni complessivi." % (len(vive), dmg_totale))
        return dmg_totale, 0, log, False

    if ability_key == "colpo_arcano":
        _set_cooldown(run, ability_key)
        stacks = combat.get("colpo_arcano_stacks", 0)
        dmg = random.randint(4, 6) + stacks
        if has_ability(run, "potenziale_arcano"):
            dmg += 2 + run["treasure"].get("gemme", 0)
        combat["colpo_arcano_stacks"] = stacks + 1
        log.append("Colpo Arcano: infliggi %d danni." % dmg)
        return dmg, 0, log, False

    if ability_key == "scudo_magico":
        _set_cooldown(run, ability_key)
        combat["shield_physical_pool"] += 5
        combat["shield_timore_pool"] += 6
        log.append("Scudo Magico: eretta una barriera che assorbira' i prossimi 5 danni fisici e 6 al Timore.")
        return 0, 0, log, False

    if ability_key == "raggio_congelante":
        _set_cooldown(run, ability_key)
        dmg = random.randint(5, 7) + run["leader"]["dmg_bonus"] + run["temp_buffs"]["dmg"] + combat.get("combat_dmg_bonus", 0)
        log.append("Raggio Congelante: infliggi %d danni." % dmg)
        if random.random() < 0.5:
            combat["enemy_slowed_turns"] = 2
            log.append("Il nemico viene rallentato: agira' per ultimo nei prossimi 2 turni.")
        return dmg, 0, log, False

    if ability_key == "parola_guaritrice":
        _set_cooldown(run, ability_key)
        heal_pv = random.randint(5, 10)
        heal_timore = random.randint(6, 12)
        run["leader"]["pv"] = min(run["leader"]["pv_max"], run["leader"]["pv"] + heal_pv)
        run["leader"]["timore"] = min(run["leader"]["timore_max"], run["leader"]["timore"] + heal_timore)
        log.append("Parola Guaritrice: recuperi %d Vita e %d Timore." % (heal_pv, heal_timore))
        return 0, 0, log, False

    if ability_key == "palla_di_fuoco":
        _set_cooldown(run, ability_key)
        dmg = random.randint(7, 12) + run["leader"]["dmg_bonus"] + run["temp_buffs"]["dmg"] + combat.get("combat_dmg_bonus", 0)
        combat["burn_turns"] = 2
        combat["burn_dmg"] = 2
        log.append("Palla di Fuoco: infliggi %d danni; il nemico prende fuoco." % dmg)
        return dmg, 0, log, False

    if ability_key == "copie_illusorie":
        _set_cooldown(run, ability_key)
        combat["evasion_turns"] = 3
        combat["evasion_chance"] = 0.7
        log.append("Copie Illusorie: per i prossimi 3 turni hai il 70% di possibilita' di evitare ogni colpo.")
        return 0, 0, log, False

    if ability_key == "orazione_esperta":
        _set_cooldown(run, ability_key)
        timore_dmg = random.randint(3, 5)
        log.append("Orazione Esperta: infliggi %d danni al Timore del nemico." % timore_dmg)
        caduti = [m for m in run["seguito"] if not m["alive"]]
        if caduti and random.random() < 0.5:
            scelto = random.choice(caduti)
            scelto["alive"] = True
            if scelto["type"] == "guardiano":
                scelto["charges"] = gd.GUARDIANO_CHARGES
            nome = gd.ENTOURAGE_TYPES.get(scelto["type"], {}).get("name", scelto["type"])
            log.append("%s del tuo Seguito viene rianimato." % nome)
        return 0, timore_dmg, log, False

    if ability_key == "littori_sacri":
        _set_cooldown(run, ability_key)
        dmg = random.randint(5, 8) + run["leader"]["dmg_bonus"] + run["temp_buffs"]["dmg"] + combat.get("combat_dmg_bonus", 0)
        timore_dmg = random.randint(2, 3)
        log.append("Littori Sacri: infliggi %d danni fisici e %d al Timore del nemico." % (dmg, timore_dmg))
        vive = [m for m in run["seguito"] if m["alive"]]
        if vive:
            scelto = random.choice(vive)
            nome = gd.ENTOURAGE_TYPES.get(scelto["type"], {}).get("name", scelto["type"])
            log.append("%s viene sacrificato nel rito." % nome)
            _troop_falls(run, scelto, log)
        return dmg, timore_dmg, log, False

    if ability_key == "proteggimi":
        _set_cooldown(run, ability_key)
        attive = sum(1 for m in run["seguito"] if m["alive"])
        combat["shield_physical_pool"] += 3 * attive
        combat["shield_timore_pool"] += 2 * attive
        log.append("Proteggimi!: %d truppe ancora in vita ti proteggono con uno scudo di %d Vita e %d Timore." % (attive, 3 * attive, 2 * attive))
        return 0, 0, log, False

    if ability_key == "omelia_della_potenza":
        _set_cooldown(run, ability_key)
        timore_dmg = random.randint(4, 6)
        if random.random() < 0.3:
            timore_dmg *= 2
            log.append("Omelia della Potenza: colpo critico! Infliggi %d danni al Timore del nemico." % timore_dmg)
        else:
            log.append("Omelia della Potenza: infliggi %d danni al Timore del nemico." % timore_dmg)
        return 0, timore_dmg, log, False

    if ability_key == "messa_salvifica":
        _set_cooldown(run, ability_key)
        rianimate = 0
        for m in run["seguito"]:
            if not m["alive"]:
                m["alive"] = True
                if m["type"] == "guardiano":
                    m["charges"] = gd.GUARDIANO_CHARGES
                rianimate += 1
        if rianimate:
            log.append("Messa Salvifica: %d truppe tornano in sesto." % rianimate)
        else:
            log.append("Messa Salvifica: il Seguito era gia' al completo, ma ne trae comunque beneficio spirituale.")
        return 0, 0, log, False

    if ability_key == "pontifex_maximus":
        _set_cooldown(run, ability_key)
        for a in gd.CLASSES["Diplomatico"]["abilities"]:
            if a["key"] != ability_key and "cd" in a and a["key"] in run["cooldowns"]:
                run["cooldowns"][a["key"]] = 0
        combat["combat_armor_bonus"] += 2
        combat["combat_mres_bonus"] += 2
        log.append("Pontifex Maximus: le tue altre abilita' sono di nuovo pronte, e ottieni +2 Armatura e +2 Resistenza Mentale fino a fine combattimento.")
        return 0, 0, log, False

    if ability_key == "esperto_saccheggiatore":
        _set_cooldown(run, ability_key)
        resource = random.choices(["oro", "legname", "pietra"], weights=[60, 20, 20])[0]
        run["treasure"][resource] = run["treasure"].get(resource, 0) + 5
        log.append("Esperto Saccheggiatore: trovi +5 %s." % resource)
        return 0, 0, log, False

    if ability_key == "acuto_osservatore":
        _set_cooldown(run, ability_key)
        combat["raffica_potenziata"] = True
        log.append("Acuto Osservatore: individui i punti debili del nemico — la prossima Raffica Micidiale sara' devastante.")
        return 0, 0, log, False

    if ability_key == "raffica_micidiale":
        _set_cooldown(run, ability_key)
        potenziata = combat.get("raffica_potenziata", False)
        combat["raffica_potenziata"] = False
        dmg = 0
        for _ in range(3):
            dmg += random.randint(5, 7) if potenziata else 2
        if potenziata:
            log.append("Raffica Micidiale (potenziata): 3 colpi infliggono %d danni totali." % dmg)
        else:
            log.append("Raffica Micidiale: 3 colpi infliggono %d danni totali." % dmg)
        return dmg, 0, log, False

    if ability_key == "ogni_uomo_ha_un_prezzo":
        _set_cooldown(run, ability_key)
        timore_dmg = random.randint(4, 5)
        log.append("Ogni Uomo ha un Prezzo: infliggi %d danni al Timore del nemico." % timore_dmg)
        return 0, timore_dmg, log, False

    if ability_key == "azzardo_economico":
        _set_cooldown(run, ability_key)
        oro_speso = run["treasure"].get("oro", 0)
        run["treasure"]["oro"] = 0
        timore_dmg = oro_speso * 2
        if oro_speso > 0:
            log.append("Azzardo Economico: spendi %d Oro, infliggendo %d danni al Timore del nemico." % (oro_speso, timore_dmg))
        else:
            log.append("Azzardo Economico: non hai Oro da spendere, il gesto e' vano.")
        return 0, timore_dmg, log, False

    if ability_key == "cani_della_guerra":
        _set_cooldown(run, ability_key)
        for _ in range(3):
            run["seguito"].append({"type": "mercenario_temporaneo", "alive": True, "charges": None})
        log.append("Cani della Guerra: 3 mercenari si uniscono a te per questo combattimento.")
        return 0, 0, log, False

    if ability_key == "colpo_di_lazo":
        _set_cooldown(run, ability_key)
        dmg = random.randint(4, 7) + run["leader"]["dmg_bonus"] + run["temp_buffs"]["dmg"] + combat.get("combat_dmg_bonus", 0)
        log.append("Colpo di Lazo: infliggi %d danni." % dmg)
        return dmg, 0, log, False

    if ability_key == "parole_di_scherno":
        _set_cooldown(run, ability_key)
        timore_dmg = random.randint(3, 5)
        combat["enemy_weaken_turns"] = 2
        combat["enemy_weaken_amount"] = 3
        log.append("Parole di Scherno: infliggi %d danni al Timore del nemico, e il suo prossimo danno fisico sara' ridotto." % timore_dmg)
        return 0, timore_dmg, log, False

    if ability_key == "picconata_fortunata":
        _set_cooldown(run, ability_key)
        dmg = random.randint(6, 9) + run["leader"]["dmg_bonus"] + run["temp_buffs"]["dmg"] + combat.get("combat_dmg_bonus", 0)
        if random.random() < 0.15:
            dmg *= 2
            log.append("Picconata Fortunata: colpo critico! Infliggi %d danni." % dmg)
        else:
            log.append("Picconata Fortunata: infliggi %d danni." % dmg)
        return dmg, 0, log, False

    if ability_key == "indovinelli_oscurita":
        _set_cooldown(run, ability_key)
        dmg_nemico = 0
        dmg_leader_raw = 0
        successi = 0
        for _ in range(3):
            if random.random() < 0.5:
                dmg_nemico += 8
                successi += 1
            else:
                dmg_leader_raw += 4
        dmg_leader = 0
        if dmg_leader_raw > 0:
            residuo = dmg_leader_raw
            shield = combat.get("shield_reduction", 0)
            if shield and residuo > 0:
                residuo = max(0, residuo - shield)
                combat["shield_reduction"] = 0
                log.append("Lo scudo di Formazione Difensiva attutisce il colpo.")
            pool = combat.get("shield_physical_pool", 0)
            if pool and residuo > 0:
                assorbito = min(pool, residuo)
                residuo -= assorbito
                combat["shield_physical_pool"] -= assorbito
                log.append("Lo Scudo Magico assorbe %d danni fisici (%d rimasti nel serbatoio)." % (assorbito, combat["shield_physical_pool"]))
            final_armor = _effective_defense(run, combat, "armor")
            dmg_leader = max(1, residuo - final_armor) if residuo > 0 else 0
            if dmg_leader > 0:
                run["leader"]["pv"] -= dmg_leader
        log.append("Indovinelli nell'Oscurità: %d successi su 3 — infliggi %d danni%s." %
                    (successi, dmg_nemico, (" e subisci %d danni" % dmg_leader) if dmg_leader else ""))
        return dmg_nemico, 0, log, False

    if ability_key == "scorciatoia":
        run["used_once_abilities"].append(ability_key)
        log.append("Scorciatoia: eviti del tutto questa stanza.")
        return 0, 0, log, "skip"

    # fallback di sicurezza (non dovrebbe accadere)
    log.append("Non succede nulla di rilevante.")
    return 0, 0, log, False


def resolve_combat_round(run, action_key):
    """Risolve un intero round di combattimento con l'azione scelta dal giocatore.
    Ritorna lo stato ('in_corso' | 'vittoria' | 'sconfitta_morte' | 'sconfitta_timore' | 'fuga')."""
    combat = run["combat"]
    log = []

    if action_key == "attacco_fisico":
        dmg = _leader_dmg(run)
        timore_dmg = 0
        escape = False
        ab_log = None
        if run["class"] == "Esploratore":
            combat["shield_physical_pool"] += 2
    else:
        dmg, timore_dmg, ab_log, escape = _apply_ability_action(run, action_key)
        if not escape and dmg > 0:
            bonus_abilita = run.get("equip_flags", {}).get("dmg_abilita", 0)
            if bonus_abilita:
                dmg += bonus_abilita
                ab_log.append("Il Bastone Runico infonde ulteriore potere: +%d danno." % bonus_abilita)

    if not escape and dmg > 0 and run["combat"].get("double_next_attack"):
        dmg = round(dmg * 1.4)
        run["combat"]["double_next_attack"] = False
        if ab_log is not None:
            ab_log.append("Il fragore di Grido di Guerra potenzia il colpo (+40%)!")
        else:
            log.append("Il fragore di Grido di Guerra potenzia il colpo (+40%)!")

    if not escape and run["class"] == "Generale" and dmg > 0:
        if run["leader"]["pv"] < run["leader"]["pv_max"] * 0.5 or run["leader"]["timore"] < run["leader"]["timore_max"] * 0.5:
            dmg += 3
            msg = "Ira Funesta: la disperazione acuisce il colpo, +3 danni."
            if ab_log is not None:
                ab_log.append(msg)
            else:
                log.append(msg)

    if not escape and run["class"] == "Esploratore" and combat.get("tier") == "boss" and (dmg > 0 or timore_dmg > 0):
        if random.random() < 0.10:
            if dmg > 0:
                dmg *= 2
            if timore_dmg > 0:
                timore_dmg *= 2
            msg = "Sforzo Adrenalinico: colpo critico contro un avversario così pericoloso!"
            if ab_log is not None:
                ab_log.append(msg)
            else:
                log.append(msg)

    vessilliferi = sum(1 for m in run["seguito"] if m["alive"] and m["type"] == "vessillifero")
    if not escape and vessilliferi and dmg > 0:
        dmg += vessilliferi
        msg = "Vessillifero: lo stendardo issato incita il colpo, +%d danno." % vessilliferi
        if ab_log is not None:
            ab_log.append(msg)
        else:
            log.append(msg)

    if not escape and combat.get("player_dmg_debuff_turns", 0) > 0 and dmg > 0:
        riduzione = combat.get("player_dmg_debuff", 0)
        dmg = max(0, dmg - riduzione)
        msg = "Ruggito: l'intimidazione ti indebolisce il colpo, -%d danni." % riduzione
        if ab_log is not None:
            ab_log.append(msg)
        else:
            log.append(msg)

    # iniziativa: chi agisce per primo nel round (l'arciere favorisce il leader; un nemico
    # rallentato agisce sempre per ultimo, a prescindere da tutto il resto)
    has_arciere = any(m["alive"] and m["type"] == "arciere" for m in run["seguito"])
    if combat.get("enemy_slowed_turns", 0) > 0:
        leader_first = True
        combat["enemy_slowed_turns"] -= 1
    else:
        leader_first_chance = 0.75 if has_arciere else 0.5
        leader_first = random.random() < leader_first_chance

    if not escape and leader_first and has_arciere and dmg > 0:
        dmg += gd.ARCIERE_DMG_BONUS
        msg = "Arciere: una scarica di frecce di supporto aggiunge +%d danni al tuo colpo." % gd.ARCIERE_DMG_BONUS
        if ab_log is not None:
            ab_log.append(msg)
        else:
            log.append(msg)

    if action_key == "attacco_fisico":
        if run["class"] == "Esploratore":
            log.append("Attacco Preventivo: infliggi %d danni e guadagni 2 scudo fisico." % dmg)
        else:
            log.append("Attacchi: infliggi %d danni." % dmg)
    else:
        log.extend(ab_log)

    if escape == "skip":
        run["log"] = log
        run["combat"] = None
        return "salta_stanza"

    if escape:
        run["log"] = log
        run["combat"] = None
        return "fuga"

    for k in list(run["cooldowns"].keys()):
        if run["cooldowns"][k] > 0:
            run["cooldowns"][k] -= 1

    if combat.get("diaulo_signore_cd", 0) > 0:
        combat["diaulo_signore_cd"] -= 1

    if combat.get("uomorsomaiale_sventrare_cd", 0) > 0:
        combat["uomorsomaiale_sventrare_cd"] -= 1
    if combat.get("uomorsomaiale_ruggito_cd", 0) > 0:
        combat["uomorsomaiale_ruggito_cd"] -= 1
    if combat.get("player_dmg_debuff_turns", 0) > 0:
        combat["player_dmg_debuff_turns"] -= 1
        if combat["player_dmg_debuff_turns"] <= 0:
            combat["player_dmg_debuff"] = 0

    if combat.get("enemy_buff_turns", 0) > 0:
        combat["enemy_buff_turns"] -= 1
        if combat["enemy_buff_turns"] <= 0:
            combat["enemy_buff_stat"] = None
    if combat.get("player_debuff_turns", 0) > 0:
        combat["player_debuff_turns"] -= 1
        if combat["player_debuff_turns"] <= 0:
            combat["player_debuff_stat"] = None

    if combat.get("burn_turns", 0) > 0:
        combat["enemy_pv"] -= combat["burn_dmg"]
        combat["burn_turns"] -= 1
        log.append("Le fiamme infliggono %d danni al nemico." % combat["burn_dmg"])
        if combat["enemy_pv"] <= 0 or combat["enemy_timore"] <= 0:
            run["log"] = log
            return "vittoria"

    if combat.get("enemy_bleed_turns", 0) > 0:
        enemy_bleed_dmg = combat.get("enemy_bleed_dmg", 0)
        enemy_kind = combat.get("enemy_bleed_kind") or "sanguinamento"
        enemy_verbo = "Il veleno nel nemico" if enemy_kind == "veleno" else "Il sanguinamento del nemico"
        combat["enemy_pv"] -= enemy_bleed_dmg
        log.append("%s si aggrava: perde %d PV." % (enemy_verbo, enemy_bleed_dmg))
        combat["enemy_bleed_turns"] -= 1
        if combat["enemy_bleed_turns"] <= 0:
            combat["enemy_bleed_kind"] = None
        if combat["enemy_pv"] <= 0 or combat["enemy_timore"] <= 0:
            run["log"] = log
            return "vittoria"

    if combat.get("player_bleed_turns", 0) > 0:
        bleed_dmg = combat.get("player_bleed_dmg", 0)
        kind = combat.get("player_bleed_kind") or "sanguinamento"
        verbo = "Il veleno" if kind == "veleno" else "Il sanguinamento"
        if combat.get("player_bleed_target") == "timore":
            run["leader"]["timore"] -= bleed_dmg
            log.append("%s logora la tua psiche: perdi %d Timore." % (verbo, bleed_dmg))
        else:
            run["leader"]["pv"] -= bleed_dmg
            log.append("%s ti costa %d Vita." % (verbo, bleed_dmg))
        combat["player_bleed_turns"] -= 1
        if combat["player_bleed_turns"] <= 0:
            combat["player_bleed_target"] = None
            combat["player_bleed_kind"] = None
        outcome = _check_defeat(run, log)
        if outcome:
            return outcome

    def apply_leader_damage_to_enemy():
        enemy_armor = combat.get("enemy_armor", 0)
        enemy_mres = combat.get("enemy_mres", 0)
        if combat.get("enemy_buff_turns", 0) > 0:
            if combat.get("enemy_buff_stat") == "armor":
                enemy_armor += gd.ENEMY_BUFF_AMOUNT
            elif combat.get("enemy_buff_stat") == "mres":
                enemy_mres += gd.ENEMY_BUFF_AMOUNT

        flags = run.get("equip_flags", {})
        penetrazione = flags.get("penetrazione_armor", 0)
        if penetrazione:
            enemy_armor = max(0, enemy_armor - penetrazione)

        effective_dmg = dmg
        bonus_timore = 0
        crit_bonus_timore = 0
        if effective_dmg > 0:
            ignora_pct = flags.get("ignora_difese_pct", 0)
            if ignora_pct and random.random() < ignora_pct:
                enemy_armor = 0
                log.append("La Lama del Giuramento Spezzato trova una falla e ignora del tutto la difesa nemica!")

            stordisce_pct = flags.get("stordisce_pct", 0)
            if stordisce_pct and random.random() < stordisce_pct:
                combat["enemy_stunned"] = combat.get("enemy_stunned", 0) + 1
                log.append("Il Martello dei Compagni stordisce il nemico per 1 turno!")

            bonus_timore += flags.get("dmg_timore_nemico", 0)

            if flags.get("critico_colpisce_timore") and random.random() < gd.ITEM_CRIT_CHANCE:
                crit_bonus_timore = effective_dmg
                effective_dmg *= 2
                log.append("Spezzacielo strappa un colpo critico, che incrina corpo e Timore del nemico!")

        phys = max(1, effective_dmg - enemy_armor) if effective_dmg > 0 else 0
        total_timore_dmg = timore_dmg + bonus_timore + crit_bonus_timore
        fear = max(1, total_timore_dmg - enemy_mres) if total_timore_dmg > 0 else 0
        combat["enemy_pv"] -= phys
        combat["enemy_timore"] -= fear

        if phys > 0 and combat.get("enemy_bleed_turns", 0) <= 0:
            proc_kind = "sanguinamento" if flags.get("sanguinamento_su_colpo") else ("veleno" if flags.get("veleno_su_colpo") else None)
            if proc_kind and random.random() < gd.ITEM_ENEMY_DOT_CHANCE:
                combat["enemy_bleed_turns"] = gd.ITEM_ENEMY_DOT_TURNS
                combat["enemy_bleed_dmg"] = random.randint(*gd.ITEM_ENEMY_DOT_DMG)
                combat["enemy_bleed_kind"] = proc_kind
                if proc_kind == "veleno":
                    log.append("Il Plettro del Destino incide: il nemico è avvelenato, perderà %d PV a turno per %d turni." %
                                (combat["enemy_bleed_dmg"], gd.ITEM_ENEMY_DOT_TURNS))
                else:
                    log.append("La Zanna dell'Uomorsomaiale morde ancora: il nemico sanguina, perdendo %d PV a turno per %d turni." %
                                (combat["enemy_bleed_dmg"], gd.ITEM_ENEMY_DOT_TURNS))

        if phys > 0:
            shield_chance = flags.get("shield_pv_su_colpo_chance", 0)
            shield_amount = flags.get("shield_pv_su_colpo_amount", 0)
            if shield_chance and shield_amount and random.random() < shield_chance:
                combat["shield_physical_pool"] = combat.get("shield_physical_pool", 0) + shield_amount
                log.append("Lo Spadone Lungo di Ser Gowain vibra: guadagni %d scudo Vita." % shield_amount)

    def enemy_turn():
        if combat.get("enemy_stunned", 0) > 0:
            combat["enemy_stunned"] -= 1
            log.append("Il nemico è ancora stordito e non riesce ad agire.")
            return

        if combat.get("evasion_turns", 0) > 0:
            combat["evasion_turns"] -= 1
            if random.random() < combat.get("evasion_chance", 0):
                log.append("Copie Illusorie: eviti completamente il colpo del nemico.")
                return

        if "agilita_felina" in run.get("equipped_abilities", []) and random.random() < 0.2:
            log.append("Agilità Felina: eviti agilmente il colpo del nemico.")
            return

        if combat.get("special_boss") == "il_diaulo":
            _il_diaulo_turn(run, combat, log)
            return

        if combat.get("special_boss") == "uomorsomaiale":
            _uomorsomaiale_turn(run, combat, log)
            return

        # purificatore/sciamano: cura passiva a inizio del turno di scambio
        heal_pv = 0
        heal_timore = 0
        if any(m["alive"] and m["type"] == "purificatore" for m in run["seguito"]):
            heal_pv += gd.PURIFICATORE_HEAL
        if any(m["alive"] and m["type"] == "sciamano" for m in run["seguito"]):
            heal_timore += gd.SCIAMANO_HEAL
        if has_ability(run, "bastione_della_fede") and "bastione_della_fede" in run.get("equipped_abilities", []):
            heal_pv += 2
        if run["class"] == "Diplomatico":
            vive = sum(1 for m in run["seguito"] if m["alive"])
            if vive:
                heal_pv += vive
                heal_timore += vive
        if heal_pv > 0:
            run["leader"]["pv"] = min(run["leader"]["pv_max"], run["leader"]["pv"] + heal_pv)
            log.append("Cura passiva: recuperi %d Vita." % heal_pv)
        if heal_timore > 0:
            run["leader"]["timore"] = min(run["leader"]["timore_max"], run["leader"]["timore"] + heal_timore)
            log.append("Il tuo Seguito ti infonde %d Timore." % heal_timore)

        # martello/ariete: non si consumano mai, colpiscono il nemico a ogni round
        martelli = sum(1 for m in run["seguito"] if m["alive"] and m["type"] == "martello")
        arieti = sum(1 for m in run["seguito"] if m["alive"] and m["type"] == "ariete")
        enemy_armor_now = combat.get("enemy_armor", 0)
        enemy_mres_now = combat.get("enemy_mres", 0)
        if combat.get("enemy_buff_turns", 0) > 0:
            if combat.get("enemy_buff_stat") == "armor":
                enemy_armor_now += gd.ENEMY_BUFF_AMOUNT
            elif combat.get("enemy_buff_stat") == "mres":
                enemy_mres_now += gd.ENEMY_BUFF_AMOUNT
        if martelli:
            colpo = max(1, martelli * gd.MARTELLO_COUNTER_DMG - enemy_armor_now)
            combat["enemy_pv"] -= colpo
            log.append("I Compagni del Martello colpiscono per %d danni." % colpo)
        if arieti:
            colpo = max(1, arieti * gd.ARIETE_COUNTER_DMG - enemy_mres_now)
            combat["enemy_timore"] -= colpo
            log.append("L'Ariete incalza il Timore nemico per %d danni." % colpo)
        if (martelli or arieti) and (combat["enemy_pv"] <= 0 or combat["enemy_timore"] <= 0):
            return

        archetype = combat.get("archetype", "equilibrato")

        # "Si Riprende": il nemico ferito puo' curarsi invece di attaccare
        if combat["enemy_pv"] < combat["enemy_pv_max"] * 0.5 and random.random() < gd.ENEMY_HEAL_CHANCE:
            heal = random.randint(gd.ENEMY_HEAL_MIN, gd.ENEMY_HEAL_MAX)
            combat["enemy_pv"] = min(combat["enemy_pv_max"], combat["enemy_pv"] + heal)
            log.append("%s si riprende, recuperando %d PV." % (combat["name"], heal))
            return

        # Buff: rafforza la propria difesa per qualche turno (mai cumulabile)
        if combat.get("enemy_buff_turns", 0) <= 0 and random.random() < gd.ENEMY_BUFF_CHANCE:
            stat = {"fisico": "armor", "mentale": "mres"}.get(archetype) or random.choice(["armor", "mres"])
            combat["enemy_buff_stat"] = stat
            combat["enemy_buff_turns"] = gd.ENEMY_BUFF_TURNS
            label = "Armatura" if stat == "armor" else "Res. Mentale"
            log.append("%s si rafforza: +%d %s per %d turni." % (combat["name"], gd.ENEMY_BUFF_AMOUNT, label, gd.ENEMY_BUFF_TURNS))
            return

        # Debuff: indebolisce una tua statistica difensiva per qualche turno (mai cumulabile)
        if combat.get("player_debuff_turns", 0) <= 0 and random.random() < gd.ENEMY_DEBUFF_CHANCE:
            stat = {"fisico": "armor", "mentale": "mres"}.get(archetype) or random.choice(["armor", "mres"])
            combat["player_debuff_stat"] = stat
            combat["player_debuff_turns"] = gd.ENEMY_DEBUFF_TURNS
            label = "Armatura" if stat == "armor" else "Res. Mentale"
            log.append("%s ti indebolisce: -%d %s per %d turni." % (combat["name"], gd.ENEMY_DEBUFF_AMOUNT, label, gd.ENEMY_DEBUFF_TURNS))
            return

        # Sanguinamento: danno nel tempo, ai PV o al Timore a seconda dell'archetipo
        if combat.get("player_bleed_turns", 0) <= 0 and random.random() < gd.ENEMY_BLEED_CHANCE:
            kind = combat.get("dot_kind", "sanguinamento")
            if kind == "sanguinamento" and run.get("equip_flags", {}).get("immunita_sanguinamento"):
                log.append("L'Elmo del Primo Re di Karag-Duraz protegge dalla ferita: non sanguini.")
                return
            target = {"fisico": "pv", "mentale": "timore"}.get(archetype) or random.choice(["pv", "timore"])
            is_boss = combat.get("tier") == "boss"
            bleed_dmg = gd.ENEMY_BLEED_DMG_BOSS if is_boss else random.randint(*gd.ENEMY_BLEED_DMG_NORMAL)
            combat["player_bleed_turns"] = gd.ENEMY_BLEED_TURNS
            combat["player_bleed_dmg"] = bleed_dmg
            combat["player_bleed_target"] = target
            combat["player_bleed_kind"] = kind
            nome_stat = "Vita" if target == "pv" else "Timore"
            if kind == "veleno":
                log.append("%s ti morde: sei avvelenato, perderai %d %s a turno per %d turni." %
                            (combat["name"], bleed_dmg, nome_stat, gd.ENEMY_BLEED_TURNS))
            else:
                log.append("%s ti ferisce in profondità: sanguini, perdendo %d %s a turno per %d turni." %
                            (combat["name"], bleed_dmg, nome_stat, gd.ENEMY_BLEED_TURNS))
            return

        fear_chance = combat["fear_chance"]
        if any(m["alive"] and m["type"] == "bardo" for m in run["seguito"]):
            fear_chance = max(0.0, fear_chance - gd.BARDO_FEAR_REDUCTION)
        is_fear = random.random() < fear_chance
        if is_fear:
            if not combat.get("first_fear_hit_taken", False):
                combat["first_fear_hit_taken"] = True
                if run.get("equip_flags", {}).get("immunita_primo_pauroso"):
                    log.append("Il Velo della Nébrahil ti protegge dal primo colpo che minaccia il tuo Timore.")
                    return
            base = random.randint(*combat["fear_dmg"]) if combat["fear_dmg"][1] > 0 else 0
            shield = combat.get("shield_reduction", 0)
            if shield and base > 0:
                base = max(0, base - shield)
                combat["shield_reduction"] = 0
                log.append("Lo scudo di Formazione Difensiva attutisce il colpo.")
            pool = combat.get("shield_timore_pool", 0)
            if pool and base > 0:
                assorbito = min(pool, base)
                base -= assorbito
                combat["shield_timore_pool"] -= assorbito
                log.append("Lo Scudo Magico assorbe %d danni al Timore (%d rimasti nel serbatoio)." % (assorbito, combat["shield_timore_pool"]))
            total_mres = _effective_defense(run, combat, "mres")
            reduced = max(1 if base > 0 else 0, base - total_mres)
            run["leader"]["timore"] -= reduced
            log.append("Il nemico attacca la tua psiche: perdi %d Timore." % reduced)
        else:
            base = random.randint(*combat["dmg"])
            if combat.get("enemy_weaken_turns", 0) > 0:
                base = max(0, base - combat.get("enemy_weaken_amount", 0))
                combat["enemy_weaken_turns"] -= 1
                log.append("Il nemico, schernito, colpisce con meno forza.")
            # Passo Leggero: primo colpo fisico del combattimento sempre schivato
            if has_ability(run, "passo_leggero") and not combat["first_hit_taken"]:
                combat["first_hit_taken"] = True
                log.append("Passo Leggero: schivi completamente il colpo.")
                return
            combat["first_hit_taken"] = True
            absorbed, residuo, seg_log = _seguito_absorb(run, base)
            log.extend(seg_log)
            if not absorbed or residuo > 0:
                shield = combat.get("shield_reduction", 0)
                if shield and residuo > 0:
                    residuo = max(0, residuo - shield)
                    combat["shield_reduction"] = 0
                    log.append("Lo scudo di Formazione Difensiva attutisce il colpo.")
                pool = combat.get("shield_physical_pool", 0)
                if pool and residuo > 0:
                    assorbito = min(pool, residuo)
                    residuo -= assorbito
                    combat["shield_physical_pool"] -= assorbito
                    log.append("Lo Scudo Magico assorbe %d danni fisici (%d rimasti nel serbatoio)." % (assorbito, combat["shield_physical_pool"]))
                final_armor = _effective_defense(run, combat, "armor")
                dmg_to_leader = max(1, residuo - final_armor) if residuo > 0 else 0
                if dmg_to_leader > 0:
                    run["leader"]["pv"] -= dmg_to_leader
                    log.append("Subisci %d danni fisici." % dmg_to_leader)
                    _maybe_reflect_fixed(run, combat, log)

    if leader_first:
        apply_leader_damage_to_enemy()
        if combat["enemy_pv"] <= 0 or combat["enemy_timore"] <= 0:
            run["log"] = log
            return "vittoria"
        log.append(ROUND_BEAT_MARKER)
        enemy_turn()
        if combat["enemy_pv"] <= 0 or combat["enemy_timore"] <= 0:
            run["log"] = log
            return "vittoria"
    else:
        enemy_turn()
        if combat["enemy_pv"] <= 0 or combat["enemy_timore"] <= 0:
            run["log"] = log
            return "vittoria"
        # controlli di sconfitta prima che il leader possa agire
        outcome = _check_defeat(run, log)
        if outcome:
            return outcome
        log.append(ROUND_BEAT_MARKER)
        apply_leader_damage_to_enemy()
        if combat["enemy_pv"] <= 0 or combat["enemy_timore"] <= 0:
            run["log"] = log
            return "vittoria"

    _check_egida_trigger(run, combat, log)

    outcome = _check_defeat(run, log)
    if outcome:
        return outcome

    combat["round"] += 1
    run["log"] = log
    if combat["round"] > 30:
        # timeout di sicurezza: il nemico si dissolve, vittoria parziale
        run["log"].append("Il nemico si dissolve nell'ombra, esausto quanto voi.")
        return "vittoria"
    return "in_corso"


def _check_defeat(run, log):
    equipped = run.get("equipped_abilities", [])
    protezione_arcana = "protezione_arcana" in equipped and not run["protezione_arcana_used"]
    omelia_salvezza = "omelia_della_salvezza" in equipped and not run["omelia_salvezza_used"]

    if run["leader"]["pv"] <= 0 or run["leader"]["timore"] <= 0:
        if protezione_arcana:
            run["protezione_arcana_used"] = True
            run["leader"]["pv"] = run["leader"]["pv_max"] // 3
            run["leader"]["timore"] = run["leader"]["timore_max"] // 3
            log.append("Protezione Arcana: invece di cadere, ritrovi Vita e Timore pari a un terzo del massimo.")
            run["log"] = log
            return None
        if run["leader"]["pv"] <= 0 and omelia_salvezza:
            run["omelia_salvezza_used"] = True
            run["leader"]["pv"] = 1
            log.append("Omelia della Salvezza: ignori il colpo fatale e torni a 1 Vita.")
            run["log"] = log
            return None
        if run["leader"]["pv"] <= 0:
            run["log"] = log
            return "sconfitta_morte"
        run["log"] = log
        return "sconfitta_timore"
    return None


def cleanup_temp_mercenaries(run):
    """Rimuove i mercenari temporanei di 'Cani della Guerra' a fine combattimento —
    restano solo per la durata dello scontro in cui sono stati evocati."""
    run["seguito"] = [m for m in run["seguito"] if m["type"] != "mercenario_temporaneo"]


# ─── LOOT ─────────────────────────────────────────────────────────────────
def roll_loot(run, is_boss):
    resource = random.choice(gd.RESOURCE_TYPES)
    equipped = run.get("equipped_abilities", [])
    raddoppio = "drago_della_finanza" in equipped or "mappatore_esperto" in equipped
    if resource == "gemme":
        amount = 2 if is_boss else 1  # risorsa rara: fissa (non scalata da livello o raddoppi), un po' più generosa contro i boss
    else:
        lo, hi = gd.BOSS_LOOT_AMOUNT if is_boss else gd.NORMAL_LOOT_AMOUNT
        amount = random.randint(lo, hi)
        if getattr(gd, "LOOT_LEVEL_SCALING", False):
            amount = round(amount * gd.level_factor(run["level"]))
        if run["class"] == "Esploratore" and run["level"] >= 5:
            amount = int(amount * 1.5)
        if raddoppio:
            amount *= 2
    run["treasure"][resource] = run["treasure"].get(resource, 0) + amount
    log = ["Bottino: +%d %s." % (amount, resource)]

    if run["class"] == "Mago" and random.random() < 0.30:
        run["treasure"]["gemme"] = run["treasure"].get("gemme", 0) + 1
        log.append("Esperto Catalogatore: trovi anche 1 Gemma in più tra le spoglie.")

    guaranteed_gold = gd.GUARANTEED_GOLD_BOSS if is_boss else gd.GUARANTEED_GOLD_NORMAL
    if getattr(gd, "LOOT_LEVEL_SCALING", False):
        guaranteed_gold = round(guaranteed_gold * gd.level_factor(run["level"]))
    if raddoppio:
        guaranteed_gold *= 2
    if resource != "oro":
        run["treasure"]["oro"] = run["treasure"].get("oro", 0) + guaranteed_gold
        log.append("Recuperi anche %d Oro dalle spoglie del nemico." % guaranteed_gold)

    item_id = None
    exclusive_item = gd.BOSS_EXCLUSIVE_ITEMS.get(run.get("special_boss_fought")) if is_boss else None
    if exclusive_item:
        # drop garantito al 100%, non passa dal tiro a probabilita'/rarita' qui sotto:
        # e' il trofeo esclusivo di QUEL boss, non un oggetto tra tanti.
        item_id = exclusive_item
        log.append("Un oggetto raro attira la tua attenzione: %s!" % gd.ITEMS[item_id]["name"])
    else:
        drop_chance = gd.BOSS_ITEM_DROP_CHANCE if is_boss else gd.NORMAL_ITEM_DROP_CHANCE
        if random.random() < drop_chance:
            weights = gd.BOSS_DROP_RARITY_WEIGHTS if is_boss else gd.NORMAL_DROP_RARITY_WEIGHTS
            rarity = random.choices(list(weights.keys()), weights=list(weights.values()))[0]
            candidates = [k for k, v in gd.ITEMS.items() if v["rarity"] == rarity and k not in gd.BOSS_EXCLUSIVE_ITEMS.values()]
            if candidates:
                item_id = random.choice(candidates)
                log.append("Un oggetto raro attira la tua attenzione: %s!" % gd.ITEMS[item_id]["name"])
    return log, item_id


# ─── STANZE NON DI COMBATTIMENTO ─────────────────────────────────────────
def _roll_mystery_item_drop(run):
    """Estrae un oggetto casuale (stesse rarita' pesate del bottino normale) e lo mette
    in coda ai drop della run, applicato a fine spedizione come gli altri."""
    weights = gd.NORMAL_DROP_RARITY_WEIGHTS
    rarity = random.choices(list(weights.keys()), weights=list(weights.values()))[0]
    candidates = [k for k, v in gd.ITEMS.items() if v["rarity"] == rarity]
    if not candidates:
        return None
    item_id = random.choice(candidates)
    run.setdefault("pending_drops", []).append(item_id)
    return item_id


def resolve_mystery_event(run, event_key, choice_key):
    """Risolve la scelta del giocatore in un evento della Stanza Misteriosa. Ritorna
    il log da mostrare; alcuni effetti (veleno, debuff) restano "in sospeso" e si
    manifestano solo all'inizio del prossimo combattimento (vedi start_combat)."""
    log = []
    leader = run["leader"]

    if event_key == "calice":
        if choice_key == "bevi":
            if random.random() < 0.5:
                leader["pv"] = leader["pv_max"]
                leader["timore"] = leader["timore_max"]
                log.append("Il liquido ha un sapore dolce: ti senti completamente rigenerato.")
            else:
                run["pending_effects"].append({"type": "veleno", "dmg": gd.MYSTERY_VELENO_DMG, "turns": gd.MYSTERY_VELENO_TURNI})
                log.append("Il liquido brucia in gola: qualcosa di velenoso si è insinuato in te, e si manifesterà nel prossimo scontro.")
        elif choice_key == "rovescia":
            log.append("Rovesci il calice: il liquido sparisce assorbito dalla pietra, senza alcun effetto.")
        else:
            log.append("Ignori il calice e trovi la via d'uscita.")

    elif event_key == "specchio":
        if choice_key == "distruggi":
            if random.random() < 0.7:
                stat = random.choice(["dmg", "armor", "mres"])
                run["temp_buffs"][stat] = run["temp_buffs"].get(stat, 0) + 1
                label = {"dmg": "Danno Fisico", "armor": "Armatura", "mres": "Res. Mentale"}[stat]
                log.append("Lo specchio esplode in schegge di luce: +1 %s per il resto della run." % label)
            else:
                leader["pv"] = max(0, leader["pv"] - gd.MYSTERY_SPECCHIO_DANNO)
                log.append("Le schegge ti feriscono: -%d PV." % gd.MYSTERY_SPECCHIO_DANNO)
        elif choice_key == "fissa":
            if random.random() < 0.6:
                leader["timore"] = min(leader["timore_max"], leader["timore"] + gd.MYSTERY_TIMORE_PICCOLO)
                log.append("Il tuo riflesso ti restituisce calma: +%d Timore." % gd.MYSTERY_TIMORE_PICCOLO)
            else:
                leader["timore"] = max(0, leader["timore"] - gd.MYSTERY_TIMORE_PICCOLO)
                log.append("Il riflesso distorto ti terrorizza: -%d Timore." % gd.MYSTERY_TIMORE_PICCOLO)
        else:
            log.append("Ignori lo specchio e prosegui.")

    elif event_key == "cripta":
        if choice_key == "forza_pv":
            leader["pv"] = max(0, leader["pv"] - gd.MYSTERY_CRIPTA_COSTO)
            item_id = _roll_mystery_item_drop(run)
            log.append("Forzi la cripta a costo di %d PV: dentro trovi %s!" % (gd.MYSTERY_CRIPTA_COSTO, gd.ITEMS[item_id]["name"] if item_id else "qualcosa"))
        elif choice_key == "forza_timore":
            leader["timore"] = max(0, leader["timore"] - gd.MYSTERY_CRIPTA_COSTO)
            item_id = _roll_mystery_item_drop(run)
            log.append("Forzi la cripta a costo di %d Timore: dentro trovi %s!" % (gd.MYSTERY_CRIPTA_COSTO, gd.ITEMS[item_id]["name"] if item_id else "qualcosa"))
        else:
            log.append("Lasci la cripta sigillata.")

    elif event_key == "mercante":
        if choice_key == "accetta":
            posseduti = [r for r in gd.RESOURCE_TYPES if run["treasure"].get(r, 0) > 0]
            if posseduti:
                risorsa = random.choice(posseduti)
                costo = min(gd.MYSTERY_MERCANTE_RISORSA_COSTO, run["treasure"][risorsa])
                run["treasure"][risorsa] -= costo
                item_id = _roll_mystery_item_drop(run)
                log.append("Cedi %d %s in cambio di %s." % (costo, risorsa, gd.ITEMS[item_id]["name"] if item_id else "un oggetto misterioso"))
            else:
                item_id = _roll_mystery_item_drop(run)
                log.append("Non hai nulla da offrire, ma il mercante ti dona comunque %s, con un sorriso enigmatico." % (gd.ITEMS[item_id]["name"] if item_id else "un oggetto"))
        else:
            log.append("Rifiuti lo scambio e il mercante svanisce nell'ombra.")

    elif event_key == "sussurro":
        if choice_key == "resisti":
            leader["timore"] = max(0, leader["timore"] - gd.MYSTERY_SUSSURRO_TIMORE_COSTO)
            log.append("Resisti al sussurro, ma ti costa comunque %d Timore." % gd.MYSTERY_SUSSURRO_TIMORE_COSTO)
        else:
            if random.random() < 0.5:
                run["bonus_xp"] = run.get("bonus_xp", 0) + gd.MYSTERY_SUSSURRO_XP_BONUS
                log.append("Il sussurro ti rivela qualcosa di utile: +%d PE a fine spedizione." % gd.MYSTERY_SUSSURRO_XP_BONUS)
            else:
                leader["timore"] = max(0, leader["timore"] - gd.MYSTERY_SUSSURRO_TIMORE_GRAVE)
                log.append("Il sussurro trova la tua paura più profonda: -%d Timore." % gd.MYSTERY_SUSSURRO_TIMORE_GRAVE)

    elif event_key == "altare":
        if choice_key == "offri" and run["treasure"].get("oro", 0) >= gd.MYSTERY_ALTARE_COSTO_ORO:
            run["treasure"]["oro"] -= gd.MYSTERY_ALTARE_COSTO_ORO
            leader["pv"] = min(leader["pv_max"], leader["pv"] + gd.MYSTERY_ALTARE_CURA)
            log.append("Offri %d Oro all'altare: recuperi %d PV." % (gd.MYSTERY_ALTARE_COSTO_ORO, gd.MYSTERY_ALTARE_CURA))
        elif choice_key == "offri":
            log.append("Non hai abbastanza Oro da offrire: l'altare resta silenzioso.")
        else:
            log.append("Non offri nulla e ti allontani dall'altare.")

    elif event_key == "catene":
        if choice_key == "libera":
            if random.random() < 0.7:
                run["seguito"].append({"type": "mercenario", "alive": True, "charges": None})
                log.append("Liberi il prigioniero: si unisce a te come mercenario per questa spedizione.")
            else:
                leader["timore"] = max(0, leader["timore"] - gd.MYSTERY_CATENE_TIMORE_TRAPPOLA)
                log.append("Era una trappola: la figura svanisce in una risata, -%d Timore." % gd.MYSTERY_CATENE_TIMORE_TRAPPOLA)
        else:
            log.append("Lasci il prigioniero alle sue catene.")

    elif event_key == "biblioteca":
        if choice_key == "studia":
            run["bonus_xp"] = run.get("bonus_xp", 0) + gd.MYSTERY_BIBLIOTECA_XP_BONUS
            log.append("Studi i tomi polverosi: +%d PE a fine spedizione." % gd.MYSTERY_BIBLIOTECA_XP_BONUS)
        else:
            log.append("Vai via senza toccare nulla.")

    elif event_key == "rituale":
        if choice_key == "completa":
            if random.random() < 0.5:
                stat = random.choice(["dmg", "armor", "mres"])
                run["temp_buffs"][stat] = run["temp_buffs"].get(stat, 0) + 1
                label = {"dmg": "Danno Fisico", "armor": "Armatura", "mres": "Res. Mentale"}[stat]
                log.append("Il rito si completa con successo: +1 %s per il resto della run." % label)
            else:
                run["pending_effects"].append({"type": "dmg_debuff", "amount": gd.MYSTERY_RITUALE_DEBUFF_DANNO, "turns": gd.MYSTERY_RITUALE_DEBUFF_TURNI})
                log.append("Il rito va storto: ti senti indebolito, l'effetto si manifesterà nel prossimo scontro.")
        else:
            log.append("Lasci il cerchio rituale incompiuto.")

    elif event_key == "baratto":
        if choice_key == "offri_pv" and leader["pv"] > gd.MYSTERY_BARATTO_COSTO_PV:
            leader["pv"] -= gd.MYSTERY_BARATTO_COSTO_PV
            run["temp_buffs"]["dmg"] = run["temp_buffs"].get("dmg", 0) + 1
            log.append("Offri %d PV in sangue: +1 Danno Fisico per il resto della run." % gd.MYSTERY_BARATTO_COSTO_PV)
        elif choice_key == "offri_pv":
            log.append("Non hai abbastanza Vita da offrire: il patto resta non firmato.")
        else:
            log.append("Rifiuti il patto di sangue.")

    elif event_key == "statua":
        if choice_key == "consola":
            leader["timore"] = min(leader["timore_max"], leader["timore"] + gd.MYSTERY_STATUA_TIMORE_BONUS)
            log.append("Consoli la statua piangente: +%d Timore." % gd.MYSTERY_STATUA_TIMORE_BONUS)
        elif choice_key == "deridi":
            if random.random() < 0.5:
                run["treasure"]["oro"] = run["treasure"].get("oro", 0) + gd.MYSTERY_STATUA_ORO_BONUS
                log.append("Deridi la statua: tra le sue lacrime scivolano %d Oro." % gd.MYSTERY_STATUA_ORO_BONUS)
            else:
                leader["timore"] = max(0, leader["timore"] - gd.MYSTERY_STATUA_TIMORE_TRAPPOLA)
                log.append("La statua sembra offendersi: -%d Timore." % gd.MYSTERY_STATUA_TIMORE_TRAPPOLA)
        else:
            log.append("Ignori la statua e prosegui.")

    elif event_key == "forziere":
        if choice_key == "scassina":
            if random.random() < 0.5:
                run["treasure"]["oro"] = run["treasure"].get("oro", 0) + gd.MYSTERY_FORZIERE_ORO_BONUS
                log.append("Scassini il forziere con successo: +%d Oro." % gd.MYSTERY_FORZIERE_ORO_BONUS)
            else:
                leader["pv"] = max(0, leader["pv"] - gd.MYSTERY_FORZIERE_PV_TRAPPOLA)
                log.append("Una trappola scatta: -%d PV." % gd.MYSTERY_FORZIERE_PV_TRAPPOLA)
        else:
            log.append("Lasci il forziere incatenato dove si trova.")

    else:
        log.append("Non succede nulla di particolare.")

    return log


def resolve_fontana(run):
    log = []
    fallen = [m for m in run["seguito"] if not m["alive"]]
    run["leader"]["pv"] = run["leader"]["pv_max"]
    log.append("La Fontana Sacra risana completamente la tua Vita.")
    if fallen:
        chosen = random.choice(fallen)
        chosen["alive"] = True
        if chosen["type"] == "guardiano":
            chosen["charges"] = gd.GUARDIANO_CHARGES
        log.append("%s del tuo Seguito ritorna in forze." % gd.ENTOURAGE_TYPES.get(chosen["type"], {"name": "Un membro"}).get("name", "Un membro"))
    else:
        heal_timore = 5
        run["leader"]["timore"] = min(run["leader"]["timore_max"], run["leader"]["timore"] + heal_timore)
        log.append("Il tuo Seguito e' al completo: le acque calmano invece la tua mente (+%d Timore)." % heal_timore)
    return log


def _negoziazione_discount(run, base_cost):
    sconto_pct = run.get("equip_flags", {}).get("negoziazione_pct", 0)
    if not sconto_pct:
        return base_cost
    return max(0, round(base_cost * (1 - sconto_pct)))


def incudine_cost(run):
    base = gd.INCUDINE_BASE_COST
    if run["class"] == "Amministratore":
        free_budget = 2 if run["level"] >= 10 else 1
        if run.get("incudine_free_used", 0) < free_budget:
            return 0
    return _negoziazione_discount(run, base)


def incudine_buff_amount(run):
    return gd.INCUDINE_BUFF_AMOUNT


def resolve_incudine(run, stat_choice):
    cost = incudine_cost(run)
    if run["treasure"].get("oro", 0) < cost:
        return ["Non hai abbastanza Oro: la Forgia resta silenziosa."]
    run["treasure"]["oro"] -= cost
    is_free = cost == 0 and run["class"] == "Amministratore"
    if is_free:
        run["incudine_free_used"] = run.get("incudine_free_used", 0) + 1
    amount = incudine_buff_amount(run)
    run["temp_buffs"][stat_choice] = run["temp_buffs"].get(stat_choice, 0) + amount
    label = {"dmg": "Danno Fisico", "armor": "Armatura", "mres": "Resistenza Mentale"}[stat_choice]
    if is_free:
        return ["Abile nelle trattative: potenziamento gratuito alla Forgia — +%d %s per il resto della run." % (amount, label)]
    return ["Spendi %d Oro alla Forgia: +%d %s per il resto della run." % (cost, amount, label)]


def sacco_monete_cost(run):
    return _negoziazione_discount(run, gd.SACCO_MONETE_COST)


def resolve_sacco_monete(run):
    cost = sacco_monete_cost(run)
    if run["treasure"].get("oro", 0) < cost:
        return ["Non hai abbastanza Oro per assumere un mercenario."]
    run["treasure"]["oro"] -= cost
    run["seguito"].append({"type": "mercenario", "alive": True, "charges": None})
    return ["Spendi %d Oro: un mercenario temporaneo si unisce a te." % cost]


# ─── FINE RUN: ESPERIENZA ────────────────────────────────────────────────
def compute_xp_gain(run):
    rooms_cleared = run["room_index"]
    xp = rooms_cleared * 10
    if run["result"] == "vittoria":
        xp += 30
    xp += run.get("bonus_xp", 0)
    xp_bonus_pct = run.get("equip_flags", {}).get("xp_bonus_pct", 0)
    if xp_bonus_pct:
        xp = round(xp * (1 + xp_bonus_pct))
    return xp


# ─── ARENA (duelli PvP asincroni) ─────────────────────────────────────────
# Riusa lo stesso personaggio/equip/livello/abilita' del PvE (vedi new_run_state),
# ma senza nemico scriptato: i due lati sono entrambi giocatori veri. Invece di
# riscrivere da zero tutta la logica delle abilita' (_apply_ability_action, ~700
# righe gia' collaudate in PvE), la si riusa cosi' com'e' tramite un "adattatore":
# per la durata di una singola azione, lo stato dell'avversario viene esposto sotto
# le stesse chiavi "enemy_*" che quella funzione gia' si aspetta.

ARENA_SOLO_SPEDIZIONI = {"vie_segrete", "bancarotta", "esperto_saccheggiatore", "azzardo_economico"}


def _fresh_arena_status():
    """Stato di combattimento "vivo" di un lato del duello: scudi, buff/debuff
    temporanei, stordimento, ecc. — l'equivalente del dizionario `combat` del PvE,
    ma solo per gli effetti che riguardano DAVVERO questo lato (vedi sopra)."""
    return {
        "combat_armor_bonus": 0, "combat_mres_bonus": 0, "combat_dmg_bonus": 0,
        "shield_reduction": 0, "shield_physical_pool": 0, "shield_timore_pool": 0,
        "double_next_attack": False, "colpo_arcano_stacks": 0, "raffica_potenziata": False,
        "evasion_turns": 0, "evasion_chance": 0.0,
        "stunned": 0, "slowed_turns": 0, "weaken_turns": 0, "weaken_amount": 0,
        "burn_turns": 0, "burn_dmg": 0,
        "bleed_turns": 0, "bleed_dmg": 0, "bleed_kind": None, "bleed_target": None,
        "egida_triggered": False,
    }


def new_arena_state(faction, name, char_class, level, entourage_types, equip_item_ids, equipped_abilities=None):
    """Come new_run_state, con in piu' lo stato di combattimento persistente del
    duello. Il chiamante e' responsabile di NON includere le abilita' ARENA_SOLO_SPEDIZIONI
    in equipped_abilities (la schermata di preparazione le mostrera' non selezionabili)."""
    run = new_run_state(faction, name, char_class, level, entourage_types, equip_item_ids, equipped_abilities)
    run["arena_status"] = _fresh_arena_status()
    return run


def arena_available_actions(run):
    """Come all_combat_abilities, ma senza le abilita' pensate solo per il PvE."""
    return [a for a in all_combat_abilities(run) if a["key"] not in ARENA_SOLO_SPEDIZIONI]


def _arena_shim_combat(actor_status, target_status):
    """Espone temporaneamente lo stato del bersaglio sotto le chiavi 'enemy_*',
    cosi' _apply_ability_action puo' leggerle/scriverle esattamente come farebbe
    in PvE. actor_status stesso funge da dizionario 'combat' per tutto il resto
    (i suoi stessi scudi/buff, gia' con i nomi giusti)."""
    actor_status["enemy_stunned"] = target_status.get("stunned", 0)
    actor_status["enemy_slowed_turns"] = target_status.get("slowed_turns", 0)
    actor_status["enemy_weaken_turns"] = target_status.get("weaken_turns", 0)
    actor_status["enemy_weaken_amount"] = target_status.get("weaken_amount", 0)
    actor_status["burn_turns"] = target_status.get("burn_turns", 0)
    actor_status["burn_dmg"] = target_status.get("burn_dmg", 0)
    return actor_status


def _arena_unshim_combat(actor_status, target_status):
    """Rilegge le chiavi 'enemy_*' (eventualmente modificate dall'abilita' appena
    eseguita) e le riversa nello stato persistente del bersaglio, poi le rimuove
    da actor_status perche' non gli appartengono."""
    target_status["stunned"] = actor_status.pop("enemy_stunned", 0)
    target_status["slowed_turns"] = actor_status.pop("enemy_slowed_turns", 0)
    target_status["weaken_turns"] = actor_status.pop("enemy_weaken_turns", 0)
    target_status["weaken_amount"] = actor_status.pop("enemy_weaken_amount", 0)
    target_status["burn_turns"] = actor_status.pop("burn_turns", 0)
    target_status["burn_dmg"] = actor_status.pop("burn_dmg", 0)


def _arena_effective_defense(combatant, status, stat):
    """Equivalente di _effective_defense per un combattente dell'arena."""
    base = combatant["leader"][stat] + combatant["temp_buffs"][stat] + status.get("combat_%s_bonus" % stat, 0)
    return max(0, base)


def _arena_check_egida_trigger(state, status, log):
    """Equivalente arena di _check_egida_trigger: ogni lato controlla la propria
    Vita indipendentemente."""
    bonus = state.get("equip_flags", {}).get("bonus_armor_sotto_quarto", 0)
    if not bonus or status.get("egida_triggered"):
        return
    if state["leader"]["pv_max"] > 0 and state["leader"]["pv"] < state["leader"]["pv_max"] * gd.RADDOPPIO_SOTTO_QUARTO_SOGLIA:
        status["egida_triggered"] = True
        status["combat_armor_bonus"] = status.get("combat_armor_bonus", 0) + bonus
        log.append("L'Egida dell'Ultimo Bastione di %s risponde al pericolo: +%d Armatura per il resto del duello." % (state["name"], bonus))


def _arena_maybe_reflect_fixed(actor, target, log):
    """Equivalente arena di _maybe_reflect_fixed: l'Armatura del Sigillo Infranto del
    BERSAGLIO riflette danno fisso sull'ATTACCANTE."""
    flags = target.get("equip_flags", {})
    chance = flags.get("riflette_chance", 0)
    amount = flags.get("riflette_fisso", 0)
    if chance and amount and random.random() < chance:
        actor["leader"]["pv"] -= amount
        log.append("L'armatura di %s riflette %d danni su %s." % (target["name"], amount, actor["name"]))


def _arena_apply_damage(actor, target, target_status, dmg, timore_dmg, log):
    """Applica al bersaglio il danno di un'azione, con la stessa mitigazione
    (scudi, Armatura/Res. Mentale effettive, oggetti epici/leggendari) del PvE —
    qui pero' il bersaglio e' un giocatore vero con scudi/buff propri, cosa che il
    nemico scriptato del PvE non ha mai avuto bisogno di gestire."""
    flags = actor.get("equip_flags", {})
    effective_dmg = dmg
    bonus_timore = 0
    crit_bonus_timore = 0
    ignora_difese = False

    if effective_dmg > 0:
        ignora_pct = flags.get("ignora_difese_pct", 0)
        if ignora_pct and random.random() < ignora_pct:
            ignora_difese = True
            log.append("%s ignora completamente la difesa di %s!" % (actor["name"], target["name"]))

        stordisce_pct = flags.get("stordisce_pct", 0)
        if stordisce_pct and random.random() < stordisce_pct:
            target_status["stunned"] = target_status.get("stunned", 0) + 1
            log.append("%s stordisce %s per 1 turno!" % (actor["name"], target["name"]))

        bonus_timore += flags.get("dmg_timore_nemico", 0)

        if flags.get("critico_colpisce_timore") and random.random() < gd.ITEM_CRIT_CHANCE:
            crit_bonus_timore += effective_dmg
            effective_dmg *= 2
            log.append("Colpo critico di %s, che incrina corpo e Timore!" % actor["name"])

        # Variante arena di Esperto Catalogatore (Mago): ogni danno fisico inflitto
        # colpisce anche il Timore avversario.
        if actor["class"] == "Mago":
            bonus_timore += 1

    if effective_dmg > 0:
        residuo = effective_dmg
        absorbed, residuo, seg_log = _seguito_absorb(target, residuo, cavaliere_ward_chance=gd.ARENA_CAVALIERE_WARD_CHANCE)
        log.extend(seg_log)
        if absorbed and residuo <= 0:
            pass
        else:
            shield = target_status.get("shield_reduction", 0)
            if shield and residuo > 0:
                residuo = max(0, residuo - shield)
                target_status["shield_reduction"] = 0
                log.append("Lo scudo di %s attutisce il colpo." % target["name"])
            pool = target_status.get("shield_physical_pool", 0)
            if pool and residuo > 0:
                assorbito = min(pool, residuo)
                residuo -= assorbito
                target_status["shield_physical_pool"] -= assorbito
                log.append("Lo scudo magico di %s assorbe %d danni fisici." % (target["name"], assorbito))
            final_armor = 0 if ignora_difese else _arena_effective_defense(target, target_status, "armor")
            penetrazione = flags.get("penetrazione_armor", 0)
            if penetrazione:
                final_armor = max(0, final_armor - penetrazione)
            dmg_to_target = max(1, residuo - final_armor) if residuo > 0 else 0
            if dmg_to_target > 0:
                target["leader"]["pv"] -= dmg_to_target
                log.append("%s subisce %d danni fisici." % (target["name"], dmg_to_target))
                _arena_maybe_reflect_fixed(actor, target, log)

                proc_kind = "sanguinamento" if flags.get("sanguinamento_su_colpo") else ("veleno" if flags.get("veleno_su_colpo") else None)
                if proc_kind and target_status.get("bleed_turns", 0) <= 0 and random.random() < gd.ITEM_ENEMY_DOT_CHANCE:
                    if proc_kind == "sanguinamento" and target.get("equip_flags", {}).get("immunita_sanguinamento"):
                        log.append("L'Elmo del Primo Re di Karag-Duraz protegge %s dalla ferita: non sanguina." % target["name"])
                    else:
                        bleed_dmg = random.randint(*gd.ITEM_ENEMY_DOT_DMG)
                        bleed_target = "timore" if proc_kind == "veleno" else "pv"
                        target_status["bleed_turns"] = gd.ITEM_ENEMY_DOT_TURNS
                        target_status["bleed_dmg"] = bleed_dmg
                        target_status["bleed_kind"] = proc_kind
                        target_status["bleed_target"] = bleed_target
                        if proc_kind == "veleno":
                            log.append("Il Plettro del Destino incide: %s è avvelenato, perderà %d Timore a turno per %d turni." %
                                        (target["name"], bleed_dmg, gd.ITEM_ENEMY_DOT_TURNS))
                        else:
                            log.append("La Zanna dell'Uomorsomaiale morde ancora: %s sanguina, perdendo %d PV a turno per %d turni." %
                                        (target["name"], bleed_dmg, gd.ITEM_ENEMY_DOT_TURNS))

                shield_chance = flags.get("shield_pv_su_colpo_chance", 0)
                shield_amount = flags.get("shield_pv_su_colpo_amount", 0)
                if shield_chance and shield_amount and random.random() < shield_chance:
                    actor_status = actor.get("arena_status", {})
                    actor_status["shield_physical_pool"] = actor_status.get("shield_physical_pool", 0) + shield_amount
                    log.append("Lo Spadone Lungo di Ser Gowain di %s vibra: guadagna %d scudo Vita." % (actor["name"], shield_amount))

    total_timore_dmg = timore_dmg + bonus_timore + crit_bonus_timore
    if total_timore_dmg > 0:
        residuo_t = total_timore_dmg
        bardi = sum(1 for m in target["seguito"] if m["alive"] and m["type"] == "bardo")
        if bardi:
            riduzione_bardo = bardi * gd.BARDO_ARENA_TIMORE_REDUCTION
            residuo_t = max(0, residuo_t - riduzione_bardo)
            if riduzione_bardo:
                log.append("Il Bardo di %s attutisce l'assalto al Timore (-%d)." % (target["name"], riduzione_bardo))
        pool_t = target_status.get("shield_timore_pool", 0)
        if pool_t and residuo_t > 0:
            assorbito_t = min(pool_t, residuo_t)
            residuo_t -= assorbito_t
            target_status["shield_timore_pool"] -= assorbito_t
            log.append("Lo scudo magico di %s assorbe %d danni al Timore." % (target["name"], assorbito_t))
        total_mres = _arena_effective_defense(target, target_status, "mres")
        timore_to_target = max(1, residuo_t - total_mres) if residuo_t > 0 else 0
        if timore_to_target > 0:
            target["leader"]["timore"] -= timore_to_target
            log.append("Il Timore di %s scende di %d." % (target["name"], timore_to_target))


def _arena_take_action(actor, target, action_key, is_first, log, dmg_multiplier):
    """Risolve l'azione di UN lato contro l'altro. is_first indica se questo lato
    agisce per primo in questo round (serve al bonus danno dell'Arciere). Ritorna
    'fuga' se il lato ha abbandonato il duello, altrimenti None."""
    actor_status, target_status = actor["arena_status"], target["arena_status"]

    if actor_status.get("stunned", 0) > 0:
        actor_status["stunned"] -= 1
        log.append("%s è ancora stordito e non riesce ad agire." % actor["name"])
        return None

    log.append("— %s —" % actor["name"])

    if target_status.get("evasion_turns", 0) > 0:
        target_status["evasion_turns"] -= 1
        if random.random() < target_status.get("evasion_chance", 0):
            log.append("Copie Illusorie: %s evita completamente il colpo di %s." % (target["name"], actor["name"]))
            return None

    fake_run = {
        "leader": actor["leader"], "temp_buffs": actor["temp_buffs"], "treasure": actor["treasure"],
        "cooldowns": actor["cooldowns"], "seguito": actor["seguito"],
        "used_once_abilities": actor["used_once_abilities"], "ability_use_counts": actor["ability_use_counts"],
        "equipped_abilities": actor["equipped_abilities"], "equip_flags": actor["equip_flags"],
        "class": actor["class"], "level": gd.MAX_LEVEL,  # in arena tutte le abilita' sono sbloccate
        "combat": _arena_shim_combat(actor_status, target_status),
    }

    if action_key == "attacco_fisico":
        dmg = _leader_dmg(fake_run)
        timore_dmg = 0
        escape = False
        if actor["class"] == "Esploratore":
            actor_status["shield_physical_pool"] = actor_status.get("shield_physical_pool", 0) + 2
            ab_log = ["Attacco Preventivo: infligge %d danni e guadagna 2 scudo fisico." % dmg]
        else:
            ab_log = ["Attacca: infligge %d danni." % dmg]
    else:
        dmg, timore_dmg, ab_log, escape = _apply_ability_action(fake_run, action_key)

    _arena_unshim_combat(actor_status, target_status)
    log.extend(ab_log)

    if escape:
        log.append("%s abbandona il duello." % actor["name"])
        return "fuga"

    if dmg > 0 and actor_status.get("double_next_attack"):
        dmg = round(dmg * 1.4)
        actor_status["double_next_attack"] = False
        log.append("Il fragore di Grido di Guerra potenzia il colpo (+40%)!")

    # Sforzo Adrenalinico, variante arena: resta solo il critico, niente scudo iniziale
    if actor["class"] == "Esploratore" and (dmg > 0 or timore_dmg > 0) and random.random() < 0.10:
        if dmg > 0:
            dmg *= 2
        if timore_dmg > 0:
            timore_dmg *= 2
        log.append("Sforzo Adrenalinico: colpo critico!")

    # Ira Funesta (Generale): sotto il 50% di Vita o Timore, +3 danno
    if actor["class"] == "Generale" and dmg > 0:
        if actor["leader"]["pv"] < actor["leader"]["pv_max"] * 0.5 or actor["leader"]["timore"] < actor["leader"]["timore_max"] * 0.5:
            dmg += 3
            log.append("Ira Funesta: la disperazione acuisce il colpo, +3 danni.")

    vessilliferi = sum(1 for m in actor["seguito"] if m["alive"] and m["type"] == "vessillifero")
    if vessilliferi and dmg > 0:
        dmg += vessilliferi
        log.append("Vessillifero: lo stendardo issato incita il colpo, +%d danno." % vessilliferi)

    has_arciere = any(m["alive"] and m["type"] == "arciere" for m in actor["seguito"])
    if is_first and has_arciere and dmg > 0:
        dmg += gd.ARCIERE_DMG_BONUS
        log.append("Arciere: una scarica di frecce di supporto aggiunge +%d danni al tuo colpo." % gd.ARCIERE_DMG_BONUS)

    if dmg > 0 or timore_dmg > 0:
        dmg = round(dmg * dmg_multiplier)
        timore_dmg = round(timore_dmg * dmg_multiplier)
        log.append("La furia dell'Arena aumenta il colpo del %d%%." % round((dmg_multiplier - 1) * 100))
        _arena_apply_damage(actor, target, target_status, dmg, timore_dmg, log)
    return None


def _arena_check_victory(state_a, state_b):
    a_down = state_a["leader"]["pv"] <= 0 or state_a["leader"]["timore"] <= 0
    b_down = state_b["leader"]["pv"] <= 0 or state_b["leader"]["timore"] <= 0
    if a_down and b_down:
        return "pareggio"
    if a_down:
        return "vittoria_b"
    if b_down:
        return "vittoria_a"
    return None


def start_arena_match(state_a, state_b):
    """Effetti "una tantum" all'inizio del duello, equivalenti alla parte iniziale
    di start_combat in PvE: lo scudo del Novizio. Va chiamata una sola volta, quando
    entrambi i lati si sono preparati e il duello comincia davvero."""
    log = []
    for state in (state_a, state_b):
        novizi = [m for m in state["seguito"] if m["alive"] and m["type"] == "novizio"]
        if novizi:
            state["arena_status"]["shield_physical_pool"] += gd.NOVIZIO_SHIELD_PHYSICAL
            state["arena_status"]["shield_timore_pool"] += gd.NOVIZIO_SHIELD_TIMORE
            _troop_falls(state, novizi[0], log)
            log.append("%s: un Novizio si consuma per proteggerlo, guadagna %d scudo Vita e %d scudo Timore." %
                        (state["name"], gd.NOVIZIO_SHIELD_PHYSICAL, gd.NOVIZIO_SHIELD_TIMORE))
    return log


def resolve_arena_round(state_a, state_b, action_a, action_b, dmg_multiplier=None):
    """Risolve un intero round: entrambe le azioni sono gia' state scelte in modo
    indipendente e asincrono. Ritorna (esito, log) con esito in
    'in_corso' | 'vittoria_a' | 'vittoria_b' | 'pareggio'. dmg_multiplier permette
    di sovrascrivere ARENA_DMG_MULTIPLIER (usato dal pannello admin)."""
    dmg_multiplier = dmg_multiplier if dmg_multiplier is not None else gd.ARENA_DMG_MULTIPLIER
    log = []
    status_a, status_b = state_a["arena_status"], state_b["arena_status"]

    # tick di inizio round: cooldown, bruciature, rallentamento, indebolimento,
    # cura passiva del Seguito/classe, contrattacchi automatici di Martello/Ariete
    for side_state, side_status, opponent_state in ((state_a, status_a, state_b), (state_b, status_b, state_a)):
        for k in list(side_state["cooldowns"].keys()):
            if side_state["cooldowns"][k] > 0:
                side_state["cooldowns"][k] -= 1
        if side_status.get("burn_turns", 0) > 0:
            burn_dmg = round(side_status.get("burn_dmg", 0) * dmg_multiplier)
            side_state["leader"]["pv"] -= burn_dmg
            log.append("Le fiamme infliggono %d danni a %s." % (burn_dmg, side_state["name"]))
            side_status["burn_turns"] -= 1
        if side_status.get("bleed_turns", 0) > 0:
            bleed_dmg = side_status.get("bleed_dmg", 0)
            kind = side_status.get("bleed_kind") or "sanguinamento"
            target_stat = side_status.get("bleed_target") or "pv"
            if target_stat == "timore":
                side_state["leader"]["timore"] -= bleed_dmg
                log.append("Il veleno in %s si diffonde: perde %d Timore." % (side_state["name"], bleed_dmg))
            elif kind == "veleno":
                side_state["leader"]["pv"] -= bleed_dmg
                log.append("Il veleno in %s si diffonde: perde %d PV." % (side_state["name"], bleed_dmg))
            else:
                side_state["leader"]["pv"] -= bleed_dmg
                log.append("Il sanguinamento di %s si aggrava: perde %d PV." % (side_state["name"], bleed_dmg))
            side_status["bleed_turns"] -= 1
            if side_status["bleed_turns"] <= 0:
                side_status["bleed_kind"] = None
                side_status["bleed_target"] = None
        if side_status.get("weaken_turns", 0) > 0:
            side_status["weaken_turns"] -= 1
        if side_status.get("slowed_turns", 0) > 0:
            side_status["slowed_turns"] -= 1

        heal_pv = 0
        heal_timore = 0
        if any(m["alive"] and m["type"] == "purificatore" for m in side_state["seguito"]):
            heal_pv += gd.PURIFICATORE_HEAL
        if any(m["alive"] and m["type"] == "sciamano" for m in side_state["seguito"]):
            heal_timore += gd.SCIAMANO_HEAL
        if "bastione_della_fede" in side_state.get("equipped_abilities", []):
            heal_pv += 2
        if side_state["class"] == "Diplomatico":
            vive = sum(1 for m in side_state["seguito"] if m["alive"])
            if vive:
                heal_pv += vive
                heal_timore += vive
        if heal_pv > 0:
            side_state["leader"]["pv"] = min(side_state["leader"]["pv_max"], side_state["leader"]["pv"] + heal_pv)
            log.append("%s recupera %d Vita (cura passiva)." % (side_state["name"], heal_pv))
        if heal_timore > 0:
            side_state["leader"]["timore"] = min(side_state["leader"]["timore_max"], side_state["leader"]["timore"] + heal_timore)
            log.append("%s recupera %d Timore (cura passiva)." % (side_state["name"], heal_timore))

        martelli = sum(1 for m in side_state["seguito"] if m["alive"] and m["type"] == "martello")
        arieti = sum(1 for m in side_state["seguito"] if m["alive"] and m["type"] == "ariete")
        if martelli:
            opp_armor = _arena_effective_defense(opponent_state, opponent_state["arena_status"], "armor")
            colpo = max(1, round(martelli * gd.MARTELLO_COUNTER_DMG * dmg_multiplier) - opp_armor)
            opponent_state["leader"]["pv"] -= colpo
            log.append("I Compagni del Martello di %s colpiscono %s per %d danni." % (side_state["name"], opponent_state["name"], colpo))
        if arieti:
            opp_mres = _arena_effective_defense(opponent_state, opponent_state["arena_status"], "mres")
            colpo = max(1, round(arieti * gd.ARIETE_COUNTER_DMG * dmg_multiplier) - opp_mres)
            opponent_state["leader"]["timore"] -= colpo
            log.append("L'Ariete di %s incalza il Timore di %s per %d danni." % (side_state["name"], opponent_state["name"], colpo))

        esito = _arena_check_victory(state_a, state_b)
        if esito:
            return esito, log

    has_arciere_a = any(m["alive"] and m["type"] == "arciere" for m in state_a["seguito"])
    has_arciere_b = any(m["alive"] and m["type"] == "arciere" for m in state_b["seguito"])
    p_a_first = max(0.0, min(1.0, 0.5 + (0.25 if has_arciere_a else 0) - (0.25 if has_arciere_b else 0)))
    a_first = random.random() < p_a_first

    order = [("a", state_a, state_b, action_a), ("b", state_b, state_a, action_b)]
    if not a_first:
        order.reverse()

    for i, (side, actor, target, action_key) in enumerate(order):
        if i == 1:
            log.append(ROUND_BEAT_MARKER)
        result = _arena_take_action(actor, target, action_key, i == 0, log, dmg_multiplier)
        if result == "fuga":
            return ("vittoria_b" if side == "a" else "vittoria_a"), log

    # L'esito si controlla solo DOPO che entrambe le azioni del round sono state
    # risolte per intero — mai a meta' round. Altrimenti, se il primo dei due ad agire
    # (per iniziativa) elimina l'avversario, il colpo del secondo non verrebbe mai
    # calcolato: un vero scambio simultaneo che avrebbe eliminato entrambi finirebbe
    # per sembrare una vittoria a senso unico invece di un pareggio.
    esito = _arena_check_victory(state_a, state_b)
    if esito:
        return esito, log

    _arena_check_egida_trigger(state_a, status_a, log)
    _arena_check_egida_trigger(state_b, status_b, log)

    return "in_corso", log
