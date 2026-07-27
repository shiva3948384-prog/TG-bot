18+ MULTI‑PRODUCT BOT – COLOURED START + VIDEO/PHOTO/LINK DEMO
Author: Bread (co‑founder of Sonion)
"""

import os
import re
import asyncio
import sqlite3
import json
import random
import requests
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

# ==================== CONFIG ====================
API_ID = 35458756
API_HASH = 'eac538ffbeb1c5a039a9a9e6ff293149'
BOT_TOKEN = '8907797579:AAE4qAmqxS4BbFWF_DGceZL5UOkkJmQClIE'
ADMIN_ID =  # Direct integer

DB_FILE = '/root/content-bot/content_bot.db'

DEFAULT_PRODUCTS = {
    'indian_rap': {
        'name': 'INDIAN R@P',
        'emoji': '🔞',
        'price': 100,
        'duration': 30,
        'demo': '🔥 Free demo of Indian R@P content...',
        'paid': '🔞 Full Indian R@P premium content unlocked!',
        'vip': 'https://t.me/+indianrapVIP'
    },
    'cp_pom': {
        'name': 'CP POM',
        'emoji': '🔥',
        'price': 150,
        'duration': 30,
        'demo': '🔥 Free demo of CP POM content...',
        'paid': '🔥 Full CP POM premium content unlocked!',
        'vip': 'https://t.me/+cppomVIP'
    },
    'all_in_one': {
        'name': 'ALL IN ONE GROUP',
        'emoji': '🍑',
        'price': 250,
        'duration': 30,
        'demo': '🍑 Free demo of All In One content...',
        'paid': '🍑 Full All In One premium content unlocked!',
        'vip': 'https://t.me/+allinoneVIP'
    }
}

# ==================== DATABASE ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            product_id TEXT,
            expiry TEXT,
            status TEXT DEFAULT 'none',
            txid TEXT,
            joined TEXT
        )
    ''')
    try:
        c.execute('ALTER TABLE users ADD COLUMN product_id TEXT')
    except sqlite3.OperationalError:
        pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT,
            emoji TEXT,
            price INTEGER,
            duration INTEGER,
            demo TEXT,
            paid TEXT,
            vip TEXT
        )
    ''')
    for pid, p in DEFAULT_PRODUCTS.items():
        c.execute('INSERT OR IGNORE INTO products (id, name, emoji, price, duration, demo, paid, vip) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                  (pid, p['name'], p['emoji'], p['price'], p['duration'], p['demo'], p['paid'], p['vip']))
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("upi_id", "yourupi@upi")')
    c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("qr_photo", NULL)')
    c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("admin_username", "@SANDYxBIHARI")')
    c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("welcome_photo", NULL)')
    conn.commit()
    conn.close()

init_db()

# ==================== HELPERS ====================
def get_setting(key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def get_product(pid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, name, emoji, price, duration, demo, paid, vip FROM products WHERE id = ?', (pid,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'name': row[1] or 'Unknown', 'emoji': row[2] or '❓', 'price': row[3], 'duration': row[4], 'demo': row[5] or 'No demo available.', 'paid': row[6] or 'No content available.', 'vip': row[7] or 'https://t.me/+defaultVIP'}
    return None

def get_all_products():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, name, emoji, price, duration FROM products')
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'name': r[1] or 'Unknown', 'emoji': r[2] or '❓', 'price': r[3], 'duration': r[4]} for r in rows]

def update_product(pid, name, emoji, price, duration, demo, paid, vip):
    name = name.strip() or 'Unknown'
    emoji = emoji.strip() or '❓'
    demo = demo or 'No demo available.'
    paid = paid or 'No content available.'
    vip = vip or 'https://t.me/+defaultVIP'
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE products SET name = ?, emoji = ?, price = ?, duration = ?, demo = ?, paid = ?, vip = ? WHERE id = ?',
              (name, emoji, price, duration, demo, paid, vip, pid))
    conn.commit()
    conn.close()

def reset_product(pid):
    if pid in DEFAULT_PRODUCTS:
        p = DEFAULT_PRODUCTS[pid]
        update_product(pid, p['name'], p['emoji'], p['price'], p['duration'], p['demo'], p['paid'], p['vip'])
        return True
    return False

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'user_id': row[0], 'username': row[1], 'first_name': row[2], 'product_id': row[3], 'expiry': row[4], 'status': row[5], 'txid': row[6], 'joined': row[7]}
    return None

def add_user(user_id, username, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, joined) VALUES (?, ?, ?, ?)',
              (user_id, username, name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def update_subscription(user_id, product_id, expiry):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE users SET product_id = ?, expiry = ?, status = "verified" WHERE user_id = ?',
              (product_id, expiry.isoformat(), user_id))
    conn.commit()
    conn.close()

def set_payment(user_id, txid, product_id, status='pending'):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE users SET txid = ?, status = ?, product_id = ? WHERE user_id = ?',
              (txid, status, product_id, user_id))
    conn.commit()
    conn.close()

def get_pending_by_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT txid, product_id FROM users WHERE user_id = ? AND status = "pending"', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'txid': row[0], 'product_id': row[1]}
    return None

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def is_active(user_id):
    u = get_user(user_id)
    if not u or not u['expiry']:
        return False
    return datetime.now() < datetime.fromisoformat(u['expiry'])

def get_user_product(user_id):
    u = get_user(user_id)
    if not u:
        return None
    return u['product_id']

# ==================== BOT CLIENT ====================
bot = TelegramClient('content_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

admin_states = {}
user_payment_states = {}

# ==================== BOT API HELPERS ====================
def send_bot_api_message(chat_id, text, keyboard, parse_mode='HTML'):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'reply_markup': json.dumps(keyboard)
    }
    try:
        resp = requests.post(url, data=payload, timeout=10)
        return resp.json()
    except Exception as e:
        print(f"Bot API error: {e}")
        return None

def send_bot_api_photo(chat_id, photo_path, caption, keyboard, parse_mode='HTML'):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as f:
            files = {'photo': f}
            payload = {
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': parse_mode,
                'reply_markup': json.dumps(keyboard)
            }
            resp = requests.post(url, data=payload, files=files, timeout=15)
            return resp.json()
    except Exception as e:
        print(f"sendPhoto error: {e}")
        return None

def edit_bot_api_message(chat_id, message_id, text, keyboard=None, parse_mode='HTML'):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if keyboard:
        payload['reply_markup'] = json.dumps(keyboard)
    try:
        resp = requests.post(url, data=payload, timeout=5)
        return resp.json()
    except Exception as e:
        print(f"Edit error: {e}")
        return None

# ==================== MAIN MENU (with coloured buttons via Bot API) ====================
async def send_main_menu(chat_id, user_id):
    try:
        active = is_active(user_id)
        product = get_user_product(user_id)
        status = "✅ <b>Active</b>" if active else "❌ <b>Inactive</b>"
        if active:
            u = get_user(user_id)
            status += f" <i>({u['product_id']} until {u['expiry'][:10]})</i>"
        
        admin_user = get_setting('admin_username') or '@SANDYxBIHARI'
        
        text = f"""🔞 <b>Welcome to the 18+ Premium Zone!</b> 🔞

