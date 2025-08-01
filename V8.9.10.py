# ==================== IMPORTS ====================
import os
import logging
import time
import random
import string
import json
import re
import zipfile
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, error
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import asyncio

# ==================== BOT CONFIGURATION ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- PASTE YOUR BOT TOKEN HERE ---
TOKEN = "8160565161:AAE6mcrvQ4RPddRbHV1a_dNJ1Z2qsMHJOQw"

# --- ADMIN & DATA ---
ADMINS = [6818427110]
ACCOUNTS_FOLDER = 'accounts'
USER_DATA_FILE = 'user_data.json'
GENERATED_KEYS_FILE = 'generated_keys.json'
KEYWORD_USAGE_FILE = 'keyword_usage.json'
BANNED_USERS_FILE = 'banned_users.json'
WELCOME_VIDEO_PATH = 'assets/welcome.mp4'
SEPARATOR_LOG_FILE = 'separator_log.txt'

file_locks = {}

# --- Conversation States ---
AWAITING_REDEEM_KEY = 0
AWAITING_BLOCKLIST_ADD = 1
AWAITING_BLOCKLIST_REMOVE = 2
AWAITING_BROADCAST_CONTENT = 3
AWAITING_MERGE_FILES = 4
AWAITING_URL_REMOVER_FILE = 5
AWAITING_DUPLICATE_REMOVER_FILE = 6
AWAITING_SEPARATOR_FILE = 7

# ==================== MENUS & STYLING ====================
def format_button_text(text: str) -> str:
    char_map = {
        'A': '𝙰', 'B': '𝙱', 'C': '𝙲', 'D': '𝙳', 'E': '𝙴', 'F': '𝙵', 'G': '𝙶', 'H': '𝙷', 'I': '𝙸', 'J': '𝙹',
        'K': '𝙺', 'L': '𝙻', 'M': '𝙼', 'N': '𝙽', 'O': '𝙾', 'P': '𝙿', 'Q': '𝚀', 'R': '𝚁', 'S': '𝚂', 'T': '𝚃',
        'U': '𝚄', 'V': '𝚅', 'W': '𝚆', 'X': '𝚇', 'Y': '𝚈', 'Z': '𝚉', 'a': '𝚊', 'b': '𝚋', 'c': '𝚌',
        'd': '𝚍', 'e': '𝚎', 'f': '𝚏', 'g': '𝚐', 'h': '𝚑', 'i': '𝚒', 'j': '𝚓', 'k': '𝚔', 'l': '𝚕',
        'm': '𝚖', 'n': '𝚗', 'o': '𝚘', 'p': '𝚙', 'q': '𝚚', 'r': '𝚛', 's': '𝚜', 't': '𝚝', 'u': '𝚞',
        'v': '𝚟', 'w': '𝚠', 'x': '𝚡', 'y': '𝚢', 'z': '𝚣', '0': '𝟶', '1': '𝟷', '2': '𝟸', '3': '𝟹',
        '4': '𝟺', '5': '𝟻', '6': '𝟼', '7': '𝟽', '8': '𝟾', '9': '𝟿', ' ': ' '
    }
    return ''.join(char_map.get(char, char) for char in text)

MENUS = {
    "main": {
        "🔍 SEARCH KEYWORDS": "menu_search", "🛡️ DATADOME": "menu_datadome",
        "📜 LOG SEPARATOR": "separator_start", "🧾 MERGE": "merge_start", 
        "🔗 URL REMOVER": "url_remover_start", "🗑️ DUPLICATE REMOVER": "duplicate_remover_start",
        "🧰 ADMIN": "menu_admin", "🧹 CLEAR": "clear_menu"
    },
    "menu_search": {
        "CALL OF DUTY": "menu_codm", "MLBB": "menu_mlbb", "ROBLOX": "menu_roblox",
        "CINEMA": "menu_cinema", "CODASHOP": "menu_codashop", "SOCIAL MEDIA": "menu_social",
        "⬅️ BACK": "main"
    },
    "menu_social": {
        "FACEBOOK": "get_other_facebook", "INSTAGRAM": "get_other_instagram", "TIKTOK": "get_other_tiktok",
        "TWITTER": "get_other_twitter", "TELEGRAM": "get_other_telegram", "DISCORD": "get_other_discord",
        "⬅️ BACK": "menu_search"
    },
    "menu_codashop": {"CODA": "get_other_coda", "⬅️ BACK": "menu_search"},
    "menu_codm": {
        "100082": "select_lines_100082", "100055": "select_lines_100055", "100080": "select_lines_100080",
        "100054": "select_lines_100054", "100072": "select_lines_100072", "GASLITE": "select_lines_gaslite",
        "AUTHGOP": "select_lines_authgop", "GARENA": "select_lines_garena", "SSO": "select_lines_sso",
        "⬅️ BACK": "menu_search"
    },
    "menu_roblox": {"RBLX": "get_other_rblx", "⬅️ BACK": "menu_search"},
    "menu_mlbb": {"MTACC": "get_other_mtacc", "MAIN ML": "get_other_mainml", "⬅️ BACK": "menu_search"},
    "menu_cinema": {"NETFLIX": "get_other_netflix", "BILI BILI": "get_other_bilibili", "YOUTUBE": "get_other_youtube", "⬅️ BACK": "menu_search"},
    "menu_admin": {"STOCK": "admin_list_stock", "USERS": "admin_list_users", "STATS": "admin_statistics", "🚫 BLOCKLIST": "menu_blocklist", "📢 BROADCAST": "broadcast_start", "⬅️ BACK": "main"},
    "menu_blocklist": {"➕ ADD TO BLOCKLIST": "blocklist_add_start", "➖ REMOVE FROM BLOCKLIST": "blocklist_remove_start", "⬅️ BACK": "menu_admin"}
}

# ==================== UTILITY & DATA FUNCTIONS ====================
def build_keyboard(menu_items: dict, layout: str = 'default') -> InlineKeyboardMarkup:
    if not menu_items: return None
    buttons = [InlineKeyboardButton(format_button_text(text), callback_data=data) for text, data in menu_items.items()]

    if layout == 'search_layout':
        keyboard = []
        if not buttons: return None
        keyboard.append([buttons.pop(0)])
        back_button = None
        if buttons and buttons[-1].callback_data in ['main', 'menu_search']:
            back_button = buttons.pop(-1)
        if buttons:
            keyboard.extend([buttons[i:i + 2] for i in range(0, len(buttons), 2)])
        if back_button:
            keyboard.append([back_button])
        return InlineKeyboardMarkup(keyboard)

    # Default layout for main menu with tools included
    if layout == 'main_menu':
        keyboard = [
            buttons[0:2], # Search, Datadome
            buttons[2:4], # Separator, Merge
            buttons[4:6], # URL Remover, Duplicate Remover
            buttons[6:8]  # Admin, Clear
        ]
        return InlineKeyboardMarkup(keyboard)

    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(keyboard)


def load_data(file_path, default_value):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading {file_path}: {e}")
    return default_value

