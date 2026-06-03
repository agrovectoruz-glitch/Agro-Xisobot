import os
import json
import urllib.request
import calendar
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

TOKEN = os.environ.get("TOKEN")
AGRO_GURUH_ID = os.environ.get("-4911960051")
SHAXSIY_GURUH_ID = "-1003966538627"

UZ_TZ = timezone(timedelta(hours=5))

# ============ MA'LUMOTLAR ============
agro_kirimlar = []
agro_chiqimlar = []
agro_haftalik_kirimlar = []
agro_haftalik_chiqimlar = []
agro_oylik_kirimlar = []
agro_oylik_chiqimlar = []

shaxsiy_kirimlar = []
shaxsiy_chiqimlar = []
shaxsiy_oldingi_qoldiq = 0

shaxsiy_haftalik_kirimlar = []
shaxsiy_haftalik_chiqimlar = []
shaxsiy_haftalik_oldingi_qoldiq = 0

shaxsiy_oylik_kirimlar = []
shaxsiy_oylik_chiqimlar = []
shaxsiy_oylik_oldingi_qoldiq = 0

holat = {}
temp = {}

# ============ YORDAMCHI ============
def formatlash(summa):
    return "{:,}".format(int(summa)).replace(",", " ")

def uz_now():
    return datetime.now(UZ_TZ)

def api(method, data):
    url = "https://api.telegram.org/bot{}/{}".format(TOKEN, method)
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print("API xato: {}".format(e))

def yuborish(chat_id, matn, keyboard=None):
    data = {"chat_id": chat_id, "text": matn, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True}
    api("sendMessage", data)

# ============ MENYULAR ============
def asosiy_menu(chat_id):
    holat[chat_id] = ""
    yuborish(chat_id, "📋 <b>Asosiy menyu:</b>", [
        ["💼 Agro Xarajat"],
        ["👤 Shaxsiy Xarajat"]
    ])

def agro_xarajat_menu(chat_id):
    holat[chat_id] = "agro_xarajat"
    yuborish(chat_id, "💼 <b>Agro Xarajat:</b>", [
        ["💰 Daromad", "💸 Xarajat"],
        ["📊 Kunlik", "📅 Haftalik", "🗓 Oylik"],
        ["🏠 Bosh menyu"]
    ])

def shaxsiy_menu(chat_id):
    holat[chat_id] = "shaxsiy"
    yuborish(chat_id, "👤 <b>Shaxsiy Xarajat:</b>", [
        ["💰 Daromad", "💸 Xarajat"],
        ["📊 Kunlik", "📅 Haftalik", "🗓 Oylik"],
        ["🏠 Bosh menyu"]
    ])

# ============ HISOBOTLAR ============
def agro_hisobot_matni(kirimlar, chiqimlar, sarlavha="Kunlik"):
    jami_kirim = sum(k["summa"] for k in kirimlar)
    jami_chiqim = sum(c["summa"] for c in chiqimlar)
    qoldiq = jami_kirim - jami_chiqim
    bugun = uz_now().strftime("%d.%m.%Y")

    matn = "📅 <b>{} | {}</b>\n".format(sarlavha, bugun)
    matn += "─────────────────\n"

    if kirimlar:
        matn += "\n💰 <b>Kirimlar:</b>\n"
        for k in kirimlar:
            matn += "  +{} — {} ({})\n".format(formatlash(k["summa"]), k["izoh"], k["tur"])
    else:
        matn += "\n💰 <b>Kirimlar:</b> yo'q\n"

    if chiqimlar:
        matn += "\n💸 <b>Chiqimlar:</b>\n"
        for c in chiqimlar:
            matn += "  -{} — {}\n".format(formatlash(c["summa"]), c["izoh"])
    else:
        matn += "\n💸 <b>Chiqimlar:</b> yo'q\n"

    matn += "─────────────────\n"
    matn += "📥 Jami kirim : <b>{}</b>\n".format(formatlash(jami_kirim))
    matn += "📤 Jami chiqim: <b>{}</b>\n".format(formatlash(jami_chiqim))
    matn += "💵 Qoldi      : <b>{}</b>".format(formatlash(qoldiq))
    return matn

