# -*- coding: utf-8 -*-
"""Dati statici del minigioco di esplorazione (dungeon). Nessuna logica qui dentro,
solo le tabelle che il motore in dungeon_app.py consulta per risolvere stanze e
combattimenti."""

RESOURCE_TYPES = ["cibo", "legname", "pietra", "ferro", "gemme", "oro"]

# ─── SEGUITO (indipendente dalle truppe delle fazioni in chronicle.py) ───────
ENTOURAGE_TYPES = {
    "fante":        {"name": "Fante",                 "icon": "⚔️", "desc": "Assorbe un colpo fisico intero, poi cade."},
    "arciere":      {"name": "Arciere",                "icon": "🏹", "desc": "Aumenta la probabilità di agire per primi; quando agisci per primo, il tuo colpo infligge anche +2 danni."},
    "cavaliere":    {"name": "Cavaliere",               "icon": "🐎", "desc": "Possibilità di annullare del tutto un attacco fisico nemico."},
    "purificatore": {"name": "Purificatore",            "icon": "✨", "desc": "Cura un poco di Vita del leader a ogni round."},
    "guardiano":    {"name": "Guardiano",               "icon": "🪨", "desc": "Riduce il danno fisico subito più volte prima di cadere."},
    "martello":     {"name": "Compagni del Martello",   "icon": "🔨", "desc": "Non si consuma mai: infligge sempre 1 danno fisico al nemico a ogni round."},
    "vessillifero": {"name": "Vessillifero",            "icon": "🎺", "desc": "Finché è vivo, i tuoi attacchi e le tue abilità infliggono +1 danno fisico."},
    "sciamano":     {"name": "Sciamano",                "icon": "🔮", "desc": "Cura un poco di Timore del leader a ogni round."},
    "bardo":        {"name": "Bardo",                   "icon": "🎭", "desc": "Riduce la possibilità che il nemico colpisca il tuo Timore invece dei PV."},
    "novizio":      {"name": "Novizio",                 "icon": "🛡️", "desc": "A inizio di ogni combattimento genera un piccolo scudo fisico e mentale, poi si consuma."},
    "ariete":       {"name": "Ariete",                  "icon": "🏇", "desc": "Non si consuma mai: infligge sempre 1 danno al Timore del nemico a ogni round."},
    "penitente":    {"name": "Penitente",               "icon": "🕯️", "desc": "Ogni volta che cade un membro del Seguito, il leader recupera un po' di Timore."},
}
ENTOURAGE_MAX_PICK = 3
GUARDIANO_CHARGES = 3
GUARDIANO_REDUCTION = 3
CAVALIERE_WARD_CHANCE = 0.30
MERCENARIO_SUCCESS_CHANCE = 0.70
MARTELLO_COUNTER_DMG = 1
PURIFICATORE_HEAL = 2
SCIAMANO_HEAL = 2
BARDO_FEAR_REDUCTION = 0.15
NOVIZIO_SHIELD_PHYSICAL = 5
NOVIZIO_SHIELD_TIMORE = 5
ARIETE_COUNTER_DMG = 1
PENITENTE_TIMORE_BONUS = 2
ARCIERE_DMG_BONUS = 2

