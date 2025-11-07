"""
Bot Telegram COMPLETO per Winter Grind 2025
Con sistema di personalizzazione totale

Requisiti:
pip install python-telegram-bot==20.7 apscheduler

Deploy Gratis su: Railway.app o Render.com
"""

import json
import logging
import base64
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# ============ CONFIGURAZIONE ============
#BOT_TOKEN = ""  # INSERISCI IL TUO TOKEN
#MINI_APP_URL = "  # INSERISCI IL TUO URL

# Stati per ConversationHandler
SETUP_NAME, SETUP_WEIGHT, SETUP_HEIGHT, SETUP_AGE, SETUP_GOAL, SETUP_ACTIVITY = range(6)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database in memoria (sostituire con DB reale in produzione)
user_profiles = {}
user_settings = {}

# Scheduler
scheduler = AsyncIOScheduler()


# ============ FUNZIONI CALCOLO ============

def calculate_bmr(weight, height, age, gender='male'):
    """Calcola il metabolismo basale (BMR)"""
    if gender.lower() == 'male':
        # Formula Mifflin-St Jeor per uomini
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        # Formula per donne
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    return bmr


def calculate_tdee(bmr, activity_level):
    """Calcola il dispendio energetico totale giornaliero"""
    multipliers = {
        'sedentary': 1.2,      # Poco o nessun esercizio
        'light': 1.375,        # Esercizio leggero 1-3 giorni/settimana
        'moderate': 1.55,      # Esercizio moderato 3-5 giorni/settimana
        'active': 1.725,       # Esercizio intenso 6-7 giorni/settimana
        'very_active': 1.9     # Esercizio molto intenso, lavoro fisico
    }
    return bmr * multipliers.get(activity_level, 1.55)


def calculate_macros(calories, goal='bulk'):
    """Calcola le macro in base all'obiettivo"""
    if goal == 'bulk':
        # Massa: +10% calorie, alto protein, medio carb
        target_cal = int(calories * 1.1)
        protein = int((target_cal * 0.30) / 4)  # 30% proteine
        carbs = int((target_cal * 0.45) / 4)    # 45% carboidrati
        fats = int((target_cal * 0.25) / 9)     # 25% grassi
    elif goal == 'cut':
        # Definizione: -20% calorie, alto protein, basso carb
        target_cal = int(calories * 0.8)
        protein = int((target_cal * 0.40) / 4)  # 40% proteine
        carbs = int((target_cal * 0.30) / 4)    # 30% carboidrati
        fats = int((target_cal * 0.30) / 9)     # 30% grassi
    else:  # maintain
        # Mantenimento
        target_cal = int(calories)
        protein = int((target_cal * 0.30) / 4)
        carbs = int((target_cal * 0.40) / 4)
        fats = int((target_cal * 0.30) / 9)
    
    return {
        'calories': target_cal,
        'protein': protein,
        'carbs': carbs,
        'fats': fats
    }


def get_workout_for_day(day_name):
    """Ritorna l'allenamento programmato"""
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


# ============ SETUP INIZIALE ============

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler per /start"""
    user = update.effective_user
    user_id = user.id
    
    # Controlla se l'utente ha già un profilo
    if user_id in user_profiles:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔥 Apri Winter Grind", web_app=WebAppInfo(url=MINI_APP_URL))
        ]])
        
        await update.message.reply_text(
            f"Bentornato {user.first_name}! 💪\n\n"
            f"Usa /menu per vedere tutti i comandi\n"
            f"Usa /setup per riconfigurare il tuo profilo",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            f"🔥 *BENVENUTO IN WINTER GRIND 2025* 🔥\n\n"
            f"Ciao {user.first_name}!\n\n"
            f"Prima di iniziare, configuriamo il tuo profilo personalizzato.\n\n"
            f"Usa /setup per iniziare la configurazione! 💪",
            parse_mode='Markdown'
        )


async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inizia il processo di setup"""
    await update.message.reply_text(
        "👤 *SETUP PROFILO*\n\n"
        "Ti farò alcune domande per personalizzare la tua esperienza.\n\n"
        "Iniziamo! Come ti chiami? (o scrivi il nome che preferisci)",
        parse_mode='Markdown'
    )
    return SETUP_NAME