def shaxsiy_hisobot_matni(kirimlar, chiqimlar, oldingi_qoldiq=0, sarlavha="Kunlik"):
    jami_kirim = sum(k["summa"] for k in kirimlar)
    jami_chiqim = sum(c["summa"] for c in chiqimlar)
    balans = oldingi_qoldiq + jami_kirim
    qoldiq = balans - jami_chiqim
    bugun = uz_now().strftime("%d.%m.%Y")

    matn = "📅 <b>{} | {}</b>\n".format(sarlavha, bugun)
    matn += "─────────────────\n"

    if oldingi_qoldiq > 0:
        matn += "\n🏦 Oldingi qoldiq: <b>{}</b>\n".format(formatlash(oldingi_qoldiq))

    if kirimlar:
        matn += "\n💰 <b>Kirimlar:</b>\n"
        for k in kirimlar:
            matn += "  +{} — {} ({})\n".format(formatlash(k["summa"]), k["izoh"], k["tur"])
    else:
        matn += "\n💰 <b>Kirimlar:</b> yo'q\n"

    if chiqimlar:
        matn += "\n💸 <b>Chiqimlar:</b>\n"
        for c in chiqimlar:
            matn += "  -{} — {}\n".format(formatlash(c["summa"]), c["izoh"])
    else:
        matn += "\n💸 <b>Chiqimlar:</b> yo'q\n"

    matn += "─────────────────\n"
    matn += "📥 Jami kirim : <b>{}</b>\n".format(formatlash(jami_kirim))
    matn += "📤 Jami chiqim: <b>{}</b>\n".format(formatlash(jami_chiqim))
    matn += "🏦 Balans     : <b>{}</b>\n".format(formatlash(balans))
    matn += "💵 Qoldi      : <b>{}</b>".format(formatlash(qoldiq))
    return matn