def save_data(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
    except IOError as e:
        logger.error(f"Error saving {file_path}: {e}")

user_data = load_data(USER_DATA_FILE, {})
generated_keys = load_data(GENERATED_KEYS_FILE, {})
keyword_usage = load_data(KEYWORD_USAGE_FILE, {})
banned_users = load_data(BANNED_USERS_FILE, {})

def get_total_stock():
    total_lines = 0
    if not os.path.exists(ACCOUNTS_FOLDER): return 0
    for filename in os.listdir(ACCOUNTS_FOLDER):
        if filename.endswith(".txt"):
            try:
                with open(os.path.join(ACCOUNTS_FOLDER, filename), 'r', encoding='utf-8', errors='ignore') as f:
                    lines = sum(1 for line in f if line.strip())
                    total_lines += lines
            except Exception: continue
    return total_lines

def get_key_remaining_time(user_info: dict) -> str:
    if not user_info: return "N/A"
    if user_info.get('duration') == float('inf'): return "Lifetime"
    redeemed_at = user_info.get('redeemed_at', 0)
    duration = user_info.get('duration', 0)
    if not redeemed_at or not duration: return "N/A"
    remaining_seconds = (redeemed_at + duration) - time.time()
    if remaining_seconds <= 0: return "Expired"
    days, rem = divmod(remaining_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{int(days)}d {int(hours)}h {int(minutes)}m"

def get_user_id_from_username(username_to_find: str) -> str | None:
    username_to_find = username_to_find.lstrip('@').lower()
    for user_id, data in user_data.items():
        if data.get('username', '').lower() == username_to_find:
            return user_id
    return None

def is_user_active(user_id):
    info = user_data.get(str(user_id))
    if not info: return False
    if info.get('duration') == float('inf'): return True
    return time.time() < (info.get('redeemed_at', 0) + info.get('duration', 0))

async def notify_admins(message: str, context: ContextTypes.DEFAULT_TYPE):
    for admin_id in ADMINS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to send notification to admin {admin_id}: {e}")

async def delete_message_after_delay(message: Update.message, delay: int):
    """Deletes a message after a specified delay in seconds."""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except error.BadRequest as e:
        logger.info(f"Could not delete message after delay: {e}")

# ==================== BAN & USAGE LIMIT SYSTEM ====================
async def show_cooldown(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Sends a message showing the generation cooldown."""
    cooldown_duration = 300  # 5 minutes
    try:
        # Initial message
        msg = await context.bot.send_message(chat_id=chat_id, text=f"▱▱▱▱▱▱▱▱▱▱ {cooldown_duration}sᴇᴄ")
        
        last_update_text = ""
        # Update loop for live countdown
        for i in range(cooldown_duration - 1, -1, -1):
            await asyncio.sleep(1)
            
            # Determine the number of solid blocks for the progress bar
            progress = int((cooldown_duration - i) / cooldown_duration * 10)
            progress_bar = "▰" * progress + "▱" * (10 - progress)
            
            current_text = f"{progress_bar} {i}sᴇᴄ"
            
            # Only edit if the text has changed to avoid hitting API limits
            if current_text != last_update_text:
                await msg.edit_text(current_text)
                last_update_text = current_text

        await msg.edit_text("▰▰▰▰▰▰▰▰▰▰ Cooldown finished")
        asyncio.create_task(delete_message_after_delay(msg, 5))
    except error.BadRequest as e:
        logger.info(f"Could not edit cooldown message, it was likely deleted: {e}")
    except Exception as e:
        logger.error(f"An error occurred in show_cooldown: {e}")

def is_user_banned(user_id):
    user_id_str = str(user_id)
    if user_id_str in banned_users:
        ban_info = banned_users[user_id_str]
        lift_time = ban_info.get("lift_time")
        if lift_time and time.time() < lift_time: return True
        elif lift_time and time.time() >= lift_time:
            del banned_users[user_id_str]
            save_data(BANNED_USERS_FILE, banned_users)
            return False
    return False

def get_ban_message(user_id):
    user_id_str = str(user_id)
    if user_id_str in banned_users:
        ban_info = banned_users[user_id_str]
        reason = ban_info.get('reason', 'Spamming generate command.')
        return (f"𝗬𝗢𝗨 𝗛𝗔𝗩𝗘 𝗕𝗘𝗘𝗡 𝗕𝗔𝗡𝗡𝗘𝗗 𝗙𝗥𝗢𝗠 𝗧𝗛𝗘 𝗦𝗬𝗦𝗧𝗘𝗠⚠️\n"
                f"──────────────────────\n"
                f"𝖱𝖤𝖠𝖲𝖮𝖭: {reason}\n"
                f"──────────────────────\n"
                f"𝘐𝘧 𝘺𝘰𝘶 𝘵𝘩𝘪𝘯𝘬 𝘵𝘩𝘪𝘴 𝘪𝘴 𝘢 𝘮𝘪𝘴𝘵𝘢𝘬𝘦 𝘱𝘭𝘦𝘢𝘴𝘦 𝘤𝘰𝘯𝘵𝘢𝘤𝘵:\n"
                f"@denjinx7📨")
    return "You are banned."

async def check_generation_gap(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id in ADMINS: return False
    user_info = user_data.get(str(user_id), {})
    last_gen_time = user_info.get('last_gen_time', 0)
    if last_gen_time > 0 and (time.time() - last_gen_time) < 300: # 5 minutes (300 seconds)
        ban_time = time.time()
        banned_users[str(user_id)] = {
            "ban_time": ban_time,
            "lift_time": ban_time + 3600, # 1 hour ban for spamming
            "reason": "Spamming generate command."
        }
        save_data(BANNED_USERS_FILE, banned_users)
        await context.bot.send_message(user_id, get_ban_message(user_id), parse_mode="HTML")
        await notify_admins(f"User @{user_info.get('username', user_id)} auto-banned for violating generation gap.", context)
        return True
    return False

def get_limit_info(user_info, line_count):
    is_lifetime = user_info.get('duration') == float('inf')
    # Lifetime users have no limits
    if is_lifetime:
        return {'limit': float('inf'), 'reset': 0, 'key': 'unlimited'}
    # Non-lifetime users
    else:
        if line_count == 50 or line_count == 100: return {'limit': float('inf'), 'reset': 0, 'key': 'unlimited'}
        if line_count == 150: return {'limit': 10, 'reset': 10800, 'key': 'cod_150'}
        if line_count == 200: return {'limit': 1, 'reset': 18000, 'key': 'cod_200_non'}
        return {'limit': 0, 'reset': 0, 'key': 'cod_500_non'}

def check_usage_limits(user_id, line_count):
    if user_id in ADMINS:
        return True, ""

    user_info = user_data.get(str(user_id), {})
    limit_info = get_limit_info(user_info, line_count)
    if limit_info['limit'] == float('inf'): return True, ""
    if limit_info['limit'] == 0: return False, "This option is unavailable for your key type."

    usage_data = user_info.get('usage_data', {})
    limit_key = limit_info['key']
    limit_record = usage_data.get(limit_key, {'count': 0, 'timestamp': 0})

    if time.time() - limit_record['timestamp'] > limit_info['reset']:
        limit_record = {'count': 0, 'timestamp': time.time()}

    if limit_record['count'] >= limit_info['limit']:
        remaining_time = limit_info['reset'] - (time.time() - limit_record['timestamp'])
        minutes, _ = divmod(remaining_time, 60)
        return False, f"Search limit reached for {line_count} lines. Resets in {int(minutes)}m."

    return True, ""

def update_usage_data(user_id, line_count):
    if user_id in ADMINS: return

    user_info = user_data.get(str(user_id), {})
    limit_info = get_limit_info(user_info, line_count)
    if limit_info['limit'] in [float('inf'), 0]: return

    usage_data = user_info.get('usage_data', {})
    limit_key = limit_info['key']
    limit_record = usage_data.get(limit_key, {'count': 0, 'timestamp': 0})
    if time.time() - limit_record['timestamp'] > limit_info['reset']:
        limit_record = {'count': 0, 'timestamp': time.time()}
    limit_record['count'] += 1
    usage_data[limit_key] = limit_record
    user_info['usage_data'] = usage_data
    user_data[str(user_id)] = user_info
    save_data(USER_DATA_FILE, user_data)

# ==================== CORE GENERATION LOGIC ====================
async def vend_accounts(user_id, keyword, line_count, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    if await check_generation_gap(user_id, context): return

    is_cod_keyword = line_count is not None
    if is_cod_keyword:
        allowed, message = check_usage_limits(user_id, line_count)
        if not allowed:
            await context.bot.send_message(chat_id=user_id, text=f"❌ {message}"); return
    else:
        is_lifetime = user_data.get(str(user_id), {}).get('duration') == float('inf')
        line_count = 150 if is_lifetime else 100
    
    # New loading animation
    loading_animation = ["▓▓▒▒▒▒▒▒▒▒▒", "▓▓▓▓▒▒▒▒▒▒▒", "▓▓▓▓▓▓▓▒▒▒▒", "▓▓▓▓▓▓▓▓▓▓▓"]
    msg = await context.bot.send_message(chat_id=user_id, text=loading_animation[0])
    for i in range(1, len(loading_animation)):
        await asyncio.sleep(1.25) # Total 5 seconds delay
        try: await msg.edit_text(loading_animation[i])
        except error.BadRequest: pass
    await msg.delete()

    file_path = os.path.join(ACCOUNTS_FOLDER, f"{keyword}.txt")
    if not os.path.exists(file_path):
        await context.bot.send_message(chat_id=user_id, text=f"❌ Cache '<code>{keyword}</code>' not found.", parse_mode="HTML"); return

    lock = file_locks.setdefault(file_path, asyncio.Lock())
    accounts_to_send = []

    async with lock:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f: lines = [line.strip() for line in f if line.strip()]
            if len(lines) < line_count:
                await context.bot.send_message(chat_id=user_id, text=f"Sorry, only {len(lines)} units left. At least {line_count} are required."); return

            accounts_to_send = random.sample(lines, line_count)
            remaining_accounts = [line for line in lines if line not in accounts_to_send]
            with open(file_path, 'w', encoding='utf-8') as f: f.write('\n'.join(remaining_accounts))
        except Exception as e:
            logger.error(f"Error vending accounts: {e}"); await context.bot.send_message(chat_id=user_id, text="An internal error occurred."); return

    output_filename = f"DENJI PREMIUM {keyword.upper()}.txt"
    with open(output_filename, 'w', encoding='utf-8') as f: f.write('\n'.join(accounts_to_send))

    try:
        user_info = user_data.get(str(user_id), {})
        file_size = os.path.getsize(output_filename)
        process_time = time.time() - start_time
        
        new_caption = (
            f"sᴜᴄᴄᴇsғᴜʟʟʏ ɢᴇɴᴇʀᴀᴛᴇᴅ ᴛʜᴀɴᴋ ʏᴏᴜ ғᴏʀ ᴜsɪɴɢ ɪᴛ✨\n\n"
            f"🍀ʀᴏᴡs: {len(accounts_to_send)}\n"
            f"🌐ᴅᴏᴍᴀɪɴ: {keyword.upper()}\n"
            f"📁ғɪʟᴇ sɪᴢᴇ: {file_size / 1024:.2f} KB\n"
            f"⚡ᴘʀᴏᴄᴇss ᴛɪᴍᴇ: {process_time:.2f} seconds\n"
            f"🔗ғᴏʀᴍᴀᴛ: user:pass\n"
            f"🗓️ɢᴇɴᴇʀᴀᴛᴇᴅ ᴏɴ: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            f"ɴᴏᴛᴇ: ᴀʟᴡᴀʏs ᴅᴏ ғᴇᴇᴅʙᴀᴄᴋs ғᴏʀ ʙᴏᴛ \n"
            f"ɪᴍᴘʀᴏᴠᴇᴍᴇɴᴛs ᴛʜᴀɴᴋ ʏᴏᴜ"
        )

        with open(output_filename, 'rb') as f:
            sent_message = await context.bot.send_document(
                chat_id=user_id, 
                document=f, 
                caption=new_caption, 
                parse_mode="HTML", 
                protect_content=True,
                filename=f"𝗗𝗘𝗡𝗝𝗜 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 {keyword.upper()}.txt"
            )
            asyncio.create_task(delete_message_after_delay(sent_message, 300)) # Delete after 5 minutes
        
        if user_id not in ADMINS:
            asyncio.create_task(show_cooldown(user_id, context))

        user_info['last_gen_time'] = time.time()
        user_info['generation_count'] = user_info.get('generation_count', 0) + 1
        user_data[str(user_id)] = user_info

        if is_cod_keyword: update_usage_data(user_id, line_count)
        else: save_data(USER_DATA_FILE, user_data)

        keyword_usage[keyword] = keyword_usage.get(keyword, 0) + 1
        save_data(KEYWORD_USAGE_FILE, keyword_usage)

        if user_id not in ADMINS:
            admin_notif = (f"<b>𝗛𝗘𝗬 𝗠𝗔𝗦𝗧𝗘𝗥 𝗦𝗢𝗠𝗘𝗢𝗡𝗘 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘𝗦 𝗙𝗜𝗟𝗘!</b>\n\n"
                           f"<b>NAME:</b> @{user_info.get('username', 'N/A')}\n"
                           f"<b>KEYWORD:</b> {keyword.upper()}\n"
                           f"<b>LINES:</b> {line_count}\n"
                           f"<b>KEY STATUS:</b> {get_key_remaining_time(user_info)}\n"
                           f"<b>DATE:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                           f"<b>𝗧𝗛𝗔𝗧 𝗜𝗦 𝗔𝗟𝗟 𝗠𝗔𝗦𝗧𝗘𝗥!</b>")
            await notify_admins(admin_notif, context)

    except Exception as e:
        logger.error(f"Failed to send document: {e}")
        async with lock:
            with open(file_path, 'a', encoding='utf-8') as f: f.write('\n'.join(accounts_to_send))
        await context.bot.send_message(chat_id=user_id, text="❌ Failed to send the file. Please try again.")
    finally:
        if os.path.exists(output_filename): os.remove(output_filename)

async def vend_datadome_file(user_id, context: ContextTypes.DEFAULT_TYPE):
    user_info = user_data.get(str(user_id), {})
    username = user_info.get('username', 'N/A')

    if await check_generation_gap(user_id, context): return

    file_path = os.path.join(ACCOUNTS_FOLDER, "datadome.txt")
    if not os.path.exists(file_path):
        await context.bot.send_message(chat_id=user_id, text="❌ The DATADOME cache is currently unavailable.", parse_mode="HTML")
        return

    lock = file_locks.setdefault(file_path, asyncio.Lock())
    limit = 5
    accounts_to_send = []
    async with lock:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            if len(lines) < limit:
                await context.bot.send_message(chat_id=user_id, text=f"Sorry, the DATADOME cache has less than {limit} lines.", parse_mode="HTML")
                return
            accounts_to_send = lines[:limit]
            remaining_accounts = lines[limit:]
            with open(file_path, 'w', encoding='utf-8') as f:
                for acc in remaining_accounts: f.write(acc + '\n')
        except Exception as e:
            logger.error(f"Error vending DATADOME file: {e}")
            await context.bot.send_message(chat_id=user_id, text="An internal error occurred.")
            return

    output_filename = f"DATADOME_BYPASS_{str(random.randint(100,999))}.txt"
    with open(output_filename, 'w', encoding='utf-8') as f: f.write('\n'.join(accounts_to_send))

    try:
        caption = (f"<b>🛡️ DATADOME BYPASSED 🛡️</b>\n\n"
                   f"<b>🧾 LINES:</b> {len(accounts_to_send)}\n"
                   f"<b>🗓️ DATE:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                   f"<b>👤 USER:</b> @{username}\n\n"
                   f"<i>This generation does not trigger bans.</i>")
        with open(output_filename, 'rb') as f:
            sent_message = await context.bot.send_document(chat_id=user_id, document=f, caption=caption, parse_mode="HTML", protect_content=True)
            asyncio.create_task(delete_message_after_delay(sent_message, 300))

        user_info['last_gen_time'] = time.time()
        user_info['generation_count'] = user_info.get('generation_count', 0) + 1
        user_data[str(user_id)] = user_info
        save_data(USER_DATA_FILE, user_data)
        
        if user_id not in ADMINS:
            admin_notification = (f"🛡️ <b>DATADOME Activity</b> 🛡️\n"
                                f"<b>User:</b> @{username}\n")
            await notify_admins(admin_notification, context)
            asyncio.create_task(show_cooldown(user_id, context))
    except Exception as e:
        logger.error(f"Failed to send DATADOME document to {user_id}: {e}")
        async with lock:
            with open(file_path, 'a', encoding='utf-8') as f: f.write('\n'.join(accounts_to_send))
        await context.bot.send_message(chat_id=user_id, text="❌ Failed to send the file. Please try again.")
    finally:
        if os.path.exists(output_filename): os.remove(output_filename)


# ==================== MAIN MENU & COMMANDS ====================
async def get_main_menu_components(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    user_info = user_data.get(str(user_id), {})
    user_name = user_info.get('username', 'N/A')

    def get_remaining(lines):
        is_lifetime = user_info.get('duration') == float('inf')
        if user_id in ADMINS or is_lifetime: return "Unlimited"
        
        limit_info = get_limit_info(user_info, lines)
        if limit_info['limit'] == float('inf'): return "Unlimited"
        if limit_info['limit'] == 0: return "0/0"
        
        limit_record = user_info.get('usage_data', {}).get(limit_info['key'], {'count': 0, 'timestamp': 0})
        if time.time() - limit_record['timestamp'] > limit_info['reset']:
            return f"0/{limit_info['limit']}"
        return f"{limit_record['count']}/{limit_info['limit']}"

    rem_500 = get_remaining(500)
    rem_200 = get_remaining(200)

    total_gens = user_info.get('generation_count', 0)
    
    popular_keyword = "N/A"
    if keyword_usage:
        popular_keyword = max(keyword_usage, key=keyword_usage.get).upper()

    caption = (
        f"ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴍᴀɪɴ ᴍᴇɴᴜ!\n"
        f"[ᴇɴᴊᴏʏ ᴛʜᴇ ᴜɴʟɪ ᴛᴏᴏʟs & ᴜɴʟɪ ɢᴇɴᴇʀᴀᴛɪᴏɴ]\n\n"
        f"[ᴜsᴇʀ ɪɴғᴏʀᴍᴀᴛɪᴏɴ]👥\n"
        f"ɴᴀᴍᴇ: {user_name}\n"
        f"ᴋᴇʏ sᴛᴀᴛᴜs: {get_key_remaining_time(user_info)}\n"
        f"500 ʟɪᴍɪᴛ: {rem_500}\n"
        f"200 ʟɪᴍɪᴛ: {rem_200}\n"
        f"ɢᴇɴᴇʀᴀᴛɪᴏɴ: {total_gens}\n\n"
        f"[ʙᴏᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ]🤖\n"
        f"ᴛᴏᴛᴀʟ ʟɪɴᴇs: {get_total_stock():,}\n"
        f"ʙᴏᴛ ᴠᴇʀsɪᴏɴ: 8.8.0\n"
        f"ᴘᴏᴘᴜʟᴀʀ: {popular_keyword}"
    )

    menu_items = MENUS["main"].copy()
    if user_id not in ADMINS: menu_items.pop("🧰 ADMIN", None)
    return caption, build_keyboard(menu_items, layout='main_menu')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text(get_ban_message(user_id), parse_mode="HTML"); return
    
    caption = (
        "⚜️𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗗𝗘𝗡𝗝𝗜 𝗣𝗥𝗜𝗩𝗔𝗧𝗘 𝗕𝗢𝗧⚜️\n\n"
        "𝖴𝖭𝖫𝖤𝖠𝖲𝖧 𝖳𝖧𝖤 𝖯𝖮𝖶𝖤𝖱 𝖮𝖥 𝖬𝖮𝖲𝖳 𝖯𝖠𝖫𝖣𝖮 𝖡𝖮𝖳\n"
        "𝖠𝖭𝖣 𝖠𝖢𝖢𝖴𝖱𝖠𝖳𝖤 𝖪𝖤𝖸𝖶𝖮𝖱𝖣𝖲 𝖶𝖨𝖳𝖧 𝖢𝖫𝖤𝖠𝖭 𝖴𝖨\n"
        "𝖠𝖭𝖣 𝖤𝖠𝖲𝖸 𝖳𝖮 𝖴𝖲𝖤 𝖶𝖨𝖳𝖧 𝖴𝖭𝖫𝖨 𝖦𝖤𝖭𝖤𝖱𝖠𝖳𝖨𝖮𝖭\n\n"
        "[ᴀᴠᴀɪʟᴀʙʟᴇ ᴜsᴇʀs ᴄᴏᴍᴍᴀɴᴅ]👥\n"
        "/sᴛᴀʀᴛ - ʟᴀᴜɴᴄʜ ᴛʜᴇ ʙᴏᴛ\n"
        "/ᴍᴇɴᴜ - ᴏᴘᴇɴ ᴛʜᴇ ᴍᴀɪɴғʀᴀᴍᴇ\n\n"
        "[ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs]💫\n"
        "/ɢᴇɴᴇʀᴀᴛᴇᴋᴇʏ - ɢᴇɴᴇʀᴀᴛᴇ ᴠᴀʟɪᴅ ᴋᴇʏ\n"
        "/ᴅᴇʟᴇᴛᴇᴜsᴇʀ - ᴅᴇʟᴇᴛᴇ sᴘᴇᴄɪғɪᴄ ᴜsᴇʀ\n"
        "/ʀᴇᴠᴏᴋᴇᴀʟʟ - ʀᴇᴠᴏᴋᴇ ᴀʟʟ ᴋᴇʏs\n"
        "/ʙʟᴏᴄᴋ - ʙʟᴏᴄᴋ sᴘᴇᴄɪғɪᴄ ᴜsᴇʀ\n"
        "/ʙʀᴏᴀᴅᴄᴀsᴛ - ᴀɴɴᴏᴜɴᴄᴇ ɪɴ ᴘᴜʙʟɪᴄ\n\n"
        "⚠️ᴀᴛᴛᴇɴᴛɪᴏɴ ᴜsᴇʀs⚠️\n"
        "[ᴘʟᴇᴀsᴇ ʀᴇᴀᴅ ᴛʜɪs ᴀɢᴀɪɴ ᴀɴᴅ ᴀɢᴀɪɴ]\n"
        "ᴛʜɪs ʙᴏᴛ ʜᴀᴠᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄ ʙᴀɴɴɪɴɢ sʏsᴛᴇᴍ\n"
        "ᴘʟᴇᴀsᴇ ᴅᴏɴ'ᴛ sᴘᴀᴍ ᴛʜᴇ ɢᴇɴᴇʀᴀᴛɪᴏɴ ᴏʀ ʏᴏᴜ\n"
        "ᴡɪʟʟ ғᴀᴄᴇ ᴛʜᴇ ᴄᴏɴsɪǫᴜᴇɴᴄᴇ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ 5\n"
        "ᴍɪɴᴜᴛᴇs ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ᴛʜᴇ ғɪʟᴇ ᴀɢᴀɪɴ.\n"
        "ɴᴇᴇᴅ ᴀ ᴠᴀʟɪᴅ ᴋᴇʏ ᴊᴜsᴛ ᴄᴏɴᴛᴀᴄᴛ ᴍᴇ ᴏɴ:\n"
        "@denjinx7📨"
    )

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(format_button_text("REDEEM"), callback_data="redeem_start")]])

    try:
        with open(WELCOME_VIDEO_PATH, 'rb') as video_file:
            await context.bot.send_video(chat_id=user_id, video=video_file, caption=caption, parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        await update.message.reply_text(caption, parse_mode='HTML', reply_markup=keyboard)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.effective_message
    if is_user_banned(user_id):
        await message.reply_text(get_ban_message(user_id), parse_mode="HTML"); return
    if user_id not in ADMINS and not is_user_active(user_id):
        await message.reply_text("❌ <b>Access Denied.</b> Use the REDEEM button or /redeemkey to authenticate.", parse_mode="HTML"); return

    caption, reply_markup = await get_main_menu_components(user_id)
    if update.callback_query:
        try: await update.callback_query.edit_message_text(caption, reply_markup=reply_markup, parse_mode="HTML")
        except error.BadRequest: await message.reply_text(caption, reply_markup=reply_markup, parse_mode="HTML")
    else: await message.reply_text(caption, reply_markup=reply_markup, parse_mode="HTML")

async def mykey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_info = user_data.get(user_id)
    if user_info and is_user_active(user_id):
        message = f"<b>Credential Status: ACTIVE</b>\n\n<b>Key:</b> <code>{user_info['key']}</code>\n<b>Access:</b> {get_key_remaining_time(user_info)}"
    else: message = "<b>Credential Status: INACTIVE</b>"
    await update.message.reply_text(message, parse_mode="HTML")

# ==================== BUTTON HANDLER ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    callback_data = query.data

    if is_user_banned(user_id):
        await query.answer(get_ban_message(user_id), show_alert=True); return

    if callback_data == "clear_menu":
        try: await query.message.delete()
        except: pass; return

    if callback_data == "main":
        await menu(update, context); return

    if callback_data == "menu_datadome":
        await query.message.delete()
        await vend_datadome_file(user_id, context)
        return

    if callback_data.startswith("select_lines_"):
        keyword = callback_data.split("select_lines_")[1]
        user_info = user_data.get(str(user_id), {})
        is_lifetime = user_info.get('duration') == float('inf')

        lines_menu = {
            "50 LINES": f"generate_{keyword}_50", "100 LINES": f"generate_{keyword}_100",
            "150 LINES": f"generate_{keyword}_150", "200 LINES": f"generate_{keyword}_200",
        }
        if is_lifetime or user_id in ADMINS:
            lines_menu["500 LINES"] = f"generate_{keyword}_500"
        lines_menu["⬅️ BACK"] = "menu_codm"

        await query.edit_message_text(text="Please select the number of lines to generate:", reply_markup=build_keyboard(lines_menu, layout='default'))
        return

    if callback_data.startswith("generate_"):
        parts = callback_data.split("_")
        keyword, line_count = parts[1], int(parts[2])
        await query.message.delete()
        await vend_accounts(user_id, keyword, line_count, context); return

    if callback_data.startswith("get_other_"):
        keyword = callback_data.split("get_other_")[1]
        await query.message.delete()
        await vend_accounts(user_id, keyword, None, context); return

    if callback_data in MENUS:
        caption = "Please choose your button below."
        layout_style = 'search_layout' if 'menu_' in callback_data and 'admin' not in callback_data and 'tools' not in callback_data else 'default'
        if callback_data == "menu_codm":
            caption = ("TANDAAN MO BANNING SYSTEM KUPAL!\n"
                       "TRY MO IBANG KEYWORD KUNG DI KA PALDO!\n"
                       "MAG FEEDBACK KA KUPAL WAG TAMAD!\n\n"
                       "𝗞𝗔𝗕𝗔𝗧𝗔𝗔𝗡 𝗔𝗡𝗚 𝗣𝗔𝗚 𝗔𝗦𝗔 𝗡𝗚 𝗕𝗔𝗬𝗔𝗡!\n"
                       "ʙʏ: J. RIZAL")
        menu_items = MENUS[callback_data].copy()
        await query.edit_message_text(text=caption, reply_markup=build_keyboard(menu_items, layout=layout_style))
        return

    if callback_data == "admin_reset_stats":
        keyword_usage.clear()
        save_data(KEYWORD_USAGE_FILE, {})
        await query.answer("✅ Keyword usage statistics have been reset.", show_alert=True)
        await admin_statistics(update, context)
        return

    if callback_data == "admin_list_stock": await admin_list_stock(update, context)
    elif callback_data == "admin_list_users": await admin_list_users(update, context)
    elif callback_data == "admin_statistics": await admin_statistics(update, context)


# ==================== FULL CONVERSATION HANDLERS & COMMANDS ====================
async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation canceled.")
    return ConversationHandler.END

async def menu_in_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await menu(update, context)
    return ConversationHandler.END

# --- REDEEM KEY ---
async def redeemkey_start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("𝗣𝗟𝗘𝗔𝗦𝗘 𝗧𝗬𝗣𝗘 𝗬𝗢𝗨𝗥 𝗞𝗘𝗬 𝗔𝗡𝗗 𝗦𝗘𝗡𝗗 𝗜𝗧 𝗛𝗘𝗥𝗘")
    return AWAITING_REDEEM_KEY

async def redeemkey_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_caption(caption="𝗣𝗟𝗘𝗔𝗦𝗘 𝗧𝗬𝗣𝗘 𝗬𝗢𝗨𝗥 𝗞𝗘𝗬 𝗔𝗡𝗗 𝗦𝗘𝗡𝗗 𝗜𝗧 𝗛𝗘𝗥𝗘", reply_markup=None)
    except error.BadRequest:
        try:
            await query.edit_message_text(text="𝗣𝗟𝗘𝗔𝗦𝗘 𝗧𝗬𝗣𝗘 𝗬𝗢𝗨𝗥 𝗞𝗘𝗬 𝗔𝗡𝗗 𝗦𝗘𝗡𝗗 𝗜𝗧 𝗛𝗘𝗥𝗘", reply_markup=None)
        except Exception as e:
            logger.error(f"Failed to start redeem conversation from callback: {e}")
            await query.message.reply_text("𝗣𝗟𝗘𝗔𝗦𝗘 𝗧𝗬𝗣𝗘 𝗬𝗢𝗨𝗥 𝗞𝗘𝗬 𝗔𝗡𝗗 𝗦𝗘𝗡𝗗 𝗜𝗧 𝗛𝗘𝗥𝗘")
    return AWAITING_REDEEM_KEY

async def process_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_info_obj = update.message.from_user; user_id = str(user_info_obj.id)
    key_to_redeem = update.message.text.strip()
    if is_user_banned(user_id):
        await update.message.reply_text(get_ban_message(user_id), parse_mode="HTML"); return ConversationHandler.END
    if is_user_active(user_id):
        await update.message.reply_text("✅ You already have an active key."); return ConversationHandler.END

    key_data = generated_keys.get(key_to_redeem)
    if key_data and time.time() - key_data.get('created_at', 0) <= 86400:
        user_data[user_id] = {
            "key": key_to_redeem,
            "redeemed_at": time.time(),
            "duration": key_data.get("duration"),
            "username": user_info_obj.username or user_info_obj.first_name,
            "last_gen_time": 0,
            "usage_data": {},
            "generation_count": 0
        }
        del generated_keys[key_to_redeem]
        save_data(USER_DATA_FILE, user_data); save_data(GENERATED_KEYS_FILE, generated_keys)
        validity = "Lifetime" if key_data.get("duration") == float('inf') else get_key_remaining_time(user_data[user_id])
        await update.message.reply_text(f"<b>✅KEY SUCCESSFULLY REDEEMED✅</b>\n<b>VALIDITY:</b> {validity}", parse_mode="HTML")
        admin_message = (f"<b>𝗛𝗘𝗬 𝗠𝗔𝗦𝗧𝗘𝗥 𝗡𝗘𝗪 𝗨𝗦𝗘𝗥 𝗥𝗘𝗗𝗘𝗠𝗣𝗧𝗜𝗢𝗡</b>\n\n"
                         f"𝖭𝖠𝖬𝖤: @{user_info_obj.username or user_info_obj.first_name}\n"
                         f"𝖵𝖠𝖫𝖨𝖣𝖨𝖳𝖸: {validity}\n"
                         f"𝖱𝖤𝖣𝖤𝖤𝖬 𝖮𝖭: {datetime.now().strftime('%Y-%m-%d')}\n"
                         f"𝖪𝖤𝖸 𝖴𝖲𝖤𝖣: <code>{key_to_redeem}</code>")
        await notify_admins(admin_message, context)
    else:
        if key_data: del generated_keys[key_to_redeem]; save_data(GENERATED_KEYS_FILE, generated_keys); await update.message.reply_text("❌ This key has expired.")
        else: await update.message.reply_text("❌ 𝗬𝗢𝗨𝗥 𝗞𝗘𝗬 𝗜𝗦 𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗢𝗥 𝗔𝗟𝗥𝗘𝗔𝗗𝗬 𝗨𝗦𝗘𝗗 ❌")

    await menu(update, context)
    return ConversationHandler.END

# --- ADMIN INFO COMMANDS ---
async def admin_list_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    stock_message = "⚜️<b>𝗞𝗘𝗬𝗪𝗢𝗥𝗗𝗦 𝗟𝗜𝗡𝗘𝗦 𝗦𝗧𝗢𝗖𝗞𝗦</b>⚜️\n\n"
    
    # Define all possible keywords that should be tracked
    all_keywords = [
        "100082", "100055", "100080", "100054", "100072", "gaslite", "authgop",
        "garena", "sso", "mtacc", "mainml", "rblx", "netflix", "bilibili",
        "youtube", "coda", "facebook", "instagram", "tiktok", "twitter",
        "telegram", "discord", "datadome"
    ]

    stock_data = {}
    for keyword in all_keywords:
        file_path = os.path.join(ACCOUNTS_FOLDER, f"{keyword}.txt")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = sum(1 for line in f if line.strip())
                stock_data[keyword] = lines
            except Exception:
                stock_data[keyword] = "Error"
        else:
            stock_data[keyword] = 0

    if not stock_data:
        stock_message += "⚫ NO KEYWORDS FOUND"
    else:
        for keyword, lines in sorted(stock_data.items()):
            if isinstance(lines, int):
                if lines > 500: dot = "🟢"
                elif lines > 100: dot = "🟠"
                elif lines > 0: dot = "🔴"
                else: dot = "⚫"
                stock_message += f"{dot} <b>{keyword.upper()}</b> - {lines:,} Lines\n"
            else: # Error case
                stock_message += f"⚫ <b>{keyword.upper()}</b> - Error Reading\n"

    await query.edit_message_text(text=stock_message, reply_markup=build_keyboard({"⬅️ BACK": "menu_admin"}), parse_mode="HTML")

async def admin_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    active_users = {uid: data for uid, data in user_data.items() if is_user_active(uid)}
    if not active_users:
        await query.edit_message_text("🧸<b>𝗔𝗖𝗧𝗜𝗩𝗘 𝗨𝗦𝗘𝗥</b>🧸\n\nNo active users found.", reply_markup=build_keyboard({"⬅️ BACK": "menu_admin"}), parse_mode="HTML"); return

    user_list_str = "🧸<b>𝗔𝗖𝗧𝗜𝗩𝗘 𝗨𝗦𝗘𝗥</b>🧸\n\n"
    for uid, info in active_users.items():
        user_list_str += f"@{info.get('username', uid)} - {get_key_remaining_time(info)}\n"

    await query.edit_message_text(text=user_list_str, reply_markup=build_keyboard({"⬅️ BACK": "menu_admin"}), parse_mode="HTML")

async def admin_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    buttons = {"RESET STATS": "admin_reset_stats", "⬅️ BACK": "menu_admin"}
    if not keyword_usage:
        await query.edit_message_text("⚜️<b>𝗞𝗘𝗬𝗪𝗢𝗥𝗗 𝗨𝗦𝗔𝗚𝗘</b>⚜️\n\nNo keywords used yet.", reply_markup=build_keyboard(buttons), parse_mode="HTML"); return

    stats_msg = "⚜️<b>𝗞𝗘𝗬𝗪𝗢𝗥𝗗 𝗨𝗦𝗔𝗚𝗘</b>⚜️\n\n<b>KEYWORD LIST     USES</b>\n"
    sorted_keywords = sorted(keyword_usage.items(), key=lambda item: item[1], reverse=True)
    for keyword, count in sorted_keywords:
        stats_msg += f"<code>{keyword.upper():<16} - {count}</code>\n"

    await query.edit_message_text(text=stats_msg, reply_markup=build_keyboard(buttons), parse_mode="HTML")

# --- BROADCAST ---
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.edit_message_text("Please send the message you want to broadcast (text or photo).")
    return AWAITING_BROADCAST_CONTENT

async def process_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_user = update.message.from_user
    active_user_ids = {uid for uid in user_data if is_user_active(uid) and not is_user_banned(uid)} | {str(admin) for admin in ADMINS}
    sent_count = 0
    message_base = f"<b>ADMIN ANNOUNCEMENT!!</b>\n────────────────────\n{{content}}\n────────────────────\n<b>Messenger:</b> @{admin_user.username}"
    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
        for user_id in active_user_ids:
            try:
                await context.bot.send_photo(chat_id=user_id, photo=photo_file_id, caption=message_base.format(content=update.message.caption or ''), parse_mode="HTML")
                sent_count += 1; await asyncio.sleep(0.05)
            except Exception as e: logger.error(f"Broadcast photo failed for {user_id}: {e}")
    elif update.message.text:
        for user_id in active_user_ids:
            try:
                await context.bot.send_message(chat_id=user_id, text=message_base.format(content=update.message.text), parse_mode="HTML")
                sent_count += 1; await asyncio.sleep(0.05)
            except Exception as e: logger.error(f"Broadcast text failed for {user_id}: {e}")
    await update.message.reply_text(f"✅ Broadcast sent to {sent_count}/{len(active_user_ids)} users.")
    return ConversationHandler.END

# --- BLOCKLIST ---
async def blocklist_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.edit_message_text("Please reply with the user to block:\n<code>@username [number] [minutes/days/years] [reason...]</code>", parse_mode="HTML")
    return AWAITING_BLOCKLIST_ADD

async def process_blocklist_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        parts = update.message.text.split(maxsplit=3)
        if len(parts) < 3: raise ValueError("Invalid format")
        username, duration_val_str, unit = parts[0], parts[1], parts[2]
        reason = parts[3] if len(parts) > 3 else "Manual ban by admin."

        if not username.startswith('@'): raise ValueError("Username must start with @")
        user_id_to_ban = get_user_id_from_username(username)
        if not user_id_to_ban:
            await update.message.reply_text(f"❌ User '<code>{username}</code>' not found.", parse_mode="HTML"); return ConversationHandler.END

        duration_val = int(duration_val_str)
        unit = unit.lower().rstrip('s')
        duration_map = {"minute": 60, "day": 86400, "year": 31536000}
        if unit not in duration_map:
            await update.message.reply_text("❌ Invalid unit. Use: <code>minutes</code>, <code>days</code>, or <code>years</code>.", parse_mode="HTML"); return AWAITING_BLOCKLIST_ADD

        ban_duration_seconds = duration_val * duration_map[unit]
        ban_time = time.time()
        banned_users[user_id_to_ban] = {"ban_time": ban_time, "lift_time": ban_time + ban_duration_seconds, "reason": reason}
        save_data(BANNED_USERS_FILE, banned_users)
        await update.message.reply_text(f"✅ User <code>{username}</code> has been added to the blocklist for {duration_val} {unit}(s).", parse_mode="HTML")
    except (IndexError, ValueError) as e:
        logger.error(f"Error processing blocklist add: {e}")
        await update.message.reply_text("Invalid format. Please use <code>@username [number] [unit] [reason...]</code>.", parse_mode="HTML"); return AWAITING_BLOCKLIST_ADD
    return ConversationHandler.END

async def blocklist_remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.edit_message_text("Please reply with the username to remove from the blocklist (e.g., @username).")
    return AWAITING_BLOCKLIST_REMOVE

async def process_blocklist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username_to_unban = update.message.text
    if not username_to_unban.startswith('@'):
        await update.message.reply_text("Invalid format. Please provide a valid username starting with @."); return AWAITING_BLOCKLIST_REMOVE
    user_id_to_unban = get_user_id_from_username(username_to_unban)
    if not user_id_to_unban:
        await update.message.reply_text(f"❌ User '<code>{username_to_unban}</code>' not found.", parse_mode="HTML"); return ConversationHandler.END
    if str(user_id_to_unban) in banned_users:
        del banned_users[str(user_id_to_unban)]
        save_data(BANNED_USERS_FILE, banned_users)
        await update.message.reply_text(f"✅ User <code>{username_to_unban}</code> removed from blocklist.", parse_mode="HTML")
        try: await context.bot.send_message(chat_id=int(user_id_to_unban), text="You have been unbanned by an admin.")
        except Exception as e: logger.error(f"Could not notify user {user_id_to_unban} about unban: {e}")
    else: await update.message.reply_text("❌ User is not on the blocklist.")
    return ConversationHandler.END

# --- TOOLS ---
async def separator_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.edit_message_text("Please send or forward the .txt file you want to separate.")
    return AWAITING_SEPARATOR_FILE

async def process_separator_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    if not (message.document and message.document.file_name.endswith('.txt')):
        await message.reply_text("⚠️ Please send or forward a <code>.txt</code> file.", parse_mode="HTML")
        return AWAITING_SEPARATOR_FILE

    doc = await message.document.get_file()
    input_filename = f"temp_separator_{doc.file_id}.txt"
    await doc.download_to_drive(input_filename)
    
    await message.reply_text("Separating file... this may take a while.")
    
    keywords = {
        "garena": "garena.txt", "sso.garena.com": "sso.txt", "100082": "100082.txt",
        "mtacc": "mtacc.txt", "facebook": "facebook.txt", "instagram": "instagram.txt",
        "tiktok": "tiktok.txt", "netflix": "netflix.txt", "discord": "discord.txt"
    }
    
    output_folder = f"separator_output_{doc.file_id}"
    os.makedirs(output_folder, exist_ok=True)
    
    line_count = {k: 0 for k in keywords}
    output_files = {k: open(os.path.join(output_folder, fname), "w", encoding="utf-8") for k, fname in keywords.items()}
    total_lines = 0
    
    try:
        with open(input_filename, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                total_lines += 1
                lcline = line.lower()
                for kw in keywords:
                    if kw in lcline:
                        output_files[kw].write(line)
                        line_count[kw] += 1
                        break
        for f in output_files.values(): f.close()

        # Create a zip file
        zip_filename = f"Separated_Logs_{doc.file_id}.zip"
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for root, _, files in os.walk(output_folder):
                for file in files:
                    if os.path.getsize(os.path.join(root, file)) > 0:
                        zipf.write(os.path.join(root, file), arcname=file)

        summary = f"<b>Separation Complete!</b>\nProcessed: {total_lines:,} lines.\n\n"
        
        if os.path.getsize(zip_filename) > 0:
            await context.bot.send_document(chat_id=message.chat_id, document=open(zip_filename, 'rb'), caption=summary, parse_mode="HTML")
        else:
            await message.reply_text("No matching keywords found to separate.")

    finally:
        # Cleanup
        os.remove(input_filename)
        if 'zip_filename' in locals() and os.path.exists(zip_filename):
            os.remove(zip_filename)
        if os.path.exists(output_folder):
            for file in os.listdir(output_folder):
                os.remove(os.path.join(output_folder, file))
            os.rmdir(output_folder)

    return ConversationHandler.END


async def merge_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['merged_content'] = []
    await update.callback_query.edit_message_text("📁 <b>Merge Tool</b>\n\nSend <code>.txt</code> files to combine. Use <code>/save &lt;filename.txt&gt;</code> when finished.", parse_mode="HTML")
    return AWAITING_MERGE_FILES

async def receive_merge_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not (update.message.document and update.message.document.file_name.endswith('.txt')): await update.message.reply_text("⚠️ Please send only <code>.txt</code> files.", parse_mode="HTML"); return AWAITING_MERGE_FILES
    try:
        file = await update.message.document.get_file()
        accounts = (await file.download_as_bytearray()).decode('utf-8').strip().splitlines()
        context.user_data.get('merged_content', []).extend(accounts)
        await update.message.reply_text(f"✅ Added <b>{len(accounts)}</b> lines.\nTotal lines: <b>{len(context.user_data['merged_content'])}</b>.", parse_mode="HTML")
    except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    return AWAITING_MERGE_FILES

async def save_merged_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if len(context.args) < 1: await update.message.reply_text("Usage: <code>/save &lt;new_filename.txt&gt;</code>", parse_mode="HTML"); return AWAITING_MERGE_FILES
    filename = context.args[0]
    if not filename.endswith('.txt'): filename += '.txt'
    merged_content = context.user_data.get('merged_content', [])
    if not merged_content: await update.message.reply_text("No content to save."); return AWAITING_MERGE_FILES
    with open(filename, 'w', encoding='utf-8') as f:
        for line in merged_content: f.write(line.strip() + '\n')
    try:
        with open(filename, 'rb') as f: await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption=(f"🎉 <b>Merge Complete!</b>\n<i>{len(merged_content)}</i> lines."), parse_mode="HTML")
    except Exception as e: await update.message.reply_text(f"❌ Failed to send file: {e}")
    finally:
        if os.path.exists(filename): os.remove(filename)
    context.user_data.pop('merged_content', None)
    return ConversationHandler.END

async def duplicate_remover_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.edit_message_text("🧾 <b>Duplicate Remover</b>\n\nPlease send the <code>.txt</code> file to clean.", parse_mode="HTML")
    return AWAITING_DUPLICATE_REMOVER_FILE

async def process_duplicate_remover_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not (update.message.document and update.message.document.file_name.endswith('.txt')): await update.message.reply_text("⚠️ Please send a <code>.txt</code> file.", parse_mode="HTML"); return AWAITING_DUPLICATE_REMOVER_FILE
    output_filename = ""
    try:
        document = update.message.document
        file = await document.get_file()
        lines = (await file.download_as_bytearray()).decode('utf-8', 'ignore').strip().splitlines()
        original_count = len(lines)
        unique_lines = list(dict.fromkeys(lines))
        cleaned_count = len(unique_lines)
        removed_count = original_count - cleaned_count
        output_filename = f"cleaned_{document.file_name}"
        with open(output_filename, 'w', encoding='utf-8') as f: f.write('\n'.join(unique_lines))
        with open(output_filename, 'rb') as f: await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption=f"✅ <b>Cleaning Complete!</b>\n\n<b>Original:</b> <code>{original_count}</code>\n<b>Removed:</b> <code>{removed_count}</code>\n<b>Final:</b> <code>{cleaned_count}</code>", parse_mode="HTML")
    except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    finally:
        if output_filename and os.path.exists(output_filename): os.remove(output_filename)
    return ConversationHandler.END

async def url_remover_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.edit_message_text("🖥️ <b>URL Remover & Credential Extractor</b>\n\nPlease send the <code>.txt</code> file to process.", parse_mode="HTML")
    return AWAITING_URL_REMOVER_FILE

async def process_url_remover_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not (update.message.document and update.message.document.file_name.endswith('.txt')):
        await update.message.reply_text("⚠️ Please send a <code>.txt</code> file.", parse_mode="HTML")
        return AWAITING_URL_REMOVER_FILE

    output_filename = ""
    try:
        document = update.message.document
        file = await document.get_file()
        lines = (await file.download_as_bytearray()).decode('utf-8', 'ignore').splitlines()
        original_count = len(lines)

        extracted_creds = []
        cred_pattern = re.compile(r'([^:]+:[^:]+)$')

        for line in lines:
            match = cred_pattern.search(line.strip())
            if match:
                extracted_creds.append(match.group(1))

        final_count = len(extracted_creds)
        output_filename = f"extracted_{document.file_name}"
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(extracted_creds))

        with open(output_filename, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.message.chat_id,
                document=f,
                caption=(
                    f"✅ <b>Extraction Complete!</b>\n\n"
                    f"<b>Lines Processed:</b> {original_count}\n"
                    f"<b>Credentials Extracted:</b> {final_count}"
                ),
                parse_mode="HTML"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing file: {e}")
    finally:
        if output_filename and os.path.exists(output_filename):
            os.remove(output_filename)
    return ConversationHandler.END


# --- ADMIN COMMANDS ---
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS: return
    if not (update.message.reply_to_message and update.message.reply_to_message.document and update.message.reply_to_message.document.file_name.endswith('.txt')):
        await update.message.reply_text("Usage: Reply to a .txt file with <code>/add &lt;keyword&gt;</code>.", parse_mode="HTML"); return
    if not context.args: await update.message.reply_text("Please specify a keyword."); return
    keyword = context.args[0].lower()
    file_path = os.path.join(ACCOUNTS_FOLDER, f"{keyword}.txt")

    try:
        file = await update.message.reply_to_message.document.get_file()
        content = (await file.download_as_bytearray()).decode('utf-8', 'ignore')

        cleaned_lines_from_upload = set()
        filter_keywords = [
            "successfully generated", "file name", "generated at", "domain",
            "process time", "rows", "format", "file size", "powered by"
        ]

        for line in content.strip().splitlines():
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            if not line_stripped or line_stripped.startswith('[duration]'): continue
            if any(kw in line_lower for kw in filter_keywords): continue

            cleaned_lines_from_upload.add(line_stripped)

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                existing_lines = {line.strip() for line in f if line.strip()}
        else:
            existing_lines = set()

        combined_lines = sorted(list(existing_lines | cleaned_lines_from_upload))

        with open(file_path, 'w', encoding='utf-8') as f:
            for line in combined_lines:
                f.write(line + '\n')

        upload_count = len(cleaned_lines_from_upload)
        total_count = len(combined_lines)
        await update.message.reply_text(f"✅ Successfully processed!\n\n- <b>Added/Updated:</b> {upload_count} lines.\n- <b>Total lines for '{keyword.upper()}':</b> {total_count} lines.", parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in /add command: {e}")
        await update.message.reply_text(f"An error occurred: {e}")

async def generatekey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    if user_id not in ADMINS: return
    if not args or len(args) < 2:
        await update.message.reply_text("<b>Usage:</b> <code>/generatekey [count] [duration] [unit]</code>\n"
                                     "<b>Example:</b> <code>/generatekey 5 7 days</code>\n"
                                     "<b>Example:</b> <code>/generatekey 1 lifetime</code>", parse_mode="HTML"); return
    try:
        count = int(args[0])
        now = datetime.now()
        date_generated_str = now.strftime('%Y-%m-%d')
        date_expire_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')

        if len(args) == 2 and args[1].lower() == 'lifetime':
            duration_seconds, validity_str = float('inf'), "LIFETIME"
        elif len(args) == 3:
            duration_val = int(args[1]); unit = args[2].lower().rstrip('s')
            duration_map = {"day": 86400, "hour": 3600, "minute": 60}
            if unit not in duration_map: await update.message.reply_text("Invalid unit."); return
            duration_seconds = duration_val * duration_map[unit]
            validity_str = f"{duration_val} {unit.upper()}(S)"
        else: await update.message.reply_text("Invalid format."); return

        keys_generated = []
        for _ in range(count):
            chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            key = f"ᴅᴇɴᴊɪ - {chars[0:4]}-{chars[4:7]}-{chars[7:10]}"
            keys_generated.append(key)
        
        for key in keys_generated: 
            generated_keys[key] = {"duration": duration_seconds, "created_at": time.time()}
        
        save_data(GENERATED_KEYS_FILE, generated_keys)
        
        keys_list_str = "\n".join([f"▫️ <code>{key}</code>" for key in keys_generated])
        
        await update.message.reply_text(
            f"𝗞𝗘𝗬(𝗦) 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘𝗗✨\n"
            f"──────────────────────\n"
            f"{keys_list_str}\n\n"
            f"ɴᴏᴛᴇ: ᴛʜɪs ᴋᴇʏ ɪs ᴏɴᴇ ᴛɪᴍᴇ ᴜsᴇ ᴏɴʟʏ!\n"
            f"──────────────────────\n"
            f"⌛ᴠᴀʟɪᴅɪᴛʏ: {validity_str}\n"
            f"🗓️ᴅᴀᴛᴇ ɢᴇɴᴇʀᴀᴛᴇ: {date_generated_str}\n"
            f"⏰ᴅᴀᴛᴇ ᴇxᴘɪʀᴇ: {date_expire_str}\n"
            f"🍀ᴛᴏᴛᴀʟ: {count}\n"
            f"🤖ʙᴏᴛ: @dej_private_bot\n\n"
            f"ᴛʜᴀɴᴋʏᴏᴜ ғᴏʀ sᴜᴘᴘᴏʀᴛɪɴɢ ᴍʏ ʙᴏᴛ!✨",
            parse_mode="HTML"
        )
    except (ValueError, IndexError): await update.message.reply_text("Invalid command format.")

async def deleteuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS: return
    if not context.args: await update.message.reply_text("Usage: /deleteuser <@username or user_id>"); return
    identifier = context.args[0]
    user_id = get_user_id_from_username(identifier) if identifier.startswith('@') else identifier
    if user_id and str(user_id) in user_data:
        del user_data[str(user_id)]
        save_data(USER_DATA_FILE, user_data)
        await update.message.reply_text(f"🗑️ User {identifier} has been deleted.")
    else: await update.message.reply_text("❌ User not found.")

async def revokeall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS: return
    generated_keys.clear(); user_data.clear()
    save_data(GENERATED_KEYS_FILE, {}); save_data(USER_DATA_FILE, {})
    await update.message.reply_text("🔥 All keys and user data purged.")

# ==================== MAIN SETUP ====================
def main():
    application = Application.builder().token(TOKEN).build()

    fallbacks = [CommandHandler("cancel", cancel_conversation), CommandHandler("menu", menu_in_conversation)]

    redeem_conv = ConversationHandler(
        entry_points=[
            CommandHandler("redeemkey", redeemkey_start_cmd),
            CallbackQueryHandler(redeemkey_start_callback, pattern='^redeem_start$')
        ],
        states={AWAITING_REDEEM_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_key)]},
        fallbacks=fallbacks,
        per_message=False
    )
    broadcast_conv = ConversationHandler(entry_points=[CallbackQueryHandler(broadcast_start, pattern='^broadcast_start$')], states={AWAITING_BROADCAST_CONTENT: [MessageHandler(filters.TEXT | filters.PHOTO, process_broadcast_content)]}, fallbacks=fallbacks, per_message=False)
    separator_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(separator_start, pattern='^separator_start$')], 
        states={AWAITING_SEPARATOR_FILE: [MessageHandler(filters.Document.TXT, process_separator_file)]}, 
        fallbacks=fallbacks, 
        per_message=False
    )
    blocklist_add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(blocklist_add_start, pattern='^blocklist_add_start$')],
        states={AWAITING_BLOCKLIST_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_blocklist_add)]},
        fallbacks=fallbacks,
        per_message=False
    )
    blocklist_remove_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(blocklist_remove_start, pattern='^blocklist_remove_start$')],
        states={AWAITING_BLOCKLIST_REMOVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_blocklist_remove)]},
        fallbacks=fallbacks,
        per_message=False
    )
    merge_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(merge_start, pattern='^merge_start$')],
        states={AWAITING_MERGE_FILES: [MessageHandler(filters.Document.TXT, receive_merge_files), CommandHandler("save", save_merged_file)]},
        fallbacks=fallbacks,
        per_message=False
    )
    duplicate_remover_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(duplicate_remover_start, pattern='^duplicate_remover_start$')],
        states={AWAITING_DUPLICATE_REMOVER_FILE: [MessageHandler(filters.Document.TXT, process_duplicate_remover_file)]},
        fallbacks=fallbacks,
        per_message=False
    )
    url_remover_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(url_remover_start, pattern='^url_remover_start$')],
        states={AWAITING_URL_REMOVER_FILE: [MessageHandler(filters.Document.TXT, process_url_remover_file)]},
        fallbacks=fallbacks,
        per_message=False
    )

    # Add all command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("mykey", mykey))
    application.add_handler(CommandHandler("generatekey", generatekey))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("revokeall", revokeall))
    application.add_handler(CommandHandler("deleteuser", deleteuser))

    # Add all conversation handlers
    application.add_handler(redeem_conv)
    application.add_handler(broadcast_conv)
    application.add_handler(separator_conv)
    application.add_handler(blocklist_add_conv)
    application.add_handler(blocklist_remove_conv)
    application.add_handler(merge_conv)
    application.add_handler(duplicate_remover_conv)
    application.add_handler(url_remover_conv)

    # Add the main button handler last
    application.add_handler(CallbackQueryHandler(button_handler))

    os.makedirs('assets', exist_ok=True)
    os.makedirs(ACCOUNTS_FOLDER, exist_ok=True)

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()