# ─── CLASSI E ABILITA' (5 per classe, sbloccate per livello) ────────────────
# type: 'danno' | 'supporto' | 'passiva' (le passive si applicano da sole, non si "usano")
CLASSES = {
    "Generale": {
        "icon": "⚔️",
        "abilities": [
            {"key": "martellata",              "lvl": 1, "name": "Martellata",                   "type": "danno",    "cd": 5, "desc": "3-5 danni; 50% di stordire il nemico per 1-2 turni."},
            {"key": "formazione_difensiva",    "lvl": 1, "name": "Formazione Difensiva",          "type": "supporto", "cd": 4, "desc": "+1 Armatura fino a fine combattimento; il prossimo colpo subito fa 3 danni in meno."},
            {"key": "doppio_colpo",            "lvl": 1, "name": "Doppio Colpo",                  "type": "danno",    "cd": 3, "desc": "Esegue due attacchi in un solo turno."},
            {"key": "vita_al_fronte",          "lvl": 3, "name": "Vita al Fronte",                "type": "supporto", "cd": 4, "desc": "Cura 1/4 della Vita massima."},
            {"key": "grido_di_guerra",         "lvl": 5, "name": "Grido di Guerra",                "type": "supporto", "cd": 4, "desc": "Non attacchi questo turno; +1 Danno fino a fine combattimento e il prossimo attacco infligge danno doppio."},
            {"key": "veterano_mille_battaglie","lvl": 7, "name": "Veterano di Mille Battaglie",    "type": "passiva",  "desc": "Sempre attiva: +2 Armatura e +2 Resistenza Mentale."},
            {"key": "fine_stratega",           "lvl": 9, "name": "Fine Stratega",                  "type": "supporto", "max_uses": 3, "desc": "Risana tutto il Seguito caduto e ottieni +1 casuale a Danno, Armatura o Resistenza Mentale (fino a 3 volte a run)."},
            {"key": "manovra_a_tenaglia",      "lvl": 10,"name": "Manovra a Tenaglia",             "type": "danno",    "once": True, "desc": "Sacrifichi tutto il Seguito rimasto: 8-10 danni al nemico per ogni truppa sacrificata."},
        ],
    },
    "Mago": {
        "icon": "✨",
        "abilities": [
            {"key": "colpo_arcano",     "lvl": 1,  "name": "Colpo Arcano",     "type": "danno",    "cd": 2, "desc": "4-6 danni; ogni utilizzo aumenta permanentemente di 1 il danno dei prossimi Colpi Arcani, per la durata del combattimento."},
            {"key": "scudo_magico",     "lvl": 1,  "name": "Scudo Magico",     "type": "supporto", "cd": 4, "desc": "Uno scudo assorbe i prossimi 5 danni fisici e i prossimi 6 danni al Timore, finche' dura o finche' il combattimento finisce."},
            {"key": "raggio_congelante","lvl": 1,  "name": "Raggio Congelante","type": "danno",    "cd": 3, "desc": "5-7 danni; 50% di rallentare il nemico, che agisce per ultimo per 2 turni."},
            {"key": "parola_guaritrice","lvl": 3,  "name": "Parola Guaritrice","type": "supporto", "cd": 4, "desc": "Cura 5-10 Vita e 6-12 Timore."},
            {"key": "potenziale_arcano","lvl": 5,  "name": "Potenziale Arcano","type": "passiva",  "desc": "Sempre attiva: +2 danno permanente al Colpo Arcano per tutta la run, +1 ulteriore per ogni Gemma raccolta."},
            {"key": "palla_di_fuoco",   "lvl": 7,  "name": "Palla di Fuoco",   "type": "danno",    "cd": 4, "desc": "7-12 danni; il nemico brucia per altri 2 danni nei 2 turni successivi."},
            {"key": "copie_illusorie",  "lvl": 9,  "name": "Copie Illusorie",  "type": "supporto", "cd": 5, "desc": "Per 3 turni, 70% di possibilita' di evitare completamente ogni colpo nemico."},
            {"key": "protezione_arcana","lvl": 10, "name": "Protezione Arcana","type": "passiva",  "once": True, "desc": "Sempre attiva: +1 Armatura, +3 Resistenza Mentale. La prima volta che Vita o Timore arrivano a 0, li recuperi entrambi a 1/3 del massimo invece di cadere (una volta a run)."},
        ],
    },
    "Diplomatico": {
        "icon": "🕊️",
        "abilities": [
            {"key": "orazione_esperta", "lvl": 1,  "name": "Orazione Esperta",    "type": "danno",    "cd": 2, "desc": "3-5 danni al Timore del nemico; 50% di rianimare una truppa caduta del tuo Seguito."},
            {"key": "littori_sacri",    "lvl": 1,  "name": "Littori Sacri",       "type": "danno",    "cd": 3, "desc": "5-8 danni fisici e 2-3 danni al Timore del nemico; una truppa a caso del tuo Seguito viene sacrificata."},
            {"key": "proteggimi",       "lvl": 1,  "name": "Proteggimi!",         "type": "supporto", "cd": 4, "desc": "Ottieni uno scudo di 3 Vita e 2 Timore per ogni truppa ancora attiva, fino a fine combattimento."},
            {"key": "bastione_della_fede","lvl": 3,"name": "Bastione della Fede", "type": "passiva",  "desc": "Sempre attiva: recuperi 2 Vita a turno, cumulabile col Purificatore del Seguito (4 Vita a turno insieme)."},
            {"key": "omelia_della_potenza","lvl": 5,"name": "Omelia della Potenza","type": "danno",   "cd": 4, "desc": "4-6 danni al Timore del nemico; 30% di critico che raddoppia il danno."},
            {"key": "omelia_della_salvezza","lvl": 7,"name": "Omelia della Salvezza","type": "passiva","once": True, "desc": "Sempre attiva: la prima volta che dovresti cadere a 0 Vita, ignori il danno e torni a 1 Vita (una volta a run)."},
            {"key": "messa_salvifica",  "lvl": 9,  "name": "Messa Salvifica",     "type": "supporto", "cd": 5, "desc": "Tutte le truppe cadute del Seguito vengono rianimate. Equipaggiandola, puoi portare 1 truppa in più nel Seguito.", "grants_extra_entourage": 1},
            {"key": "pontifex_maximus", "lvl": 10, "name": "Pontifex Maximus",    "type": "supporto", "cd": 8, "desc": "Azzera il cooldown di tutte le altre tue abilita' e ottieni +2 Armatura e +2 Resistenza Mentale fino a fine combattimento."},
        ],
    },
    "Esploratore": {
        "icon": "🧭",
        "abilities": [
            {"key": "strumenti_del_mestiere","lvl": 1, "name": "Strumenti del Mestiere","type": "passiva", "desc": "Sempre attiva: scegli liberamente 3 oggetti (solo rarita' base) dal catalogo, senza doverli possedere."},
            {"key": "colpo_di_lazo",        "lvl": 1,  "name": "Colpo di Lazo",         "type": "danno",    "cd": 2, "desc": "4-7 danni fisici."},
            {"key": "agilita_felina",       "lvl": 1,  "name": "Agilità Felina",        "type": "passiva",  "desc": "Sempre attiva: 20% di possibilita' di evitare completamente ogni colpo."},
            {"key": "parole_di_scherno",    "lvl": 3,  "name": "Parole di Scherno",     "type": "danno",    "cd": 4, "desc": "3-5 danni al Timore del nemico; il suo danno fisico e' ridotto di 3 per i 2 turni successivi."},
            {"key": "picconata_fortunata",  "lvl": 5,  "name": "Picconata Fortunata",   "type": "danno",    "cd": 3, "desc": "6-9 danni fisici; 15% di critico che raddoppia il danno."},
            {"key": "indovinelli_oscurita", "lvl": 7,  "name": "Indovinelli nell'Oscurità","type": "danno", "cd": 5, "desc": "3 tiri al 50%: ogni successo infligge 8 danni al nemico, ogni fallimento te ne infligge 4 (mitigati da scudi e armatura)."},
            {"key": "mappatore_esperto",    "lvl": 9,  "name": "Mappatore Esperto",     "type": "passiva",  "desc": "Sempre attiva: vedi in anticipo le stanze successive, e raddogli le risorse ottenute a fine combattimento."},
            {"key": "vie_segrete",          "lvl": 10, "name": "Vie Segrete",           "type": "supporto", "once": True, "room_action": True, "desc": "Una volta a run, salti tutte le stanze rimanenti e ti ritrovi direttamente davanti al miniboss."},
        ],
    },
    "Amministratore": {
        "icon": "📜",
        "abilities": [
            {"key": "esperto_saccheggiatore","lvl": 1, "name": "Esperto Saccheggiatore","type": "supporto", "cd": 3, "desc": "Trovi +5 unita' di una risorsa a caso tra Oro (60%), Legname (20%) e Pietra (20%)."},
            {"key": "acuto_osservatore",     "lvl": 1, "name": "Acuto Osservatore",     "type": "supporto", "cd": 3, "desc": "Individui i punti debili del nemico: potenzia il prossimo utilizzo di Raffica Micidiale."},
            {"key": "raffica_micidiale",     "lvl": 1, "name": "Raffica Micidiale",     "type": "danno",    "cd": 4, "desc": "3 colpi da 2 danni ciascuno; se potenziata da Acuto Osservatore, 3 colpi da 5-7 danni ciascuno."},
            {"key": "ogni_uomo_ha_un_prezzo","lvl": 3, "name": "Ogni Uomo ha un Prezzo","type": "danno",    "cd": 2, "desc": "4-5 danni al Timore del nemico."},
            {"key": "azzardo_economico",     "lvl": 5, "name": "Azzardo Economico",     "type": "danno",    "cd": 4, "desc": "Spendi tutto il tuo Oro: infligge 2 danni al Timore del nemico per ogni unita' di Oro speso."},
            {"key": "cani_della_guerra",     "lvl": 7, "name": "Cani della Guerra",     "type": "supporto", "cd": 6, "desc": "Attiri 3 mercenari al tuo servizio, che se ne andranno alla fine di questo combattimento."},
            {"key": "drago_della_finanza",   "lvl": 9, "name": "Drago della Finanza",   "type": "passiva",  "desc": "Sempre attiva: raddoppia tutti i guadagni ottenuti a fine combattimento."},
            {"key": "bancarotta",            "lvl": 10,"name": "Bancarotta",            "type": "supporto", "once": True, "room_action": True, "desc": "Massimo 1 volta a run: abbandoni la spedizione illeso, portando con te tutte le risorse raccolte fino a questo momento."},
        ],
    },
}

LEVEL_UNLOCK_THRESHOLDS = [1, 1, 1, 1, 10]  # le prime 4 abilita' sono disponibili da subito, la quinta (la piu' forte) resta un traguardo a lungo termine
XP_PER_LEVEL = 150  # livello = 1 + xp // XP_PER_LEVEL (fino a livello massimo)
MAX_LEVEL = 10

# ─── STATISTICHE BASE DEL LEADER ─────────────────────────────────────────────
BASE_PV = 28
BASE_TIMORE = 28
BASE_ARMOR = 0
BASE_MRES = 0
BASE_DMG_MIN, BASE_DMG_MAX = 3, 5

# Statistiche base per classe: solo le classi gia' ridisegnate hanno una voce qui.
# Le classi non ancora ridisegnate (in attesa del loro turno) usano i valori globali sopra,
# senza crescita per livello (esattamente come si comportavano finora).
CLASS_BASE_STATS = {
    "Generale": {"pv": 28, "timore": 32},
    "Mago": {"pv": 28, "timore": 28},
    "Diplomatico": {"pv": 28, "timore": 26},
    "Amministratore": {"pv": 26, "timore": 30},
    "Esploratore": {"pv": 26, "timore": 34},
}
CLASS_LEVEL_GROWTH = {
    "Generale": {"pv_per_level": 2, "timore_per_level": 1},
    "Mago": {"pv_per_level": 1, "timore_per_level": 2},
    "Diplomatico": {"pv_per_level": 2, "timore_per_level": 1},
    "Amministratore": {"pv_per_level": 2, "timore_per_level": 1},
    "Esploratore": {"pv_per_level": 2, "timore_per_level": 2},
}
# Range di danno del solo Attacco Fisico base, specifico per classe (fallback: BASE_DMG_MIN/MAX)
CLASS_BASE_DMG = {
    "Mago": (2, 3),
    "Diplomatico": (2, 3),
    "Amministratore": (2, 3),
    "Esploratore": (1, 2),
}
ABILITY_LOADOUT_SIZE = 4  # quante abilita' (Attacco incluso) si possono avere equipaggiate insieme