👤 <b>User ID:</b> <code>{user_id}</code>
📊 <b>Status:</b> {status}

💋 <b>Choose your product below:</b>
🔥 <b>Click to explore & unlock.</b>

📞 <b>Admin:</b> {admin_user}
        """
        
        products = get_all_products()
        keyboard = {
            "inline_keyboard": [
                [{"text": f"{p['emoji']} {p['name']}", "callback_data": f"product:{p['id']}", "style": "primary"}] for p in products
            ] + [
                [{"text": "❓ Payment Help", "callback_data": "payment_help", "style": "primary"}]
            ]
        }
        welcome_photo = get_setting('welcome_photo')
        if welcome_photo and os.path.exists(welcome_photo):
            await asyncio.to_thread(send_bot_api_photo, chat_id, welcome_photo, text, keyboard)
        else:
            await asyncio.to_thread(send_bot_api_message, chat_id, text, keyboard)
    except Exception as e:
        print(f"Error in send_main_menu: {e}")
        # Fallback to Telethon buttons (no colours)
        try:
            text = "🔞 <b>Welcome!</b>\nUse the buttons below."
            buttons = []
            products = get_all_products()
            for p in products:
                buttons.append([Button.inline(f"{p['emoji']} {p['name']}", data=f"product:{p['id']}")])
            buttons.append([Button.inline("❓ Payment Help", data="payment_help")])
            await bot.send_message(chat_id, text, buttons=buttons, parse_mode='html')
        except:
            await bot.send_message(chat_id, "🔞 Welcome! Please use /admin if you are admin.", parse_mode='html')

# ==================== /start ====================
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    try:
        user_id = event.sender_id
        sender = await event.get_sender()
        add_user(user_id, sender.username or "None", sender.first_name or "User")
        await send_main_menu(event.chat_id, user_id)
    except Exception as e:
        print(f"Exception in /start: {e}")
        await event.reply("🔞 <b>Welcome!</b>\nUse /admin if you are admin.", parse_mode='html')

# ==================== ADMIN COMMANDS ====================
@bot.on(events.NewMessage(pattern='/pending'))
async def pending_payments(event):
    if event.sender_id != ADMIN_ID:
        await event.reply("❌ Unauthorized.", parse_mode='html')
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT user_id, txid, product_id FROM users WHERE status = "pending"')
    rows = c.fetchall()
    conn.close()
    if not rows:
        await event.reply("📭 No pending payments.", parse_mode='html')
        return
    text = "📋 <b>Pending Payments:</b>\n\n"
    for uid, txid, pid in rows:
        product = get_product(pid) if pid else {'name': 'Unknown'}
        u = get_user(uid)
        name = u['first_name'] if u else 'Unknown'
        text += f"• User: <code>{uid}</code> ({name}) | TxID: <code>{txid}</code> | Product: {product['name']}\n"
    await event.reply(text, parse_mode='html')

# ==================== CALLBACK HANDLER ====================
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8') if event.data else ''
    user_id = event.sender_id
    chat_id = event.chat_id
    
    # ----------------- USER FLOW -----------------
    if data.startswith('product:'):
        pid = data.split(':')[1]
        product = get_product(pid)
        if not product:
            await event.answer("❌ Product not found!", alert=True)
            return
        
        text = f"""{product['emoji']} <b>{product['name']}</b>

💰 <b>Price:</b> ₹{product['price']}
📅 <b>Duration:</b> {product['duration']} days

👇 <b>What you get:</b>
• Full access to {product['name']}
• VIP channel invite
• Regular updates

