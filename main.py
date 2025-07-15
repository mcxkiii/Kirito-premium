# ==================== IMPORTS ====================
import os
import logging
import time
import random
import string
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import asyncio

# ==================== BOT CONFIGURATION ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "7930962502:AAFmGuNzHCu5HVyr_ocfmei3OZLmnAZmj-s"
ADMINS = [6818427110]

ACCOUNTS_FOLDER = 'accounts'
USER_DATA_FILE = 'user_data.json'
GENERATED_KEYS_FILE = 'generated_keys.json'
RECRUITMENT_DATA_FILE = 'recruitment_data.json'
file_locks = {}

# Conversation states
RECEIVING_FILES, AWAITING_FILENAME = range(2)
AWAITING_RECRUITER_UID, AWAITING_INVITED_UID = range(2, 4)

# ==================== UTILITY FUNCTIONS ====================
def load_data(file_path, default_value):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return default_value
    return default_value

def save_data(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

# Load existing data from files at startup
user_data = load_data(USER_DATA_FILE, {})
generated_keys = load_data(GENERATED_KEYS_FILE, {})
recruitment_data = load_data(RECRUITMENT_DATA_FILE, {})
user_cooldowns = {}

MENUS = {
    "main": {
        "🎯 CALL OF DUTY": "menu_codm",
        "📦 ROBLOX": "menu_roblox",
        "💎 MOONTOON": "menu_moontoon",
        "⚙️ ADMIN TOOLS": "menu_admin"
    },
    "menu_free_key": {
        "RECRUITER UID🧸": "recruiter_uid",
        "INVITED UID🧸": "invited_uid",
        "INSTRUCTIONS🗒️": "instructions",
        "⬅️ Back": "main"
    },
    "menu_codm": {
        "100082": "get_100082", "AUTHGOP": "get_authgop", "GASLITE": "get_gaslite",
        "GARENA": "get_garena", "SSO": "get_sso", "VIP1": "get_vip1",
        "⬅️ Back": "main"
    },
    "menu_roblox": { "RBLX": "get_rblx", "⬅️ Back": "main" },
    "menu_moontoon": { "MTACC": "get_mtacc", "MIXED MLBB": "get_mixedmlbb", "⬅️ Back": "main" },
    "menu_admin": { "📊 LIST ALL STOCK": "admin_list_stock", "👥 LIST USERS": "admin_list_users", "⬅️ Back": "main" }
}

def is_user_active(user_id):
    info = user_data.get(str(user_id))
    if not info: return False
    if info['duration'] == float('inf'): return True
    return time.time() < (info['redeemed_at'] + info['duration'])

def check_cooldown(user_id):
    if user_id in ADMINS: return 0
    if user_id not in user_cooldowns: return 0
    elapsed = time.time() - user_cooldowns[user_id]
    cooldown_period = 60
    return max(cooldown_period - int(elapsed), 0)

def update_cooldown(user_id):
    user_cooldowns[user_id] = time.time()

# ==================== CORE FUNCTIONS ====================
async def vend_accounts(user_id, keyword, context: ContextTypes.DEFAULT_TYPE):
    file_path = os.path.join(ACCOUNTS_FOLDER, f"{keyword}.txt")
    if not os.path.exists(file_path): return f"❌ Cache '{keyword}' not found."
    if file_path not in file_locks: file_locks[file_path] = asyncio.Lock()
    lock = file_locks[file_path]
    limit = 100
    async with lock:
        try:
            with open(file_path, 'r', encoding='utf-8') as f: lines = [line.strip() for line in f if line.strip()]
            if not lines: return f"Sorry, cache '{keyword}' is empty."
            if len(lines) < limit: return f"Sorry, only {len(lines)} units left in '{keyword}'. At least {limit} are required."
            accounts_to_send = lines[:limit]
            remaining_accounts = lines[limit:]
            with open(file_path, 'w', encoding='utf-8') as f:
                for acc in remaining_accounts: f.write(acc + '\n')
        except Exception as e:
            logger.error(f"Error vending accounts for {keyword}: {e}")
            return f"An internal error occurred while accessing the cache."
    output_filename = f"{keyword}_{user_id}.txt"
    with open(output_filename, 'w', encoding='utf-8') as f: f.write('\n'.join(accounts_to_send))
    try:
        with open(output_filename, 'rb') as f:
            unique_messages = ["Your data has been securely transferred.", "Here are the resources you requested.", "Mission complete! The package is yours.", "Access granted. Handle with care."]
            new_caption = (f"✨ {random.choice(unique_messages)}\n\nLINES: `{len(accounts_to_send)}`\nTYPE: `{keyword.upper()}`\n\n╰┈➤ `Credits: @mcxkiii`")
            await context.bot.send_document(chat_id=user_id, document=f, caption=new_caption, parse_mode="Markdown")
        update_cooldown(user_id)
        return None
    except Exception as e:
        logger.error(f"Failed to send document to {user_id}: {e}")
        async with lock:
            with open(file_path, 'a', encoding='utf-8') as f:
                for acc in accounts_to_send: f.write(acc + '\n')
        return "❌ Failed to send the file. Please try again."
    finally:
        if os.path.exists(output_filename): os.remove(output_filename)

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    welcome_msg = f"""✨ <b>WELCOME TO KIRITO PREMIUM BOT</b> ✨\n\n📜 <u>Available Commands</u>:\n/search - Browse account database\n/redeemkey [key] - Activate access\n/mykey - Check key status\n/credits - View system info\n\n🔑 <b>Key Status</b>: {'✅ Active' if is_user_active(user_id) else '❌ Inactive'}\n\n💎 <b>Credits</b>: @mcxkiii"""
    
    reply_markup = None
    # Show the Free Key button ONLY if the user does NOT have an active key
    if not is_user_active(user_id):
        keyboard = [[InlineKeyboardButton("FREE KEY🔑", callback_data="menu_free_key")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_msg,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔮 <b>System Credits</b>\n\n• Developer: @mcxkiii\n• Special thanks to our users!", parse_mode="HTML")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ADMINS and not is_user_active(user_id):
        await update.message.reply_text("❌ Access Denied. Use `/redeemkey <key>` to authenticate.")
        return
    main_menu = MENUS["main"].copy()
    if user_id not in ADMINS: del main_menu["⚙️ ADMIN TOOLS"]
    
    buttons = [InlineKeyboardButton(text, callback_data=data) for text, data in main_menu.items()]
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('**Data Cache Interface:** Select a primary category.', reply_markup=reply_markup, parse_mode="Markdown")

async def generatekey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS: return
    if len(context.args) < 3:
        await update.message.reply_text("✨ <b>Key Generation System</b> ✨\n\nUsage: <code>/generatekey [count] [duration] [unit]</code>\n\nExamples:\n• <code>/generatekey 5 30 days</code>\n• <code>/generatekey 3 1 lifetime</code>\n\n💎 <b>Credits:</b> @mcxkiii", parse_mode="HTML")
        return
    try:
        count, duration_val, unit = int(context.args[0]), int(context.args[1]), context.args[2].lower()
        duration_map = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
        if unit.rstrip('s') in duration_map: duration_seconds = duration_val * duration_map[unit.rstrip('s')]
        elif unit == "lifetime": duration_seconds = float('inf')
        else: await update.message.reply_text("❌ Invalid unit (seconds/minutes/hours/days/lifetime)"); return
        keys_generated = []
        for _ in range(count):
            key = f"kirito-{''.join(random.choices(string.hexdigits.upper(), k=7))}"
            generated_keys[key] = duration_seconds
            keys_generated.append(key)
        save_data(GENERATED_KEYS_FILE, generated_keys)
        duration_display = f"{duration_val} {unit}" if unit != "lifetime" else "LIFETIME"
        keys_list = "\n".join(f"• <code>{key}</code>" for key in keys_generated)
        reply_message = f"""🔑 <b>BULK KEY GENERATION COMPLETE</b> 🔑\n\n✨ <i>{count} premium access keys created</i> ✨\n\n⏳ <b>Validity Period:</b> {duration_display}\n\n📜 <b>Generated Keys:</b>\n{keys_list}\n\n💎 <b>Credits:</b> @mcxkiii\n\n⚠️ <i>Keys will be invalidated after first use</i>"""
        await update.message.reply_text(reply_message, parse_mode="HTML", disable_web_page_preview=True)
    except (ValueError, IndexError): await update.message.reply_text("❌ Invalid command format. Please check your input.")

async def redeemkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = update.message.from_user
    user_id = str(user_info.id)
    if len(context.args) < 1: await update.message.reply_text("Usage: `/redeemkey <key>`"); return
    if is_user_active(user_id): await update.message.reply_text("✅ Access already authenticated."); return
    key_to_redeem = context.args[0]
    duration = generated_keys.get(key_to_redeem)
    if duration is not None:
        user_data[user_id] = {"key": key_to_redeem, "redeemed_at": time.time(), "duration": duration}
        del generated_keys[key_to_redeem]
        save_data(USER_DATA_FILE, user_data)
        save_data(GENERATED_KEYS_FILE, generated_keys)
        await update.message.reply_text("✅ Access Authenticated.\nYour operational timer has begun.")
        admin_id = ADMINS[0]
        username = f"@{user_info.username}" if user_info.username else "N/A"
        validity_str = "Lifetime" if duration == float('inf') else f"{int(duration / 86400)} Day(s)"
        unique_messages = ["A new key has been activated!", "Key redemption successful.", "Access granted for a new user."]
        notification_text = f"<b>✨ {random.choice(unique_messages)} ✨</b>\n\n👤 <b>UID:</b> <code>{user_id}</code>\n🗣 <b>Username:</b> {username}\n🔑 <b>Redeemed Key:</b> <code>{key_to_redeem}</code>\n⏳ <b>Validity:</b> {validity_str}"
        await context.bot.send_message(chat_id=admin_id, text=notification_text, parse_mode="HTML")
    else: await update.message.reply_text("❌ Authentication Failed: Invalid or already used key.")

async def mykey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    info = user_data.get(str(user_id))
    if info and is_user_active(user_id):
        if info['duration'] == float('inf'): exp_message = "Your access is **Permanent**."
        else:
            expiration_time = info['redeemed_at'] + info['duration']
            remaining_seconds = expiration_time - time.time()
            if remaining_seconds > 0:
                days, hours = int(remaining_seconds / 86400), int((remaining_seconds % 86400) / 3600)
                exp_message = f"Access credentials expire in approx. **{days} days, {hours} hours**."
            else: exp_message = "Your access has expired."
        message = f"**Credential Status: ACTIVE**\n\n*Key:* `{info['key']}`\n*{exp_message}*"
    else: message = "Credential Status: **INACTIVE**"
    await update.message.reply_text(message, parse_mode="Markdown")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS: return
    if not (update.message.reply_to_message and update.message.reply_to_message.document and update.message.reply_to_message.document.file_name.endswith('.txt')):
        await update.message.reply_text("Usage: Send a .txt file, then reply to it with `/add <keyword>`."); return
    if len(context.args) < 1: await update.message.reply_text("Please specify a keyword."); return
    keyword = context.args[0].lower()
    file_path = os.path.join(ACCOUNTS_FOLDER, f"{keyword}.txt")
    try:
        document = update.message.reply_to_message.document
        file = await document.get_file()
        content_bytes = await file.download_as_bytearray()
        accounts = content_bytes.decode('utf-8').strip().splitlines()
        os.makedirs(ACCOUNTS_FOLDER, exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as f:
            for acc in accounts:
                if acc.strip(): f.write(acc.strip() + '\n')
        await update.message.reply_text(f"✅ Added {len(accounts)} data packets to `{keyword}`.")
    except Exception as e: await update.message.reply_text(f"❌ Error: {e}")

async def revokeall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS: return
    generated_keys.clear(); user_data.clear()
    save_data(GENERATED_KEYS_FILE, {}); save_data(USER_DATA_FILE, {})
    await update.message.reply_text("🔥 All keys and user data purged from the system.")

async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS: return
    active_users = [uid for uid, data in user_data.items() if is_user_active(uid)]
    if not active_users: await update.message.reply_text("🤷 No users with active keys found."); return
    message = "╔═══════ ஜ۩👤۩ஜ ═══════╗\n         **ACTIVE USERS**\n╚═══════ ஜ۩👤۩ஜ ═══════╝\n\n"
    user_lines = []
    for uid in active_users:
        info = user_data.get(str(uid), {})
        if info.get('duration') == float('inf'): exp_message = "Permanent"
        else:
            expiration_time = info.get('redeemed_at', 0) + info.get('duration', 0)
            remaining_seconds = expiration_time - time.time()
            if remaining_seconds > 0:
                days, hours = int(remaining_seconds / 86400), int((remaining_seconds % 86400) / 3600)
                exp_message = f"{days}d, {hours}h left"
            else: exp_message = "Expired"
        user_lines.append(f"🔑 User: `{uid}`\n   └── ⏳ Status: *{exp_message}*")
    message += "\n\n".join(user_lines)
    await update.message.reply_text(message, parse_mode="Markdown")

async def deleteuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS: return
    if len(context.args) < 1: await update.message.reply_text("Usage: `/deleteuser <user_id>`"); return
    user_id_to_delete = context.args[0]
    if user_id_to_delete in user_data:
        del user_data[user_id_to_delete]
        save_data(USER_DATA_FILE, user_data)
        await update.message.reply_text(f"🗑️ User `{user_id_to_delete}` has been deleted.")
    else: await update.message.reply_text("❌ User not found.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS: await update.message.reply_text("❌ Admin access required."); return
    if not update.message.reply_to_message: await update.message.reply_text("ℹ️ Reply to a message with /broadcast to send it to all users"); return
    all_user_ids = set(user_data.keys()) | {str(admin) for admin in ADMINS}
    total_users = len(all_user_ids)
    sent_count = 0
    progress_msg = await update.message.reply_text(f"📤 Broadcasting to {total_users} users...")
    for user_id in all_user_ids:
        try:
            await context.bot.copy_message(chat_id=user_id, from_chat_id=update.message.chat_id, message_id=update.message.reply_to_message.message_id)
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e: logger.error(f"Failed to send broadcast to {user_id}: {e}")
    await progress_msg.edit_text(f"✅ Broadcast complete\n• Success: {sent_count}\n• Failed: {total_users - sent_count}\n• Total: {total_users}")

# ==================== CONVERSATION HANDLERS ====================
async def merge_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id not in ADMINS: return ConversationHandler.END
    context.user_data['merged_content'] = []
    await update.message.reply_text("📁 **Merge Session Started** 📁\n\nSend me the `.txt` files you want to combine. When you are finished, use the command `/save <new_filename.txt>` to finalize.", parse_mode="Markdown")
    return RECEIVING_FILES
async def receive_files_to_merge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not (update.message.document and update.message.document.file_name.endswith('.txt')):
        await update.message.reply_text("Please send only `.txt` files."); return RECEIVING_FILES
    try:
        document = update.message.document
        file = await document.get_file()
        content_bytes = await file.download_as_bytearray()
        accounts = content_bytes.decode('utf-8').strip().splitlines()
        context.user_data['merged_content'].extend(accounts)
        await update.message.reply_text(f"✅ Added *{len(accounts)}* lines from `{document.file_name}`. Total lines collected: *{len(context.user_data['merged_content'])}*.", parse_mode="Markdown")
    except Exception as e: await update.message.reply_text(f"❌ Error processing file: {e}")
    return RECEIVING_FILES
async def save_merged_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if len(context.args) < 1: await update.message.reply_text("Usage: `/save <new_filename.txt>`"); return RECEIVING_FILES
    filename = context.args[0]
    if not filename.endswith('.txt'): filename += '.txt'
    merged_content = context.user_data.get('merged_content', [])
    if not merged_content: await update.message.reply_text("No content to save. Send some files first."); return RECEIVING_FILES
    with open(filename, 'w', encoding='utf-8') as f:
        for line in merged_content: f.write(line.strip() + '\n')
    try:
        with open(filename, 'rb') as f:
            await context.bot.send_document(chat_id=update.message.chat_id, document=f, caption=(f"🎉 **Merge Complete!**\n\nHere is your merged file with *{len(merged_content)}* lines."), parse_mode="Markdown")
    except Exception as e: await update.message.reply_text(f"❌ Failed to send file: {e}")
    finally:
        if os.path.exists(filename): os.remove(filename)
    del context.user_data['merged_content']
    return ConversationHandler.END
async def cancel_merge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if 'merged_content' in context.user_data: del context.user_data['merged_content']
    await update.message.reply_text("Merge operation canceled.")
    return ConversationHandler.END

async def recruitment_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = str(query.from_user.id)
    await query.answer()
    
    if user_id in recruitment_data and time.time() - recruitment_data[user_id].get('claimed_at', 0) < 7 * 86400:
        await query.message.reply_text("❌ You have already claimed a free key recently. Please try again later.")
        return ConversationHandler.END
    
    if is_user_active(user_id):
        await query.message.reply_text("❌ You already have an active key.")
        return ConversationHandler.END
        
    role = "recruiter" if query.data == "recruiter_uid" else "invited"
    context.user_data['recruitment_role'] = role
    prompt = "Please enter the User ID of the person you **invited**." if role == "recruiter" else "Please enter the User ID of the person who **recruited** you."
    
    await query.edit_message_text(text=f"🤝 **Recruitment System**\n\n{prompt}\n\nType /cancel to exit.", reply_markup=None)
    
    return AWAITING_RECRUITER_UID if role == "invited" else AWAITING_INVITED_UID

async def process_uid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    partner_uid = update.message.text
    role = context.user_data.get('recruitment_role')

    if not partner_uid.isdigit():
        await update.message.reply_text("❌ Invalid User ID. Please enter a valid number."); return
    if partner_uid == user_id:
        await update.message.reply_text("❌ You cannot recruit yourself."); return

    recruitment_data[user_id] = {"partner_uid": partner_uid, "role": role}
    save_data(RECRUITMENT_DATA_FILE, recruitment_data)

    await update.message.reply_text(f"✅ Your entry has been recorded. We are now waiting for the other person (`{partner_uid}`) to complete their part.")

    partner_info = recruitment_data.get(partner_uid)
    if partner_info and partner_info.get("partner_uid") == user_id:
        recruiter_id = user_id if role == "recruiter" else partner_uid
        invited_id = partner_uid if role == "recruiter" else user_id

        duration_seconds = 86400 
        key = f"recruit-{recruiter_id[:4]}-{invited_id[:4]}-{''.join(random.choices(string.hexdigits.upper(), k=4))}"
        
        user_data[recruiter_id] = {"key": key, "redeemed_at": time.time(), "duration": duration_seconds}
        user_data[invited_id] = {"key": key, "redeemed_at": time.time(), "duration": duration_seconds}
        save_data(USER_DATA_FILE, user_data)
        
        recruitment_data[recruiter_id]['claimed_at'] = time.time()
        recruitment_data[invited_id]['claimed_at'] = time.time()
        save_data(RECRUITMENT_DATA_FILE, recruitment_data)

        success_message = f"🎉 **Success!** You and your partner have both been granted a **1-day key**!\n\nYour key is: <code>{key}</code>\n\nUse /mykey to check its status."
        await context.bot.send_message(chat_id=recruiter_id, text=success_message, parse_mode="HTML")
        await context.bot.send_message(chat_id=invited_id, text=success_message, parse_mode="HTML")
        
        return ConversationHandler.END

    return ConversationHandler.END

async def cancel_recruitment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id in recruitment_data:
        del recruitment_data[user_id]
        save_data(RECRUITMENT_DATA_FILE, recruitment_data)
    await update.message.reply_text("Recruitment process canceled.")
    return ConversationHandler.END

# ==================== UI HANDLER (BUTTONS) ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    callback_data = query.data

    if callback_data == "instructions":
        instructions_text = """
        📜 **Free Key Instructions** 📜

        This system allows you and a friend to get a free 1-day key each by recruiting each other!

        **How it works:**

        1️⃣ **Find a Partner**: One person will be the "Recruiter" and the other will be the "Invited".

        2️⃣ **Get User IDs**: Both of you need your unique Telegram User ID. You can get this by forwarding a message from yourself to a bot like `@userinfobot`.

        3️⃣ **The Recruiter**: Taps the `RECRUITER UID` button and enters the User ID of the person they invited.

        4️⃣ **The Invited Person**: Taps the `INVITED UID` button and enters the User ID of the person who recruited them.

        5️⃣ **Claim Your Prize**: Once both of you have correctly entered each other's IDs, you will *both* instantly receive a 1-day key!

        ⚠️ **Rules:**
        - You cannot recruit yourself.
        - Users with an active key cannot participate.
        - You can only claim a free key this way once every 7 days.
        """
        await query.edit_message_text(text=instructions_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_free_key")]]))
        return
        
    if callback_data == "menu_free_key":
        # This menu is accessible to everyone, so we handle it before the active key check
        menu_items = MENUS[callback_data].copy()
        buttons = [InlineKeyboardButton(text, callback_data=data) for text, data in menu_items.items()]
        keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="**GET A FREE KEY**", reply_markup=reply_markup, parse_mode="Markdown")
        return

    if user_id not in ADMINS and not is_user_active(user_id):
        await query.edit_message_text(text="❌ Access Denied. Use `/redeemkey <key>` to authenticate.", parse_mode="Markdown"); return

    if callback_data == "admin_list_stock":
        if user_id not in ADMINS: return
        if not os.path.exists(ACCOUNTS_FOLDER) or not os.listdir(ACCOUNTS_FOLDER):
            await query.edit_message_text("⚠️ No data caches.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_admin")]])); return
        stock_list = []
        for filename in sorted(os.listdir(ACCOUNTS_FOLDER)):
            if filename.endswith(".txt"):
                keyword = filename.replace(".txt", "")
                try:
                    with open(os.path.join(ACCOUNTS_FOLDER, filename), 'r', encoding='utf-8') as f: lines = len([line for line in f if line.strip()])
                    stock_list.append(f"📁 ` {keyword.upper()} `\n   └── 📦 Stock: *{lines} lines*")
                except Exception as e: stock_list.append(f"📁 ` {keyword.upper()} `\n   └── ⚠️ Error: {e}")
        stock_report = "\n\n".join(stock_list)
        message = f"╔═══════ ஜ۩🔥۩ஜ ═══════╗\n         **SYSTEM INVENTORY**\n╚═══════ ஜ۩🔥۩ஜ ═══════╝\n\n{stock_report}"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="menu_admin")]])
        await query.edit_message_text(text=message, reply_markup=reply_markup, parse_mode="Markdown"); return

    if callback_data == "admin_list_users":
        if user_id not in ADMINS: return
        active_users = [uid for uid in user_data if is_user_active(uid)]
        if not active_users:
            await query.edit_message_text("🤷 No users with active keys found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_admin")]])); return
        message = "╔═══════ ஜ۩👤۩ஜ ═══════╗\n         **ACTIVE USERS**\n╚═══════ ஜ۩👤۩ஜ ═══════╝\n\n"
        user_lines = []
        for uid in active_users:
            info = user_data.get(str(uid), {})
            if info.get('duration') == float('inf'): exp_message = "Permanent"
            else:
                expiration_time = info.get('redeemed_at', 0) + info.get('duration', 0)
                remaining_seconds = expiration_time - time.time()
                if remaining_seconds > 0:
                    days, hours = int(remaining_seconds / 86400), int((remaining_seconds % 86400) / 3600)
                    exp_message = f"{days}d, {hours}h left"
                else: exp_message = "Expired"
            user_lines.append(f"🔑 User: `{uid}`\n   └── ⏳ Status: *{exp_message}*")
        message += "\n\n".join(user_lines)
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="menu_admin")]])
        await query.edit_message_text(text=message, reply_markup=reply_markup, parse_mode="Markdown"); return

    if callback_data in MENUS:
        menu_items = MENUS[callback_data].copy()
        if user_id not in ADMINS and "⚙️ ADMIN TOOLS" in menu_items: del menu_items["⚙️ ADMIN TOOLS"]
        
        buttons = [InlineKeyboardButton(text, callback_data=data) for text, data in menu_items.items()]
        back_button_row = [btn for btn in buttons if "Back" in btn.text]
        non_back_buttons = [btn for btn in buttons if "Back" not in btn.text]
        keyboard = [non_back_buttons[i:i+2] for i in range(0, len(non_back_buttons), 2)]
        if back_button_row: keyboard.append(back_button_row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        title = "Mainframe" if callback_data == "main" else f"Category: {callback_data.replace('menu_', '').upper()}"
        await query.edit_message_text(text=f"**{title}:** Select target.", reply_markup=reply_markup, parse_mode="Markdown")

    elif callback_data.startswith("get_"):
        keyword = callback_data.split("get_")[1]
        if keyword == "vip1":
            info = user_data.get(str(user_id), {})
            if info.get('duration') != float('inf'):
                await context.bot.send_message(chat_id=user_id, text="< BUY A LIFETIME KEY TO UNLOCK THIS >"); return
        remaining = check_cooldown(user_id)
        if remaining > 0:
            await context.bot.send_message(chat_id=user_id, text=f"⏳ Please wait {remaining} seconds before generating another file."); return
        await query.message.edit_text(text=f"Accessing cache for `{keyword}`...", parse_mode="Markdown")
        error_message = await vend_accounts(user_id, keyword, context)
        if error_message: await context.bot.send_message(chat_id=user_id, text=error_message)
        await query.message.delete()

# ==================== MAIN SETUP ====================
async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("search", "Browse accounts"),
        BotCommand("redeemkey", "Redeem access key"),
        BotCommand("mykey", "Check your key status"),
        BotCommand("credits", "View system credits"),
        BotCommand("generatekey", "Admin: Generate multiple keys"),
        BotCommand("broadcast", "Admin: Broadcast to all users"),
        BotCommand("add", "Admin: Add accounts to a cache"),
        BotCommand("listusers", "Admin: List all active users"),
        BotCommand("deleteuser", "Admin: Remove a user's access"),
        BotCommand("revokeall", "Admin: Revoke all keys and users"),
        BotCommand("merge", "Admin: Merge multiple txt files")
    ])

def main():
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    merge_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("merge", merge_start)],
        states={ RECEIVING_FILES: [MessageHandler(filters.Document.TXT, receive_files_to_merge), CommandHandler("save", save_merged_file)], },
        fallbacks=[CommandHandler("cancel", cancel_merge)],
    )

    recruitment_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(recruitment_start, pattern='^recruiter_uid$'),
            CallbackQueryHandler(recruitment_start, pattern='^invited_uid$')
        ],
        states={
            AWAITING_INVITED_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_uid)],
            AWAITING_RECRUITER_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_uid)],
        },
        fallbacks=[CommandHandler("cancel", cancel_recruitment)],
    )

    application.add_handler(merge_conv_handler)
    application.add_handler(recruitment_conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("credits", credits))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("redeemkey", redeemkey))
    application.add_handler(CommandHandler("mykey", mykey))
    application.add_handler(CommandHandler("generatekey", generatekey))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("revokeall", revokeall))
    application.add_handler(CommandHandler("listusers", listusers))
    application.add_handler(CommandHandler("deleteuser", deleteuser))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(button_handler))

    os.makedirs(ACCOUNTS_FOLDER, exist_ok=True)
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()