async def setup_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva il nome e chiedi peso"""
    context.user_data['name'] = update.message.text
    
    await update.message.reply_text(
        f"Perfetto {context.user_data['name']}! 👍\n\n"
        f"⚖️ Qual è il tuo peso attuale? (in kg)\n\n"
        f"Esempio: 75",
        parse_mode='Markdown'
    )
    return SETUP_WEIGHT


async def setup_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva peso e chiedi altezza"""
    try:
        weight = float(update.message.text.replace(',', '.'))
        context.user_data['weight'] = weight
        
        await update.message.reply_text(
            f"✅ Peso: {weight} kg\n\n"
            f"📏 Qual è la tua altezza? (in cm)\n\n"
            f"Esempio: 175",
            parse_mode='Markdown'
        )
        return SETUP_HEIGHT
    except ValueError:
        await update.message.reply_text("❌ Inserisci un numero valido (es: 75)")
        return SETUP_WEIGHT


async def setup_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva altezza e chiedi età"""
    try:
        height = float(update.message.text.replace(',', '.'))
        context.user_data['height'] = height
        
        await update.message.reply_text(
            f"✅ Altezza: {height} cm\n\n"
            f"🎂 Quanti anni hai?\n\n"
            f"Esempio: 25",
            parse_mode='Markdown'
        )
        return SETUP_AGE
    except ValueError:
        await update.message.reply_text("❌ Inserisci un numero valido (es: 175)")
        return SETUP_HEIGHT


async def setup_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva età e chiedi obiettivo"""
    try:
        age = int(update.message.text)
        context.user_data['age'] = age
        
        keyboard = [
            [InlineKeyboardButton("💪 Massa Muscolare (Bulk)", callback_data="goal_bulk")],
            [InlineKeyboardButton("🔥 Definizione (Cut)", callback_data="goal_cut")],
            [InlineKeyboardButton("⚖️ Mantenimento", callback_data="goal_maintain")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Età: {age} anni\n\n"
            f"🎯 Qual è il tuo obiettivo?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return SETUP_GOAL
    except ValueError:
        await update.message.reply_text("❌ Inserisci un numero valido (es: 25)")
        return SETUP_AGE


async def setup_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva obiettivo e chiedi livello attività"""
    query = update.callback_query
    await query.answer()
    
    goal = query.data.replace('goal_', '')
    context.user_data['goal'] = goal
    
    goal_names = {
        'bulk': '💪 Massa Muscolare',
        'cut': '🔥 Definizione',
        'maintain': '⚖️ Mantenimento'
    }
    
    keyboard = [
        [InlineKeyboardButton("🛋️ Sedentario (poco esercizio)", callback_data="activity_sedentary")],
        [InlineKeyboardButton("🚶 Leggero (1-3 giorni/sett)", callback_data="activity_light")],
        [InlineKeyboardButton("🏃 Moderato (3-5 giorni/sett)", callback_data="activity_moderate")],
        [InlineKeyboardButton("💪 Attivo (6-7 giorni/sett)", callback_data="activity_active")],
        [InlineKeyboardButton("🔥 Molto Attivo (2x al giorno)", callback_data="activity_very_active")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Obiettivo: {goal_names[goal]}\n\n"
        f"🏃 Qual è il tuo livello di attività?",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return SETUP_ACTIVITY


async def setup_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Completa il setup e calcola tutto"""
    query = update.callback_query
    await query.answer()
    
    activity = query.data.replace('activity_', '')
    context.user_data['activity'] = activity
    
    # Calcola tutto
    user_id = update.effective_user.id
    data = context.user_data
    
    bmr = calculate_bmr(data['weight'], data['height'], data['age'])
    tdee = calculate_tdee(bmr, activity)
    macros = calculate_macros(tdee, data['goal'])
    
    # Salva profilo
    user_profiles[user_id] = {
        'name': data['name'],
        'weight': data['weight'],
        'height': data['height'],
        'age': data['age'],
        'goal': data['goal'],
        'activity': activity,
        'bmr': bmr,
        'tdee': tdee,
        'macros': macros,
        'created_at': datetime.now().isoformat()
    }
    
    # Abilita notifiche di default
    user_settings[user_id] = {
        'notifications': True,
        'reminder_morning': True,
        'reminder_evening': True,
        'reminder_weekly': True
    }
    
    goal_emoji = {'bulk': '💪', 'cut': '🔥', 'maintain': '⚖️'}
    
    # Crea payload per mini app con le macro personalizzate
    app_data = {
        'macros': macros,
        'userName': data['name'],
        'goal': data['goal']
    }
    encoded = base64.b64encode(json.dumps(app_data).encode()).decode()
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🔥 Apri Winter Grind",
            web_app=WebAppInfo(url=f"{MINI_APP_URL}?data={encoded}")
        )
    ]])
    
    await query.edit_message_text(
        f"✅ *PROFILO CONFIGURATO!*\n\n"
        f"👤 Nome: {data['name']}\n"
        f"⚖️ Peso: {data['weight']} kg\n"
        f"📏 Altezza: {data['height']} cm\n"
        f"🎂 Età: {data['age']} anni\n"
        f"{goal_emoji[data['goal']]} Obiettivo: {data['goal'].upper()}\n\n"
        f"📊 *I TUOI NUMERI:*\n"
        f"🔥 Calorie giornaliere: {macros['calories']} kcal\n"
        f"🥩 Proteine: {macros['protein']}g\n"
        f"🍚 Carboidrati: {macros['carbs']}g\n"
        f"🥑 Grassi: {macros['fats']}g\n\n"
        f"Questi dati sono già impostati nella tua app! 🎉\n\n"
        f"Usa /menu per vedere tutti i comandi disponibili.",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    return ConversationHandler.END


async def setup_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancella il setup"""
    await update.message.reply_text(
        "Setup annullato. Usa /setup per ricominciare.",
    )
    return ConversationHandler.END


# ============ COMANDI PRINCIPALI ============

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra il menu completo"""
    message = """
📋 *MENU COMPLETO*

*🏠 Base:*
/app - Apri la Mini App
/oggi - Allenamento di oggi
/status - Stato settimanale

*⚙️ Configurazione:*
/setup - Configura profilo
/profilo - Vedi il tuo profilo
/macros - Mostra le tue macro
/notifiche - Gestisci promemoria

*🛠️ Modifica Dati App:*
/setsettimana <N> - Imposta settimana (es: /setsettimana 5)
/addsgarro <N> - Aggiungi punti sgarro (es: /addsgarro 2)
/setpeso <N> - Aggiungi peso (es: /setpeso 75.5)
/resetsettimana - Reset settimana corrente
/addstreak <N> - Aggiungi streak (es: /addstreak 3)

*📊 Personalizzazione:*
/cambiaobiettivo - Cambia obiettivo (bulk/cut/maintain)
/cambiapeso - Aggiorna peso
/ricalcola - Ricalcola macro

*❓ Altro:*
/help - Guida completa
    """
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apre la Mini App con i dati dell'utente"""
    user_id = update.effective_user.id
    
    # Prepara dati personalizzati
    app_data = {}
    if user_id in user_profiles:
        profile = user_profiles[user_id]
        app_data = {
            'macros': profile['macros'],
            'userName': profile['name'],
            'goal': profile['goal']
        }
    
    encoded = base64.b64encode(json.dumps(app_data).encode()).decode()
    url = f"{MINI_APP_URL}?data={encoded}" if app_data else MINI_APP_URL
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔥 Apri App", web_app=WebAppInfo(url=url))
    ]])
    
    await update.message.reply_text(
        "Clicca per aprire Winter Grind 💪",
        reply_markup=keyboard
    )


