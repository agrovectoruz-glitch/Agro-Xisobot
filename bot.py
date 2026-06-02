import os
import json
import urllib.request
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

TOKEN = os.environ.get("TOKEN")
GURUH_ID = os.environ.get("-4911960051")
YUBORISH_SOAT = int(os.environ.get("YUBORISH_SOAT", "15"))

# ============ MA'LUMOTLAR ============
# Agro Ombor
ombor = []  # {id, uskuna_turi, uskuna_nomi, traktor, soni, qoldiq, sana}
sotuvlar = []  # {id, ombor_id, ismi, telefon, viloyat, tuman, uskuna_nomi, soni, sana}

# Agro Xarajat
agro_kirimlar = []   # {summa, izoh, tur, sana}
agro_chiqimlar = []  # {summa, izoh, sana}

# Shaxsiy Xarajat
shaxsiy_kirimlar = []   # {summa, izoh, tur, sana}
shaxsiy_chiqimlar = []  # {summa, izoh, sana}
shaxsiy_oldingi_qoldiq = 0

holat = {}
temp = {}

# ============ YORDAMCHI ============
def formatlash(summa):
    return "{:,}".format(int(summa)).replace(",", " ")

def api(method, data):
    url = "https://api.telegram.org/bot{}/{}".format(TOKEN, method)
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print("API xato: {}".format(e))

def yuborish(chat_id, matn, keyboard=None, inline=None):
    data = {"chat_id": chat_id, "text": matn, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True}
    elif inline:
        data["reply_markup"] = {"inline_keyboard": inline}
    api("sendMessage", data)

def callback_javob(callback_id):
    api("answerCallbackQuery", {"callback_query_id": callback_id})

# ============ MENYULAR ============
def asosiy_menu(chat_id):
    holat[chat_id] = ""
    yuborish(chat_id, "📋 Asosiy menyu:", [
        ["📦 Agro Ombor", "💼 Agro Xarajat"],
        ["👤 Shaxsiy Xarajat"]
    ])

