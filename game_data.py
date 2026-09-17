# -*- coding: utf-8 -*-
"""Dati statici del minigioco di esplorazione (dungeon). Nessuna logica qui dentro,
solo le tabelle che il motore in dungeon_app.py consulta per risolvere stanze e
combattimenti."""

RESOURCE_TYPES = ["cibo", "legname", "pietra", "ferro", "gemme", "oro"]

# ─── SEGUITO (indipendente dalle truppe delle fazioni in chronicle.py) ───────
ENTOURAGE_TYPES = {
    "fante":        {"name": "Fante",                 "icon": "⚔️", "desc": "Assorbe un colpo fisico intero, poi cade."},
    "arciere":      {"name": "Arciere",                "icon": "🏹", "desc": "Aumenta la probabilità di agire per primi."},
    "cavaliere":    {"name": "Cavaliere",               "icon": "🐎", "desc": "Possibilità di annullare del tutto un attacco fisico nemico."},
    "purificatore": {"name": "Purificatore",            "icon": "✨", "desc": "Cura un poco di Vita del leader a ogni round."},
    "guardiano":    {"name": "Guardiano",               "icon": "🪨", "desc": "Riduce il danno fisico subito più volte prima di cadere."},
    "martello":     {"name": "Compagni del Martello",   "icon": "🔨", "desc": "Quando assorbe un colpo, infligge un contrattacco al nemico."},
}
ENTOURAGE_MAX_PICK = 3
GUARDIANO_CHARGES = 3
GUARDIANO_REDUCTION = 3
CAVALIERE_WARD_CHANCE = 0.30
MERCENARIO_SUCCESS_CHANCE = 0.70
MARTELLO_COUNTER_DMG = 2
PURIFICATORE_HEAL = 2

# ─── CLASSI E ABILITA' (5 per classe, sbloccate per livello) ────────────────
# type: 'danno' | 'supporto' | 'passiva' (le passive si applicano da sole, non si "usano")
CLASSES = {
    "Generale": {
        "icon": "⚔️",
        "abilities": [
            {"key": "carica",          "lvl": 1,  "name": "Carica",              "type": "danno",    "once": True,  "desc": "Un attacco molto potente, una volta a spedizione."},
            {"key": "grido_di_guerra", "lvl": 3,  "name": "Grido di Guerra",      "type": "supporto", "once": False, "desc": "Il Seguito agisce con più efficacia per 2 stanze."},
            {"key": "colpo_decisivo",  "lvl": 5,  "name": "Colpo Decisivo",       "type": "danno",    "once": False, "desc": "50% di possibilità di infliggere danno doppio."},
            {"key": "resistenza",      "lvl": 7,  "name": "Resistenza",           "type": "passiva",  "once": False, "desc": "Dopo il primo colpo fisico subito, +2 Armatura per il resto della run."},
            {"key": "ultima_resistenza","lvl": 10,"name": "Ultima Resistenza",    "type": "passiva",  "once": True,  "desc": "Se dovresti cadere, sopravvivi una volta con 1 Vita e contrattacchi pesantemente."},
        ],
    },
    "Mago": {
        "icon": "✨",
        "abilities": [
            {"key": "colpo_arcano",       "lvl": 1,  "name": "Colpo Arcano",        "type": "danno",    "once": False, "desc": "Danno che ignora parte delle difese del nemico."},
            {"key": "sigillo",             "lvl": 3,  "name": "Sigillo",              "type": "supporto", "once": False, "desc": "Indebolisce il prossimo attacco del nemico."},
            {"key": "rigenerazione_arcana","lvl": 5,  "name": "Rigenerazione Arcana", "type": "supporto", "once": False, "desc": "Recupera immediatamente un po' di Vita."},
            {"key": "nebbia_illusoria",    "lvl": 7,  "name": "Nebbia Illusoria",     "type": "supporto", "once": True,  "desc": "Sparisci nella nebbia, evitando il combattimento in corso."},
            {"key": "esplosione_elementale","lvl": 10,"name": "Esplosione Elementale","type": "danno",   "once": True,  "desc": "Danno pesante, specialmente efficace contro il miniboss."},
        ],
    },
    "Diplomatico": {
        "icon": "🕊️",
        "abilities": [
            {"key": "negoziazione",       "lvl": 1,  "name": "Negoziazione",        "type": "supporto", "once": True,  "desc": "Evita del tutto un combattimento, se usata al primo round."},
            {"key": "sguardo_autorevole", "lvl": 3,  "name": "Sguardo Autorevole",  "type": "passiva",  "once": False, "desc": "Incontri meno combattimenti nelle stanze successive."},
            {"key": "parola_ispirata",    "lvl": 5,  "name": "Parola Ispirata",     "type": "passiva",  "once": False, "desc": "Bottini leggermente più generosi."},
            {"key": "patto_d_emergenza",  "lvl": 7,  "name": "Patto d'Emergenza",   "type": "supporto", "once": True,  "desc": "Spendi tutto il tesoro raccolto per guarire Vita e Timore."},
            {"key": "trattato_di_sangue", "lvl": 10, "name": "Trattato di Sangue",  "type": "danno",    "once": True,  "desc": "Se questo colpo abbatte il nemico, si unisce al tuo Seguito per il resto della run."},
        ],
    },
    "Esploratore": {
        "icon": "🧭",
        "abilities": [
            {"key": "fiuto",              "lvl": 1,  "name": "Fiuto",               "type": "passiva",  "once": False, "desc": "Riveli il nemico prima di entrare in battaglia."},
            {"key": "passo_leggero",      "lvl": 3,  "name": "Passo Leggero",       "type": "passiva",  "once": False, "desc": "Il primo colpo fisico di ogni combattimento viene schivato."},
            {"key": "occhio_di_falco",    "lvl": 5,  "name": "Occhio di Falco",     "type": "passiva",  "once": False, "desc": "Bottini più abbondanti."},
            {"key": "scorciatoia",        "lvl": 7,  "name": "Scorciatoia",         "type": "supporto", "once": True,  "desc": "Salta la stanza corrente senza rischi, una volta a run."},
            {"key": "maestro_dei_sentieri","lvl": 10,"name": "Maestro dei Sentieri","type": "passiva",  "once": False, "desc": "Vedi le statistiche del miniboss prima di affrontarlo."},
        ],
    },
    "Amministratore": {
        "icon": "📜",
        "abilities": [
            {"key": "contabile",   "lvl": 1,  "name": "Contabile",     "type": "passiva", "once": False, "desc": "Incudine e Sacco di Monete costano 1 Oro in meno."},
            {"key": "scorta_extra","lvl": 3,  "name": "Scorta Extra",  "type": "passiva", "once": False, "desc": "Inizi ogni spedizione con Oro bonus."},
            {"key": "razionamento","lvl": 5,  "name": "Razionamento",  "type": "passiva", "once": False, "desc": "Il Seguito ha più probabilità di sopravvivere quando assorbe un colpo."},
            {"key": "investimento","lvl": 7,  "name": "Investimento",  "type": "passiva", "once": False, "desc": "I potenziamenti dell'Incudine sono più efficaci."},
            {"key": "tesoriere",   "lvl": 10, "name": "Tesoriere",     "type": "passiva", "once": False, "desc": "L'Oro non speso si converte in Esperienza extra a fine run."},
        ],
    },
}