# ─── NEMICI PER STANZA (1..N, formula) E MINIBOSS ───────────────────────────
# Pool ampi per varieta': ogni combattimento sceglie a caso un nome dal pool del proprio
# livello di difficolta'. Le statistiche invece sono calcolate con una formula (get_enemy_tier),
# cosi' funzionano per qualunque numero di stanze senza dover riscrivere una tabella a mano.
ENEMY_POOLS = {
    1: [("Goblin Razziatore", "👺", "equilibrato"), ("Cane Selvatico", "🐺", "fisico"), ("Predone Solitario", "🗡️", "equilibrato"),
        ("Ratto Colossale", "🐀", "fisico"), ("Corvo Malato", "🐦", "mentale")],
    2: [("Orco Sbandato", "👹", "fisico"), ("Sciacallo delle Rovine", "🦴", "fisico"), ("Predone Armato", "🗡️", "equilibrato"),
        ("Goblin Sciamano", "👺", "mentale"), ("Cinghiale Furioso", "🐗", "fisico")],
    3: [("Ombra Vagante", "👻", "mentale"), ("Bandito Esperto", "🗡️", "equilibrato"), ("Orco Guerriero", "👹", "fisico"),
        ("Troll delle Paludi", "🧌", "fisico"), ("Nano Spergiuro", "🪓", "equilibrato")],
    4: [("Spettro del Confine", "👹", "mentale"), ("Fauna Corrotta", "🐗", "fisico"), ("Draugr Risvegliato", "💀", "mentale"),
        ("Purificatore Eretico", "✨", "mentale"), ("Troll da Guerra", "🧌", "fisico")],
    5: [("Cavaliere Caduto", "💀", "equilibrato"), ("Orrore Nebbioso", "👁️", "mentale"), ("Colosso di Pietra", "🗿", "fisico"),
        ("Orco Ancestrale", "👹", "fisico"), ("Nano Spergiuro Anziano", "🪓", "equilibrato")],
    6: [("Draugr Ancestrale", "💀", "mentale"), ("Purificatore Eretico Superiore", "✨", "mentale"), ("Colosso Runico", "🗿", "fisico"),
        ("Troll delle Cime", "🧌", "fisico"), ("Ombra Ancestrale", "👻", "mentale")],
    7: [("Colosso di Guerra", "🗿", "fisico"), ("Draugr Signore", "💀", "mentale"), ("Orco Sovrano", "👹", "fisico"),
        ("Purificatore Eretico Supremo", "✨", "mentale"), ("Nano Spergiuro Maledetto", "🪓", "equilibrato")],
}
BOSS_POOL = [("Il Signore delle Rovine", "👑", "equilibrato"), ("Il Colosso Corrotto", "🗿", "fisico"),
             ("Il Re-Ombra", "👻", "mentale"), ("Lo Spergiuro Eterno", "🪓", "equilibrato")]


def slugify(text):
    """'Purificatore Eretico' -> 'purificatore_eretico', per far combaciare il nome del
    nemico col file immagine in static/monsters/<slug>.png (o .jpg/.webp)."""
    import re
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()


def level_factor(level):
    """Usato per le RICOMPENSE (bottino/oro): +8% per livello oltre il primo."""
    return 1 + (level - 1) * 0.08


def enemy_power_factor(level):
    """Usato per PV/danno NEMICI: cresce piu' lentamente delle ricompense, cosi' il
    livello resta vantaggioso in senso assoluto (piu' bottino, nemici solo un po' piu' duri)."""
    return 1 + (level - 1) * 0.05


# ─── COMPORTAMENTI AGGIUNTIVI DEL NEMICO (oltre ad attacco fisico / al Timore) ─────
# Valori volutamente bassi: sono varianti tattiche, non un salto di difficolta'.
ENEMY_HEAL_CHANCE = 0.25       # per round, solo se il nemico e' sotto il 50% dei PV
ENEMY_HEAL_MIN, ENEMY_HEAL_MAX = 3, 5
ENEMY_BUFF_CHANCE = 0.12       # per round, solo se non ha gia' un buff attivo
ENEMY_BUFF_AMOUNT = 1
ENEMY_BUFF_TURNS = 3
ENEMY_DEBUFF_CHANCE = 0.12     # per round, solo se il giocatore non ha gia' un debuff attivo
ENEMY_DEBUFF_AMOUNT = 1
ENEMY_DEBUFF_TURNS = 3
ENEMY_BLEED_CHANCE = 0.12      # per round, solo se il giocatore non sta gia' sanguinando
ENEMY_BLEED_TURNS = 3
ENEMY_BLEED_DMG_NORMAL = (1, 2)  # per turno, nemici normali
ENEMY_BLEED_DMG_BOSS = 3         # per turno, solo boss/miniboss

# ─── BOSS SPECIALI (incontri unici, non nel pool casuale) ───────────────────
# Compaiono con una probabilita' propria quando si genera il miniboss di una run,
# al posto del solito pescaggio casuale da BOSS_POOL. Ognuno ha un moveset dedicato
# gestito a parte in engine.py (non usa il sistema generico cura/buff/debuff/sanguinamento).
IL_DIAULO = {
    "name": "IL DIAULO",
    "icon": "😈",
    "spawn_chance": 0.20,
    "armor": 2,
    "mres": 3,
    "dmg_timore_base": (8, 11),   # attacco base, danno al Timore
    "penetrazione_mres": 2,       # riduce la Res. Mentale effettiva SOLO per l'attacco base
    "veleno_dmg": 3,
    "veleno_turni": 3,
    "amico_rettiliani_chance": 0.35,
    "amico_rettiliani_dmg": (6, 8),        # fisico
    "amico_rettiliani_dmg_timore": (6, 8), # Timore
    "buttacettete_chance": 0.15,
    "buttacettete_dmg": (10, 16),
    "buttacettete_contraccolpo": (6, 8),
    "sfx_prefix": "il_diaulo_",  # static/sfx/il_diaulo_hit_dealt_1.mp3, ecc.
}

UOMORSOMAIALE = {
    "name": "Uomorsomaiale",
    "icon": "🐗",
    "spawn_chance": 0.20,  # solo se non e' gia' comparso IL DIAULO (controllato in engine.py)
    "armor": 0,
    "mres": 0,
    "pv_table": {1: 70, 5: 85, 10: 100},
    "timore_table": {1: 26, 5: 30, 10: 36},
    "dmg_base": (6, 10),
    "colpi_base": 2,             # l'attacco base colpisce 2 volte a turno
    "sventrare_dmg": (8, 14),
    "sventrare_cd": 5,
    "sventrare_bleed_dmg": 4,
    "sventrare_bleed_turni": 3,
    "ruggito_riduzione": 2,       # riduce il DANNO INFLITTO dal giocatore (non le sue difese)
    "ruggito_turni": 2,
    "ruggito_cd": 4,
    "sfx_prefix": "uomorsomaiale_",
}


