import json
import logging
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Configurazione logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ CONFIGURAZIONE ============
BOT_TOKEN = "8518603872:AAHh9fUbvvp5FhDlFjydrVwx8kf0wDxL_2E"
MINI_APP_URL = "https://wintergrindbot.netlify.app/"  # Sostituisci con il tuo URL

# Database in memoria (in produzione usa un vero database)
user_data = {}

# Schedulatore per i promemoria
scheduler = AsyncIOScheduler()


# ============ FUNZIONI HELPER ============

def get_workout_for_day(day_name):
    """Ritorna l'allenamento programmato per il giorno"""
    workouts = {
        'monday': '💪 Upper A (Push) - Petto, Spalle, Tricipiti',
        'tuesday': '🦵 Lower A (Squat) - Gambe Focus Quadricipiti',
        'wednesday': '🏃 Cardio - 20-30 minuti corsa',
        'thursday': '💪 Upper B (Pull) - Dorso, Bicipiti',
        'friday': '🦵 Lower B (Deadlift) - Gambe Focus Femorali',
        'saturday': '🏃 Cardio - 20-30 minuti corsa',
        'sunday': '😌 Riposo / Stretching'
    }
    return workouts.get(day_name.lower(), 'Riposo')


async def get_user_week_status(user_id):
    """Recupera lo stato della settimana corrente (simulato)"""
    # In produzione, recupera da Cloud Storage di Telegram o database
    if user_id in user_data:
        return user_data[user_id]
    return None


# ============ COMMAND HANDLERS ============

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler per /start"""
    user = update.effective_user
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🔥 Apri Winter Grind",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])
    
    welcome_message = f"""
🔥 *WINTER GRIND 2025* 🔥

Benvenuto {user.first_name}!

Questo bot ti aiuterà a rimanere accountable durante il tuo percorso invernale.

📱 *Funzionalità:*
• Tracciamento allenamenti e dieta
• Promemoria giornalieri automatici
• Report settimanali
• Sistema punti sgarro

🎯 *Comandi disponibili:*
/app - Apri la Mini App
/oggi - Allenamento di oggi
/status - Il tuo stato settimanale
/notifiche - Gestisci promemoria
/help - Guida completa

Clicca sul pulsante qui sotto per iniziare! 👇
    """
    
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=keyboard
    )


async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apre la Mini App"""
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🔥 Apri App",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])
    
    await update.message.reply_text(
        "Clicca per aprire Winter Grind 💪",
        reply_markup=keyboard
    )


async def oggi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra l'allenamento di oggi"""
    today = datetime.now().strftime('%A').lower()
    workout = get_workout_for_day(today)
    
    day_names = {
        'monday': 'Lunedì',
        'tuesday': 'Martedì', 
        'wednesday': 'Mercoledì',
        'thursday': 'Giovedì',
        'friday': 'Venerdì',
        'saturday': 'Sabato',
        'sunday': 'Domenica'
    }
    
    message = f"""
📅 *Oggi è {day_names.get(today, 'oggi')}*

{workout}

Hai già completato l'allenamento? Apri l'app per segnarlo! 💪
    """
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Segna Completato", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=keyboard
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra lo stato settimanale (placeholder)"""
    # In produzione, recupera dati reali da Cloud Storage
    message = """
📊 *IL TUO STATO SETTIMANALE*

Settimana: 1
Punti: 75/100

✅ Allenamenti: 5/6
✅ Dieta: 6/7
✅ Cardio: 2/2

🎯 Status: 💪 SOLIDO

Continua così! Mancano solo 15 punti per la settimana BESTIA! 🔥
    """
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📱 Vedi Dettagli", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=keyboard
    )


async def notifiche_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce le notifiche"""
    user_id = update.effective_user.id
    
    # Toggle notifiche
    if user_id not in user_data:
        user_data[user_id] = {'notifications': True}
    else:
        user_data[user_id]['notifications'] = not user_data[user_id].get('notifications', True)
    
    status = "attivate" if user_data[user_id]['notifications'] else "disattivate"
    emoji = "🔔" if user_data[user_id]['notifications'] else "🔕"
    
    message = f"""
{emoji} *Notifiche {status}*

Riceverai promemoria:
• Ogni mattina (8:00) - Allenamento del giorno
• Ogni sera (20:00) - Reminder se non hai loggato
• Domenica sera (21:00) - Report settimanale

Usa di nuovo /notifiche per cambiare.
    """
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la guida"""
    message = """
📖 *GUIDA WINTER GRIND*

*Comandi Bot:*
/app - Apri la Mini App
/oggi - Allenamento di oggi
/status - Stato settimanale
/notifiche - Attiva/Disattiva promemoria
/help - Questa guida

*Come Funziona:*
1️⃣ Ogni giorno segna allenamento e dieta nell'app
2️⃣ Accumula punti (max 100/settimana)
3️⃣ Settimana 90+ = 1 punto sgarro 🍕
4️⃣ Mantieni la streak per diventare una BESTIA 🔥