async def profilo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra il profilo dell'utente"""
    user_id = update.effective_user.id
    
    if user_id not in user_profiles:
        await update.message.reply_text(
            "❌ Non hai ancora un profilo configurato.\n\n"
            "Usa /setup per crearlo!"
        )
        return
    
    profile = user_profiles[user_id]
    goal_names = {'bulk': '💪 Massa', 'cut': '🔥 Definizione', 'maintain': '⚖️ Mantenimento'}
    
    message = f"""
👤 *IL TUO PROFILO*

📝 Nome: {profile['name']}
⚖️ Peso: {profile['weight']} kg
📏 Altezza: {profile['height']} cm
🎂 Età: {profile['age']} anni
🎯 Obiettivo: {goal_names.get(profile['goal'], profile['goal'])}

📊 *METABOLISMO:*
🔥 BMR: {int(profile['bmr'])} kcal/giorno
⚡ TDEE: {int(profile['tdee'])} kcal/giorno

🍽️ *MACRO GIORNALIERE:*
📍 Calorie: {profile['macros']['calories']} kcal
🥩 Proteine: {profile['macros']['protein']}g
🍚 Carboidrati: {profile['macros']['carbs']}g
🥑 Grassi: {profile['macros']['fats']}g

Usa /cambiaobiettivo o /cambiapeso per aggiornare.
    """
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def macros_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra solo le macro"""
    user_id = update.effective_user.id
    
    if user_id not in user_profiles:
        await update.message.reply_text("Usa /setup per configurare il profilo!")
        return
    
    macros = user_profiles[user_id]['macros']
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📱 Apri App", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    
    await update.message.reply_text(
        f"🍽️ *LE TUE MACRO GIORNALIERE*\n\n"
        f"📍 Calorie: *{macros['calories']} kcal*\n"
        f"🥩 Proteine: *{macros['protein']}g*\n"
        f"🍚 Carboidrati: *{macros['carbs']}g*\n"
        f"🥑 Grassi: *{macros['fats']}g*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )


async def oggi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allenamento di oggi"""
    today = datetime.now().strftime('%A').lower()
    workout = get_workout_for_day(today)
    
    day_names = {
        'monday': 'Lunedì', 'tuesday': 'Martedì', 'wednesday': 'Mercoledì',
        'thursday': 'Giovedì', 'friday': 'Venerdì', 'saturday': 'Sabato', 'sunday': 'Domenica'
    }
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Segna Completato", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    
    await update.message.reply_text(
        f"📅 *Oggi è {day_names.get(today, 'oggi')}*\n\n{workout}\n\n"
        f"Hai già completato l'allenamento? 💪",
        parse_mode='Markdown',
        reply_markup=keyboard
    )