def enemy_defense(archetype, level):
    """Armatura/Resistenza Mentale del nemico in base al suo archetipo e al livello del
    personaggio (le difese nemiche crescono col potere del party, non con la stanza).
    Valori ridotti di 1/3 rispetto alla formula grezza, per non essere troppo punitivi."""
    if archetype == "fisico":
        raw_armor, raw_mres = 2 + level // 3, level // 6
    elif archetype == "mentale":
        raw_armor, raw_mres = level // 6, 2 + level // 3
    else:  # equilibrato
        raw_armor = raw_mres = 1 + level // 4
    return round(raw_armor * 2 / 3), round(raw_mres * 2 / 3)


ENEMY_PV_MULTIPLIER = 1.3   # +30% ai PV base nemici (i giocatori li abbattevano troppo in fretta)

# Danno nemico: tabella tarata a mano da Amedeo dopo test live (sostituisce il vecchio
# moltiplicatore automatico). Valori esatti ai livelli 1/5/10, interpolati linearmente
# per i livelli intermedi (2-4, 6-9), cosi' la curva resta fedele a questi tre punti fissi.
ENEMY_DMG_TABLE = {
    1: {1: (4, 6),  5: (5, 7),   10: (6, 8)},
    2: {1: (4, 7),  5: (5, 8),   10: (6, 9)},
    3: {1: (5, 8),  5: (6, 9),   10: (7, 10)},
    4: {1: (6, 9),  5: (6, 10),  10: (8, 11)},
    5: {1: (7, 10), 5: (8, 11),  10: (9, 11)},
    6: {1: (8, 11), 5: (9, 12),  10: (10, 12)},
    7: {1: (9, 12), 5: (10, 13), 10: (11, 14)},
}
ENEMY_BOSS_DMG_TABLE = {1: (10, 14), 5: (11, 16), 10: (13, 18)}


def _interp_dmg(table_by_level, level):
    """Interpola linearmente (min, max) tra i livelli-ancora piu' vicini presenti
    nella tabella, arrotondando all'intero. Fuori range, resta sull'estremo."""
    keys = sorted(table_by_level.keys())
    if level <= keys[0]:
        return table_by_level[keys[0]]
    if level >= keys[-1]:
        return table_by_level[keys[-1]]
    lo = max(k for k in keys if k <= level)
    hi = min(k for k in keys if k >= level)
    if lo == hi:
        return table_by_level[lo]
    lo_v, hi_v = table_by_level[lo], table_by_level[hi]
    t = (level - lo) / (hi - lo)
    return (round(lo_v[0] + (hi_v[0] - lo_v[0]) * t),
            round(lo_v[1] + (hi_v[1] - lo_v[1]) * t))


def get_enemy_tier(n, level=1):
    """Statistiche del nemico per la stanza n (1-based) e il livello del personaggio."""
    pool = ENEMY_POOLS.get(n, ENEMY_POOLS[max(ENEMY_POOLS.keys())])
    pv = round((8 + 2 * (n - 1)) * ENEMY_PV_MULTIPLIER * enemy_power_factor(level))
    table = ENEMY_DMG_TABLE.get(n, ENEMY_DMG_TABLE[max(ENEMY_DMG_TABLE.keys())])
    dmg_min, dmg_max = _interp_dmg(table, level)
    fear_chance = max(0.0, min(0.6, (n - 2) * 0.12))
    fear_dmg = (dmg_min + 1, dmg_max + 1) if fear_chance > 0 else (0, 0)
    return {"pv": pv, "dmg": (dmg_min, dmg_max), "fear_chance": fear_chance, "fear_dmg": fear_dmg, "pool": pool}


def get_boss_tier(rooms_per_run, level=1):
    """Il miniboss scala in base al numero di stanze della run e al livello del personaggio:
    PV sempre circa 1.75x l'ultima stanza normale, danno dalla tabella tarata a mano."""
    last = get_enemy_tier(rooms_per_run, level)
    pv = int(last["pv"] * 1.75)
    dmg = _interp_dmg(ENEMY_BOSS_DMG_TABLE, level)
    return {"pv": pv, "dmg": dmg, "fear_chance": 0.5, "fear_dmg": (dmg[0], dmg[1]), "pool": BOSS_POOL}

ROOMS_PER_RUN = 7

# ─── TIPI DI STANZA ───────────────────────────────────────────────────────────
ROOM_TYPES = {
    "battaglia":         {"icon": "⚔️", "name": "Sala delle Ombre",     "desc": "Un nemico si cela nell'oscurità."},
    "fontana":           {"icon": "⛲", "name": "Fontana Sacra",        "desc": "Le acque risanano le ferite."},
    "incudine":          {"icon": "🔨", "name": "Forgia Antica",        "desc": "Investi il tesoro in un potenziamento per questa run."},
    "sacco_monete":      {"icon": "💰", "name": "Sacco di Monete",      "desc": "Assumi un mercenario temporaneo."},
    "stanza_misteriosa": {"icon": "❔", "name": "Stanza Misteriosa",    "desc": "Qualcosa di inaspettato ti attende — non saprai cosa finché non entri."},
}

MYSTERY_ROOM_CHANCE = 0.20  # come la Fontana: conclude la stanza, salta il combattimento

# ─── EVENTI DELLA STANZA MISTERIOSA (uno pescato a caso ogni volta) ─────────
# Ogni evento ha sempre un'opzione "sicura" al 100% oltre a quelle rischiose.
MYSTERY_EVENTS = {
    "calice": {
        "name": "Il Calice Colmo", "icon": "🍷",
        "text": "Ti trovi in una stanza buia con una flebile luce puntata su un calice ricolmo di uno strano liquido.",
        "options": [("bevi", "Bevi il contenuto"), ("rovescia", "Rovescialo per terra"), ("ignora", "Ignoralo e cerca la via d'uscita")],
    },
    "specchio": {
        "name": "Lo Specchio Incrinato", "icon": "🪞",
        "text": "Un riflesso distorto ti fissa da uno specchio incrinato appoggiato al muro.",
        "options": [("distruggi", "Distruggilo"), ("fissa", "Fissalo a lungo"), ("ignora", "Ignoralo e prosegui")],
    },
    "cripta": {
        "name": "La Cripta Sigillata", "icon": "⚰️",
        "text": "Una cripta di pietra, sigillata da secoli, promette qualcosa al suo interno.",
        "options": [("forza_pv", "Forzala (paga Vita)"), ("forza_timore", "Forzala (paga Timore)"), ("lascia", "Lasciala stare")],
    },
    "mercante": {
        "name": "Il Mercante Errante", "icon": "🧙",
        "text": "Una figura incappucciata emerge dall'ombra, offrendoti uno scambio.",
        "options": [("accetta", "Accetta lo scambio"), ("rifiuta", "Rifiuta e vai via")],
    },
    "sussurro": {
        "name": "Il Sussurro nel Buio", "icon": "👂",
        "text": "Qualcosa nel buio bisbiglia la tua paura più grande.",
        "options": [("resisti", "Resisti e prosegui"), ("ascolta", "Ascolta il sussurro")],
    },
    "altare": {
        "name": "L'Altare Dimenticato", "icon": "🕯️",
        "text": "Un altare coperto di polvere sembra ancora attivo, in cerca di un'offerta.",
        "options": [("offri", "Offri Oro"), ("non_offrire", "Non offrire nulla")],
    },
    "catene": {
        "name": "Le Catene Spezzate", "icon": "⛓️",
        "text": "Una figura incatenata ti osserva in silenzio, in attesa di una decisione.",
        "options": [("libera", "Liberalo"), ("lascia", "Lascialo incatenato")],
    },
    "biblioteca": {
        "name": "La Biblioteca Polverosa", "icon": "📚",
        "text": "Scaffali carichi di tomi dimenticati riempiono la stanza.",
        "options": [("studia", "Studia i tomi"), ("vai_via", "Vai via")],
    },
    "rituale": {
        "name": "Il Rituale a Metà", "icon": "🔮",
        "text": "Un cerchio rituale incompiuto attende che qualcuno lo completi.",
        "options": [("completa", "Completalo"), ("lascia", "Lascialo incompiuto")],
    },
    "baratto": {
        "name": "Il Baratto di Sangue", "icon": "🩸",
        "text": "Un patto silenzioso ti viene offerto: il tuo sangue in cambio di potere.",
        "options": [("offri_pv", "Offri Vita"), ("rifiuta", "Rifiuta")],
    },
    "statua": {
        "name": "La Statua Piangente", "icon": "🗿",
        "text": "Una statua di pietra piange lacrime che non dovrebbero esistere.",
        "options": [("consola", "Consolala"), ("deridi", "Deridila"), ("ignora", "Ignorala")],
    },
    "forziere": {
        "name": "Il Forziere Incatenato", "icon": "🔒",
        "text": "Un forziere chiuso da pesanti catene arrugginite giace in un angolo.",
        "options": [("scassina", "Scassinalo"), ("lascia", "Lascialo stare")],
    },
}