def agro_ombor_menu(chat_id):
    holat[chat_id] = "agro_ombor"
    yuborish(chat_id, "📦 Agro Ombor:", [
        ["➕ Mahsulot qo'shish", "✅ Sotildi"],
        ["📊 Hisobot", "🏠 Bosh menyu"]
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

# ============ AGRO OMBOR ============
def ombor_qoshish_boshlash(chat_id):
    holat[chat_id] = "ombor_tur"
    temp[chat_id] = {}
    yuborish(chat_id, "Uskuna turini tanlang:", [
        ["🤖 Avtopilot", "🔧 Boshqa"],
        ["🔙 Orqaga"]
    ])

def ombor_hisobot(chat_id):
    if not ombor:
        yuborish(chat_id, "📦 Ombor bo'sh!")
        agro_ombor_menu(chat_id)
        return

    matn = "📦 <b>Agro Ombor holati:</b>\n\n"
    for m in ombor:
        matn += "🔹 <b>{}</b> ({})\n".format(m["uskuna_nomi"], m["traktor"])
        matn += "   Kirim: {} | Qoldiq: {}\n\n".format(
            formatlash(m["soni"]), formatlash(m["qoldiq"]))

    yuborish(chat_id, matn)

    # Sotuv hisoboti
    if sotuvlar:
        bugun = datetime.now().strftime("%m.%Y")
        oylik = [s for s in sotuvlar if s["sana"].endswith(bugun)]
        matn2 = "📊 <b>Bu oy sotuvlar ({}):</b>\n\n".format(bugun)
        viloyatlar = {}
        for s in oylik:
            v = s["viloyat"]
            viloyatlar[v] = viloyatlar.get(v, 0) + s["soni"]
        for v, son in viloyatlar.items():
            matn2 += "📍 {}: {} ta\n".format(v, son)
        matn2 += "\n<b>Jami: {} ta</b>".format(sum(s["soni"] for s in oylik))
        yuborish(chat_id, matn2)

    agro_ombor_menu(chat_id)

def sotildi_boshlash(chat_id):
    if not ombor:
        yuborish(chat_id, "⚠️ Ombor bo'sh! Avval mahsulot qo'shing.")
        agro_ombor_menu(chat_id)
        return
    holat[chat_id] = "sotildi_uskuna"
    temp[chat_id] = {}
    # Inline tugmalar bilan ombordagi mahsulotlar
    inline = []
    for m in ombor:
        if m["qoldiq"] > 0:
            inline.append([{"text": "📦 {} — {} ta qoldiq".format(
                m["uskuna_nomi"], int(m["qoldiq"])),
                "callback_data": "ombor_{}".format(m["id"])}])
    if not inline:
        yuborish(chat_id, "⚠️ Omborda sotilishi mumkin bo'lgan mahsulot yo'q!")
        agro_ombor_menu(chat_id)
        return
    yuborish(chat_id, "Qaysi mahsulot sotildi?", inline=inline)

# ============ AGRO XARAJAT ============
def agro_kirim_hisobot(chat_id):
    jami = sum(k["summa"] for k in agro_kirimlar)
    jami_ch = sum(c["summa"] for c in agro_chiqimlar)
    qoldiq = jami - jami_ch

    matn = "💼 <b>Agro Xarajat Balansi:</b>\n\n"

    if agro_kirimlar:
        matn += "💰 <b>Daromadlar:</b>\n"
        for k in agro_kirimlar[-10:]:
            matn += "+{} {} ({})\n".format(formatlash(k["summa"]), k["izoh"], k["tur"])
        matn += "\n"

    if agro_chiqimlar:
        matn += "💸 <b>Xarajatlar:</b>\n"
        for c in agro_chiqimlar[-10:]:
            matn += "-{} {}\n".format(formatlash(c["summa"]), c["izoh"])
        matn += "\n"

    matn += "━━━━━━━━━━━━━━━\n"
    matn += "💰 Jami daromad: <b>{}</b>\n".format(formatlash(jami))
    matn += "💸 Jami xarajat: <b>{}</b>\n".format(formatlash(jami_ch))
    matn += "✅ Qoldiq: <b>{}</b>".format(formatlash(qoldiq))

    yuborish(chat_id, matn)
    agro_xarajat_menu(chat_id)

# ============ SHAXSIY XARAJAT ============
def shaxsiy_hisobot(chat_id):
    global shaxsiy_oldingi_qoldiq
    jami_kirim = sum(k["summa"] for k in shaxsiy_kirimlar)
    jami_chiqim = sum(c["summa"] for c in shaxsiy_chiqimlar)
    balans = shaxsiy_oldingi_qoldiq + jami_kirim
    qoldiq = balans - jami_chiqim

    bugun = datetime.now().strftime("%d.%m.%Y")
    matn = "👤 <b>Shaxsiy Xarajat — {}</b>\n\n".format(bugun)

    if shaxsiy_kirimlar:
        matn += "💰 <b>Daromadlar:</b>\n"
        for k in shaxsiy_kirimlar[-10:]:
            matn += "+{} {} ({})\n".format(formatlash(k["summa"]), k["izoh"], k["tur"])
        matn += "\n"

    if shaxsiy_chiqimlar:
        matn += "💸 <b>Xarajatlar:</b>\n"
        for c in shaxsiy_chiqimlar[-10:]:
            matn += "-{} {}\n".format(formatlash(c["summa"]), c["izoh"])
        matn += "\n"

    matn += "━━━━━━━━━━━━━━━\n"
    matn += "💰 Jami daromad: <b>{}</b>\n".format(formatlash(jami_kirim))
    matn += "💸 Jami xarajat: <b>{}</b>\n".format(formatlash(jami_chiqim))
    matn += "📊 Balans: <b>{}</b>\n".format(formatlash(balans))
    matn += "✅ Qoldiq: <b>{}</b>".format(formatlash(qoldiq))

    yuborish(chat_id, matn)
    shaxsiy_menu(chat_id)

# ============ XABAR QAYTA ISHLASH ============
def xabar_qayta_ishlash(chat_id, matn):
    global shaxsiy_oldingi_qoldiq

    if matn in ["/start", "/menu"]:
        asosiy_menu(chat_id)
        return

    h = holat.get(chat_id, "")

    # === ASOSIY MENYU ===
    if matn == "📦 Agro Ombor":
        agro_ombor_menu(chat_id)
        return
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
        if h.startswith("ombor"):
            agro_ombor_menu(chat_id)
        elif h.startswith("agro"):
            agro_xarajat_menu(chat_id)
        elif h.startswith("shaxsiy"):
            shaxsiy_menu(chat_id)
        else:
            asosiy_menu(chat_id)
        return

    # === AGRO OMBOR MENYUSI ===
    if h == "agro_ombor":
        if matn == "➕ Mahsulot qo'shish":
            ombor_qoshish_boshlash(chat_id)
        elif matn == "✅ Sotildi":
            sotildi_boshlash(chat_id)
        elif matn == "📊 Hisobot":
            ombor_hisobot(chat_id)
        return

    # === MAHSULOT QO'SHISH ===
    if h == "ombor_tur":
        if matn == "🤖 Avtopilot":
            temp[chat_id]["uskuna_turi"] = "Avtopilot"
            holat[chat_id] = "ombor_nomi"
            yuborish(chat_id, "Avtopilot nomini kiriting (masalan: Autopilot X1):")
        elif matn == "🔧 Boshqa":
            temp[chat_id]["uskuna_turi"] = "Boshqa"
            holat[chat_id] = "ombor_nomi"
            yuborish(chat_id, "Uskuna nomini kiriting:")
        return

    if h == "ombor_nomi":
        temp[chat_id]["uskuna_nomi"] = matn
        holat[chat_id] = "ombor_traktor"
        yuborish(chat_id, "Traktor markasini kiriting (masalan: New Holland):")
        return

    if h == "ombor_traktor":
        temp[chat_id]["traktor"] = matn
        holat[chat_id] = "ombor_soni"
        yuborish(chat_id, "Sonini kiriting:")
        return

    if h == "ombor_soni":
        try:
            soni = int(matn.replace(" ", ""))
            t = temp[chat_id]
            # Mavjud mahsulot bormi?
            mavjud = None
            for m in ombor:
                if m["uskuna_nomi"].lower() == t["uskuna_nomi"].lower():
                    mavjud = m
                    break
            if mavjud:
                mavjud["soni"] += soni
                mavjud["qoldiq"] += soni
                yuborish(chat_id, "✅ <b>{}</b> ga {} ta qo'shildi!\nJami qoldiq: {} ta".format(
                    mavjud["uskuna_nomi"], soni, int(mavjud["qoldiq"])))
            else:
                yangi_id = len(ombor) + 1
                ombor.append({
                    "id": yangi_id,
                    "uskuna_turi": t["uskuna_turi"],
                    "uskuna_nomi": t["uskuna_nomi"],
                    "traktor": t["traktor"],
                    "soni": soni,
                    "qoldiq": soni,
                    "sana": datetime.now().strftime("%d.%m.%Y")
                })
                yuborish(chat_id, "✅ Mahsulot qo'shildi!\n📦 <b>{}</b>\n🚜 {}\nSoni: {} ta".format(
                    t["uskuna_nomi"], t["traktor"], soni))
            holat[chat_id] = "agro_ombor"
            agro_ombor_menu(chat_id)
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
        return

    # === SOTILDI ===
    if h == "sotildi_ismi":
        temp[chat_id]["ismi"] = matn
        holat[chat_id] = "sotildi_telefon"
        yuborish(chat_id, "Telefon raqamini kiriting:")
        return

    if h == "sotildi_telefon":
        temp[chat_id]["telefon"] = matn
        holat[chat_id] = "sotildi_viloyat"
        yuborish(chat_id, "Viloyatini kiriting:")
        return

    if h == "sotildi_viloyat":
        temp[chat_id]["viloyat"] = matn
        holat[chat_id] = "sotildi_tuman"
        yuborish(chat_id, "Tumanini kiriting:")
        return

    if h == "sotildi_tuman":
        temp[chat_id]["tuman"] = matn
        holat[chat_id] = "sotildi_soni"
        yuborish(chat_id, "Nechta sotildi?")
        return

    if h == "sotildi_soni":
        try:
            soni = int(matn.replace(" ", ""))
            ombor_id = temp[chat_id]["ombor_id"]
            mahsulot = next((m for m in ombor if m["id"] == ombor_id), None)
            if not mahsulot:
                yuborish(chat_id, "⚠️ Mahsulot topilmadi!")
                agro_ombor_menu(chat_id)
                return
            if soni > mahsulot["qoldiq"]:
                yuborish(chat_id, "⚠️ Qoldiqda faqat {} ta bor!".format(int(mahsulot["qoldiq"])))
                return
            temp[chat_id]["soni"] = soni
            holat[chat_id] = "sotildi_sana"
            yuborish(chat_id, "Sotilgan sanani kiriting (masalan: 03.06.2026):")
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
        return

    if h == "sotildi_sana":
        t = temp[chat_id]
        ombor_id = t["ombor_id"]
        mahsulot = next((m for m in ombor if m["id"] == ombor_id), None)
        soni = t["soni"]

        # Qoldiqdan ayir
        mahsulot["qoldiq"] -= soni

        sotuv = {
            "id": len(sotuvlar) + 1,
            "ombor_id": ombor_id,
            "ismi": t["ismi"],
            "telefon": t["telefon"],
            "viloyat": t["viloyat"],
            "tuman": t["tuman"],
            "uskuna_nomi": mahsulot["uskuna_nomi"],
            "traktor": mahsulot["traktor"],
            "soni": soni,
            "sana": matn
        }
        sotuvlar.append(sotuv)

        # Guruhga xabar
        guruh_matn = (
            "✅ <b>Yangi sotuv!</b>\n\n"
            "👤 Ismi: {}\n"
            "📞 Telefon: {}\n"
            "📍 Viloyat: {}\n"
            "🏘 Tuman: {}\n"
            "📦 Uskuna: {}\n"
            "🚜 Traktor: {}\n"
            "🔢 Soni: {} ta\n"
            "📅 Sana: {}\n"
            "📦 Qoldiq: {} ta"
        ).format(
            t["ismi"], t["telefon"], t["viloyat"], t["tuman"],
            mahsulot["uskuna_nomi"], mahsulot["traktor"],
            soni, matn, int(mahsulot["qoldiq"])
        )
        if GURUH_ID:
            yuborish(GURUH_ID, guruh_matn)

        yuborish(chat_id, guruh_matn)
        holat[chat_id] = "agro_ombor"
        agro_ombor_menu(chat_id)
        return

    # === AGRO XARAJAT MENYUSI ===
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
            agro_kirim_hisobot(chat_id)
        return

    if h == "agro_kirim_tur":
        if matn == "🏦 Rahbardan":
            temp[chat_id] = {"tur": "Rahbardan"}
            holat[chat_id] = "agro_kirim_summa"
            yuborish(chat_id, "Summani kiriting:")
        elif matn == "📦 Zakladdan":
            temp[chat_id] = {"tur": "Zakladdan"}
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
            "sana": datetime.now().strftime("%d.%m.%Y")
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
            "sana": datetime.now().strftime("%d.%m.%Y")
        })
        yuborish(chat_id, "✅ -{} {} saqlandi!".format(formatlash(t.get("summa", 0)), matn))
        agro_xarajat_menu(chat_id)
        return

    # === SHAXSIY XARAJAT MENYUSI ===
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
            shaxsiy_hisobot(chat_id)
        return

    if h == "shaxsiy_kirim_tur":
        if matn in ["💼 Oylik", "📢 Reklama", "🔖 Boshqa"]:
            temp[chat_id] = {"tur": matn}
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
            "sana": datetime.now().strftime("%d.%m.%Y")
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
            "sana": datetime.now().strftime("%d.%m.%Y")
        })
        yuborish(chat_id, "✅ -{} {} saqlandi!".format(formatlash(t.get("summa", 0)), matn))
        shaxsiy_menu(chat_id)
        return

    # Default
    asosiy_menu(chat_id)