# ============ COMANDI MODIFICA APP ============

async def set_settimana_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Imposta settimana - /setsettimana 5"""
    try:
        week_num = int(context.args[0])
        data = {'currentWeek': week_num}
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "📱 Apri App (Settimana Aggiornata)",
                web_app=WebAppInfo(url=f"{MINI_APP_URL}?data={encoded}")
            )
        ]])
        
        await update.message.reply_text(
            f"✅ *Settimana impostata a: {week_num}*\n\n"
            f"Apri l'app per applicare 👇",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Uso: `/setsettimana <numero>`\nEsempio: `/setsettimana 5`",
            parse_mode='Markdown'
        )


async def add_sgarro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aggiungi punti sgarro - /addsgarro 2"""
    try:
        punti = int(context.args[0])
        data = {'pointsForSgarro': punti}
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "🍕 Apri App (Sgarri Aggiornati)",
                web_app=WebAppInfo(url=f"{MINI_APP_URL}?data={encoded}")
            )
        ]])
        
        await update.message.reply_text(
            f"✅ *Impostati {punti} punti sgarro!*\n\nApri l'app 🍕",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Uso: `/addsgarro <numero>`\nEsempio: `/addsgarro 2`",
            parse_mode='Markdown'
        )


async def set_peso_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aggiungi peso - /setpeso 75.5"""
    user_id = update.effective_user.id
    
    try:
        peso = float(context.args[0].replace(',', '.'))
        
        # Ottieni settimana corrente (simulata, in produzione leggi da app)
        current_week = 1
        if user_id in user_profiles:
            # Potresti salvare la settimana corrente nel profilo
            current_week = user_profiles[user_id].get('current_week', 1)
        
        data = {
            'savedWeights': [{'week': current_week, 'weight': peso}]
        }
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "⚖️ Apri App (Peso Aggiunto)",
                web_app=WebAppInfo(url=f"{MINI_APP_URL}?data={encoded}")
            )
        ]])
        
        await update.message.reply_text(
            f"✅ *Peso aggiunto: {peso} kg*\n\nApri l'app per vedere 📊",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Uso: `/setpeso <peso>`\nEsempio: `/setpeso 75.5`",
            parse_mode='Markdown'
        )


async def reset_settimana_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset settimana"""
    data = {
        'weekData': {
            day: {'workout': False, 'diet': False, 'cardio': False}
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        }
    }
    encoded = base64.b64encode(json.dumps(data).encode()).decode()
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🔄 Apri App (Reset Applicato)",
            web_app=WebAppInfo(url=f"{MINI_APP_URL}?data={encoded}")
        )
    ]])
    
    await update.message.reply_text(
        "⚠️ *Settimana Resettata*\n\nApri l'app per confermare 👇",
        parse_mode='Markdown',
        reply_markup=keyboard
    )