MYSTERY_VELENO_DMG = 4
MYSTERY_VELENO_TURNI = 3
MYSTERY_SPECCHIO_DANNO = 3
MYSTERY_TIMORE_PICCOLO = 5
MYSTERY_CRIPTA_COSTO = 5
MYSTERY_MERCANTE_RISORSA_COSTO = 3
MYSTERY_SUSSURRO_TIMORE_COSTO = 3
MYSTERY_SUSSURRO_TIMORE_GRAVE = 12
MYSTERY_SUSSURRO_XP_BONUS = 15
MYSTERY_ALTARE_COSTO_ORO = 4
MYSTERY_ALTARE_CURA = 8
MYSTERY_CATENE_TIMORE_TRAPPOLA = 6
MYSTERY_BIBLIOTECA_XP_BONUS = 10
MYSTERY_RITUALE_DEBUFF_DANNO = 2
MYSTERY_RITUALE_DEBUFF_TURNI = 2
MYSTERY_BARATTO_COSTO_PV = 6
MYSTERY_STATUA_TIMORE_BONUS = 4
MYSTERY_STATUA_TIMORE_TRAPPOLA = 6
MYSTERY_STATUA_ORO_BONUS = 3
MYSTERY_FORZIERE_ORO_BONUS = 6
MYSTERY_FORZIERE_PV_TRAPPOLA = 6

INCUDINE_BASE_COST = 3   # in Oro
INCUDINE_BUFF_AMOUNT = 1
SACCO_MONETE_COST = 5    # in Oro
FONTANA_APPEARANCE_CHANCE = 0.25  # probabilita' che la Fontana compaia come opzione (solo dalla stanza 4 in poi)
FONTANA_MIN_ROOM = 4  # numero di stanza (1-based) da cui la Fontana puo' iniziare a comparire

INCUDINE_OPTIONS = [
    {"stat": "dmg",   "label": "+1 Danno Fisico"},
    {"stat": "armor", "label": "+1 Armatura"},
    {"stat": "mres",  "label": "+1 Resistenza Mentale"},
]

# ─── PASSIVE DI CLASSE (sempre attive, non occupano uno slot equipaggiabile) ─
CLASS_PASSIVES = {
    "Generale": {
        "key": "ira_funesta", "name": "Ira Funesta", "icon": "😡",
        "desc": "Quando scendi sotto il 50% dei PV o del Timore, tutte le tue abilità e i tuoi attacchi infliggono +3 danni.",
    },
    "Mago": {
        "key": "esperto_catalogatore", "name": "Esperto Catalogatore", "icon": "💎",
        "desc": "30% di possibilità di ottenere una Gemma bonus dopo ogni combattimento.",
    },
    "Diplomatico": {
        "key": "pretoriani", "name": "Pretoriani", "icon": "🛡️",
        "desc": "Ad ogni turno, recuperi 1 Vita e 1 Timore per ogni truppa ancora in vita nel tuo Seguito.",
    },
    "Esploratore": {
        "key": "sforzo_adrenalinico", "name": "Sforzo Adrenalinico", "icon": "⚡",
        "desc": "Contro Boss e Miniboss: guadagni il 25% dei tuoi PV e Timore massimi come scudo a inizio combattimento, e tutte le tue mosse hanno un ulteriore 10% di possibilità di infliggere un colpo critico.",
    },
    "Amministratore": {
        "key": "abile_nelle_trattative", "name": "Abile nelle Trattative", "icon": "🤝",
        "desc": "Il primo potenziamento della Forgia in ogni run è gratuito (i primi 2, dal livello 10 in su).",
    },
}

# ─── LOOT (stanze di battaglia normali e miniboss) ──────────────────────────
NORMAL_LOOT_AMOUNT = (2, 4)
BOSS_LOOT_AMOUNT = (4, 8)
GUARANTEED_GOLD_NORMAL = 1
GUARANTEED_GOLD_BOSS = 3
NORMAL_ITEM_DROP_CHANCE = 0.05
BOSS_ITEM_DROP_CHANCE = 0.65
# pesi di rarita' per i due contesti di drop (normal vs boss)
NORMAL_DROP_RARITY_WEIGHTS = {"base": 0.90, "epica": 0.08, "leggendaria": 0.02}
BOSS_DROP_RARITY_WEIGHTS = {"base": 0.20, "epica": 0.50, "leggendaria": 0.30}