LEVEL_UNLOCK_THRESHOLDS = [1, 3, 5, 7, 10]  # livelli a cui si sbloccano le 5 abilita', in ordine
XP_PER_LEVEL = 150  # livello = 1 + xp // XP_PER_LEVEL (fino a livello massimo)
MAX_LEVEL = 10

# ─── STATISTICHE BASE DEL LEADER ─────────────────────────────────────────────
BASE_PV = 20
BASE_TIMORE = 20
BASE_ARMOR = 0
BASE_MRES = 0
BASE_DMG_MIN, BASE_DMG_MAX = 3, 5

# ─── NEMICI PER STANZA (1-5) E MINIBOSS ─────────────────────────────────────
ENEMY_TIERS = {
    1: {"pv": 8,  "dmg": (2, 4), "fear_chance": 0.0,  "fear_dmg": (0, 0), "pool": [("Predone Solitario", "🗡️"), ("Cane Selvatico", "🐺")]},
    2: {"pv": 10, "dmg": (3, 4), "fear_chance": 0.0,  "fear_dmg": (0, 0), "pool": [("Sciacallo delle Rovine", "🦴"), ("Predone Armato", "🗡️")]},
    3: {"pv": 12, "dmg": (3, 5), "fear_chance": 0.20, "fear_dmg": (3, 5), "pool": [("Ombra Vagante", "👻"), ("Bandito Esperto", "🗡️")]},
    4: {"pv": 14, "dmg": (4, 6), "fear_chance": 0.35, "fear_dmg": (4, 6), "pool": [("Spettro del Confine", "👹"), ("Fauna Corrotta", "🐗")]},
    5: {"pv": 16, "dmg": (4, 7), "fear_chance": 0.50, "fear_dmg": (5, 7), "pool": [("Cavaliere Caduto", "💀"), ("Orrore Nebbioso", "👁️")]},
}
BOSS_TIER = {"pv": 35, "dmg": (6, 10), "fear_chance": 0.50, "fear_dmg": (6, 9), "pool": [("Signore delle Rovine", "👑")]}

ROOMS_PER_RUN = 5

# ─── TIPI DI STANZA ───────────────────────────────────────────────────────────
ROOM_TYPES = {
    "battaglia":     {"icon": "⚔️", "name": "Sala delle Ombre",  "desc": "Un nemico si cela nell'oscurità."},
    "fontana":       {"icon": "⛲", "name": "Fontana Sacra",     "desc": "Le acque risanano le ferite."},
    "incudine":      {"icon": "🔨", "name": "Forgia Antica",     "desc": "Investi il tesoro in un potenziamento per questa run."},
    "sacco_monete":  {"icon": "💰", "name": "Sacco di Monete",   "desc": "Assumi un mercenario temporaneo."},
}

INCUDINE_BASE_COST = 3   # in Oro
INCUDINE_BUFF_AMOUNT = 1
SACCO_MONETE_COST = 5    # in Oro

INCUDINE_OPTIONS = [
    {"stat": "dmg",   "label": "+1 Danno Fisico"},
    {"stat": "armor", "label": "+1 Armatura"},
    {"stat": "mres",  "label": "+1 Resistenza Mentale"},
]

# ─── LOOT (stanze di battaglia normali e miniboss) ──────────────────────────
NORMAL_LOOT_AMOUNT = (2, 4)
BOSS_LOOT_AMOUNT = (4, 8)
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
    "mantello_bruma":        {"name": "Mantello di Bruma Sottile",     "slot": "armatura", "rarity": "epica",       "effects": {"mres": 2, "armor": -1},         "lore": "Chi lo indossa dice di sentire meno il freddo — e meno anche la paura."},
    "velo_nebrahil":         {"name": "Velo della Nébrahil",           "slot": "armatura", "rarity": "leggendaria", "effects": {"mres": 3, "immunita_primo_pauroso": True}, "lore": "Si narra fosse indossato dalla Regina stessa, nei giorni in cui la nebbia sembrava non finire mai."},
}

EQUIP_SLOTS = ["slot_arma", "slot_armatura", "slot_jolly"]  # jolly: arma o armatura, a scelta