async def add_streak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aggiungi streak - /addstreak 3"""
    try:
        streak = int(context.args[0])
        data = {'streak': streak}
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "🔥 Apri App (Streak Aggiornata)",
                web_app=WebAppInfo(url=f"{MINI_APP_URL}?data={encoded}")
            )
        ]])
        
        await update.message.reply_text(
            f"✅ *Streak impostata a: {streak}*\n\nApri l'app 🔥",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Uso: `/addstreak <numero>`\nEsempio: `/addstreak 3`",
            parse_mode='Markdown'
        )


# ============ GESTIONE NOTIFICHE ============

async def notifiche_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisci notifiche"""
    user_id = update.effective_user.id
    
    if user_id not in user_settings:
        user_settings[user_id] = {'notifications': True}
    
    user_settings[user_id]['notifications'] = not user_settings[user_id].get('notifications', True)
    status = "attivate" if user_settings[user_id]['notifications'] else "disattivate"
    emoji = "🔔" if user_settings[user_id]['notifications'] else "🔕"
    
    await update.message.reply_text(
        f"{emoji} *Notifiche {status}*\n\n"
        f"Promemoria programmati:\n"
        f"• 08:00 - Allenamento del giorno\n"
        f"• 20:00 - Reminder serale\n"
        f"• Domenica 21:00 - Report settimanale\n\n"
        f"Usa di nuovo /notifiche per cambiare.",
        parse_mode='Markdown'
    )


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce dati dalla Mini App"""
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        data_type = data.get('type')
        
        if data_type == 'sgarro_used':
            remaining = data.get('remainingSgarri', 0)
            await update.message.reply_text(
                f"🍕 *Sgarro Usato!*\n\nGoditelo 😋\nSgarri rimasti: {remaining}",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Errore webapp data: {e}")


# ============ PROMEMORIA AUTOMATICI ============

async def morning_reminder(application: Application):
    """Reminder mattutino - 8:00"""
    today = datetime.now().strftime('%A').lower()
    workout = get_workout_for_day(today)
    day_names = {
        'monday': 'Lunedì', 'tuesday': 'Martedì', 'wednesday': 'Mercoledì',
        'thursday': 'Giovedì', 'friday': 'Venerdì', 'saturday': 'Sabato', 'sunday': 'Domenica'
    }
    
    message = f"☀️ *Buongiorno Bestia!*\n\nOggi è {day_names.get(today, 'oggi')}\n\n{workout}\n\nAndiamo a spaccare! 💪🔥"
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📱 Apri App", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    
    for user_id, settings in user_settings.items():
        if settings.get('notifications', True):
            try:
                await application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Errore invio morning reminder a {user_id}: {e}")


async def evening_reminder(application: Application):
    """Reminder serale - 20:00"""
    message = "🌙 *Check Serale*\n\nHai già loggato oggi?\n\n✅ Allenamento fatto?\n✅ Dieta rispettata?\n\nOgni giorno conta! 💪"
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📱 Segna Ora", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    
    for user_id, settings in user_settings.items():
        if settings.get('notifications', True):
            try:
                await application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Errore invio evening reminder a {user_id}: {e}")


async def weekly_report(application: Application):
    """Report settimanale - Domenica 21:00"""
    message = "📊 *REPORT SETTIMANALE*\n\nSettimana completata! 🎉\n\n" \
              "È il momento di:\n1️⃣ Controllare i tuoi punti totali\n" \
              "2️⃣ Vedere se hai guadagnato uno sgarro\n" \
              "3️⃣ Resettare per la prossima settimana\n\n" \
              "La costanza batte il talento! 🔥"
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 Vedi Report", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    
    for user_id, settings in user_settings.items():
        if settings.get('notifications', True):
            try:
                await application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Errore invio weekly report a {user_id}: {e}")


# ============ CAMBIO OBIETTIVO/PESO ============

async def cambia_obiettivo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cambia obiettivo"""
    user_id = update.effective_user.id
    
    if user_id not in user_profiles:
        await update.message.reply_text("Usa /setup per configurare il profilo!")
        return
    
    keyboard = [
        [InlineKeyboardButton("💪 Massa Muscolare", callback_data="change_goal_bulk")],
        [InlineKeyboardButton("🔥 Definizione", callback_data="change_goal_cut")],
        [InlineKeyboardButton("⚖️ Mantenimento", callback_data="change_goal_maintain")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎯 *CAMBIA OBIETTIVO*\n\nSeleziona il nuovo obiettivo:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def change_goal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback per cambio obiettivo"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    new_goal = query.data.replace('change_goal_', '')
    
    if user_id not in user_profiles:
        await query.edit_message_text("Usa /setup per configurare il profilo!")
        return
    
    profile = user_profiles[user_id]
    profile['goal'] = new_goal
    
    # Ricalcola macro
    new_macros = calculate_macros(profile['tdee'], new_goal)
    profile['macros'] = new_macros
    
    goal_names = {'bulk': '💪 Massa', 'cut': '🔥 Definizione', 'maintain': '⚖️ Mantenimento'}
    
    # Prepara dati per app
    app_data = {
        'macros': new_macros,
        'goal': new_goal
    }
    encoded = base64.b64encode(json.dumps(app_data).encode()).decode()
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "📱 Apri App (Aggiornata)",
            web_app=WebAppInfo(url=f"{MINI_APP_URL}?data={encoded}")
        )
    ]])
    
    await query.edit_message_text(
        f"✅ *Obiettivo cambiato: {goal_names[new_goal]}*\n\n"
        f"📊 *NUOVE MACRO:*\n"
        f"🔥 Calorie: {new_macros['calories']} kcal\n"
        f"🥩 Proteine: {new_macros['protein']}g\n"
        f"🍚 Carboidrati: {new_macros['carbs']}g\n"
        f"🥑 Grassi: {new_macros['fats']}g\n\n"
        f"Apri l'app per vedere le modifiche!",
        parse_mode='Markdown',
        reply_markup=keyboard
    )