# ─── OGGETTI EQUIPAGGIABILI (persistenti, slot: arma | armatura) ───────────
ITEMS = {
    # ARMI
    "spada_novizio":        {"name": "Spada del Novizio",              "slot": "arma", "rarity": "base",        "effects": {"dmg": 1},                       "lore": "Consegnata a ogni giovane guardia dell'Arcontato il giorno del giuramento; la lama non ha ancora versato sangue."},
    "ascia_boscaiolo":       {"name": "Ascia da Boscaiolo",             "slot": "arma", "rarity": "base",        "effects": {"dmg": 2},                       "lore": "Più adatta a spaccare legna che carne, ma nelle mani giuste fa comunque il suo."},
    "stiletto_veloce":       {"name": "Stiletto Veloce",                "slot": "arma", "rarity": "base",        "effects": {"dmg": 1, "iniziativa": 1},      "lore": "Preferito dagli agenti del Velarium: colpisce prima che l'avversario capisca cosa sia successo."},
    "martello_compagni":     {"name": "Martello dei Compagni",         "slot": "arma", "rarity": "base",        "effects": {"dmg": 2, "stordisce_pct": 0.10},"lore": "Forgiato nelle fucine di Karag-Duraz, porta il sigillo dei Compagni del Martello."},
    "bastone_runico":        {"name": "Bastone Runico",                 "slot": "arma", "rarity": "base",        "effects": {"dmg": 1, "dmg_abilita": 1},     "lore": "Intagliato con rune che nessun vivente sa più leggere per intero."},
    "lama_giuramento":       {"name": "Lama del Giuramento Spezzato",   "slot": "arma", "rarity": "epica",       "effects": {"dmg": 3, "ignora_difese_pct": 0.15}, "lore": "Si dice fosse impugnata da un Arconte caduto, spergiuro alla propria stessa causa."},
    "frusta_nebbia":         {"name": "Frusta di Nebbia",               "slot": "arma", "rarity": "epica",       "effects": {"dmg": 2, "dmg_timore_nemico": 2}, "lore": "Tessuta con fili di bruma del Velarium, lascia chi la subisce incerto se sia stata reale."},
    "spezzacielo":           {"name": "Spezzacielo",                    "slot": "arma", "rarity": "leggendaria", "effects": {"dmg": 5, "critico_colpisce_timore": True}, "lore": "Il colpo finale di un condottiero mai nominato nelle cronache ufficiali, per volere di chi vinse quella guerra."},
    # ARMATURE FISICHE
    "corazza_cuoio":         {"name": "Corazza di Cuoio Bollito",       "slot": "armatura", "rarity": "base",        "effects": {"armor": 1},                     "lore": "L'equipaggiamento standard di ogni recluta della Casta Operosa."},
    "scudo_confine":         {"name": "Scudo Rotondo del Confine",      "slot": "armatura", "rarity": "base",        "effects": {"armor": 2, "iniziativa": -1},   "lore": "Portato dai coloni ai margini delle terre selvagge, più per intimidire che per combattere."},
    "piastre_naniche":       {"name": "Piastre Runiche Naniche",        "slot": "armatura", "rarity": "base",        "effects": {"armor": 1, "mres": 1},          "lore": "I nani di Karag-Duraz temprano il metallo e lo spirito nella stessa fucina."},
    "armatura_sigillo":      {"name": "Armatura del Sigillo Infranto",  "slot": "armatura", "rarity": "epica",       "effects": {"armor": 3, "riflette_pct": 0.10}, "lore": "Un tempo proteggeva un tempio ormai crollato; protegge ancora, a modo suo."},
    "egida_bastione":        {"name": "Egida dell'Ultimo Bastione",     "slot": "armatura", "rarity": "leggendaria", "effects": {"armor": 5, "raddoppio_sotto_quarto": True}, "lore": "Indossata da chi non ha mai indietreggiato — e non è mai tornato a raccontarlo."},
    # RESISTENZA MENTALE (stesso slot armatura)
    "amuleto_quiete":        {"name": "Amuleto della Quiete",          "slot": "armatura", "rarity": "base",        "effects": {"mres": 1},                      "lore": "Un ciondolo semplice, benedetto dai sacerdoti dell'Arcontato per calmare i nuovi coloni."},
    "bracciale_filo":        {"name": "Bracciale dei Figli del Filo",  "slot": "armatura", "rarity": "base",        "effects": {"mres": 1, "negoziazione_pct": 0.10}, "lore": "Intrecciato dagli Iorph per chi cerca la parola prima della lama."},
    "collana_silenzio":      {"name": "Collana del Silenzio",          "slot": "armatura", "rarity": "base",        "effects": {"mres": 2},                      "lore": "Tolta dal collo di un cadavere che, dicono, non aveva mai smesso di sorridere."},
    "mantello_bruma":        {"name": "Mantello di Bruma Sottile",     "slot": "armatura", "rarity": "epica",       "effects": {"mres": 2, "armor": 1},          "lore": "Chi lo indossa dice di sentire meno il freddo — e meno anche la paura."},
    "velo_nebrahil":         {"name": "Velo della Nébrahil",           "slot": "armatura", "rarity": "leggendaria", "effects": {"mres": 3, "immunita_primo_pauroso": True}, "lore": "Si narra fosse indossato dalla Regina stessa, nei giorni in cui la nebbia sembrava non finire mai."},
}

EQUIP_SLOTS = ["slot_arma", "slot_armatura", "slot_jolly"]  # jolly: arma o armatura, a scelta
LOOT_LEVEL_SCALING = True  # se True, roll_loot() applica level_factor() al bottino

# ─── COSTANTI PER GLI EFFETTI EPICI/LEGGENDARI (vedi ITEMS sopra) ───────────
ITEM_CRIT_CHANCE = 0.15          # Spezzacielo: probabilita' di colpo critico per round
RADDOPPIO_SOTTO_QUARTO_SOGLIA = 0.25  # Egida dell'Ultimo Bastione: soglia di Vita sotto cui l'Armatura raddoppia
# In PvE il Bardo riduce la probabilita' che il nemico scriptato colpisca il Timore
# invece della Vita (BARDO_FEAR_REDUCTION) — un concetto che non esiste in un duello
# PvP, dove il tipo di danno dipende dall'abilita' scelta dall'avversario, non da un
# tiro casuale. Variante per l'arena: riduce direttamente il danno al Timore subito.
BARDO_ARENA_TIMORE_REDUCTION = 1

# In arena i danni sono spesso bassi rispetto a difese elevate: raddoppia tutte le
# fonti di danno (attacchi, abilita', contrattacchi del Seguito, bruciature), non
# le difese - applicato in un solo punto per l'azione (_arena_apply_damage) e per i
# tick automatici (Martello/Ariete/bruciatura) in resolve_arena_round.
ARENA_DMG_MULTIPLIER = 2

# Gilda degli Avventurieri: valore in "gloria" (una risorsa a parte, per la classifica
# della cassa comune) di un boss battuto — none/il_diaulo/uomorsomaiale come chiave.
GUILD_GLORIA_VALUES = {None: 10, "il_diaulo": 50, "uomorsomaiale": 100}


def format_item_effects(effects):
    """Rende leggibile in italiano ogni effetto meccanico di un oggetto — di base,
    epico o leggendario che sia. Tutti i flag qui sotto sono collegati a una logica
    reale in engine.py."""
    parts = []
    if effects.get("dmg"):
        parts.append("%+d Danno" % effects["dmg"])
    if effects.get("armor"):
        parts.append("%+d Armatura" % effects["armor"])
    if effects.get("mres"):
        parts.append("%+d Res. Mentale" % effects["mres"])
    if effects.get("iniziativa"):
        parts.append("%+d Iniziativa" % effects["iniziativa"])
    if effects.get("dmg_abilita"):
        parts.append("%+d danno quando usi un'abilità" % effects["dmg_abilita"])
    if effects.get("stordisce_pct"):
        parts.append("%d%% di stordire per 1 turno il nemico colpito" % round(effects["stordisce_pct"] * 100))
    if effects.get("ignora_difese_pct"):
        parts.append("%d%% di ignorare del tutto l'Armatura nemica sul colpo" % round(effects["ignora_difese_pct"] * 100))
    if effects.get("dmg_timore_nemico"):
        parts.append("+%d danno al Timore nemico a ogni colpo fisico" % effects["dmg_timore_nemico"])
    if effects.get("critico_colpisce_timore"):
        parts.append("%d%% di colpo critico (danno raddoppiato) che colpisce anche il Timore nemico" % round(ITEM_CRIT_CHANCE * 100))
    if effects.get("riflette_pct"):
        parts.append("riflette il %d%% dei danni fisici subiti sul nemico" % round(effects["riflette_pct"] * 100))
    if effects.get("raddoppio_sotto_quarto"):
        parts.append("raddoppia l'Armatura quando sei sotto 1/4 di Vita")
    if effects.get("immunita_primo_pauroso"):
        parts.append("annulla il primo attacco che colpirebbe il Timore in ogni combattimento")
    if effects.get("negoziazione_pct"):
        parts.append("-%d%% al costo di Forgia e Mercenario" % round(effects["negoziazione_pct"] * 100))
    return ", ".join(parts) if parts else "Nessun effetto meccanico attivo al momento"