# ============ XABAR QAYTA ISHLASH ============
def xabar_qayta_ishlash(chat_id, matn):
    global shaxsiy_oldingi_qoldiq
    global shaxsiy_haftalik_oldingi_qoldiq
    global shaxsiy_oylik_oldingi_qoldiq

    if matn in ["/start", "/menu"]:
        asosiy_menu(chat_id)
        return

    h = holat.get(chat_id, "")

    # === UMUMIY TUGMALAR ===
    if matn == "💼 Agro Xarajat":
        agro_xarajat_menu(chat_id)
        return
    if matn == "👤 Shaxsiy Xarajat":
        shaxsiy_menu(chat_id)
        return
    if matn == "🏠 Bosh menyu":
        asosiy_menu(chat_id)
        return
    if matn == "🔙 Orqaga":
        if h.startswith("agro"):
            agro_xarajat_menu(chat_id)
        elif h.startswith("shaxsiy"):
            shaxsiy_menu(chat_id)
        else:
            asosiy_menu(chat_id)
        return

    # ===========================
    # === AGRO XARAJAT ===
    # ===========================
    if h == "agro_xarajat":
        if matn == "💰 Daromad":
            holat[chat_id] = "agro_kirim_tur"
            yuborish(chat_id, "💰 Daromad turini tanlang:", [
                ["🏦 Rahbardan", "📦 Zakladdan"],
                ["🔙 Orqaga"]
            ])
        elif matn == "💸 Xarajat":
            holat[chat_id] = "agro_chiqim_summa"
            yuborish(chat_id, "💸 Xarajat summasini kiriting:", [["🔙 Orqaga"]])
        elif matn == "📊 Kunlik":
            yuborish(chat_id,
                "💼 <b>Agro Kunlik hisobot:</b>\n\n" +
                agro_hisobot_matni(agro_kirimlar, agro_chiqimlar, "Kunlik"))
            agro_xarajat_menu(chat_id)
        elif matn == "📅 Haftalik":
            yuborish(chat_id,
                "💼 <b>Agro Haftalik hisobot:</b>\n\n" +
                agro_hisobot_matni(agro_haftalik_kirimlar, agro_haftalik_chiqimlar, "Haftalik"))
            agro_xarajat_menu(chat_id)
        elif matn == "🗓 Oylik":
            yuborish(chat_id,
                "💼 <b>Agro Oylik hisobot:</b>\n\n" +
                agro_hisobot_matni(agro_oylik_kirimlar, agro_oylik_chiqimlar, "Oylik"))
            agro_xarajat_menu(chat_id)
        return

    if h == "agro_kirim_tur":
        if matn in ["🏦 Rahbardan", "📦 Zakladdan"]:
            tur = matn.split(" ", 1)[1]
            temp[chat_id] = {"tur": tur}
            holat[chat_id] = "agro_kirim_summa"
            yuborish(chat_id, "💰 Summani kiriting:")
        return

    if h == "agro_kirim_summa":
        try:
            summa = int(matn.replace(" ", "").replace(",", ""))
            temp[chat_id]["summa"] = summa
            holat[chat_id] = "agro_kirim_izoh"
            yuborish(chat_id, "📝 Izoh kiriting:")
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
        return

    if h == "agro_kirim_izoh":
        t = temp.get(chat_id, {})
        yozuv = {
            "summa": t.get("summa", 0),
            "izoh": matn,
            "tur": t.get("tur", ""),
            "sana": uz_now().strftime("%d.%m.%Y")
        }
        agro_kirimlar.append(yozuv)
        agro_haftalik_kirimlar.append(yozuv)
        agro_oylik_kirimlar.append(yozuv)
        yuborish(chat_id, "✅ +{} — {} ({}) saqlandi!".format(
            formatlash(t.get("summa", 0)), matn, t.get("tur", "")))
        agro_xarajat_menu(chat_id)
        return

    if h == "agro_chiqim_summa":
        try:
            temp[chat_id] = {"summa": int(matn.replace(" ", "").replace(",", ""))}
            holat[chat_id] = "agro_chiqim_izoh"
            yuborish(chat_id, "📝 Izoh kiriting:")
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
        return

    if h == "agro_chiqim_izoh":
        t = temp.get(chat_id, {})
        yozuv = {
            "summa": t.get("summa", 0),
            "izoh": matn,
            "sana": uz_now().strftime("%d.%m.%Y")
        }
        agro_chiqimlar.append(yozuv)
        agro_haftalik_chiqimlar.append(yozuv)
        agro_oylik_chiqimlar.append(yozuv)
        yuborish(chat_id, "✅ -{} — {} saqlandi!".format(
            formatlash(t.get("summa", 0)), matn))
        agro_xarajat_menu(chat_id)
        return

    # ===========================
    # === SHAXSIY XARAJAT ===
    # ===========================
    if h == "shaxsiy":
        if matn == "💰 Daromad":
            holat[chat_id] = "shaxsiy_kirim_tur"
            yuborish(chat_id, "💰 Daromad turini tanlang:", [
                ["💼 Oylik", "📢 Reklama", "🔖 Boshqa"],
                ["🔙 Orqaga"]
            ])
        elif matn == "💸 Xarajat":
            holat[chat_id] = "shaxsiy_chiqim_summa"
            yuborish(chat_id, "💸 Xarajat summasini kiriting:", [["🔙 Orqaga"]])
        elif matn == "📊 Kunlik":
            yuborish(chat_id,
                "👤 <b>Shaxsiy Kunlik hisobot:</b>\n\n" +
                shaxsiy_hisobot_matni(shaxsiy_kirimlar, shaxsiy_chiqimlar, shaxsiy_oldingi_qoldiq, "Kunlik"))
            shaxsiy_menu(chat_id)
        elif matn == "📅 Haftalik":
            yuborish(chat_id,
                "👤 <b>Shaxsiy Haftalik hisobot:</b>\n\n" +
                shaxsiy_hisobot_matni(shaxsiy_haftalik_kirimlar, shaxsiy_haftalik_chiqimlar, shaxsiy_haftalik_oldingi_qoldiq, "Haftalik"))
            shaxsiy_menu(chat_id)
        elif matn == "🗓 Oylik":
            yuborish(chat_id,
                "👤 <b>Shaxsiy Oylik hisobot:</b>\n\n" +
                shaxsiy_hisobot_matni(shaxsiy_oylik_kirimlar, shaxsiy_oylik_chiqimlar, shaxsiy_oylik_oldingi_qoldiq, "Oylik"))
            shaxsiy_menu(chat_id)
        return

    if h == "shaxsiy_kirim_tur":
        if matn in ["💼 Oylik", "📢 Reklama", "🔖 Boshqa"]:
            tur = matn.split(" ", 1)[1]
            temp[chat_id] = {"tur": tur}
            holat[chat_id] = "shaxsiy_kirim_summa"
            yuborish(chat_id, "💰 Summani kiriting:")
        return

    if h == "shaxsiy_kirim_summa":
        try:
            summa = int(matn.replace(" ", "").replace(",", ""))
            temp[chat_id]["summa"] = summa
            holat[chat_id] = "shaxsiy_kirim_izoh"
            yuborish(chat_id, "📝 Izoh kiriting:")
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
        return

    if h == "shaxsiy_kirim_izoh":
        t = temp.get(chat_id, {})
        yozuv = {
            "summa": t.get("summa", 0),
            "izoh": matn,
            "tur": t.get("tur", ""),
            "sana": uz_now().strftime("%d.%m.%Y")
        }
        shaxsiy_kirimlar.append(yozuv)
        shaxsiy_haftalik_kirimlar.append(yozuv)
        shaxsiy_oylik_kirimlar.append(yozuv)
        yuborish(chat_id, "✅ +{} — {} ({}) saqlandi!".format(
            formatlash(t.get("summa", 0)), matn, t.get("tur", "")))
        shaxsiy_menu(chat_id)
        return

    if h == "shaxsiy_chiqim_summa":
        try:
            temp[chat_id] = {"summa": int(matn.replace(" ", "").replace(",", ""))}
            holat[chat_id] = "shaxsiy_chiqim_izoh"
            yuborish(chat_id, "📝 Izoh kiriting:")
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
        return

    if h == "shaxsiy_chiqim_izoh":
        t = temp.get(chat_id, {})
        yozuv = {
            "summa": t.get("summa", 0),
            "izoh": matn,
            "sana": uz_now().strftime("%d.%m.%Y")
        }
        shaxsiy_chiqimlar.append(yozuv)
        shaxsiy_haftalik_chiqimlar.append(yozuv)
        shaxsiy_oylik_chiqimlar.append(yozuv)
        yuborish(chat_id, "✅ -{} — {} saqlandi!".format(
            formatlash(t.get("summa", 0)), matn))
        shaxsiy_menu(chat_id)
        return

    asosiy_menu(chat_id)