async def cambia_peso_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cambia peso"""
    await update.message.reply_text(
        "⚖️ *AGGIORNA PESO*\n\n"
        "Inserisci il nuovo peso in kg:\n\n"
        "Esempio: `75.5`",
        parse_mode='Markdown'
    )
    context.user_data['waiting_for_weight'] = True


async def ricalcola_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ricalcola tutto"""
    user_id = update.effective_user.id
    
    if user_id not in user_profiles:
        await update.message.reply_text("Usa /setup per configurare il profilo!")
        return
    
    profile = user_profiles[user_id]
    
    # Ricalcola tutto
    bmr = calculate_bmr(profile['weight'], profile['height'], profile['age'])
    tdee = calculate_tdee(bmr, profile['activity'])
    macros = calculate_macros(tdee, profile['goal'])
    
    profile['bmr'] = bmr
    profile['tdee'] = tdee
    profile['macros'] = macros
    
    app_data = {'macros': macros}
    encoded = base64.b64encode(json.dumps(app_data).encode()).decode()
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "📱 Apri App (Aggiornata)",
            web_app=WebAppInfo(url=f"{MINI_APP_URL}?data={encoded}")
        )
    ]])
    
    await update.message.reply_text(
        f"✅ *RICALCOLO COMPLETATO*\n\n"
        f"📊 *NUOVI VALORI:*\n"
        f"🔥 BMR: {int(bmr)} kcal\n"
        f"⚡ TDEE: {int(tdee)} kcal\n\n"
        f"🍽️ *MACRO:*\n"
        f"📍 {macros['calories']} kcal\n"
        f"🥩 {macros['protein']}g proteine\n"
        f"🍚 {macros['carbs']}g carbo\n"
        f"🥑 {macros['fats']}g grassi",
        parse_mode='Markdown',
        reply_markup=keyboard
    )


