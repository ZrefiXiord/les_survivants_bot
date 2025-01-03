# Bot de validation de formulaire




# Fonctionnalités

Le bot fait : 
- Vérifie les nouvelles réponses sur le google sheet
- Réagit aux réactions faites sur les messages de validation (envoie de message, etc...)
- Si le bot est hors ligne, la prochaine fois qu'il est en ligne, il validera toutes les validations non vérifiées.

# Configuration
Fichier `.env`
```
DISCORD_TOKEN=YOUR_DISCORD_TOKEN
GOOGLE_CREDENTIALS_PATH=PATH/TO/CREDS
```
Fichier `config.json`
```
{
"CHANNEL_ID": Id,
"SPREADSHEET_ID": "Id",
"CHECK_SHEET_DELAY_SECONDS": DELAY,
"ROLE_NAME": "role name",
"PROCESSED_MESSAGES_PATH": "PATH/TO/FILE",
"LAST_ROW_FILE": "PATH/TO/FILE",
"WELCOME_MESSAGE": "Welcome message",
"ACCEPTED_MESSAGE": "Accept message",
"REFUSED_MESSAGE": "Refuse message"

}
```


