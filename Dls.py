import logging
import random
import string
import asyncio
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from database import db


# Render uchun web server
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti!")
    def log_message(self, format, *args):
        pass

def run_web():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# ===================== SOZLAMALAR =====================
BOT_TOKEN = "7156597056:AAG-4YVJh0yhMaZkWQhtsgE6eM4o-cVyTJM"
ADMIN_USERNAME = "@Almardonivich"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== YORDAMCHI FUNKSIYALAR =====================

def generate_match_code():
    """6 belgili tasodifiy kod yaratish"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🤝 O'rtoqlik O'yini"), KeyboardButton("👤 O'yinchi Profili")],
        [KeyboardButton("📢 Reklama"), KeyboardButton("👥 Do'stlarni Taklif Qilish")],
        [KeyboardButton("🏆 Reyting"), KeyboardButton("ℹ️ Bot Haqida")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_profile_inline():
    keyboard = [
        [InlineKeyboardButton("🖼️ Logo Qo'yish", callback_data="set_logo")],
        [InlineKeyboardButton("📊 O'yin Tarixi", callback_data="game_history")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ===================== START HANDLER =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Referral tekshirish
    ref_code = None
    if context.args:
        ref_code = context.args[0]

    # Foydalanuvchini bazaga qo'shish
    db.add_user(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name,
        ref_code=ref_code
    )

    welcome_text = (
        f"🎮 *Xush kelibsiz, {user.first_name}!*\n\n"
        f"🌟 *O'yin Botiga Xush Kelibsiz!*\n\n"
        f"Bu bot orqali siz:\n"
        f"🤝 Do'stlar bilan o'yin o'ynashingiz\n"
        f"🏆 Reyting jadvalida o'rin egallashingiz\n"
        f"👥 Do'stlarni taklif qilishingiz mumkin!\n\n"
        f"⬇️ *Quyidagi tugmalardan birini tanlang:*"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# ===================== O'RTOQLIK O'YINI =====================

async def friendship_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or "", user.full_name)

    # Kutayotgan o'yinchilar ro'yxatini tekshirish
    waiting = db.get_waiting_player()

    if waiting and waiting['user_id'] != user.id:
        # Juftlik topildi!
        player1_id = waiting['user_id']
        player2_id = user.id
        match_code = generate_match_code()

        # O'yinni yaratish
        db.create_match(player1_id, player2_id, match_code)
        db.remove_from_waiting(player1_id)

        player1_info = db.get_user(player1_id)
        player2_info = db.get_user(player2_id)

        # Ikkala o'yinchiga xabar yuborish
        match_text_p1 = (
            f"🎉 *Juftlik Topildi!*\n\n"
            f"🔑 *Sizning kodingiz:* `{match_code}`\n\n"
            f"👤 *O'rtoqingiz:*\n"
            f"├ 📛 Ismi: {user.full_name}\n"
            f"├ 🔖 Username: @{user.username or 'yoq'}\n"
            f"└ 🎮 Umumiy o'yinlar: {db.get_total_games(player2_id)}\n\n"
            f"🍀 *Yaxshi o'yin tilaymiz!*"
        )

        match_text_p2 = (
            f"🎉 *Juftlik Topildi!*\n\n"
            f"🔑 *Sizning kodingiz:* `{match_code}`\n\n"
            f"👤 *O'rtoqingiz:*\n"
            f"├ 📛 Ismi: {player1_info['full_name']}\n"
            f"├ 🔖 Username: @{player1_info['username'] or 'yoq'}\n"
            f"└ 🎮 Umumiy o'yinlar: {db.get_total_games(player1_id)}\n\n"
            f"🍀 *Yaxshi o'yin tilaymiz!*"
        )

        p1_logo = db.get_user_logo(player1_id)
        p2_logo = db.get_user_logo(player2_id)

        # 1-o'yinchiga xabar
        if p2_logo:
            await context.bot.send_photo(
                chat_id=player1_id,
                photo=p2_logo,
                caption=match_text_p1,
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=player1_id,
                text=match_text_p1,
                parse_mode="Markdown"
            )

        # 2-o'yinchiga xabar
        if p1_logo:
            await context.bot.send_photo(
                chat_id=player2_id,
                photo=p1_logo,
                caption=match_text_p2,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                match_text_p2,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )

    else:
        # Kutish rejimi
        db.add_to_waiting(user.id)

        wait_text = (
            f"⏳ *Kutish Rejimi*\n\n"
            f"🔍 O'rtoq qidirilmoqda...\n\n"
            f"⏱️ *5 daqiqa* kutasiz\n"
            f"Har daqiqada sizga eslatma yuboriladi.\n\n"
            f"🚪 Chiqish uchun /cancel buyrug'ini yuboring"
        )

        await update.message.reply_text(
            wait_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

        # 5 daqiqa kutish - har daqiqada eslatma
        for minute in range(1, 6):
            await asyncio.sleep(60)

            # Hali kutayaptimi?
            still_waiting = db.is_waiting(user.id)
            if not still_waiting:
                return

            remaining = 5 - minute
            if remaining > 0:
                remind_text = (
                    f"⏰ *Eslatma!*\n\n"
                    f"🔍 Hali o'rtoq qidirilmoqda...\n"
                    f"⏱️ Qolgan vaqt: *{remaining} daqiqa*\n\n"
                    f"Sabr qiling, tez topiladi! 💪"
                )
                try:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=remind_text,
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

        # 5 daqiqa o'tdi, hali ham kutayaptimi?
        if db.is_waiting(user.id):
            db.remove_from_waiting(user.id)
            sorry_text = (
                f"😔 *Uzr!*\n\n"
                f"Hozirda o'rtoqlik o'yini o'ynamoqchilar yo'q.\n\n"
                f"🔄 Keyinroq qayta urinib ko'ring!\n"
                f"👥 Do'stlaringizni ham taklif qiling!"
            )
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=sorry_text,
                    parse_mode="Markdown"
                )
            except Exception:
                pass

async def cancel_waiting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.remove_from_waiting(user.id)
    await update.message.reply_text(
        "✅ Kutish bekor qilindi.",
        reply_markup=get_main_keyboard()
    )

# ===================== PROFIL =====================

async def player_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or "", user.full_name)

    user_data = db.get_user(user.id)
    total_games = db.get_total_games(user.id)
    invited_count = db.get_invited_count(user.id)
    logo = db.get_user_logo(user.id)

    profile_text = (
        f"👤 *Mening Profilim*\n\n"
        f"📛 *Ism:* {user.full_name}\n"
        f"🔖 *Username:* @{user.username or 'yoq'}\n"
        f"🆔 *ID:* `{user.id}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🎮 *Umumiy o'yinlar:* {total_games} ta\n"
        f"👥 *Taklif etilganlar:* {invited_count} ta\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"🖼️ Logo: {'✅ Qoyilgan' if logo else '❌ Yoq'}\n\n"
        f"🏅 *Profil sozlamalari uchun tugmalardan foydalaning:*"
    )

    if logo:
        await update.message.reply_photo(
            photo=logo,
            caption=profile_text,
            parse_mode="Markdown",
            reply_markup=get_profile_inline()
        )
    else:
        await update.message.reply_text(
            profile_text,
            parse_mode="Markdown",
            reply_markup=get_profile_inline()
        )

# ===================== DO'STLARNI TAKLIF QILISH =====================

async def invite_friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username

    ref_link = f"https://t.me/{bot_username}?start={user.id}"
    invited_count = db.get_invited_count(user.id)

    invite_text = (
        f"👥 *Do'stlarni Taklif Qilish*\n\n"
        f"🔗 *Sizning maxsus havolangiz:*\n"
        f"`{ref_link}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 *Siz taklif qilganlar:* {invited_count} ta\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📌 *Qanday ishlaydi?*\n"
        f"1️⃣ Havolani do'stingizga yuboring\n"
        f"2️⃣ Do'stingiz botni ishga tushirsin\n"
        f"3️⃣ Siz avtomatik bonusga ega bo'lasiz!\n\n"
        f"🎁 Har bir taklif uchun maxsus sovg'alar!"
    )

    keyboard = [
        [InlineKeyboardButton("📤 Ulashish", switch_inline_query=f"O'yin botiga qo'shiling! {ref_link}")]
    ]

    await update.message.reply_text(
        invite_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===================== REKLAMA =====================

async def advertisement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad_text = (
        f"📢 *Reklama Bo'limi*\n\n"
        f"💼 Botimizda reklama joylashtirmoqchimisiz?\n\n"
        f"✅ *Afzalliklari:*\n"
        f"├ 👁️ Ko'p auditoriya\n"
        f"├ 🎯 Maqsadli ko'rsatish\n"
        f"├ 💰 Arzon narx\n"
        f"└ 📊 Statistika taqdim etiladi\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📩 *Bog'lanish uchun:*\n"
        f"👨‍💼 Admin: {ADMIN_USERNAME}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"⚡ Tezroq murojaat qiling!"
    )

    keyboard = [
        [InlineKeyboardButton("📩 Admin bilan bog'lanish", url=f"https://t.me/Almardonivich")]
    ]

    await update.message.reply_text(
        ad_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===================== REYTING =====================

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = db.get_top_players(10)

    rating_text = "🏆 *Top 10 O'yinchilar*\n\n"

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for i, player in enumerate(top_users):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        username = f"@{player['username']}" if player['username'] else player['full_name']
        rating_text += f"{medal} {username} — *{player['total_games']}* o'yin\n"

    if not top_users:
        rating_text += "😔 Hali hech kim o'yin o'ynamagan.\nBirinchi bo'ling! 🚀"

    rating_text += f"\n\n⏰ *Yangilangan:* {datetime.now().strftime('%H:%M')}"

    await update.message.reply_text(
        rating_text,
        parse_mode="Markdown"
    )

# ===================== BOT HAQIDA =====================

async def about_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = (
        f"ℹ️ *Bot Haqida*\n\n"
        f"🤖 *Bot nomi:* O'yin Boti\n"
        f"👨‍💻 *Ishlab chiquvchi:* {ADMIN_USERNAME}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🎮 *Imkoniyatlar:*\n"
        f"├ 🤝 O'rtoqlik o'yini\n"
        f"├ 👤 Shaxsiy profil\n"
        f"├ 🏆 Reyting jadvali\n"
        f"├ 👥 Do'stlarni taklif\n"
        f"└ 📢 Reklama xizmati\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💡 *Versiya:* 1.0.0\n"
        f"📅 *Sana:* 2024\n\n"
        f"❓ Savollar uchun: {ADMIN_USERNAME}"
    )

    await update.message.reply_text(
        about_text,
        parse_mode="Markdown"
    )

# ===================== CALLBACK HANDLERS =====================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if query.data == "set_logo":
        context.user_data['waiting_logo'] = True
        await query.message.reply_text(
            "🖼️ *Logo Yuklash*\n\n"
            "Profil uchun rasm yuboring.\n"
            "_(Rasm sifatida yuboring, fayl emas)_",
            parse_mode="Markdown"
        )

    elif query.data == "game_history":
        matches = db.get_user_matches(user.id)
        if not matches:
            history_text = "📊 *O'yin Tarixi*\n\n😔 Hali o'yin o'ynamagansiz."
        else:
            history_text = "📊 *So'nggi O'yinlar:*\n\n"
            for i, match in enumerate(matches[:10], 1):
                date = match['created_at'][:10] if match['created_at'] else "—"
                history_text += f"{i}. 🔑 `{match['match_code']}` — 📅 {date}\n"

        await query.message.reply_text(
            history_text,
            parse_mode="Markdown"
        )

    elif query.data == "back_main":
        await query.message.reply_text(
            "🏠 Asosiy menyu:",
            reply_markup=get_main_keyboard()
        )

# ===================== RASM YUKLASH =====================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if context.user_data.get('waiting_logo'):
        photo = update.message.photo[-1]
        file_id = photo.file_id
        db.set_user_logo(user.id, file_id)
        context.user_data['waiting_logo'] = False

        await update.message.reply_text(
            "✅ *Logo muvaffaqiyatli saqlandi!*\n\n"
            "Endi profil sahifangizda ko'rinadi. 🎉",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "📸 Rasmingiz qabul qilindi.\n"
            "Logoni o'rnatish uchun Profil bo'limiga o'ting.",
            reply_markup=get_main_keyboard()
        )

# ===================== MATN HANDLERS =====================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    db.add_user(user.id, user.username or "", user.full_name)

    if text == "🤝 O'rtoqlik O'yini":
        await friendship_game(update, context)
    elif text == "👤 O'yinchi Profili":
        await player_profile(update, context)
    elif text == "📢 Reklama":
        await advertisement(update, context)
    elif text == "👥 Do'stlarni Taklif Qilish":
        await invite_friends(update, context)
    elif text == "🏆 Reyting":
        await leaderboard(update, context)
    elif text == "ℹ️ Bot Haqida":
        await about_bot(update, context)
    else:
        await update.message.reply_text(
            "❓ Nima demoqchi ekanligingizni tushunmadim.\n"
            "Quyidagi tugmalardan birini tanlang:",
            reply_markup=get_main_keyboard()
        )

# ===================== MAIN =====================

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_waiting))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("✅ Bot ishga tushdi!")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