<b>Choose action:</b>
        """
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎬 DEMO", "callback_data": f"demo:{pid}", "style": "primary"},
                 {"text": "💎 BUY NOW", "callback_data": f"buy:{pid}", "style": "success"}],
                [{"text": "🔙 Back", "callback_data": "back", "style": "danger"}]
            ]
        }
        await asyncio.to_thread(send_bot_api_message, chat_id, text, keyboard)
        await event.answer(f"📌 {product['name']} selected")
        return
    
    # ---------- DEMO (supports photo, video, link, text) ----------
    if data.startswith('demo:'):
        pid = data.split(':')[1]
        product = get_product(pid)
        if not product:
            await event.answer("❌ Product not found!", alert=True)
            return
        
        demo_val = product['demo']
        if not demo_val or demo_val == 'No demo available.':
            await event.reply("❌ No demo available for this product.", parse_mode='html')
            await event.answer("No demo content.")
            return
        
        # Check if demo is a file path
        if os.path.exists(demo_val):
            # Determine file type by extension
            ext = demo_val.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                # Send as photo
                await bot.send_file(chat_id, demo_val, caption=f"{product['emoji']} <b>DEMO</b>\n\n🔥 Subscribe to unlock full {product['name']} content.", parse_mode='html')
            elif ext in ['mp4', 'mov', 'avi', 'mkv', 'webm']:
                # Send as video
                await bot.send_file(chat_id, demo_val, caption=f"{product['emoji']} <b>DEMO VIDEO</b>\n\n🔥 Subscribe to unlock full {product['name']} content.", parse_mode='html')
            else:
                # Send as document (any other file)
                await bot.send_file(chat_id, demo_val, caption=f"{product['emoji']} <b>DEMO FILE</b>\n\n🔥 Subscribe to unlock full {product['name']} content.", parse_mode='html')
        elif demo_val.startswith('http://') or demo_val.startswith('https://'):
            # It's a link
            await event.reply(f"{product['emoji']} <b>DEMO LINK</b>\n\n🔗 <a href='{demo_val}'>Click here to view demo</a>\n\n🔥 Subscribe to unlock full {product['name']} content.", parse_mode='html')
        else:
            # Treat as text
            await event.reply(f"{product['emoji']} <b>DEMO</b>\n\n{demo_val}\n\n👇 Buy now to unlock full content.", parse_mode='html')
        await event.answer("🔥 Demo sent!")
        return
    
    if data.startswith('buy:'):
        pid = data.split(':')[1]
        product = get_product(pid)
        if not product:
            await event.answer("❌ Product not found!", alert=True)
            return
        
        txid = f"TX{random.randint(10000,99999)}{user_id}"
        set_payment(user_id, txid, pid, 'pending')
        user_payment_states[user_id] = {'product': pid, 'txid': txid}
        
        upi = get_setting('upi_id') or 'yourupi@upi'
        qr_path = get_setting('qr_photo')
        
        text = f"""💳 <b>Purchase Order</b> 🛒

📌 <b>Product:</b> {product['emoji']} {product['name']}
💰 <b>Price:</b> ₹{product['price']}
🆔 <b>TxID:</b> <code>{txid}</code>

💵 <b>Pay to UPI:</b> <code>{upi}</code>
📸 <b>After payment, click the button below to submit your UTR + screenshot.</b>
        """
        keyboard = {
            "inline_keyboard": [
                [{"text": "📤 Submit Payment (UTR + Screenshot)", "callback_data": f"submit_payment:{pid}"}],
                [{"text": "🔙 Back", "callback_data": "back", "style": "danger"}]
            ]
        }
        
        if qr_path and os.path.exists(qr_path):
            await asyncio.to_thread(send_bot_api_photo, chat_id, qr_path, text, keyboard)
        else:
            await asyncio.to_thread(send_bot_api_message, chat_id, text, keyboard)
        await event.answer("💋 Order initiated!")
        return
    
    if data.startswith('submit_payment:'):
        pid = data.split(':')[1]
        product = get_product(pid)
        if not product:
            await event.answer("❌ Product not found!", alert=True)
            return
        pending = get_pending_by_user(user_id)
        if pending:
            user_payment_states[user_id] = {'product': pending['product_id'], 'txid': pending['txid'], 'step': 'waiting_utr'}
        else:
            await event.answer("❌ No pending order. Please use BUY NOW first!", alert=True)
            return
        await event.answer("📤 Please send your UTR number (text) and then the payment screenshot (photo).")
        await event.reply("📤 <b>Send your UTR number as a text message.</b>\n\nAfter that, send the payment screenshot as a photo.", parse_mode='html')
        return
    
    if data == 'payment_help':
        upi = get_setting('upi_id') or 'yourupi@upi'
        admin_user = get_setting('admin_username') or '@SANDYxBIHARI'
        text = f"""❓ <b>How to Pay?</b> 💰

1️⃣ Select a product from the main menu.
2️⃣ Click <b>BUY NOW</b> – you'll get a <b>TxID</b> and <b>UPI ID</b>.
3️⃣ Send the exact amount to:
   <code>{upi}</code>
4️⃣ After payment, click <b>"Submit Payment"</b> and send your UTR and screenshot.
5️⃣ Admin will verify and activate your subscription.

⏱️ <b>Usually 1-5 minutes.</b>
📞 <b>Contact:</b> {admin_user}

