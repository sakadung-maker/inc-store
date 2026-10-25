from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import os, asyncio
from PIL import Image
import io

TOKEN = "8309739428:AAHOk7u_OC3hXRpCpAkxN8zysndl6IpZoyE"
ADMIN_ID = 8840797458
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QRIS_PATH = os.path.join(BASE_DIR, "qris.jpg")
STOCK_DIR = os.path.join(BASE_DIR, "stocks")
os.makedirs(STOCK_DIR, exist_ok=True)

PRODUCTS = {
    "capcut_7d": {"name": "Capcut Pro 7 Hari", "price": 5000, "need_email": False},
    "canva_member": {"name": "Canva Pro Member 1 Bulan", "price": 3000, "need_email": True},
    "canva_1b": {"name": "Canva Pro 1 Bulan Full", "price": 15000, "need_email": False},
    "capcut_1b": {"name": "Capcut Pro 1 Bulan", "price": 20000, "need_email": False},
}

def get_stock_count(key):
    path = os.path.join(STOCK_DIR, f"{key}.txt")
    if not os.path.exists(path): return 0
    with open(path, "r", encoding="utf-8") as f: return len([l.strip() for l in f if l.strip()])

def pop_stock(key):
    path = os.path.join(STOCK_DIR, f"{key}.txt")
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines: return None
    stock, sisa = lines[0], lines[1:]
    with open(path, "w", encoding="utf-8") as f: f.write("\n".join(sisa))
    return stock

def get_compressed_qris():
    img = Image.open(QRIS_PATH)
    img.thumbnail((600, 600)) # gue kecilin biar gak timeout
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=60, optimize=True)
    buf.seek(0)
    return buf

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    # loading simple 1x aja, gak spam
    m = await update.message.reply_text("⏳ INC STORE lagi loading...")
    await asyncio.sleep(0.8)
    try: await m.delete()
    except: pass
    
    keyboard = []
    for k,v in PRODUCTS.items():
        if not v["need_email"]:
            keyboard.append([InlineKeyboardButton(f"{v['name']} - Rp {v['price']} (Sisa: {get_stock_count(k)})", callback_data=f"buy_{k}")])
        else:
            keyboard.append([InlineKeyboardButton(f"{v['name']} - Rp {v['price']}", callback_data=f"buy_{k}")])
    
    await update.message.reply_text("🛒 *INC STORE* 🛒\nToko Premium Auto - Pilih paket:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # loading cuma 1 pesan
    loading = await query.message.reply_text("⏳ Memproses...")
    await asyncio.sleep(0.5)
    try: await loading.delete()
    except: pass

    key = query.data.replace("buy_","")
    product = PRODUCTS.get(key)
    if not product["need_email"] and get_stock_count(key) == 0:
        await query.message.reply_text(f"❌ Stok {product['name']} HABIS!"); return
    
    context.user_data["buying"] = key
    if product["need_email"]:
        await query.message.reply_text(f"Kamu pilih: *{product['name']}*\nKirim email Canva:", parse_mode="Markdown")
        context.user_data["awaiting_email"] = True
    else: 
        await show_qris(query.message.chat_id, context, key)

async def handle_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_email"): return
    email = update.message.text.strip()
    if "@" not in email: await update.message.reply_text("Email salah co"); return
    context.user_data["buyer_email"] = email; context.user_data["awaiting_email"] = False
    await update.message.reply_text(f"✅ Oke: {email}")
    await show_qris(update.message.chat_id, context, context.user_data["buying"])

async def show_qris(chat_id, context, key):
    product = PRODUCTS[key]; buyer_email = context.user_data.get("buyer_email", "-")
    caption = f"🛒 INC STORE\n{product['name']}\nRp {product['price']}\nEmail: {buyer_email}\n\nScan QRIS & klik Sudah Bayar."
    keyboard = [[InlineKeyboardButton("✅ Sudah Bayar", callback_data=f"paid_{key}")]]
    await context.bot.send_photo(chat_id=chat_id, photo=get_compressed_qris(), caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    key = query.data.replace("paid_",""); product = PRODUCTS[key]; user = query.from_user
    buyer_email = context.user_data.get("buyer_email", "-")
    keyboard = [[InlineKeyboardButton("✅ ACC", callback_data=f"acc_{user.id}_{key}"), InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{user.id}_{key}")]]
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"💰 ORDER INC STORE\n{product['name']}\nRp {product['price']}\n@{user.username} | {user.id}\nEmail: {buyer_email}\nSisa: {get_stock_count(key)}", reply_markup=InlineKeyboardMarkup(keyboard))
    await query.message.reply_text("✅ Terkirim! Admin INC STORE cek dulu 🙏"); context.user_data.clear()

async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    parts = query.data.split("_"); action = parts[0]; user_id = int(parts[1]); key = "_".join(parts[2:]); product = PRODUCTS.get(key)
    if action == "acc":
        if product["need_email"]:
            await context.bot.send_message(chat_id=user_id, text=f"✅ ACC INC STORE! {product['name']} udah diinvite.")
            await query.edit_message_text(f"✅ DONE {user_id}")
        else:
            akun = pop_stock(key)
            if not akun: await context.bot.send_message(chat_id=user_id, text="❌ Stok habis."); await query.edit_message_text(f"❌ HABIS {key}"); return
            await context.bot.send_message(chat_id=user_id, text=f"✅ LUNAS INC STORE\n{product['name']}\n\n{akun}")
            await query.edit_message_text(f"✅ TERKIRIM {akun} | Sisa: {get_stock_count(key)}")
    else:
        await context.bot.send_message(chat_id=user_id, text="❌ Ditolak."); await query.edit_message_text(f"❌ Tolak {user_id}")

async def cekstok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    text = "📦 STOK INC STORE:\n" + "\n".join([f"{v['name']}: {get_stock_count(k)}" for k,v in PRODUCTS.items() if not v["need_email"]])
    await update.message.reply_text(text)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start)); app.add_handler(CommandHandler("cekstok", cekstok))
    app.add_handler(CallbackQueryHandler(handle_buy, pattern="^buy_")); app.add_handler(CallbackQueryHandler(handle_paid, pattern="^paid_"))
    app.add_handler(CallbackQueryHandler(handle_admin, pattern="^(acc|reject)_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email_input))
    print("INC STORE FIX TIMEOUT JALAN...")
    app.run_polling()

if __name__ == "__main__": main()