def callback_qayta_ishlash(chat_id, data, callback_id):
    callback_javob(callback_id)

    if data.startswith("ombor_"):
        ombor_id = int(data.split("_")[1])
        mahsulot = next((m for m in ombor if m["id"] == ombor_id), None)
        if mahsulot:
            temp[chat_id] = {"ombor_id": ombor_id}
            holat[chat_id] = "sotildi_ismi"
            yuborish(chat_id,
                "📦 <b>{}</b> tanlandi (Qoldiq: {} ta)\n\nMijoz ismini kiriting:".format(
                    mahsulot["uskuna_nomi"], int(mahsulot["qoldiq"])),
                keyboard=[["🔙 Orqaga"]])

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
                # Callback
                if "callback_query" in u:
                    cq = u["callback_query"]
                    chat_id = str(cq["message"]["chat"]["id"])
                    data = cq.get("data", "")
                    callback_id = cq["id"]
                    callback_qayta_ishlash(chat_id, data, callback_id)
                    continue
                msg = u.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                matn = msg.get("text", "")
                if chat_id and matn:
                    xabar_qayta_ishlash(chat_id, matn)
        except Exception as e:
            print("Xato: {}".format(e))
            time.sleep(5)

def kunlik_yuborish():
    while True:
        now = datetime.now()
        if now.hour == YUBORISH_SOAT and now.minute == 0:
            try:
                if GURUH_ID:
                    # Agro ombor hisoboti
                    if ombor:
                        matn = "📦 <b>Kunlik Agro Ombor hisoboti:</b>\n\n"
                        for m in ombor:
                            matn += "🔹 {} — Qoldiq: {} ta\n".format(
                                m["uskuna_nomi"], int(m["qoldiq"]))
                        yuborish(GURUH_ID, matn)
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
