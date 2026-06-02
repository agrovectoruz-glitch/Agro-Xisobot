import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

TOKEN = os.environ.get("TOKEN")
AGRO_GURUH_ID = os.environ.get("GURUH_ID")      # -4911960051
SHAXSIY_GURUH_ID = "-1003966538627"

UZ_TZ = timezone(timedelta(hours=5))  # O'zbekiston vaqti UTC+5

# ============ MA'LUMOTLAR ============
agro_kirimlar = []   # {summa, izoh, tur, sana}
agro_chiqimlar = []  # {summa, izoh, sana}

shaxsiy_kirimlar = []   # {summa, izoh, tur, sana}
shaxsiy_chiqimlar = []  # {summa, izoh, sana}
shaxsiy_oldingi_qoldiq = 0

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
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
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
    yuborish(chat_id, "📋 Asosiy menyu:", [
        ["💼 Agro Xarajat"],
        ["👤 Shaxsiy Xarajat"]
    ])

def agro_xarajat_menu(chat_id):
    holat[chat_id] = "agro_xarajat"
    yuborish(chat_id, "💼 Agro Xarajat:", [
        ["💰 Daromad", "💸 Xarajat"],
        ["📊 Balans", "🏠 Bosh menyu"]
    ])

def shaxsiy_menu(chat_id):
    holat[chat_id] = "shaxsiy"
    yuborish(chat_id, "👤 Shaxsiy Xarajat:", [
        ["💰 Daromad", "💸 Xarajat"],
        ["📊 Balans", "🏠 Bosh menyu"]
    ])

# ============ HISOBOTLAR ============
def agro_hisobot_matni():
    jami_kirim = sum(k["summa"] for k in agro_kirimlar)
    jami_chiqim = sum(c["summa"] for c in agro_chiqimlar)
    balans = jami_kirim
    qoldiq = jami_kirim - jami_chiqim

    bugun = uz_now().strftime("%d.%m.%Y")
    matn = "📅 {}\n\n".format(bugun)

    for k in agro_kirimlar:
        matn += "+{} {} ({})\n".format(formatlash(k["summa"]), k["izoh"], k["tur"])

    if agro_kirimlar:
        matn += "\n"

    for c in agro_chiqimlar:
        matn += "{} {}\n".format(formatlash(c["summa"]), c["izoh"])

    matn += "\nJami: {}\nBalans: {}\nQoldi: {}".format(
        formatlash(jami_chiqim), formatlash(balans), formatlash(qoldiq))
    return matn

def shaxsiy_hisobot_matni():
    global shaxsiy_oldingi_qoldiq
    jami_kirim = sum(k["summa"] for k in shaxsiy_kirimlar)
    jami_chiqim = sum(c["summa"] for c in shaxsiy_chiqimlar)
    balans = shaxsiy_oldingi_qoldiq + jami_kirim
    qoldiq = balans - jami_chiqim

    bugun = uz_now().strftime("%d.%m.%Y")
    matn = "📅 {}\n\n".format(bugun)

    for k in shaxsiy_kirimlar:
        matn += "+{} {} ({})\n".format(formatlash(k["summa"]), k["izoh"], k["tur"])

    if shaxsiy_kirimlar:
        matn += "\n"

    for c in shaxsiy_chiqimlar:
        matn += "{} {}\n".format(formatlash(c["summa"]), c["izoh"])

    matn += "\nJami: {}\nBalans: {}\nQoldi: {}".format(
        formatlash(jami_chiqim), formatlash(balans), formatlash(qoldiq))
    return matn