async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce messaggi di testo (es: nuovo peso)"""
    user_id = update.effective_user.id
    
    if context.user_data.get('waiting_for_weight'):
        try:
            new_weight = float(update.message.text.replace(',', '.'))
            
            if user_id in user_profiles:
                user_profiles[user_id]['weight'] = new_weight
                
                # Ricalcola
                profile = user_profiles[user_id]
                bmr = calculate_bmr(new_weight, profile['height'], profile['age'])
                tdee = calculate_tdee(bmr, profile['activity'])
                macros = calculate_macros(tdee, profile['goal'])
                
                profile['bmr'] = bmr
                profile['tdee'] = tdee
                profile['macros'] = macros
                
                await update.message.reply_text(
                    f"✅ *Peso aggiornato: {new_weight} kg*\n\n"
                    f"Le tue macro sono state ricalcolate!\n"
                    f"Usa /macros per vederle.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("Usa /setup per configurare il profilo!")
            
            context.user_data['waiting_for_weight'] = False
        except ValueError:
            await update.message.reply_text("❌ Inserisci un numero valido (es: 75.5)")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guida completa"""
    message = """
📖 *GUIDA WINTER GRIND*

*🎯 Come Funziona:*
1️⃣ Configura il tuo profilo con /setup
2️⃣ Ricevi macro personalizzate
3️⃣ Traccia allenamenti e dieta nell'app
4️⃣ Accumula punti e guadagna sgarri

*📊 Sistema Punti:*
• Palestra = 15 punti
• Cardio = 10 punti
• Dieta = 3 punti
• 90+ punti = 1 sgarro 🍕

*🔔 Notifiche Automatiche:*
• Mattina (8:00) - Workout del giorno
• Sera (20:00) - Reminder
• Domenica (21:00) - Report settimanale

*⚙️ Personalizzazione:*
Il bot calcola automaticamente le tue macro in base a:
- Peso, altezza, età
- Obiettivo (massa/definizione/mantenimento)
- Livello di attività

Usa /menu per vedere tutti i comandi! 💪
    """
    
    await update.message.reply_text(message, parse_mode='Markdown')


# ============ INIT POST-STARTUP ============

async def post_init(application: Application):
    """Inizializza scheduler dopo l'avvio"""
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
    
    scheduler.start()
    
    logger.info("✅ Bot avviato! Promemoria configurati:")
    logger.info("⏰ 08:00 - Reminder mattutino")
    logger.info("⏰ 20:00 - Reminder serale")
    logger.info("⏰ Domenica 21:00 - Report settimanale")


# ============ MAIN ============

def main():
    """Avvia il bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Setup conversation handler
    setup_handler = ConversationHandler(
        entry_points=[CommandHandler('setup', setup_start)],
        states={
            SETUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_name)],
            SETUP_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_weight)],
            SETUP_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_height)],
            SETUP_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_age)],
            SETUP_GOAL: [CallbackQueryHandler(setup_goal, pattern='^goal_')],
            SETUP_ACTIVITY: [CallbackQueryHandler(setup_activity, pattern='^activity_')],
        },
        fallbacks=[CommandHandler('cancel', setup_cancel)],
    )
    
    # Aggiungi handlers
    application.add_handler(setup_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("app", app_command))
    application.add_handler(CommandHandler("profilo", profilo_command))
    application.add_handler(CommandHandler("macros", macros_command))
    application.add_handler(CommandHandler("oggi", oggi_command))
    application.add_handler(CommandHandler("notifiche", notifiche_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Comandi modifica app
    application.add_handler(CommandHandler("setsettimana", set_settimana_command))
    application.add_handler(CommandHandler("addsgarro", add_sgarro_command))
    application.add_handler(CommandHandler("setpeso", set_peso_command))
    application.add_handler(CommandHandler("resetsettimana", reset_settimana_command))
    application.add_handler(CommandHandler("addstreak", add_streak_command))
    
    # Comandi personalizzazione
    application.add_handler(CommandHandler("cambiaobiettivo", cambia_obiettivo_command))
    application.add_handler(CommandHandler("cambiapeso", cambia_peso_command))
    application.add_handler(CommandHandler("ricalcola", ricalcola_command))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(change_goal_callback, pattern='^change_goal_'))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    # Post init
    application.post_init = post_init
    
    logger.info("🚀 Avvio bot in corso...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
