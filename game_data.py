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
            {"key": "scudo_magico",     "lvl": 1,  "name": "Scudo Magico",     "type": "supporto", "cd": 4, "desc": "Uno scudo assorbe i prossimi 10 danni fisici e i prossimi 12 danni alla Timore, finche' dura o finche' il combattimento finisce."},
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
            {"key": "orazione_esperta", "lvl": 1,  "name": "Orazione Esperta",    "type": "danno",    "cd": 2, "desc": "3-5 danni alla Timore del nemico; 50% di rianimare una truppa caduta del tuo Seguito."},
            {"key": "littori_sacri",    "lvl": 1,  "name": "Littori Sacri",       "type": "danno",    "cd": 3, "desc": "5-8 danni fisici e 2-3 danni alla Timore del nemico; una truppa a caso del tuo Seguito viene sacrificata."},
            {"key": "proteggimi",       "lvl": 1,  "name": "Proteggimi!",         "type": "supporto", "cd": 4, "desc": "Ottieni uno scudo di 4 Vita e 2 Timore per ogni truppa ancora attiva, fino a fine combattimento."},
            {"key": "bastione_della_fede","lvl": 3,"name": "Bastione della Fede", "type": "passiva",  "desc": "Sempre attiva: recuperi 2 Vita a turno, cumulabile col Purificatore del Seguito (4 Vita a turno insieme)."},
            {"key": "omelia_della_potenza","lvl": 5,"name": "Omelia della Potenza","type": "danno",   "cd": 4, "desc": "4-6 danni alla Timore del nemico; 30% di critico che raddoppia il danno."},
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
            {"key": "parole_di_scherno",    "lvl": 3,  "name": "Parole di Scherno",     "type": "danno",    "cd": 4, "desc": "3-5 danni alla Timore del nemico; il suo danno fisico e' ridotto di 3 per i 2 turni successivi."},
            {"key": "picconata_fortunata",  "lvl": 5,  "name": "Picconata Fortunata",   "type": "danno",    "cd": 3, "desc": "6-9 danni fisici; 15% di critico che raddoppia il danno."},
            {"key": "indovinelli_oscurita", "lvl": 7,  "name": "Indovinelli nell'Oscurità","type": "danno", "cd": 5, "desc": "3 tiri al 50%: ogni successo infligge 8 danni al nemico, ogni fallimento te ne infligge 4 diretti."},
            {"key": "mappatore_esperto",    "lvl": 9,  "name": "Mappatore Esperto",     "type": "passiva",  "desc": "Sempre attiva: vedi in anticipo le stanze successive, e raddogli le risorse ottenute a fine combattimento."},
            {"key": "vie_segrete",          "lvl": 10, "name": "Vie Segrete",           "type": "supporto", "once": True, "room_action": True, "desc": "Una volta a run, salta la stanza corrente (non il miniboss) senza affrontarla."},
        ],
    },
    "Amministratore": {
        "icon": "📜",
        "abilities": [
            {"key": "esperto_saccheggiatore","lvl": 1, "name": "Esperto Saccheggiatore","type": "supporto", "cd": 3, "desc": "Trovi +5 unita' di una risorsa a caso tra Oro (60%), Legname (20%) e Pietra (20%)."},
            {"key": "acuto_osservatore",     "lvl": 1, "name": "Acuto Osservatore",     "type": "supporto", "cd": 3, "desc": "Individui i punti debili del nemico: potenzia il prossimo utilizzo di Raffica Micidiale."},
            {"key": "raffica_micidiale",     "lvl": 1, "name": "Raffica Micidiale",     "type": "danno",    "cd": 4, "desc": "3 colpi da 2 danni ciascuno; se potenziata da Acuto Osservatore, 3 colpi da 5-7 danni ciascuno."},
            {"key": "ogni_uomo_ha_un_prezzo","lvl": 3, "name": "Ogni Uomo ha un Prezzo","type": "danno",    "cd": 2, "desc": "4-5 danni alla Timore del nemico."},
            {"key": "azzardo_economico",     "lvl": 5, "name": "Azzardo Economico",     "type": "danno",    "cd": 4, "desc": "Spendi tutto il tuo Oro: infligge 2 danni alla Timore del nemico per ogni unita' di Oro speso."},
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
    1: [("Goblin Razziatore", "👺"), ("Cane Selvatico", "🐺"), ("Predone Solitario", "🗡️"),
        ("Ratto Colossale", "🐀"), ("Corvo Malato", "🐦")],
    2: [("Orco Sbandato", "👹"), ("Sciacallo delle Rovine", "🦴"), ("Predone Armato", "🗡️"),
        ("Goblin Sciamano", "👺"), ("Cinghiale Furioso", "🐗")],
    3: [("Ombra Vagante", "👻"), ("Bandito Esperto", "🗡️"), ("Orco Guerriero", "👹"),
        ("Troll delle Paludi", "🧌"), ("Nano Spergiuro", "🪓")],
    4: [("Spettro del Confine", "👹"), ("Fauna Corrotta", "🐗"), ("Draugr Risvegliato", "💀"),
        ("Purificatore Eretico", "✨"), ("Troll da Guerra", "🧌")],
    5: [("Cavaliere Caduto", "💀"), ("Orrore Nebbioso", "👁️"), ("Colosso di Pietra", "🗿"),
        ("Orco Ancestrale", "👹"), ("Nano Spergiuro Anziano", "🪓")],
    6: [("Draugr Ancestrale", "💀"), ("Purificatore Eretico Superiore", "✨"), ("Colosso Runico", "🗿"),
        ("Troll delle Cime", "🧌"), ("Ombra Ancestrale", "👻")],
    7: [("Colosso di Guerra", "🗿"), ("Draugr Signore", "💀"), ("Orco Sovrano", "👹"),
        ("Purificatore Eretico Supremo", "✨"), ("Nano Spergiuro Maledetto", "🪓")],
}
BOSS_POOL = [("Il Signore delle Rovine", "👑"), ("Il Colosso Corrotto", "🗿"),
             ("Il Re-Ombra", "👻"), ("Lo Spergiuro Eterno", "🪓")]


def get_enemy_tier(n):
    """Statistiche del nemico per la stanza n (1-based), calcolate con una formula cosi'
    da poter cambiare ROOMS_PER_RUN senza dover riscrivere una tabella a mano. Il pool dei
    nomi usa il tier piu' alto disponibile se n supera quelli definiti in ENEMY_POOLS."""
    pool = ENEMY_POOLS.get(n, ENEMY_POOLS[max(ENEMY_POOLS.keys())])
    pv = 8 + 2 * (n - 1)
    dmg_min = 2 + (n - 1) // 3
    dmg_max = 4 + (n - 1) // 2
    fear_chance = max(0.0, min(0.6, (n - 2) * 0.12))
    fear_dmg = (dmg_min + 1, dmg_max + 1) if fear_chance > 0 else (0, 0)
    return {"pv": pv, "dmg": (dmg_min, dmg_max), "fear_chance": fear_chance, "fear_dmg": fear_dmg, "pool": pool}


def get_boss_tier(rooms_per_run):
    """Il miniboss scala in base al numero di stanze della run (piu' stanze = nemico finale
    piu' duro), sempre circa 1.75x le PV dell'ultima stanza normale."""
    last = get_enemy_tier(rooms_per_run)
    pv = int(last["pv"] * 1.75)
    dmg = (last["dmg"][0] + 2, last["dmg"][1] + 3)
    return {"pv": pv, "dmg": dmg, "fear_chance": 0.5, "fear_dmg": (dmg[0], dmg[1]), "pool": BOSS_POOL}

ROOMS_PER_RUN = 7

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
    "mantello_bruma":        {"name": "Mantello di Bruma Sottile",     "slot": "armatura", "rarity": "epica",       "effects": {"mres": 2, "armor": -1},         "lore": "Chi lo indossa dice di sentire meno il freddo — e meno anche la paura."},
    "velo_nebrahil":         {"name": "Velo della Nébrahil",           "slot": "armatura", "rarity": "leggendaria", "effects": {"mres": 3, "immunita_primo_pauroso": True}, "lore": "Si narra fosse indossato dalla Regina stessa, nei giorni in cui la nebbia sembrava non finire mai."},
}

EQUIP_SLOTS = ["slot_arma", "slot_armatura", "slot_jolly"]  # jolly: arma o armatura, a scelta