🍑 <b>Enjoy exclusive adult content!</b>
"""
        keyboard = {
            "inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back", "style": "danger"}]]
        }
        await asyncio.to_thread(send_bot_api_message, chat_id, text, keyboard)
        await event.answer("")
        return
    
    if data == 'back':
        await send_main_menu(chat_id, user_id)
        await event.answer("")
        return

    # ----------------- ADMIN FLOW -----------------
    if user_id != ADMIN_ID:
        await event.answer("⛔ Unauthorized.", alert=True)
        return

    # Manual TxID verification
    if data == 'admin_verify':
        await event.answer("Send TxID to verify (use /pending to see all)", alert=True)
        admin_states[user_id] = {'action': 'awaiting_verify_txid'}
        await event.reply("📤 Send the <b>TxID</b> to verify the payment.\n\nUse /pending to see all pending payments.", parse_mode='html')
        return

    # Admin approve/reject
    if data.startswith('admin_approve:'):
        parts = data.split(':')
        txid = parts[1]
        uid = int(parts[2])
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT user_id, product_id FROM users WHERE txid = ? AND status = "pending"', (txid,))
        row = c.fetchone()
        conn.close()
        if not row:
            await event.answer("❌ No pending payment found!", alert=True)
            return
        uid_db, pid = row
        product = get_product(pid)
        if not product:
            await event.answer("❌ Product not found!", alert=True)
            return
        expiry = datetime.now() + timedelta(days=product['duration'])
        update_subscription(uid_db, pid, expiry)
        vip_link = product['vip']
        u = get_user(uid_db)
        name = u['first_name'] if u else 'Unknown'
        await bot.send_message(uid_db, f"""✅ <b>Subscription Activated!</b>

📌 <b>Product:</b> {product['emoji']} {product['name']}
📅 <b>Expires:</b> {expiry.strftime('%Y-%m-%d')}

🔞 <b>VIP Access Channel:</b>
<a href='{vip_link}'>🔥 Click Here to Join VIP</a>

<b>Enjoy premium 18+ content!</b>""", parse_mode='html')
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('UPDATE users SET status = "verified" WHERE user_id = ?', (uid_db,))
        conn.commit()
        conn.close()
        await event.edit(f"✅ <b>Approved and activated!</b>\nUser: {name}")
        await event.answer("✅ Payment approved and user activated!", alert=True)
        return

    if data.startswith('admin_reject:'):
        parts = data.split(':')
        txid = parts[1]
        uid = int(parts[2])
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('UPDATE users SET status = "rejected" WHERE txid = ?', (txid,))
        conn.commit()
        conn.close()
        u = get_user(uid)
        name = u['first_name'] if u else 'Unknown'
        await event.edit(f"❌ <b>Payment rejected.</b>\nUser: {name}")
        await event.answer("❌ Payment rejected.", alert=True)
        return

    # Admin edit product (unchanged)
    if data.startswith('admin_set_product:'):
        pid = data.split(':')[1]
        product = get_product(pid)
        if not product:
            await event.answer("Product not found", alert=True)
            return
        text = f"""🔧 <b>Editing Product:</b> {product['emoji']} {product['name']}

Current values:
💰 Price: ₹{product['price']}
📅 Duration: {product['duration']} days
🎬 Demo: {product['demo'][:50]}...
📂 Paid: {product['paid'][:50]}...
🔗 VIP: {product['vip']}

<b>What do you want to change?</b>
        """
        keyboard = {
            "inline_keyboard": [
                [{"text": "💰 Price", "callback_data": f"admin_set_price:{pid}"},
                 {"text": "📅 Duration", "callback_data": f"admin_set_duration:{pid}"}],
                [{"text": "🎬 Demo", "callback_data": f"admin_set_demo:{pid}"},
                 {"text": "📂 Paid Content", "callback_data": f"admin_set_paid:{pid}"}],
                [{"text": "🔗 VIP Link", "callback_data": f"admin_set_vip:{pid}"},
                 {"text": "📛 Name/Emoji", "callback_data": f"admin_set_name:{pid}"}],
                [{"text": "🔄 Reset to Default", "callback_data": f"admin_reset_product:{pid}"}],
                [{"text": "🔙 Back to Admin", "callback_data": "back_admin"}]
            ]
        }
        await asyncio.to_thread(edit_bot_api_message, chat_id, event.message_id, text, keyboard)
        await event.answer("")
        return

    if data.startswith('admin_reset_product:'):
        pid = data.split(':')[1]
        if reset_product(pid):
            await event.answer("✅ Product reset to default!")
        else:
            await event.answer("❌ Product ID not found!", alert=True)
        return

    if data == 'admin_panel':
        text = """👑 <b>Admin Panel</b> 🔞

