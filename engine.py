# -*- coding: utf-8 -*-
"""Motore di gioco puro (nessuna dipendenza da Flask/sessione), cosi' e' testabile
in isolamento. Tutte le funzioni operano su un dizionario `run` passato esplicitamente
e ritornano/mutano quello stesso dizionario, piu' una lista di righe di log."""
import random
import game_data as gd


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
    for item_id in equip_item_ids:
        if not item_id:
            continue
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
    }
    return run


# ─── GENERAZIONE STANZE ──────────────────────────────────────────────────
def generate_rooms_plan():
    """Genera, per ognuna delle ROOMS_PER_RUN stanze, un set di 3 tipi di stanza distinti
    tra cui scegliere. Garantisce che la Fontana compaia almeno ogni 2 stanze."""
    plan = []
    rooms_since_fontana = 0
    all_types = list(gd.ROOM_TYPES.keys())
    for i in range(gd.ROOMS_PER_RUN):
        options = {"battaglia"}  # la minaccia e' sempre un'opzione disponibile
        force_fontana = rooms_since_fontana >= 2
        if force_fontana:
            options.add("fontana")
        remaining = [t for t in all_types if t not in options]
        random.shuffle(remaining)
        while len(options) < 3 and remaining:
            options.add(remaining.pop())
        options = list(options)
        random.shuffle(options)
        plan.append(options)
        if "fontana" in options:
            rooms_since_fontana = 0
        else:
            rooms_since_fontana += 1
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
def _seguito_absorb(run, incoming_dmg):
    """Tenta di far assorbire il colpo fisico dal Seguito. Ritorna (assorbito: bool,
    danno_residuo_al_leader: int, righe_di_log: list)."""
    log = []
    seg = run["seguito"]

    def alive_of(t):
        return [m for m in seg if m["alive"] and m["type"] == t]

    # Cavaliere: possibilita' di annullare l'attacco senza consumare nessuno
    if alive_of("cavaliere") and random.random() < gd.CAVALIERE_WARD_CHANCE:
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
            m["alive"] = False
            log.append("Il Guardiano, esausto, cade.")
        return True, residuo, log

    for tipo, msg_extra in (("fante", ""), ("martello", "")):
        membri = alive_of(tipo)
        if membri:
            m = membri[0]
            survive = razionamento and random.random() < 0.5
            if not survive:
                m["alive"] = False
            nome = gd.ENTOURAGE_TYPES[tipo]["name"]
            log.append("%s assorbe il colpo interamente%s." % (nome, " e resiste ancora!" if survive else ", e cade."))
            if tipo == "martello":
                run["combat"]["enemy_pv"] -= gd.MARTELLO_COUNTER_DMG
                log.append("I Compagni del Martello contrattaccano per %d danni!" % gd.MARTELLO_COUNTER_DMG)
            return True, 0, log

    mercenari = alive_of("mercenario")
    if mercenari:
        m = mercenari[0]
        m["alive"] = False
        if random.random() < gd.MERCENARIO_SUCCESS_CHANCE:
            log.append("Il mercenario assorbe il colpo prima di fuggire.")
            return True, 0, log
        else:
            log.append("Il mercenario fugge senza proteggerti!")
            return False, incoming_dmg, log

    return False, incoming_dmg, log