# ─── RIEPILOGO DISCORD (embed narrativo a fine spedizione) ──────────────────
# Ogni voce e' (titolo, descrizione), con {name} e {faction} sostituiti a runtime
# (mai nomi di luoghi o fazioni inventati: solo la fazione vera del personaggio,
# cosi' non puo' mai comparire fuori contesto). "sconfitta_morte" NON è la morte
# del personaggio: la spedizione collassa e si perde tutto il bottino raccolto,
# ma il personaggio resta vivo e giocabile dal turno successivo.
DISCORD_EMBED_COLORS = {
    "vittoria": 0x2ecc71,
    "sconfitta_morte": 0x8c2a2a,
    "sconfitta_timore": 0x4a2a7a,
    "ritirata_bancarotta": 0xc4962a,
}

DISCORD_NARRATIVE = {
    "vittoria": {
        "Generale": [
            ("Il Generale {name} è tornato dalle profondità",
             "Emerge coperto di polvere e sangue non suo, il passo pesante ma il capo alto. {faction} avrà una nuova storia da raccontare stanotte."),
            ("{name} ha spezzato ogni resistenza nel dungeon",
             "Torna con l'armatura ammaccata e lo sguardo di chi non ha mai dubitato dell'esito. Un altro pericolo per {faction} è stato ridotto in polvere."),
            ("Vittoria per {name}",
             "Nessuna cerimonia, nessun proclama: solo un soldato che torna da un compito portato a termine, come sempre."),
        ],
        "Mago": [
            ("{name} torna con nuovi appunti (e qualche ustione)",
             "Il dungeon ha offerto più risposte di quante ne cercasse, e {name} le ha annotate tutte prima di andarsene. {faction} ne trarrà beneficio."),
            ("Un altro enigma risolto da {name}",
             "Torna borbottando formule e schemi ancora da verificare, ma con addosso l'aria soddisfatta di chi ha imparato qualcosa di nuovo."),
            ("{name} ha domato le profondità con la sola volontà",
             "Il fuoco arcano ha aperto la strada; {faction} accoglie un mago un po' più esperto e un po' più insonne."),
        ],
        "Diplomatico": [
            ("{name} ha portato la Fede nelle profondità",
             "Emerge con la stola macchiata ma lo sguardo fermo, come chi ha guardato l'oscurità negli occhi e le ha recitato una litania in faccia. I fedeli di {faction} accoglieranno questa storia come una nuova parabola."),
            ("Un nuovo segno per {name}",
             "Torna intonando sottovoce un canto di ringraziamento, convinto che nulla di ciò che ha visto sia stato lasciato al caso. {faction} avrà un'altra prova della sua devozione."),
            ("Il voto di {name} è stato onorato",
             "Le profondità hanno messo alla prova la sua fede più delle sue armi, ed entrambe hanno retto. Torna a {faction} con reliquie e certezze rinnovate."),
        ],
        "Esploratore": [
            ("{name} ha trovato una via anche dove non ce n'era",
             "Torna con il fiuto ancora acceso e le tasche piene di cose che, giura, valgono più di quanto sembrino. {faction} approva, per una volta senza fare domande."),
            ("Un'altra scommessa vinta da {name}",
             "Il dungeon nascondeva più insidie del previsto, ma niente che un po' di sangue freddo e fortuna sfacciata non potessero risolvere."),
            ("{name} torna dalle profondità con un sorriso storto",
             "Non tutto è andato come previsto, ma è andato bene lo stesso — e per {name} è già una vittoria."),
        ],
        "Amministratore": [
            ("{name} ha chiuso i conti in attivo",
             "Ogni rischio calcolato, ogni spesa giustificata: torna con un bilancio che farebbe invidia a qualunque casa di {faction}."),
            ("Un investimento ben riuscito per {name}",
             "Le profondità si sono rivelate un affare redditizio. I registri di {faction} si arricchiscono di una voce molto positiva."),
            ("{name} ha portato a casa il profitto atteso",
             "Nessun imprevisto che i numeri non avessero già previsto. Un'altra spedizione, un altro margine di guadagno."),
        ],
    },
    "sconfitta_morte": {
        "Generale": [
            ("{name} è stato ricacciato indietro, a mani vuote",
             "Il Seguito lo ha portato fuori privo di sensi ma vivo; tutto ciò che aveva raccolto è andato perduto nelle profondità. {faction} rifletterà a lungo su cosa sia andato storto."),
            ("La spedizione di {name} è crollata sotto i colpi nemici",
             "Torna a {faction} con l'orgoglio più ferito del corpo, e nessun bottino da mostrare per il rischio corso."),
            ("{name} è stato costretto alla ritirata più dura",
             "Sconfitto ma non perduto: le profondità gli hanno tolto tutto tranne la possibilità di riprovarci."),
        ],
        "Mago": [
            ("Un calcolo sbagliato per {name}",
             "Qualcosa nel dungeon non seguiva le regole previste. Torna a {faction} intero ma svuotato di ogni componente e appunto raccolto."),
            ("{name} è stato sopraffatto prima di completare lo studio",
             "Le profondità hanno vinto questa volta; tornerà a {faction} con qualche teoria in meno da dimostrare, e a mani vuote."),
            ("Il rituale di {name} si è interrotto a metà",
             "Portato fuori esausto dal proprio Seguito, non resta nulla di ciò che aveva trovato — solo la lezione, amara, di aver sottovalutato il pericolo."),
        ],
        "Diplomatico": [
            ("La fede di {name} è stata messa a dura prova, e la spedizione è crollata",
             "Il Seguito lo ha portato fuori vivo ma privo di ogni reliquia raccolta. {faction} pregherà per lui questa notte."),
            ("{name} non ha ottenuto il segno che cercava",
             "Le profondità gli hanno negato ogni grazia, e con essa ogni bottino. Torna a {faction} intero nel corpo, umiliato nello spirito."),
            ("Un voto interrotto per {name}",
             "La spedizione si è chiusa prima del tempo, e con essa ogni cosa raccolta lungo il cammino. Resta la fede; il resto è perduto."),
        ],
        "Esploratore": [
            ("{name} ha spinto la fortuna oltre il limite",
             "Questa volta è andata male: portato fuori privo di sensi, senza nulla da mostrare per il rischio corso. {faction} lo accoglierà comunque, come sempre."),
            ("La scommessa di {name} non ha pagato",
             "Torna a {faction} con le tasche vuote quanto lo sguardo — ma torna, ed è già qualcosa."),
            ("{name} è stato ricacciato fuori dalle profondità",
             "Nessun bottino, nessuna scusa: solo la certezza che la prossima volta andrà diversamente."),
        ],
        "Amministratore": [
            ("Un bilancio in perdita per {name}",
             "Il rischio calcolato questa volta non ha pagato: torna a {faction} vivo ma senza un solo bene da registrare a proprio favore."),
            ("{name} ha dovuto segnare la spedizione come perdita totale",
             "Nessun profitto, nessuna consolazione contabile — solo la certezza di essere tornato in vita, che almeno quella non si registra a debito."),
            ("Le profondità hanno azzerato il guadagno di {name}",
             "Portato fuori dal proprio Seguito senza nulla in mano, dovrà rifarsi al prossimo turno."),
        ],
    },
    "sconfitta_timore": {
        "Generale": [
            ("{name} si è ritirato, la mente scossa ma il bottino salvo",
             "Le ombre del dungeon erano insopportabili anche per un veterano come lui. Il corpo è tornato integro, e con sé ciò che era già stato raccolto."),
            ("Il coraggio di {name} ha ceduto, non le mani",
             "Torna a {faction} con lo sguardo turbato, ma con ogni cosa trovata lungo il cammino ancora al sicuro."),
            ("{name} ha scelto di fermarsi prima che fosse troppo tardi",
             "Il Timore ha avuto la meglio sull'ambizione, ma non sul buon senso: torna a {faction} con il bottino intatto."),
        ],
        "Mago": [
            ("Qualcosa nelle profondità ha spezzato la concentrazione di {name}",
             "Torna scosso ma lucido a sufficienza da non aver lasciato nulla indietro. {faction} studierà con cautela ciò che ha visto."),
            ("{name} si è ritirato davanti a un orrore che i libri non descrivevano",
             "La mente vacilla, ma le mani hanno tenuto stretto ogni componente raccolto."),
            ("Il Timore ha avuto la meglio su {name}, non sulla sua borsa",
             "Torna turbato ma con il bottino al sicuro, pronto a consultare i testi di {faction} su ciò che ha visto."),
        ],
        "Diplomatico": [
            ("La fede di {name} ha vacillato, ma non è caduta",
             "Le profondità hanno mostrato qualcosa che nessuna preghiera sembrava poter placare. Si ritira, portando comunque con sé ogni reliquia raccolta."),
            ("{name} ha scelto la ritirata, non la disperazione",
             "Torna a {faction} turbato nello spirito ma saldo nel possesso di ciò che ha trovato."),
            ("Un'ombra che nemmeno {name} sapeva come esorcizzare",
             "Si ritira con il Timore ancora addosso, ma con il bottino intatto — la fede, dice, tornerà con il riposo e la preghiera."),
        ],
        "Esploratore": [
            ("Anche {name} conosce il momento di fermarsi",
             "Il dungeon ha mostrato i denti, e stavolta ha scelto di ritirarsi invece di rischiare tutto. Il bottino resta comunque suo."),
            ("{name} si è ritirato con la pelle d'oca e le tasche piene",
             "Non tutte le battaglie vanno combattute fino in fondo: torna scosso, ma con tutto ciò che aveva già racimolato."),
            ("Il fiuto di {name} gli ha detto di tornare indietro",
             "Meglio vivi e turbati che morti e con un bottino più grande, dice — e nessuno a {faction} può contraddirlo."),
        ],
        "Amministratore": [
            ("{name} ha fatto un calcolo del rischio, e ha vinto la prudenza",
             "Il Timore accumulato superava il valore atteso di continuare. Si ritira, portando comunque a casa ogni guadagno fatto finora."),
            ("Una ritirata prudente per {name}",
             "I nervi hanno ceduto prima dei conti: torna a {faction} turbato ma con il bilancio della spedizione ancora in attivo."),
            ("{name} ha scelto di non rischiare l'intero capitale",
             "Il Timore ha imposto una pausa, non una perdita: ogni risorsa raccolta resta al sicuro nei suoi registri."),
        ],
    },
    "ritirata_bancarotta": {
        "Amministratore": [
            ("{name} ha dichiarato la spedizione conclusa — per convenienza",
             "Con le casse abbastanza piene e la voglia di rischiare ormai esaurita, ha deciso che il bottino di oggi bastava. I suoi registri approvano."),
            ("Una ritirata strategica, dice {name}",
             "Nessuna sconfitta, nessun pericolo imminente: solo la fredda conclusione che continuare non avrebbe migliorato il bilancio. Torna a {faction} con tutto ciò che aveva raccolto."),
            ("{name} ha chiuso i conti in anticipo",
             "Perché rischiare un profitto già solido? Si ritira con ogni risorsa al sicuro, soddisfatto della propria disciplina."),
        ],
    },
}