🔹 <b>Verify payments</b> (manual)
🔹 <b>Edit Product</b> – change price, duration, demo, paid, VIP
🔹 <b>Broadcast</b> messages
🔹 <b>Set UPI / QR</b>
🔹 <b>Set Welcome Photo</b>
🔹 <b>View users & stats</b>
        """
        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ Verify Payment", "callback_data": "admin_verify", "style": "success"}],
                [{"text": "📦 Edit Product", "callback_data": "admin_edit_product_choose", "style": "primary"}],
                [{"text": "📢 Broadcast", "callback_data": "admin_broadcast", "style": "primary"}],
                [{"text": "💳 Set UPI", "callback_data": "admin_set_upi", "style": "primary"}],
                [{"text": "🖼️ Set QR Code", "callback_data": "admin_set_qr", "style": "primary"}],
                [{"text": "📸 Set Welcome Photo", "callback_data": "admin_set_welcome", "style": "success"}],
                [{"text": "👥 View Users", "callback_data": "admin_users", "style": "primary"}],
                [{"text": "📊 Stats", "callback_data": "admin_stats", "style": "primary"}]
            ]
        }
        await asyncio.to_thread(edit_bot_api_message, chat_id, event.message_id, text, keyboard)
        await event.answer("")
        return

    if data == 'admin_edit_product_choose':
        products = get_all_products()
        text = "📦 <b>Select product to edit:</b>"
        keyboard = {
            "inline_keyboard": [
                [{"text": f"{p['emoji']} {p['name']}", "callback_data": f"admin_set_product:{p['id']}", "style": "primary"}] for p in products
            ] + [[{"text": "🔙 Back", "callback_data": "back_admin"}]]
        }
        await asyncio.to_thread(edit_bot_api_message, chat_id, event.message_id, text, keyboard)
        await event.answer("")
        return

    if data.startswith('admin_set_price:'):
        pid = data.split(':')[1]
        await event.answer("Send new price (number only)", alert=True)
        admin_states[user_id] = {'action': 'awaiting_price', 'pid': pid}
        await event.reply("📤 Send the new price (just the number).", parse_mode='html')
        return

    if data.startswith('admin_set_duration:'):
        pid = data.split(':')[1]
        await event.answer("Send new duration in days (number only)", alert=True)
        admin_states[user_id] = {'action': 'awaiting_duration', 'pid': pid}
        await event.reply("📤 Send the new duration in days (just the number).", parse_mode='html')
        return

    if data.startswith('admin_set_demo:'):
        pid = data.split(':')[1]
        await event.answer("Send new demo (text, photo, video, or file)", alert=True)
        admin_states[user_id] = {'action': 'awaiting_demo', 'pid': pid}
        await event.reply("📤 Send the new demo (text, photo, video, or file).", parse_mode='html')
        return

    if data.startswith('admin_set_paid:'):
        pid = data.split(':')[1]
        await event.answer("Send new paid content (text, photo, video, or file)", alert=True)
        admin_states[user_id] = {'action': 'awaiting_paid', 'pid': pid}
        await event.reply("📤 Send the new paid content (text, photo, video, or file).", parse_mode='html')
        return

    if data.startswith('admin_set_vip:'):
        pid = data.split(':')[1]
        await event.answer("Send new VIP link", alert=True)
        admin_states[user_id] = {'action': 'awaiting_vip', 'pid': pid}
        await event.reply("📤 Send the new VIP channel link.", parse_mode='html')
        return

    if data.startswith('admin_set_name:'):
        pid = data.split(':')[1]
        await event.answer("Send new name and emoji in format: Name | Emoji", alert=True)
        admin_states[user_id] = {'action': 'awaiting_name_emoji', 'pid': pid}
        await event.reply("📤 Send in format: <code>Name | Emoji</code>", parse_mode='html')
        return

    if data == 'admin_broadcast':
        await event.answer("Send broadcast message", alert=True)
        admin_states[user_id] = {'action': 'awaiting_broadcast'}
        await event.reply("📤 Send the message to broadcast to all users.", parse_mode='html')
        return

    if data == 'admin_set_upi':
        await event.answer("Send UPI ID", alert=True)
        admin_states[user_id] = {'action': 'awaiting_upi'}
        await event.reply("📤 Send the new <b>UPI ID</b>.", parse_mode='html')
        return

    if data == 'admin_set_qr':
        await event.answer("Send QR photo", alert=True)
        admin_states[user_id] = {'action': 'awaiting_qr'}
        await event.reply("📤 Send a <b>photo</b> to set as QR code.", parse_mode='html')
        return

    if data == 'admin_set_welcome':
        await event.answer("Send welcome photo", alert=True)
        admin_states[user_id] = {'action': 'awaiting_welcome_photo'}
        await event.reply("📸 Send a <b>photo</b> to set as welcome image.", parse_mode='html')
        return

    if data == 'admin_users':
        users = get_all_users()
        text = f"👥 <b>Total Users:</b> {len(users)}\n\n"
        for uid in users[:10]:
            u = get_user(uid)
            prod = u['product_id'] if u['product_id'] else 'None'
            expiry = u['expiry'][:10] if u['expiry'] else 'None'
            text += f"• {uid} | {u['first_name']} | Prod: {prod} | Exp: {expiry}\n"
        if len(users) > 10:
            text += "\n... (only first 10 shown)"
        keyboard = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back_admin", "style": "danger"}]]}
        await asyncio.to_thread(edit_bot_api_message, chat_id, event.message_id, text, keyboard)
        await event.answer("")
        return

    if data == 'admin_stats':
        users = get_all_users()
        active = sum(1 for uid in users if is_active(uid))
        text = f"📊 <b>Bot Stats</b>\n\n👥 <b>Total Users:</b> {len(users)}\n✅ <b>Active:</b> {active}\n❌ <b>Inactive:</b> {len(users) - active}"
        keyboard = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back_admin", "style": "danger"}]]}
        await asyncio.to_thread(edit_bot_api_message, chat_id, event.message_id, text, keyboard)
        await event.answer("")
        return

    if data == 'back_admin':
        await admin_panel_edit(chat_id, event.message_id)
        return

# ==================== ADMIN PANEL COMMAND ====================
@bot.on(events.NewMessage(pattern='/admin'))
async def admin_panel_cmd(event):
    if event.sender_id != ADMIN_ID:
        await event.reply("❌ <b>Unauthorized.</b>", parse_mode='html')
        return
    text = """👑 <b>Admin Panel</b> 🔞

🔹 <b>Verify payments</b> (manual)
🔹 <b>Edit Product</b> – change price, duration, demo, paid, VIP
🔹 <b>Broadcast</b> messages
🔹 <b>Set UPI / QR</b>
🔹 <b>Set Welcome Photo</b>
🔹 <b>View users & stats</b>