# ─── COMBATTIMENTO ────────────────────────────────────────────────────────
def start_combat(run, tier):
    """tier: 1..N per stanze normali, 'boss' per il miniboss."""
    level = run["level"]
    data = gd.get_boss_tier(gd.ROOMS_PER_RUN, level) if tier == "boss" else gd.get_enemy_tier(tier, level)
    name, icon, archetype = random.choice(data["pool"])
    enemy_armor, enemy_mres = gd.enemy_defense(archetype, level)
    run["cooldowns"] = {}  # i cooldown si resettano a ogni nuovo combattimento, non durano tutta la run
    run["combat"] = {
        "tier": tier, "name": name, "icon": icon, "archetype": archetype,
        "enemy_armor": enemy_armor, "enemy_mres": enemy_mres,
        "enemy_pv": data["pv"], "enemy_pv_max": data["pv"],
        "enemy_timore": data["pv"], "enemy_timore_max": data["pv"],
        "dmg": data["dmg"], "fear_chance": data["fear_chance"], "fear_dmg": data["fear_dmg"],
        "round": 1, "first_hit_taken": False, "negotiated_escape": False, "enemy_stunned": 0,
        "combat_armor_bonus": 0, "combat_mres_bonus": 0, "combat_dmg_bonus": 0,
        "shield_reduction": 0, "double_next_attack": False, "skip_attack": False,
        "colpo_arcano_stacks": 0, "shield_physical_pool": 0, "shield_timore_pool": 0,
        "enemy_slowed_turns": 0, "burn_turns": 0, "burn_dmg": 0,
        "evasion_turns": 0, "evasion_chance": 0.0,
        "raffica_potenziata": False, "enemy_weaken_turns": 0, "enemy_weaken_amount": 0,
    }
    run["log"] = []
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
        log.append("Grido di Guerra: non attacchi questo turno, ma il tuo prossimo colpo sara' devastante (+1 Danno, danno doppio al prossimo attacco).")
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
            m["alive"] = False
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
        combat["shield_physical_pool"] += 10
        combat["shield_timore_pool"] += 12
        log.append("Scudo Magico: eretta una barriera che assorbira' i prossimi 10 danni fisici e 12 al Timore.")
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
            scelto["alive"] = False
            nome = gd.ENTOURAGE_TYPES.get(scelto["type"], {}).get("name", scelto["type"])
            log.append("%s viene sacrificato nel rito." % nome)
        return dmg, timore_dmg, log, False

    if ability_key == "proteggimi":
        _set_cooldown(run, ability_key)
        attive = sum(1 for m in run["seguito"] if m["alive"])
        combat["shield_physical_pool"] += 4 * attive
        combat["shield_timore_pool"] += 2 * attive
        log.append("Proteggimi!: %d truppe ancora in vita ti proteggono con uno scudo di %d Vita e %d Timore." % (attive, 4 * attive, 2 * attive))
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
            final_armor = run["leader"]["armor"] + run["temp_buffs"]["armor"] + combat.get("combat_armor_bonus", 0)
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

    if not escape and dmg > 0 and run["combat"].get("double_next_attack"):
        dmg *= 2
        run["combat"]["double_next_attack"] = False
        if ab_log is not None:
            ab_log.append("Il fragore di Grido di Guerra raddoppia il colpo!")
        else:
            log.append("Il fragore di Grido di Guerra raddoppia il colpo!")

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

    if combat.get("burn_turns", 0) > 0:
        combat["enemy_pv"] -= combat["burn_dmg"]
        combat["burn_turns"] -= 1
        log.append("Le fiamme infliggono %d danni al nemico." % combat["burn_dmg"])
        if combat["enemy_pv"] <= 0 or combat["enemy_timore"] <= 0:
            run["log"] = log
            return "vittoria"

    # iniziativa: chi agisce per primo nel round (l'arciere favorisce il leader; un nemico
    # rallentato agisce sempre per ultimo, a prescindere da tutto il resto)
    if combat.get("enemy_slowed_turns", 0) > 0:
        leader_first = True
        combat["enemy_slowed_turns"] -= 1
    else:
        has_arciere = any(m["alive"] and m["type"] == "arciere" for m in run["seguito"])
        leader_first_chance = 0.75 if has_arciere else 0.5
        leader_first = random.random() < leader_first_chance

    def apply_leader_damage_to_enemy():
        phys = max(1, dmg - combat.get("enemy_armor", 0)) if dmg > 0 else 0
        fear = max(1, timore_dmg - combat.get("enemy_mres", 0)) if timore_dmg > 0 else 0
        combat["enemy_pv"] -= phys
        combat["enemy_timore"] -= fear

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

        # purificatore: cura passiva a inizio del turno di scambio
        heal_pv = 0
        heal_timore = 0
        if any(m["alive"] and m["type"] == "purificatore" for m in run["seguito"]):
            heal_pv += gd.PURIFICATORE_HEAL
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
            log.append("Pretoriani: il tuo Seguito ti infonde %d Timore." % heal_timore)

        is_fear = random.random() < combat["fear_chance"]
        if is_fear:
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
            total_mres = run["leader"]["mres"] + run["temp_buffs"]["mres"] + combat.get("combat_mres_bonus", 0)
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
                final_armor = run["leader"]["armor"] + run["temp_buffs"]["armor"] + combat.get("combat_armor_bonus", 0)
                dmg_to_leader = max(1, residuo - final_armor) if residuo > 0 else 0
                if dmg_to_leader > 0:
                    run["leader"]["pv"] -= dmg_to_leader
                    log.append("Subisci %d danni fisici." % dmg_to_leader)

    if leader_first:
        apply_leader_damage_to_enemy()
        if combat["enemy_pv"] <= 0 or combat["enemy_timore"] <= 0:
            run["log"] = log
            return "vittoria"
        enemy_turn()
    else:
        enemy_turn()
        # controlli di sconfitta prima che il leader possa agire
        outcome = _check_defeat(run, log)
        if outcome:
            return outcome
        apply_leader_damage_to_enemy()
        if combat["enemy_pv"] <= 0 or combat["enemy_timore"] <= 0:
            run["log"] = log
            return "vittoria"

    outcome = _check_defeat(run, log)
    if outcome:
        return outcome

    combat["round"] += 1
    run["log"] = log
    if combat["round"] > 8:
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
    lo, hi = gd.BOSS_LOOT_AMOUNT if is_boss else gd.NORMAL_LOOT_AMOUNT
    amount = random.randint(lo, hi)
    if getattr(gd, "LOOT_LEVEL_SCALING", False):
        amount = round(amount * gd.level_factor(run["level"]))
    if run["class"] == "Esploratore" and run["level"] >= 5:
        amount = int(amount * 1.5)
    equipped = run.get("equipped_abilities", [])
    raddoppio = "drago_della_finanza" in equipped or "mappatore_esperto" in equipped
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
    drop_chance = gd.BOSS_ITEM_DROP_CHANCE if is_boss else gd.NORMAL_ITEM_DROP_CHANCE
    if random.random() < drop_chance:
        weights = gd.BOSS_DROP_RARITY_WEIGHTS if is_boss else gd.NORMAL_DROP_RARITY_WEIGHTS
        rarity = random.choices(list(weights.keys()), weights=list(weights.values()))[0]
        candidates = [k for k, v in gd.ITEMS.items() if v["rarity"] == rarity]
        if candidates:
            item_id = random.choice(candidates)
            log.append("Un oggetto raro attira la tua attenzione: %s!" % gd.ITEMS[item_id]["name"])
    return log, item_id


# ─── STANZE NON DI COMBATTIMENTO ─────────────────────────────────────────
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


def incudine_cost(run):
    base = gd.INCUDINE_BASE_COST
    if run["class"] == "Amministratore":
        free_budget = 2 if run["level"] >= 10 else 1
        if run.get("incudine_free_used", 0) < free_budget:
            return 0
    return base


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
    return gd.SACCO_MONETE_COST


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
    return xp