# ============ XABAR QAYTA ISHLASH ============
def xabar_qayta_ishlash(chat_id, matn):
    global shaxsiy_oldingi_qoldiq

    if matn in ["/start", "/menu"]:
        asosiy_menu(chat_id)
        return

    h = holat.get(chat_id, "")

    # === ASOSIY MENYU ===
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

    # === AGRO XARAJAT ===
    if h == "agro_xarajat":
        if matn == "💰 Daromad":
            holat[chat_id] = "agro_kirim_tur"
            yuborish(chat_id, "Daromad turi:", [
                ["🏦 Rahbardan", "📦 Zakladdan"],
                ["🔙 Orqaga"]
            ])
        elif matn == "💸 Xarajat":
            holat[chat_id] = "agro_chiqim_summa"
            yuborish(chat_id, "Xarajat summasini kiriting:")
        elif matn == "📊 Balans":
            yuborish(chat_id, agro_hisobot_matni())
            agro_xarajat_menu(chat_id)
        return

    if h == "agro_kirim_tur":
        if matn in ["🏦 Rahbardan", "📦 Zakladdan"]:
            tur = matn.split(" ", 1)[1]  # "Rahbardan" yoki "Zakladdan"
            temp[chat_id] = {"tur": tur}
            holat[chat_id] = "agro_kirim_summa"
            yuborish(chat_id, "Summani kiriting:")
        return

    if h == "agro_kirim_summa":
        try:
            summa = int(matn.replace(" ", "").replace(",", ""))
            temp[chat_id]["summa"] = summa
            holat[chat_id] = "agro_kirim_izoh"
            yuborish(chat_id, "Izoh kiriting:")
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
        return

    if h == "agro_kirim_izoh":
        t = temp.get(chat_id, {})
        agro_kirimlar.append({
            "summa": t.get("summa", 0),
            "izoh": matn,
            "tur": t.get("tur", ""),
            "sana": uz_now().strftime("%d.%m.%Y")
        })
        yuborish(chat_id, "✅ +{} {} ({}) saqlandi!".format(
            formatlash(t.get("summa", 0)), matn, t.get("tur", "")))
        agro_xarajat_menu(chat_id)
        return

    if h == "agro_chiqim_summa":
        try:
            temp[chat_id] = {"summa": int(matn.replace(" ", "").replace(",", ""))}
            holat[chat_id] = "agro_chiqim_izoh"
            yuborish(chat_id, "Izoh kiriting:")
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
        return

    if h == "agro_chiqim_izoh":
        t = temp.get(chat_id, {})
        agro_chiqimlar.append({
            "summa": t.get("summa", 0),
            "izoh": matn,
            "sana": uz_now().strftime("%d.%m.%Y")
        })
        yuborish(chat_id, "✅ -{} {} saqlandi!".format(formatlash(t.get("summa", 0)), matn))
        agro_xarajat_menu(chat_id)
        return

    # === SHAXSIY XARAJAT ===
    if h == "shaxsiy":
        if matn == "💰 Daromad":
            holat[chat_id] = "shaxsiy_kirim_tur"
            yuborish(chat_id, "Daromad turi:", [
                ["💼 Oylik", "📢 Reklama", "🔖 Boshqa"],
                ["🔙 Orqaga"]
            ])
        elif matn == "💸 Xarajat":
            holat[chat_id] = "shaxsiy_chiqim_summa"
            yuborish(chat_id, "Xarajat summasini kiriting:")
        elif matn == "📊 Balans":
            yuborish(chat_id, shaxsiy_hisobot_matni())
            shaxsiy_menu(chat_id)
        return

    if h == "shaxsiy_kirim_tur":
        if matn in ["💼 Oylik", "📢 Reklama", "🔖 Boshqa"]:
            tur = matn.split(" ", 1)[1]
            temp[chat_id] = {"tur": tur}
            holat[chat_id] = "shaxsiy_kirim_summa"
            yuborish(chat_id, "Summani kiriting:")
        return

    if h == "shaxsiy_kirim_summa":
        try:
            summa = int(matn.replace(" ", "").replace(",", ""))
            temp[chat_id]["summa"] = summa
            holat[chat_id] = "shaxsiy_kirim_izoh"
            yuborish(chat_id, "Izoh kiriting:")
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
        return

    if h == "shaxsiy_kirim_izoh":
        t = temp.get(chat_id, {})
        shaxsiy_kirimlar.append({
            "summa": t.get("summa", 0),
            "izoh": matn,
            "tur": t.get("tur", ""),
            "sana": uz_now().strftime("%d.%m.%Y")
        })
        yuborish(chat_id, "✅ +{} {} ({}) saqlandi!".format(
            formatlash(t.get("summa", 0)), matn, t.get("tur", "")))
        shaxsiy_menu(chat_id)
        return

    if h == "shaxsiy_chiqim_summa":
        try:
            temp[chat_id] = {"summa": int(matn.replace(" ", "").replace(",", ""))}
            holat[chat_id] = "shaxsiy_chiqim_izoh"
            yuborish(chat_id, "Izoh kiriting:")
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
        return

    if h == "shaxsiy_chiqim_izoh":
        t = temp.get(chat_id, {})
        shaxsiy_chiqimlar.append({
            "summa": t.get("summa", 0),
            "izoh": matn,
            "sana": uz_now().strftime("%d.%m.%Y")
        })
        yuborish(chat_id, "✅ -{} {} saqlandi!".format(formatlash(t.get("summa", 0)), matn))
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
            print("Xato: {}".format(e))
            time.sleep(5)

def kunlik_yuborish():
    global shaxsiy_oldingi_qoldiq, agro_kirimlar, agro_chiqimlar, shaxsiy_kirimlar, shaxsiy_chiqimlar
    while True:
        now = uz_now()
        if now.hour == 21 and now.minute == 0:
            try:
                # Agro xarajat guruhiga
                if AGRO_GURUH_ID:
                    yuborish(AGRO_GURUH_ID, "💼 <b>Agro Xarajat kunlik hisobot:</b>\n\n" + agro_hisobot_matni())

                # Shaxsiy xarajat guruhiga
                yuborish(SHAXSIY_GURUH_ID, "👤 <b>Shaxsiy Xarajat kunlik hisobot:</b>\n\n" + shaxsiy_hisobot_matni())

                # Qoldiqni yangi kunga o'tkazish
                jami_k = sum(k["summa"] for k in agro_kirimlar)
                jami_ch = sum(c["summa"] for c in agro_chiqimlar)
                agro_kirimlar = []
                agro_chiqimlar = []

                sh_k = sum(k["summa"] for k in shaxsiy_kirimlar)
                sh_ch = sum(c["summa"] for c in shaxsiy_chiqimlar)
                shaxsiy_oldingi_qoldiq = shaxsiy_oldingi_qoldiq + sh_k - sh_ch
                shaxsiy_kirimlar = []
                shaxsiy_chiqimlar = []

            except Exception as e:
                print("Yuborish xatosi: {}".format(e))
        time.sleep(60)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Agro Xisobot bot ishlayapti!".encode())
    def log_message(self, *args):
        pass

if __name__ == "__main__":
    threading.Thread(target=kunlik_yuborish, daemon=True).start()
    threading.Thread(target=polling, daemon=True).start()
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), Handler).serve_forever()