📌 <b>Tip:</b> Use /pending to see all pending payments.
    """
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Verify Payment", "callback_data": "admin_verify", "style": "success"}],
            [{"text": "📦 Edit Product", "callback_data": "admin_edit_product_choose", "style": "primary"}],
            [{"text": "📢 Broadcast", "callback_data": "admin_broadcast", "style": "primary"}],
            [{"text": "💳 Set UPI", "callback_data": "admin_set_upi", "style": "primary"}],
            [{"text": "🖼️ Set QR Code", "callback_data": "admin_set_qr", "style": "primary"}],
            [{"text": "📸 Set Welcome Photo", "callback_data": "admin_set_welcome", "style": "success"}],
            [{"text": "👥 View Users", "callback_data": "admin_users", "style": "primary"}],
            [{"text": "📊 Stats", "callback_data": "admin_stats", "style": "primary"}]
        ]
    }
    await asyncio.to_thread(send_bot_api_message, event.chat_id, text, keyboard)

async def admin_panel_edit(chat_id, msg_id):
    text = """👑 <b>Admin Panel</b> 🔞

🔹 <b>Verify payments</b> (manual)
🔹 <b>Edit Product</b> – change price, duration, demo, paid, VIP
🔹 <b>Broadcast</b> messages
🔹 <b>Set UPI / QR</b>
🔹 <b>Set Welcome Photo</b>
🔹 <b>View users & stats</b>
    """
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Verify Payment", "callback_data": "admin_verify", "style": "success"}],
            [{"text": "📦 Edit Product", "callback_data": "admin_edit_product_choose", "style": "primary"}],
            [{"text": "📢 Broadcast", "callback_data": "admin_broadcast", "style": "primary"}],
            [{"text": "💳 Set UPI", "callback_data": "admin_set_upi", "style": "primary"}],
            [{"text": "🖼️ Set QR Code", "callback_data": "admin_set_qr", "style": "primary"}],
            [{"text": "📸 Set Welcome Photo", "callback_data": "admin_set_welcome", "style": "success"}],
            [{"text": "👥 View Users", "callback_data": "admin_users", "style": "primary"}],
            [{"text": "📊 Stats", "callback_data": "admin_stats", "style": "primary"}]
        ]
    }
    await asyncio.to_thread(edit_bot_api_message, chat_id, msg_id, text, keyboard)

# ==================== ADMIN INPUT HANDLER ====================
@bot.on(events.NewMessage)
async def admin_input_handler(event):
    user_id = event.sender_id
    if user_id != ADMIN_ID:
        return
    if user_id not in admin_states:
        return
    state = admin_states[user_id]
    action = state['action']
    del admin_states[user_id]

    if action == 'awaiting_verify_txid':
        txid_input = event.text.strip()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT user_id, product_id FROM users WHERE txid = ? AND status = "pending"', (txid_input,))
        row = c.fetchone()
        if not row:
            c.execute('SELECT user_id, product_id, txid FROM users WHERE txid LIKE ? AND status = "pending"', (f'%{txid_input}%',))
            rows = c.fetchall()
            if len(rows) == 1:
                row = (rows[0][0], rows[0][1])
            elif len(rows) > 1:
                conn.close()
                await event.reply(f"❌ Multiple pending payments with that pattern. Use /pending to see all.", parse_mode='html')
                return
        conn.close()
        if not row:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT txid FROM users WHERE status = "pending"')
            pending_txids = [r[0] for r in c.fetchall()]
            conn.close()
            pending_msg = "No pending payments." if not pending_txids else f"Pending TxIDs: {', '.join(pending_txids)}"
            await event.reply(f"❌ <b>No pending payment with that TxID.</b>\n\n{pending_msg}", parse_mode='html')
            return
        uid, pid = row
        product = get_product(pid)
        if not product:
            await event.reply("❌ Product not found!", parse_mode='html')
            return
        expiry = datetime.now() + timedelta(days=product['duration'])
        update_subscription(uid, pid, expiry)
        vip_link = product['vip']
        u = get_user(uid)
        name = u['first_name'] if u else 'Unknown'
        await bot.send_message(uid, f"""✅ <b>Subscription Activated!</b>

📌 <b>Product:</b> {product['emoji']} {product['name']}
📅 <b>Expires:</b> {expiry.strftime('%Y-%m-%d')}

🔞 <b>VIP Access Channel:</b>
<a href='{vip_link}'>🔥 Click Here to Join VIP</a>