*Sistema Punti:*
• Palestra = 15 punti
• Cardio = 10 punti
• Dieta = 3 punti

*Livelli:*
🚨 0-59 = RESET
⚡ 60-74 = IN RIPRESA
💪 75-89 = SOLIDO
🔥 90+ = BESTIA

Buon grind! 💪
    """
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i dati inviati dalla Mini App"""
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        data_type = data.get('type')
        
        if data_type == 'sgarro_used':
            remaining = data.get('remainingSgarri', 0)
            await update.message.reply_text(
                f"🍕 *Sgarro Usato!*\n\n"
                f"Goditelo con moderazione 😋\n"
                f"Sgarri rimasti: {remaining}",
                parse_mode='Markdown'
            )
        
        elif data_type == 'stateUpdate':
            # Salva stato (in produzione salva su database)
            user_id = update.effective_user.id
            user_data[user_id] = data.get('state', {})
            logger.info(f"Stato aggiornato per user {user_id}")
        
        elif data_type == 'state_report':
            state = data.get('state', {})
            points = calculate_points(state.get('weekData', {}))
            
            await update.message.reply_text(
                f"📊 *Report Ricevuto*\n\n"
                f"Punti settimana: {points}/100\n"
                f"Stato salvato con successo! ✅",
                parse_mode='Markdown'
            )
    
    except Exception as e:
        logger.error(f"Errore gestione webapp data: {e}")


def calculate_points(week_data):
    """Calcola punti dalla settimana"""
    total = 0
    for day_data in week_data.values():
        if day_data.get('workout'):
            total += 15
        if day_data.get('cardio'):
            total += 10
        if day_data.get('diet'):
            total += 3
    return min(total, 100)


# ============ PROMEMORIA AUTOMATICI ============

async def morning_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Promemoria mattutino - 8:00"""
    today = datetime.now().strftime('%A').lower()
    workout = get_workout_for_day(today)
    
    day_names = {
        'monday': 'Lunedì',
        'tuesday': 'Martedì',
        'wednesday': 'Mercoledì',
        'thursday': 'Giovedì',
        'friday': 'Venerdì',
        'saturday': 'Sabato',
        'sunday': 'Domenica'
    }
    
    message = f"""
☀️ *Buongiorno Bestia!*

Oggi è {day_names.get(today, 'oggi')}

{workout}

Colazione fatta? Andiamo a spaccare! 💪🔥
    """
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📱 Apri App", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    
    # Invia a tutti gli utenti con notifiche attive
    for user_id, data in user_data.items():
        if data.get('notifications', True):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Errore invio reminder a {user_id}: {e}")


async def evening_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Promemoria serale - 20:00"""
    message = """
🌙 *Check Serale*

Hai già loggato oggi?

✅ Allenamento fatto?
✅ Dieta rispettata?

Ogni giorno conta per il tuo grind invernale! 💪
    """
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📱 Segna Ora", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    
    for user_id, data in user_data.items():
        if data.get('notifications', True):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Errore invio evening reminder a {user_id}: {e}")


async def weekly_report(context: ContextTypes.DEFAULT_TYPE):
    """Report settimanale - Domenica 21:00"""
    message = """
📊 *REPORT SETTIMANALE*

Settimana completata! 🎉

È il momento di:
1️⃣ Controllare i tuoi punti totali
2️⃣ Vedere se hai guadagnato uno sgarro
3️⃣ Resettare per la prossima settimana

Usa il pulsante "Nuova Settimana" nell'app!

Ricorda: La costanza batte il talento. Continua così! 🔥
    """
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 Vedi Report", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    
    for user_id, data in user_data.items():
        if data.get('notifications', True):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Errore invio weekly report a {user_id}: {e}")


# ============ MAIN ============

async def post_init(application: Application):
    """Inizializza scheduler dopo l'avvio del bot"""
    # Configura scheduler promemoria
    scheduler.add_job(
        morning_reminder,
        CronTrigger(hour=8, minute=0),
        args=[application],
        id='morning_reminder',
        replace_existing=True
    )
    
    scheduler.add_job(
        evening_reminder,
        CronTrigger(hour=20, minute=0),
        args=[application],
        id='evening_reminder',
        replace_existing=True
    )
    
    scheduler.add_job(
        weekly_report,
        CronTrigger(day_of_week='sun', hour=21, minute=0),
        args=[application],
        id='weekly_report',
        replace_existing=True
    )
    
    # Avvia scheduler
    scheduler.start()
    
    logger.info("✅ Bot avviato! Promemoria configurati:")
    logger.info("⏰ 08:00 - Reminder mattutino")
    logger.info("⏰ 20:00 - Reminder serale")
    logger.info("⏰ Domenica 21:00 - Report settimanale")


def main():
    """Avvia il bot"""
    # Crea applicazione
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Aggiungi handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("app", app_command))
    application.add_handler(CommandHandler("oggi", oggi_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("notifiche", notifiche_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    
    # Configura post_init per avviare scheduler dopo l'avvio
    application.post_init = post_init
    
    logger.info("🚀 Avvio bot in corso...")
    
    # Avvia bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()