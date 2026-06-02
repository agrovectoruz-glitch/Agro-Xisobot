import logging
import os
from datetime import datetime, time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TOKEN")
GURUH_ID = os.environ.get("GURUH_ID")
YUBORISH_SOAT = int(os.environ.get("YUBORISH_SOAT", "21"))

TUR, SUMMA, IZOH, ZAKLAD_IZOH = range(4)

kunlik = {"kirimlar": [], "chiqimlar": [], "oldingi_qoldiq": 0}

def formatlash(summa):
    return "{:,}".format(int(summa)).replace(",", " ")

async def start(update, context):
    keyboard = [
        [KeyboardButton("💰 Kirim"), KeyboardButton("💸 Chiqim")],
        [KeyboardButton("💼 Oldingi qoldiq"), KeyboardButton("📊 Xisobot ko'rish")]
    ]
    await update.message.reply_text("Nima qilmoqchisiz?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def xabar(update, context):
    matn = update.message.text
    if matn == "💰 Kirim":
        keyboard = [[KeyboardButton("🏦 Rahbardan"), KeyboardButton("📦 Zakladdan")], [KeyboardButton("🔙 Orqaga")]]
        await update.message.reply_text("Kirim turi?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return TUR
    elif matn == "💸 Chiqim":
        context.user_data["tur"] = "chiqim"
        await update.message.reply_text("Chiqim summasini kiriting:")
        return SUMMA
    elif matn == "💼 Oldingi qoldiq":
        context.user_data["tur"] = "qoldiq"
        await update.message.reply_text("Oldingi qoldiq summasini kiriting:")
        return SUMMA
    elif matn == "📊 Xisobot ko'rish":
        await xisobot_yuborish(update, context, faqat_korish=True)
    return ConversationHandler.END

async def tur_tanlash(update, context):
    matn = update.message.text
    if matn == "🏦 Rahbardan":
        context.user_data["tur"] = "rahbar"
        await update.message.reply_text("Summani kiriting:")
        return SUMMA
    elif matn == "📦 Zakladdan":
        context.user_data["tur"] = "zaklad"
        await update.message.reply_text("Summani kiriting:")
        return SUMMA
    elif matn == "🔙 Orqaga":
        await start(update, context)
        return ConversationHandler.END
    return TUR

async def summa_qabul(update, context):
    try:
        summa = int(update.message.text.replace(" ", "").replace(",", ""))
        context.user_data["summa"] = summa
        tur = context.user_data.get("tur")
        if tur == "qoldiq":
            kunlik["oldingi_qoldiq"] = summa
            await update.message.reply_text(f"✅ Oldingi qoldiq: {formatlash(summa)} so'm saqlandi!")
            await start(update, context)
            return ConversationHandler.END
        elif tur == "rahbar":
            kunlik["kirimlar"].append((summa, "Rahbardan olingan"))
            await update.message.reply_text(f"✅ +{formatlash(summa)} Rahbardan olingan")
            await start(update, context)
            return ConversationHandler.END
        elif tur == "zaklad":
            await update.message.reply_text("Zaklad izohini kiriting:")
            return ZAKLAD_IZOH
        elif tur == "chiqim":
            await update.message.reply_text("Izohini kiriting:")
            return IZOH
    except ValueError:
        await update.message.reply_text("⚠️ Faqat raqam kiriting!")
        return SUMMA

async def izoh_qabul(update, context):
    izoh = update.message.text
    summa = context.user_data.get("summa")
    kunlik["chiqimlar"].append((summa, izoh))
    await update.message.reply_text(f"✅ {formatlash(summa)} {izoh}")
    await start(update, context)
    return ConversationHandler.END

async def zaklad_izoh_qabul(update, context):
    izoh = update.message.text
    summa = context.user_data.get("summa")
    kunlik["kirimlar"].append((summa, izoh))
    await update.message.reply_text(f"✅ +{formatlash(summa)} {izoh}")
    await start(update, context)
    return ConversationHandler.END

async def xisobot_yuborish(update=None, context=None, faqat_korish=False):
    bugun = datetime.now().strftime("%d.%m.%Y")
    kirimlar = kunlik["kirimlar"]
    chiqimlar = kunlik["chiqimlar"]
    oldingi_qoldiq = kunlik["oldingi_qoldiq"]
    jami_kirim = sum(s for s, _ in kirimlar)
    jami_chiqim = sum(s for s, _ in chiqimlar)
    balans = oldingi_qoldiq + jami_kirim
    qoldi = balans - jami_chiqim
    kirim_text = "\n".join(f"+{formatlash(s)} {i}" for s, i in kirimlar)
    chiqim_text = "\n".join(f"{formatlash(s)} {i}" for s, i in chiqimlar)
    xisobot = f"📅 {bugun}\n"
    if kirim_text:
        xisobot += f"\n{kirim_text}\n"
    if chiqim_text:
        xisobot += f"\n{chiqim_text}\n"
    xisobot += f"\nJami: {formatlash(jami_chiqim)}\nBalans: {formatlash(balans)}\nQoldi: {formatlash(qoldi)}"
    if faqat_korish and update:
        await update.message.reply_text(xisobot)
    elif not faqat_korish and context:
        await context.bot.send_message(chat_id=GURUH_ID, text=xisobot)
        kunlik["oldingi_qoldiq"] = qoldi
        kunlik["kirimlar"] = []
        kunlik["chiqimlar"] = []

async def kunlik_yuborish(context):
    await xisobot_yuborish(context=context, faqat_korish=False)

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, xabar)],
        states={
            TUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, tur_tanlash)],
            SUMMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, summa_qabul)],
            IZOH: [MessageHandler(filters.TEXT & ~filters.COMMAND, izoh_qabul)],
            ZAKLAD_IZOH: [MessageHandler(filters.TEXT & ~filters.COMMAND, zaklad_izoh_qabul)],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.job_queue.run_daily(kunlik_yuborish, time=time(hour=YUBORISH_SOAT, minute=0))
    app.run_polling()

if __name__ == "__main__":
    main()