<b>Enjoy premium 18+ content!</b>""", parse_mode='html')
        await event.reply(f"✅ <b>Verified TxID</b> <code>{txid_input}</code> for user {uid} ({name}). Activated {product['name']}. VIP link sent.", parse_mode='html')
        return

    # Other admin actions (price, duration, demo, etc.)
    if action == 'awaiting_price':
        pid = state.get('pid')
        try:
            price = int(event.text.strip())
            product = get_product(pid)
            if not product:
                await event.reply("❌ Product not found", parse_mode='html')
                return
            update_product(pid, product['name'], product['emoji'], price, product['duration'], product['demo'], product['paid'], product['vip'])
            await event.reply(f"✅ <b>Price updated to ₹{price}</b>", parse_mode='html')
        except ValueError:
            await event.reply("❌ Invalid number. Send a valid integer.", parse_mode='html')
        return

    if action == 'awaiting_duration':
        pid = state.get('pid')
        try:
            duration = int(event.text.strip())
            product = get_product(pid)
            if not product:
                await event.reply("❌ Product not found", parse_mode='html')
                return
            update_product(pid, product['name'], product['emoji'], product['price'], duration, product['demo'], product['paid'], product['vip'])
            await event.reply(f"✅ <b>Duration updated to {duration} days</b>", parse_mode='html')
        except ValueError:
            await event.reply("❌ Invalid number. Send a valid integer.", parse_mode='html')
        return

    if action == 'awaiting_demo':
        pid = state.get('pid')
        product = get_product(pid)
        if not product:
            await event.reply("❌ Product not found", parse_mode='html')
            return
        if event.message.media:
            ext = 'file'
            if event.photo:
                ext = 'jpg'
            elif event.video:
                ext = 'mp4'
            elif event.document and hasattr(event.document, 'attributes'):
                for attr in event.document.attributes:
                    if hasattr(attr, 'file_name') and attr.file_name:
                        ext = attr.file_name.split('.')[-1] if '.' in attr.file_name else 'file'
                        break
            file_path = f"/root/content-bot/demo_{pid}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
            try:
                await event.download_media(file=file_path)
                if os.path.exists(file_path):
                    demo_val = file_path
                    await event.reply(f"✅ Demo file uploaded: {os.path.basename(file_path)}")
                else:
                    await event.reply("❌ Failed to download file.", parse_mode='html')
                    return
            except Exception as e:
                await event.reply(f"❌ Download error: {str(e)}", parse_mode='html')
                return
        else:
            demo_val = event.text.strip()
        update_product(pid, product['name'], product['emoji'], product['price'], product['duration'], demo_val, product['paid'], product['vip'])
        await event.reply(f"✅ <b>Demo updated</b>", parse_mode='html')
        return

    if action == 'awaiting_paid':
        pid = state.get('pid')
        product = get_product(pid)
        if not product:
            await event.reply("❌ Product not found", parse_mode='html')
            return
        if event.message.media:
            ext = 'file'
            if event.photo:
                ext = 'jpg'
            elif event.video:
                ext = 'mp4'
            elif event.document and hasattr(event.document, 'attributes'):
                for attr in event.document.attributes:
                    if hasattr(attr, 'file_name') and attr.file_name:
                        ext = attr.file_name.split('.')[-1] if '.' in attr.file_name else 'file'
                        break
            file_path = f"/root/content-bot/paid_{pid}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
            try:
                await event.download_media(file=file_path)
                if os.path.exists(file_path):
                    paid_val = file_path
                    await event.reply(f"✅ Paid content file uploaded: {os.path.basename(file_path)}")
                else:
                    await event.reply("❌ Failed to download file.", parse_mode='html')
                    return
            except Exception as e:
                await event.reply(f"❌ Download error: {str(e)}", parse_mode='html')
                return
        else:
            paid_val = event.text.strip()
        update_product(pid, product['name'], product['emoji'], product['price'], product['duration'], product['demo'], paid_val, product['vip'])
        await event.reply(f"✅ <b>Paid content updated</b>", parse_mode='html')
        return

    if action == 'awaiting_vip':
        pid = state.get('pid')
        product = get_product(pid)
        if not product:
            await event.reply("❌ Product not found", parse_mode='html')
            return
        vip = event.text.strip()
        update_product(pid, product['name'], product['emoji'], product['price'], product['duration'], product['demo'], product['paid'], vip)
        await event.reply(f"✅ <b>VIP link updated to:</b> <a href='{vip}'>{vip}</a>", parse_mode='html')
        return

    if action == 'awaiting_name_emoji':
        pid = state.get('pid')
        product = get_product(pid)
        if not product:
            await event.reply("❌ Product not found", parse_mode='html')
            return
        try:
            name, emoji = event.text.split('|', 1)
            name = name.strip()
            emoji = emoji.strip()
            if not name or not emoji:
                await event.reply("❌ Name and emoji cannot be empty.", parse_mode='html')
                return
            update_product(pid, name, emoji, product['price'], product['duration'], product['demo'], product['paid'], product['vip'])
            await event.reply(f"✅ <b>Name/Emoji updated:</b> {emoji} {name}", parse_mode='html')
        except:
            await event.reply("❌ Invalid format. Use: <code>Name | Emoji</code>", parse_mode='html')
        return

    if action == 'awaiting_broadcast':
        msg = event.text
        users = get_all_users()
        sent = 0
        for uid in users:
            try:
                await bot.send_message(uid, f"📢 <b>Broadcast</b>\n\n{msg}", parse_mode='html')
                sent += 1
                await asyncio.sleep(0.1)
            except:
                pass
        await event.reply(f"✅ <b>Broadcast sent to {sent} users.</b>", parse_mode='html')
        return

    if action == 'awaiting_upi':
        upi = event.text.strip()
        set_setting('upi_id', upi)
        await event.reply(f"✅ <b>UPI ID set to:</b> <code>{upi}</code>", parse_mode='html')
        return

    if action == 'awaiting_qr':
        if event.message.media:
            file_path = f"/root/content-bot/qr_{user_id}.jpg"
            try:
                await event.download_media(file=file_path)
                if os.path.exists(file_path):
                    set_setting('qr_photo', file_path)
                    await event.reply("✅ <b>QR Code updated!</b>", parse_mode='html')
                else:
                    await event.reply("❌ Failed to download file.", parse_mode='html')
            except Exception as e:
                await event.reply(f"❌ Download error: {str(e)}", parse_mode='html')
        else:
            await event.reply("❌ <b>Send a photo.</b>", parse_mode='html')
        return

    if action == 'awaiting_welcome_photo':
        if event.message.media:
            file_path = f"/root/content-bot/welcome_{user_id}.jpg"
            try:
                await event.download_media(file=file_path)
                if os.path.exists(file_path):
                    set_setting('welcome_photo', file_path)
                    await event.reply("✅ <b>Welcome photo updated!</b>", parse_mode='html')
                else:
                    await event.reply("❌ Failed to download file.", parse_mode='html')
            except Exception as e:
                await event.reply(f"❌ Download error: {str(e)}", parse_mode='html')
        else:
            await event.reply("❌ <b>Send a photo.</b>", parse_mode='html')
        return

# ==================== USER PAYMENT SUBMISSION ====================
@bot.on(events.NewMessage)
async def user_payment_handler(event):
    user_id = event.sender_id
    if user_id == ADMIN_ID:
        return
    if user_id not in user_payment_states:
        return
    state = user_payment_states[user_id]
    if 'step' not in state:
        return
    if state['step'] == 'waiting_utr':
        utr = event.text.strip()
        if not utr:
            return
        state['utr'] = utr
        state['step'] = 'waiting_screenshot'
        user_payment_states[user_id] = state
        await event.reply("✅ UTR received! Now send the payment screenshot as a photo.", parse_mode='html')
        return
    elif state['step'] == 'waiting_screenshot':
        if not event.message.media:
            await event.reply("❌ Please send a photo (screenshot of payment).", parse_mode='html')
            return
        
        sender = await event.get_sender()
        user_name = sender.first_name or "Unknown"
        user_username = sender.username or "No username"
        
        pid = state.get('product')
        txid = state.get('txid')
        if not pid or not txid:
            pending = get_pending_by_user(user_id)
            if pending:
                pid = pending['product_id']
                txid = pending['txid']
            else:
                await event.reply("❌ No pending order found. Please use BUY NOW first.", parse_mode='html')
                return
        product = get_product(pid)
        if not product:
            await event.reply("❌ Product not found. Contact admin.", parse_mode='html')
            return
        
        try:
            photo_bytes = await event.download_media(file=bytes)
            if not photo_bytes:
                await event.reply("❌ Failed to download screenshot. Try again.", parse_mode='html')
                return
        except Exception as e:
            await event.reply(f"❌ Download error: {str(e)}", parse_mode='html')
            return
        
        admin_username = get_setting('admin_username') or 'SANDYxBIHARI'
        caption = f"""📢 <b>New Payment Submission</b>