# ─── NARRATIVA DEI BOSS SPECIALI (sostituisce DISCORD_NARRATIVE quando il boss
# incontrato in quella run è uno di questi, indipendentemente dalla classe) ──────
SPECIAL_BOSS_NARRATIVE = {
    "il_diaulo": {
        "vittoria": [
            ("{name} ha respinto IL DIAULO nell'oscurità da cui è venuto",
             "Non un mostro qualunque, ma il Terrore in persona — e {name} lo ha guardato negli occhi senza cedere. {faction} non dimenticherà questa notte."),
            ("IL DIAULO è caduto per mano di {name}",
             "I sussurri si sono spenti, il Timore si è placato. Pochi a {faction} crederanno al racconto, ma la cicatrice che porta {name} dice il contrario."),
            ("{name} ha spezzato il patto infernale",
             "Amico dei Rettiliani, Buttacettete, Signore Oscuro — ogni sua mossa ha fallito. {faction} accoglie un eroe, non solo un sopravvissuto."),
        ],
        "sconfitta_morte": [
            ("IL DIAULO ha spezzato {name}, non la sua volontà",
             "Il Seguito lo ha portato fuori privo di sensi, svuotato di tutto ciò che aveva raccolto. Il Terrore, per questa volta, ha vinto lui."),
            ("{name} è stato travolto da IL DIAULO",
             "Nessun bottino, nessuna gloria — solo il ricordo di occhi che sussurravano il suo nome. Torna a {faction} vivo, e questo basterà per ora."),
            ("Il patto infernale ha avuto la meglio su {name}",
             "Portato fuori dalle profondità senza nulla in mano, {faction} lo rivedrà con un conto ancora aperto con IL DIAULO."),
        ],
        "sconfitta_timore": [
            ("{name} si è ritirato davanti a IL DIAULO, il bottino ancora in mano",
             "Non tutti possono guardare il Terrore negli occhi. {name} lo ha fatto, e ha scelto di vivere per riprovarci."),
            ("IL DIAULO ha spezzato il coraggio di {name}, non le sue tasche",
             "Torna a {faction} turbato nello spirito, ma con ogni cosa raccolta ancora al sicuro."),
            ("{name} ha sentito il sussurro di IL DIAULO, e si è ritirato in tempo",
             "Meglio vivi e turbati che tra le sue grinfie: torna a {faction} con il bottino intatto."),
        ],
    },
    "uomorsomaiale": {
        "vittoria": [
            ("{name} ha abbattuto l'Uomorsomaiale",
             "Una furia di zanne e muscoli, e {name} l'ha fermata a forza di colpi. {faction} ne parlerà come di una vera prova di sangue."),
            ("L'Uomorsomaiale è caduto sotto i colpi di {name}",
             "Non c'è stata strategia, solo resistenza: chi si fermava prima perdeva. {name} non si è fermato."),
            ("{name} ha domato la bestia",
             "Zanne, ruggiti, sventrate — niente ha piegato {name}. {faction} accoglie un macellaio di mostri."),
        ],
        "sconfitta_morte": [
            ("L'Uomorsomaiale ha travolto {name}",
             "Il Seguito lo ha portato fuori privo di sensi, sventrato e svuotato di tutto ciò che aveva raccolto. La bestia non fa prigionieri."),
            ("{name} è stato ridotto in polvere dall'Uomorsomaiale",
             "Nessun bottino, nessuna gloria — solo zanne e furia. Torna a {faction} vivo per un pelo."),
            ("La furia dell'Uomorsomaiale ha avuto la meglio su {name}",
             "Portato fuori dalle profondità senza nulla in mano, {faction} lo rivedrà pieno di cicatrici nuove."),
        ],
        "sconfitta_timore": [
            ("{name} si è ritirato davanti all'Uomorsomaiale, il bottino ancora in mano",
             "Anche il coraggio ha un limite di fronte a tanta furia cieca. {name} lo ha riconosciuto in tempo."),
            ("L'Uomorsomaiale ha spezzato il coraggio di {name}, non le sue tasche",
             "Torna a {faction} scosso, ma con ogni cosa raccolta ancora al sicuro."),
            ("{name} ha sentito il ruggito, e si è ritirato in tempo",
             "Meglio vivi e turbati che sotto quelle zanne: torna a {faction} con il bottino intatto."),
        ],
    },
}