# ============ POLLING ============
def polling():
    offset = 0
    while True:
        try:
            url = "https://api.telegram.org/bot{}/getUpdates?offset={}&timeout=30".format(TOKEN, offset)
            with urllib.request.urlopen(url, timeout=35) as r:
                updates = json.loads(r.read())
            for u in updates.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                matn = msg.get("text", "")
                if chat_id and matn:
                    xabar_qayta_ishlash(chat_id, matn)
        except Exception as e:
            print("Polling xato: {}".format(e))
            time.sleep(5)

# ============ KUNLIK HISOBOT — 21:00 ============
def kunlik_yuborish():
    global shaxsiy_oldingi_qoldiq

    while True:
        now = uz_now()
        if now.hour == 21 and now.minute == 0:
            try:
                if AGRO_GURUH_ID:
                    yuborish(AGRO_GURUH_ID,
                        "💼 <b>Agro Kunlik hisobot:</b>\n\n" +
                        agro_hisobot_matni(agro_kirimlar, agro_chiqimlar, "Kunlik"))

                yuborish(SHAXSIY_GURUH_ID,
                    "👤 <b>Shaxsiy Kunlik hisobot:</b>\n\n" +
                    shaxsiy_hisobot_matni(shaxsiy_kirimlar, shaxsiy_chiqimlar, shaxsiy_oldingi_qoldiq, "Kunlik"))

                # Kunlik qoldiqni keyingi kunga o'tkazish
                sh_k = sum(k["summa"] for k in shaxsiy_kirimlar)
                sh_ch = sum(c["summa"] for c in shaxsiy_chiqimlar)
                shaxsiy_oldingi_qoldiq = shaxsiy_oldingi_qoldiq + sh_k - sh_ch

                agro_kirimlar.clear()
                agro_chiqimlar.clear()
                shaxsiy_kirimlar.clear()
                shaxsiy_chiqimlar.clear()

            except Exception as e:
                print("Kunlik yuborish xatosi: {}".format(e))
            time.sleep(61)
        else:
            time.sleep(30)