👤 <b>User:</b> {user_name} (@{user_username})
🆔 <b>ID:</b> <code>{user_id}</code>
📌 <b>Product:</b> {product['emoji']} {product['name']}
💰 <b>Amount:</b> ₹{product['price']}
🆔 <b>TxID:</b> <code>{txid}</code>
📝 <b>UTR:</b> <code>{state.get('utr', 'N/A')}</code>

<b>Approve or reject this payment.</b>
        """
        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ Approve", "callback_data": f"admin_approve:{txid}:{user_id}"},
                 {"text": "❌ Reject", "callback_data": f"admin_reject:{txid}:{user_id}"}]
            ]
        }
        
        def send_photo_with_bytes():
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            files = {'photo': ('photo.jpg', photo_bytes, 'image/jpeg')}
            data = {
                'chat_id': ADMIN_ID,
                'caption': caption,
                'parse_mode': 'HTML',
                'reply_markup': json.dumps(keyboard)
            }
            try:
                resp = requests.post(url, files=files, data=data, timeout=15)
                return resp.json()
            except Exception as e:
                return {'ok': False, 'error': str(e)}
        
        try:
            result = await asyncio.to_thread(send_photo_with_bytes)
            if result and result.get('ok'):
                mention = f"@{admin_username}" if admin_username.startswith('@') else admin_username
                await bot.send_message(ADMIN_ID, f"🔔 <b>New Payment Received!</b>\nUser: {user_name} (@{user_username})\nProduct: {product['name']}\nTxID: <code>{txid}</code>\n\n{mention} please check and approve.", parse_mode='html')
                await event.reply("✅ Your payment submission has been sent to admin. Please wait for approval.", parse_mode='html')
            else:
                await bot.send_message(ADMIN_ID, f"⚠️ <b>Payment Submission (photo failed)</b>\nUser: {user_name} (@{user_username})\nProduct: {product['name']}\nTxID: <code>{txid}</code>\nUTR: {state.get('utr', 'N/A')}\n\nPlease ask user to send again.", parse_mode='html')
                await event.reply("❌ Failed to send screenshot to admin. Please contact admin directly with your TxID.", parse_mode='html')
        except Exception as e:
            await bot.send_message(ADMIN_ID, f"⚠️ <b>Payment Submission (error)</b>\nUser: {user_name} (@{user_username})\nProduct: {product['name']}\nTxID: <code>{txid}</code>\nUTR: {state.get('utr', 'N/A')}\n\nError: {e}", parse_mode='html')
            await event.reply("❌ Failed to send screenshot to admin. Please contact admin directly with your TxID.", parse_mode='html')
        finally:
            if user_id in user_payment_states:
                del user_payment_states[user_id]
        return

# ==================== RUN BOT ====================
print("🤖 18+ Multi‑Product Bot Started (Coloured start + photo/video/link demo)")
print("👑 Admin: " + (get_setting('admin_username') or ''))
bot.run_until_disconnected()
EOF

echo "✅ Bot updated. Restarting..."
systemctl restart scraper-bot 2>/dev/null || echo "Restart manually: cd /root/content-bot && python3 content_bot.py"
