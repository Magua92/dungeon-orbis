# Come mettere online "La Spedizione" su PythonAnywhere (piano gratuito)

## 1. Carica i file
Nella dashboard di PythonAnywhere, apri una **Bash console** e crea una cartella, es.:
```
mkdir dungeon
cd dungeon
```
Carica lì dentro tutti i file di questa cartella (`dungeon_app.py`, `engine.py`, `game_data.py`,
`db.py`, `requirements.txt`, e la sottocartella `templates/` con tutti i suoi `.html`) —
tramite la scheda "Files" del sito (drag&drop) o con `git`/`wget` se preferisci.

## 2. Installa le dipendenze
Sempre dalla Bash console, dentro la cartella `dungeon`:
```
pip3.10 install --user -r requirements.txt
```
(il numero di versione di pip potrebbe differire leggermente — PythonAnywhere lo indica
nella pagina "Consoles" quando apri una Bash console).

## 3. Configura l'app Web
- Vai su **Web** → **Add a new web app** → scegli **Flask**, la versione di Python che hai
  usato per installare le dipendenze, e come percorso indica il file `dungeon_app.py` dentro
  la cartella che hai creato.
- Nella sezione **Code**, verifica che "Source code" e "Working directory" puntino entrambi
  alla cartella `dungeon` che hai creato.
- Nella sezione **WSGI configuration file**, assicurati che importi `app` da `dungeon_app`
  (PythonAnywhere lo configura da solo scegliendo Flask, ma controlla che il percorso sia corretto).

## 4. Variabili di configurazione (opzionali ma consigliate)
Nella sezione **Web → Environment variables** (o direttamente nel file WSGI, se la tua
versione del pannello non ha questa sezione) imposta:
- `DUNGEON_SECRET_KEY` — una stringa lunga a caso, per firmare i cookie di sessione
- `DUNGEON_ADMIN_PASSWORD` — la password per la pagina `/admin` (sblocco spedizioni)
- `DUNGEON_DISCORD_WEBHOOK` — l'URL del webhook Discord dove mandare i riepiloghi (lascia
  vuoto per disattivare l'invio automatico; funzionerà comunque, il riepilogo compare a schermo
  a fine spedizione)

Se non le imposti, l'app usa dei valori di default scritti in `dungeon_app.py` — funziona,
ma **cambia almeno la password admin** prima di condividere il link con i giocatori.

## 5. Ricarica l'app
Bottone verde **Reload** nella pagina Web. Il sito sara' raggiungibile a
`https://tuonome.pythonanywhere.com/`.

## Note
- Il database (`dungeon.db`) si crea da solo al primo avvio, nella stessa cartella.
- Per "aprire un nuovo turno" (sbloccare tutti i personaggi), vai su `/admin`, inserisci la
  password e premi "Sblocca tutti i personaggi".
- Questa app non tocca mai `factions.json` di Chronicle — il riepilogo di fine spedizione
  (mostrato a schermo, e mandato su Discord se hai configurato il webhook) va applicato a mano
  nel Master Panel, come per le altre azioni di turno.