# ============ HAFTALIK HISOBOT — SHANBA 20:00 ============
def haftalik_yuborish():
    global shaxsiy_haftalik_oldingi_qoldiq

    while True:
        now = uz_now()
        # weekday(): 5 = Shanba
        if now.weekday() == 5 and now.hour == 20 and now.minute == 0:
            try:
                if AGRO_GURUH_ID:
                    yuborish(AGRO_GURUH_ID,
                        "💼 <b>Agro Haftalik hisobot:</b>\n\n" +
                        agro_hisobot_matni(agro_haftalik_kirimlar, agro_haftalik_chiqimlar, "Haftalik"))

                yuborish(SHAXSIY_GURUH_ID,
                    "👤 <b>Shaxsiy Haftalik hisobot:</b>\n\n" +
                    shaxsiy_hisobot_matni(shaxsiy_haftalik_kirimlar, shaxsiy_haftalik_chiqimlar, shaxsiy_haftalik_oldingi_qoldiq, "Haftalik"))

                sh_k = sum(k["summa"] for k in shaxsiy_haftalik_kirimlar)
                sh_ch = sum(c["summa"] for c in shaxsiy_haftalik_chiqimlar)
                shaxsiy_haftalik_oldingi_qoldiq = shaxsiy_haftalik_oldingi_qoldiq + sh_k - sh_ch

                agro_haftalik_kirimlar.clear()
                agro_haftalik_chiqimlar.clear()
                shaxsiy_haftalik_kirimlar.clear()
                shaxsiy_haftalik_chiqimlar.clear()

            except Exception as e:
                print("Haftalik yuborish xatosi: {}".format(e))
            time.sleep(61)
        else:
            time.sleep(30)

# ============ OYLIK HISOBOT — OY OXIRIDAN 2 KUN OLDIN 20:00 ============
def oylik_yuborish():
    global shaxsiy_oylik_oldingi_qoldiq

    while True:
        now = uz_now()
        oxirgi_kun = calendar.monthrange(now.year, now.month)[1]
        yuborish_kuni = oxirgi_kun - 2

        if now.day == yuborish_kuni and now.hour == 20 and now.minute == 0:
            try:
                if AGRO_GURUH_ID:
                    yuborish(AGRO_GURUH_ID,
                        "💼 <b>Agro Oylik hisobot:</b>\n\n" +
                        agro_hisobot_matni(agro_oylik_kirimlar, agro_oylik_chiqimlar, "Oylik"))

                yuborish(SHAXSIY_GURUH_ID,
                    "👤 <b>Shaxsiy Oylik hisobot:</b>\n\n" +
                    shaxsiy_hisobot_matni(shaxsiy_oylik_kirimlar, shaxsiy_oylik_chiqimlar, shaxsiy_oylik_oldingi_qoldiq, "Oylik"))

                sh_k = sum(k["summa"] for k in shaxsiy_oylik_kirimlar)
                sh_ch = sum(c["summa"] for c in shaxsiy_oylik_chiqimlar)
                shaxsiy_oylik_oldingi_qoldiq = shaxsiy_oylik_oldingi_qoldiq + sh_k - sh_ch

                agro_oylik_kirimlar.clear()
                agro_oylik_chiqimlar.clear()
                shaxsiy_oylik_kirimlar.clear()
                shaxsiy_oylik_chiqimlar.clear()

            except Exception as e:
                print("Oylik yuborish xatosi: {}".format(e))
            time.sleep(61)
        else:
            time.sleep(30)

# ============ HTTP SERVER ============
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("✅ Agro Xisobot bot ishlayapti!".encode())
    def log_message(self, *args):
        pass

# ============ ISHGA TUSHIRISH ============
if __name__ == "__main__":
    threading.Thread(target=kunlik_yuborish, daemon=True).start()
    threading.Thread(target=haftalik_yuborish, daemon=True).start()
    threading.Thread(target=oylik_yuborish, daemon=True).start()
    threading.Thread(target=polling, daemon=True).start()
    print("✅ Bot ishga tushdi!")
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), Handler).serve_forever()
