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


# ─── CREAZIONE STATO DI UNA RUN ──────────────────────────────────────────
def new_run_state(faction, name, char_class, level, entourage_types, equip_item_ids):
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
    if char_class == "Amministratore" and level >= 3:
        oro_iniziale += 5

    seguito = [{"type": t, "alive": True, "charges": gd.GUARDIANO_CHARGES if t == "guardiano" else None}
               for t in entourage_types]

    run = {
        "faction": faction, "name": name, "class": char_class, "level": level,
        "leader": {
            "pv": gd.BASE_PV, "pv_max": gd.BASE_PV,
            "timore": gd.BASE_TIMORE, "timore_max": gd.BASE_TIMORE,
            "armor": armor, "mres": mres, "dmg_bonus": dmg_bonus, "iniziativa_bonus": iniziativa_bonus,
        },
        "equip_flags": flags,
        "seguito": seguito,
        "treasure": {**{r: 0 for r in gd.RESOURCE_TYPES}, "oro": oro_iniziale},
        "room_index": 0,
        "rooms_plan": generate_rooms_plan(),
        "used_once_abilities": [],
        "temp_buffs": {"dmg": 0, "armor": 0, "mres": 0, "grido_di_guerra_rooms": 0},
        "resistenza_triggered": False,
        "ultima_resistenza_used": False,
        "log": [],
        "combat": None,  # stato del combattimento in corso (se presente)
        "finished": False,
        "result": None,  # 'vittoria' | 'ritirata_timore' | 'ritirata_morte'
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
def available_combat_actions(run):
    """Ritorna la lista delle azioni selezionabili nel round corrente (attacco fisico +
    abilita' attive non ancora esaurite)."""
    actions = [{"key": "attacco_fisico", "name": "Attacco Fisico", "type": "fisico"}]
    abilities = unlocked_abilities(run["class"], run["level"])
    for a in abilities:
        if a["type"] == "passiva":
            continue
        if a["once"] and a["key"] in run["used_once_abilities"]:
            continue
        # negoziazione e nebbia_illusoria: fuggire dal combattimento, sempre selezionabili se non usate
        actions.append({"key": a["key"], "name": a["name"], "type": a["type"]})
    return actions


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

    razionamento = run["class"] == "Amministratore" and run["level"] >= 5

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
    data = gd.get_boss_tier(gd.ROOMS_PER_RUN) if tier == "boss" else gd.get_enemy_tier(tier)
    name, icon = random.choice(data["pool"])
    run["combat"] = {
        "tier": tier, "name": name, "icon": icon,
        "enemy_pv": data["pv"], "enemy_pv_max": data["pv"],
        "dmg": data["dmg"], "fear_chance": data["fear_chance"], "fear_dmg": data["fear_dmg"],
        "round": 1, "first_hit_taken": False, "negotiated_escape": False,
    }
    run["log"] = []
    if has_ability(run, "fiuto"):
        run["log"].append("🧭 Fiuto: percepisci la presenza di %s %s prima ancora di vederlo." % (icon, name))
    run["log"].append("%s %s emerge dall'ombra." % (icon, name))


def _leader_dmg(run):
    lo, hi = gd.BASE_DMG_MIN, gd.BASE_DMG_MAX
    base = random.randint(lo, hi)
    return base + run["leader"]["dmg_bonus"] + run["temp_buffs"]["dmg"]


def _apply_ability_action(run, ability_key):
    """Applica l'effetto di un'abilita' attiva scelta dal giocatore per questo round.
    Ritorna (danno_al_nemico:int, righe_di_log:list, fuga:bool)."""
    log = []
    combat = run["combat"]
    if ability_key in ("negoziazione", "nebbia_illusoria"):
        run["used_once_abilities"].append(ability_key)
        combat["negotiated_escape"] = True
        verbo = "Le tue parole convincono il nemico a ritirarsi" if ability_key == "negoziazione" else "Sparisci nella nebbia, sottraendoti allo scontro"
        log.append("%s." % verbo)
        return 0, log, True

    if ability_key == "carica":
        run["used_once_abilities"].append(ability_key)
        dmg = _leader_dmg(run) * 3
        log.append("Carica! Un attacco devastante infligge %d danni." % dmg)
        return dmg, log, False

    if ability_key == "grido_di_guerra":
        run["temp_buffs"]["grido_di_guerra_rooms"] = 2
        log.append("Grido di Guerra: il tuo Seguito combatte con rinnovato vigore per le prossime stanze.")
        return 0, log, False

    if ability_key == "colpo_decisivo":
        dmg = _leader_dmg(run)
        if random.random() < 0.5:
            dmg *= 2
            log.append("Colpo Decisivo! Danno raddoppiato: %d." % dmg)
        else:
            log.append("Colpo Decisivo: infliggi %d danni." % dmg)
        return dmg, log, False

    if ability_key == "colpo_arcano":
        dmg = _leader_dmg(run) + 2
        log.append("Colpo Arcano: %d danni che ignorano parte delle difese nemiche." % dmg)
        return dmg, log, False

    if ability_key == "sigillo":
        combat["dmg"] = (max(0, combat["dmg"][0] - 2), max(1, combat["dmg"][1] - 2))
        log.append("Sigillo: il prossimo attacco del nemico sara' piu' debole.")
        return 0, log, False

    if ability_key == "rigenerazione_arcana":
        heal = 5
        run["leader"]["pv"] = min(run["leader"]["pv_max"], run["leader"]["pv"] + heal)
        log.append("Rigenerazione Arcana: recuperi %d Vita." % heal)
        return 0, log, False

    if ability_key == "esplosione_elementale":
        run["used_once_abilities"].append(ability_key)
        dmg = _leader_dmg(run) * (4 if combat["tier"] == "boss" else 2)
        log.append("Esplosione Elementale: %d danni!" % dmg)
        return dmg, log, False

    if ability_key == "patto_d_emergenza":
        run["used_once_abilities"].append(ability_key)
        run["treasure"] = {k: 0 for k in run["treasure"]}
        run["leader"]["pv"] = run["leader"]["pv_max"]
        run["leader"]["timore"] = run["leader"]["timore_max"]
        log.append("Patto d'Emergenza: spendi tutto il tesoro raccolto e guarisci completamente.")
        return 0, log, False

    if ability_key == "trattato_di_sangue":
        run["used_once_abilities"].append(ability_key)
        dmg = _leader_dmg(run) + 2
        log.append("Trattato di Sangue: infliggi %d danni." % dmg)
        if dmg >= combat["enemy_pv"]:
            run["seguito"].append({"type": "convertito", "alive": True, "charges": None})
            log.append("Il nemico sconfitto si unisce al tuo Seguito per il resto della spedizione.")
        return dmg, log, False

    if ability_key == "scorciatoia":
        run["used_once_abilities"].append(ability_key)
        log.append("Scorciatoia: eviti del tutto questa stanza.")
        return 0, log, "skip"

    # fallback di sicurezza (non dovrebbe accadere)
    log.append("Non succede nulla di rilevante.")
    return 0, log, False


def resolve_combat_round(run, action_key):
    """Risolve un intero round di combattimento con l'azione scelta dal giocatore.
    Ritorna lo stato ('in_corso' | 'vittoria' | 'sconfitta_morte' | 'sconfitta_timore' | 'fuga')."""
    combat = run["combat"]
    log = []

    if action_key == "attacco_fisico":
        dmg = _leader_dmg(run)
        log.append("Attacchi: infliggi %d danni." % dmg)
        escape = False
    else:
        dmg, ab_log, escape = _apply_ability_action(run, action_key)
        log.extend(ab_log)

    if escape == "skip":
        run["log"] = log
        run["combat"] = None
        return "salta_stanza"

    if escape:
        run["log"] = log
        run["combat"] = None
        return "fuga"

    # iniziativa: chi agisce per primo nel round (l'arciere favorisce il leader)
    has_arciere = any(m["alive"] and m["type"] == "arciere" for m in run["seguito"])
    leader_first_chance = 0.75 if has_arciere else 0.5
    leader_first = random.random() < leader_first_chance

    def apply_leader_damage_to_enemy():
        combat["enemy_pv"] -= dmg

    def enemy_turn():
        # purificatore: cura passiva a inizio del turno di scambio
        if any(m["alive"] and m["type"] == "purificatore" for m in run["seguito"]):
            heal = gd.PURIFICATORE_HEAL
            run["leader"]["pv"] = min(run["leader"]["pv_max"], run["leader"]["pv"] + heal)
            log.append("Il Purificatore cura %d Vita." % heal)

        is_fear = random.random() < combat["fear_chance"]
        if is_fear:
            base = random.randint(*combat["fear_dmg"]) if combat["fear_dmg"][1] > 0 else 0
            reduced = max(1 if base > 0 else 0, base - run["leader"]["mres"] - run["temp_buffs"]["mres"])
            run["leader"]["timore"] -= reduced
            log.append("Il nemico attacca la tua psiche: perdi %d Timore." % reduced)
        else:
            base = random.randint(*combat["dmg"])
            # Passo Leggero: primo colpo fisico del combattimento sempre schivato
            if has_ability(run, "passo_leggero") and not combat["first_hit_taken"]:
                combat["first_hit_taken"] = True
                log.append("Passo Leggero: schivi completamente il colpo.")
                return
            combat["first_hit_taken"] = True
            absorbed, residuo, seg_log = _seguito_absorb(run, base)
            log.extend(seg_log)
            if not absorbed or residuo > 0:
                final_armor = run["leader"]["armor"] + run["temp_buffs"]["armor"]
                dmg_to_leader = max(1, residuo - final_armor) if residuo > 0 else 0
                if dmg_to_leader > 0:
                    run["leader"]["pv"] -= dmg_to_leader
                    log.append("Subisci %d danni fisici." % dmg_to_leader)
                    if run["class"] == "Generale" and run["level"] >= 7 and not run["resistenza_triggered"]:
                        run["resistenza_triggered"] = True
                        run["leader"]["armor"] += 2
                        log.append("Resistenza: la tua Armatura aumenta permanentemente di 2.")

    if leader_first:
        apply_leader_damage_to_enemy()
        if combat["enemy_pv"] <= 0:
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
        if combat["enemy_pv"] <= 0:
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
    ultima_resistenza = run["class"] == "Generale" and run["level"] >= 10 and not run["ultima_resistenza_used"]
    if run["leader"]["pv"] <= 0:
        if ultima_resistenza:
            run["ultima_resistenza_used"] = True
            run["leader"]["pv"] = 1
            run["combat"]["enemy_pv"] -= 10
            log.append("Ultima Resistenza: sopravvivi con 1 Vita e contrattacchi per 10 danni!")
            run["log"] = log
            if run["combat"]["enemy_pv"] <= 0:
                return "vittoria"
            return None
        run["log"] = log
        return "sconfitta_morte"
    if run["leader"]["timore"] <= 0:
        run["log"] = log
        return "sconfitta_timore"
    return None


# ─── LOOT ─────────────────────────────────────────────────────────────────
def roll_loot(run, is_boss):
    resource = random.choice(gd.RESOURCE_TYPES)
    lo, hi = gd.BOSS_LOOT_AMOUNT if is_boss else gd.NORMAL_LOOT_AMOUNT
    amount = random.randint(lo, hi)
    if run["class"] == "Diplomatico" and run["level"] >= 5:
        amount = int(amount * 1.2) + 1
    if run["class"] == "Esploratore" and run["level"] >= 5:
        amount = int(amount * 1.5)
    run["treasure"][resource] = run["treasure"].get(resource, 0) + amount
    log = ["Bottino: +%d %s." % (amount, resource)]

    guaranteed_gold = gd.GUARANTEED_GOLD_BOSS if is_boss else gd.GUARANTEED_GOLD_NORMAL
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
    cost = gd.INCUDINE_BASE_COST
    if run["class"] == "Amministratore" and run["level"] >= 1:
        cost = max(1, cost - 1)
    return cost


def incudine_buff_amount(run):
    amount = gd.INCUDINE_BUFF_AMOUNT
    if run["class"] == "Amministratore" and run["level"] >= 7:
        amount *= 2
    return amount


def resolve_incudine(run, stat_choice):
    cost = incudine_cost(run)
    if run["treasure"].get("oro", 0) < cost:
        return ["Non hai abbastanza Oro: la Forgia resta silenziosa."]
    run["treasure"]["oro"] -= cost
    amount = incudine_buff_amount(run)
    run["temp_buffs"][stat_choice] = run["temp_buffs"].get(stat_choice, 0) + amount
    label = {"dmg": "Danno Fisico", "armor": "Armatura", "mres": "Resistenza Mentale"}[stat_choice]
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
    if run["class"] == "Amministratore" and run["level"] >= 10:
        xp += run["treasure"].get("oro", 0) // 2
    return xp
