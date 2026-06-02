
import os
import json
import urllib.request
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import calendar

TOKEN = os.environ.get("SHAXSIY_TOKEN")
GURUH_ID = os.environ.get("-1003966538627")
YUBORISH_SOAT = 15

ma_lumot = {"daromadlar": [], "xarajatlar": [], "oldingi_qoldiq": 0}
holat = {}
oylik = {"daromadlar": [], "xarajatlar": []}
haftalik = {"daromadlar": [], "xarajatlar": []}
byudjet = {}  # {"Oziq-ovqat": 500000, ...}

DAROMAD_TURLARI = [
    "💼 Oylik maosh",
    "📢 Reklamadan",
    "🔧 Qo'shimcha ishlardan",
    "💡 Boshqa"
]

XARAJAT_KATEGORIYALARI = [
    "🍔 Oziq-ovqat",
    "🚗 Transport",
    "🏠 Kommunal",
    "👕 Kiyim-kechak",
    "💊 Sog'liq",
    "🎓 Ta'lim",
    "🎮 Ko'ngil ochar",
    "📦 Boshqa"
]


def formatlash(summa):
    return "{:,}".format(int(summa)).replace(",", " ")


def api(method, data):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"API xato: {e}")


def yuborish(chat_id, matn, keyboard=None):
    data = {"chat_id": chat_id, "text": matn, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True}
    api("sendMessage", data)


def asosiy_menu(chat_id):
    yuborish(chat_id, "📲 <b>Asosiy menyu</b>\nNima qilmoqchisiz?", [
        ["💰 Daromad", "💸 Xarajat"],
        ["💼 Oldingi qoldiq", "📊 Kunlik xisobot"],
        ["📅 Oylik xisobot", "📆 Haftalik xisobot"],
        ["🎯 Byudjet belgilash", "📋 Byudjet holati"]
    ])


# ─── HISOBOT MATNLARI ────────────────────────────────────────────────────────

def kunlik_xisobot_matni():
    bugun = datetime.now().strftime("%d.%m.%Y")
    jami_daromad = sum(s for s, _ in ma_lumot["daromadlar"])
    jami_xarajat = sum(s for s, _ in ma_lumot["xarajatlar"])
    balans = ma_lumot["oldingi_qoldiq"] + jami_daromad
    qoldi = balans - jami_xarajat

    daromad_text = "\n".join(
        f"  +{formatlash(s)} — {i}" for s, i in ma_lumot["daromadlar"]
    )
    xarajat_text = "\n".join(
        f"  -{formatlash(s)} — {i}" for s, i in ma_lumot["xarajatlar"]
    )

    x = f"📅 <b>{bugun} — Kunlik xisobot</b>\n"
    if daromad_text:
        x += f"\n💰 <b>Daromadlar:</b>\n{daromad_text}\n"
    if xarajat_text:
        x += f"\n💸 <b>Xarajatlar:</b>\n{xarajat_text}\n"
    x += (
        f"\n━━━━━━━━━━━━━━━━\n"
        f"Jami xarajat: <b>{formatlash(jami_xarajat)}</b>\n"
        f"Balans: <b>{formatlash(balans)}</b>\n"
        f"Qoldi: <b>{formatlash(qoldi)}</b>"
    )
    return x, qoldi


def oylik_xisobot_matni():
    oy = datetime.now().strftime("%B %Y")
    jami_daromad = sum(s for s, _ in oylik["daromadlar"])
    jami_xarajat = sum(s for s, _ in oylik["xarajatlar"])
    qoldi = jami_daromad - jami_xarajat

    # Kategoriya bo'yicha tahlil
    kategoriya = {}
    for summa, izoh in oylik["xarajatlar"]:
        kat = izoh.split(" — ")[0] if " — " in izoh else "📦 Boshqa"
        kategoriya[kat] = kategoriya.get(kat, 0) + summa

    daromad_text = "\n".join(
        f"  +{formatlash(s)} — {i}" for s, i in oylik["daromadlar"]
    )
    xarajat_text = "\n".join(
        f"  -{formatlash(s)} — {i}" for s, i in oylik["xarajatlar"]
    )
    kat_text = "\n".join(
        f"  {k}: {formatlash(v)}" for k, v in sorted(
            kategoriya.items(), key=lambda x: x[1], reverse=True
        )
    )

    x = f"📅 <b>{oy} — Oylik xisobot</b>\n"
    if daromad_text:
        x += f"\n💰 <b>Daromadlar:</b>\n{daromad_text}\n"
    if xarajat_text:
        x += f"\n💸 <b>Xarajatlar:</b>\n{xarajat_text}\n"
    if kat_text:
        x += f"\n📊 <b>Kategoriya tahlili:</b>\n{kat_text}\n"
    x += (
        f"\n━━━━━━━━━━━━━━━━\n"
        f"Jami daromad: <b>{formatlash(jami_daromad)}</b>\n"
        f"Jami xarajat: <b>{formatlash(jami_xarajat)}</b>\n"
        f"Qoldi: <b>{formatlash(qoldi)}</b>"
    )
    return x


def haftalik_xisobot_matni():
    hafta_boshi = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%d.%m")
    hafta_oxiri = datetime.now().strftime("%d.%m.%Y")
    jami_daromad = sum(s for s, _ in haftalik["daromadlar"])
    jami_xarajat = sum(s for s, _ in haftalik["xarajatlar"])
    qoldi = jami_daromad - jami_xarajat

    # Kategoriya bo'yicha tahlil
    kategoriya = {}
    for summa, izoh in haftalik["xarajatlar"]:
        kat = izoh.split(" — ")[0] if " — " in izoh else "📦 Boshqa"
        kategoriya[kat] = kategoriya.get(kat, 0) + summa

    kat_text = "\n".join(
        f"  {k}: {formatlash(v)}" for k, v in sorted(
            kategoriya.items(), key=lambda x: x[1], reverse=True
        )
    )

    x = f"📆 <b>{hafta_boshi}–{hafta_oxiri} — Haftalik xisobot</b>\n"
    if kat_text:
        x += f"\n📊 <b>Kategoriya tahlili:</b>\n{kat_text}\n"
    x += (
        f"\n━━━━━━━━━━━━━━━━\n"
        f"Jami daromad: <b>{formatlash(jami_daromad)}</b>\n"
        f"Jami xarajat: <b>{formatlash(jami_xarajat)}</b>\n"
        f"Qoldi: <b>{formatlash(qoldi)}</b>"
    )
    return x


def byudjet_holati_matni():
    if not byudjet:
        return "🎯 Hozircha byudjet belgilanmagan.\n'🎯 Byudjet belgilash' tugmasini bosing."

    # Oylik xarajatlarni kategoriya bo'yicha yig'ish
    sarflangan = {}
    for summa, izoh in oylik["xarajatlar"]:
        kat = izoh.split(" — ")[0] if " — " in izoh else "📦 Boshqa"
        sarflangan[kat] = sarflangan.get(kat, 0) + summa

    x = "📋 <b>Byudjet holati</b>\n\n"
    for kat, limit in byudjet.items():
        sarf = sarflangan.get(kat, 0)
        qoldi = limit - sarf
        foiz = int((sarf / limit) * 100) if limit > 0 else 0
        # Progress bar
        to_ldirilgan = min(foiz // 10, 10)
        bar = "█" * to_ldirilgan + "░" * (10 - to_ldirilgan)
        status = "🔴" if foiz >= 90 else ("🟡" if foiz >= 70 else "🟢")
        x += (
            f"{status} <b>{kat}</b>\n"
            f"  [{bar}] {foiz}%\n"
            f"  Sarflangan: {formatlash(sarf)} / {formatlash(limit)}\n"
            f"  Qoldi: {formatlash(qoldi)}\n\n"
        )
    return x


def byudjet_ogohlantirish(chat_id, kategoriya_nomi):
    """Byudjet limitiga yaqinlashganda yoki oshganda ogohlantirish."""
    if kategoriya_nomi not in byudjet:
        return
    limit = byudjet[kategoriya_nomi]
    sarf = sum(
        s for s, izoh in oylik["xarajatlar"]
        if izoh.split(" — ")[0] == kategoriya_nomi
    )
    foiz = int((sarf / limit) * 100) if limit > 0 else 0
    if foiz >= 100:
        yuborish(
            chat_id,
            f"🔴 <b>Byudjet oshdi!</b>\n{kategoriya_nomi} uchun "
            f"belgilangan {formatlash(limit)} so'm limitdan oshib ketdi!\n"
            f"Sarflangan: {formatlash(sarf)}"
        )
    elif foiz >= 80:
        yuborish(
            chat_id,
            f"🟡 <b>Diqqat!</b>\n{kategoriya_nomi} byudjetining "
            f"{foiz}% sarflandi.\nQoldi: {formatlash(limit - sarf)}"
        )


# ─── XABAR QAYTA ISHLASH ─────────────────────────────────────────────────────

def xabar_qayta_ishlash(chat_id, matn):
    if matn in ["/start", "/menu"]:
        holat[chat_id] = ""
        yuborish(chat_id, "👋 <b>Xush kelibsiz!</b>\nShaxsiy moliya botiga xush kelibsiz.")
        asosiy_menu(chat_id)
        return

    h = holat.get(chat_id, "")

    # ── ASOSIY TUGMALAR ──────────────────────────────────────────────────────
    if matn == "💰 Daromad":
        holat[chat_id] = "daromad_tur"
        keyboard = [[t] for t in DAROMAD_TURLARI] + [["🔙 Orqaga"]]
        yuborish(chat_id, "Daromad turini tanlang:", keyboard)

    elif matn == "💸 Xarajat":
        holat[chat_id] = "xarajat_kategoriya"
        keyboard = [[k] for k in XARAJAT_KATEGORIYALARI] + [["🔙 Orqaga"]]
        yuborish(chat_id, "Xarajat kategoriyasini tanlang:", keyboard)

    elif matn == "💼 Oldingi qoldiq":
        holat[chat_id] = "qoldiq_summa"
        yuborish(chat_id, "Oldingi qoldiq summasini kiriting (so'm):")

    elif matn == "📊 Kunlik xisobot":
        x, _ = kunlik_xisobot_matni()
        yuborish(chat_id, x)
        asosiy_menu(chat_id)

    elif matn == "📅 Oylik xisobot":
        x = oylik_xisobot_matni()
        yuborish(chat_id, x)
        asosiy_menu(chat_id)

    elif matn == "📆 Haftalik xisobot":
        x = haftalik_xisobot_matni()
        yuborish(chat_id, x)
        asosiy_menu(chat_id)

    elif matn == "🎯 Byudjet belgilash":
        holat[chat_id] = "byudjet_kategoriya"
        keyboard = [[k] for k in XARAJAT_KATEGORIYALARI] + [["🔙 Orqaga"]]
        yuborish(chat_id, "Byudjet belgilamoqchi bo'lgan kategoriyani tanlang:", keyboard)

    elif matn == "📋 Byudjet holati":
        x = byudjet_holati_matni()
        yuborish(chat_id, x)
        asosiy_menu(chat_id)

    elif matn == "🔙 Orqaga":
        holat[chat_id] = ""
        asosiy_menu(chat_id)

    # ── DAROMAD OQIMI ────────────────────────────────────────────────────────
    elif h == "daromad_tur":
        if matn in DAROMAD_TURLARI:
            holat[chat_id + "_tur"] = matn
            holat[chat_id] = "daromad_summa"
            yuborish(chat_id, f"{matn} — summani kiriting (so'm):")
        else:
            yuborish(chat_id, "⚠️ Tugmalardan birini tanlang!")

    elif h == "daromad_summa":
        try:
            summa = int(matn.replace(" ", "").replace(",", ""))
            tur = holat.get(chat_id + "_tur", "Daromad")
            ma_lumot["daromadlar"].append((summa, tur))
            oylik["daromadlar"].append((summa, tur))
            haftalik["daromadlar"].append((summa, tur))
            holat[chat_id] = ""
            yuborish(chat_id, f"✅ <b>+{formatlash(summa)} so'm</b> qo'shildi\n{tur}")
            asosiy_menu(chat_id)
        except Exception:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")

    # ── XARAJAT OQIMI ────────────────────────────────────────────────────────
    elif h == "xarajat_kategoriya":
        if matn in XARAJAT_KATEGORIYALARI:
            holat[chat_id + "_kat"] = matn
            holat[chat_id] = "xarajat_summa"
            yuborish(chat_id, f"{matn} — summani kiriting (so'm):")
        else:
            yuborish(chat_id, "⚠️ Tugmalardan birini tanlang!")

    elif h == "xarajat_summa":
        try:
            holat[chat_id + "_summa"] = int(matn.replace(" ", "").replace(",", ""))
            holat[chat_id] = "xarajat_izoh"
            yuborish(chat_id, "Izohini kiriting (masalan: 'Tushlik'):")
        except Exception:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")

    elif h == "xarajat_izoh":
        summa = holat.get(chat_id + "_summa", 0)
        kat = holat.get(chat_id + "_kat", "📦 Boshqa")
        yozuv = f"{kat} — {matn}"
        ma_lumot["xarajatlar"].append((summa, yozuv))
        oylik["xarajatlar"].append((summa, yozuv))
        haftalik["xarajatlar"].append((summa, yozuv))
        holat[chat_id] = ""
        yuborish(chat_id, f"✅ <b>-{formatlash(summa)} so'm</b> yozildi\n{yozuv}")
        byudjet_ogohlantirish(chat_id, kat)
        asosiy_menu(chat_id)

    # ── QOLDIQ OQIMI ─────────────────────────────────────────────────────────
    elif h == "qoldiq_summa":
        try:
            ma_lumot["oldingi_qoldiq"] = int(matn.replace(" ", "").replace(",", ""))
            holat[chat_id] = ""
            yuborish(
                chat_id,
                f"✅ Oldingi qoldiq: <b>{formatlash(ma_lumot['oldingi_qoldiq'])} so'm</b> saqlandi!"
            )
            asosiy_menu(chat_id)
        except Exception:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")

    # ── BYUDJET BELGILASH OQIMI ───────────────────────────────────────────────
    elif h == "byudjet_kategoriya":
        if matn in XARAJAT_KATEGORIYALARI:
            holat[chat_id + "_byudjet_kat"] = matn
            holat[chat_id] = "byudjet_summa"
            mavjud = byudjet.get(matn, 0)
            xabar = f"{matn} uchun oylik byudjet limitini kiriting (so'm):"
            if mavjud:
                xabar += f"\n(Hozirgi limit: {formatlash(mavjud)} so'm)"
            yuborish(chat_id, xabar)
        else:
            yuborish(chat_id, "⚠️ Tugmalardan birini tanlang!")

    elif h == "byudjet_summa":
        try:
            summa = int(matn.replace(" ", "").replace(",", ""))
            kat = holat.get(chat_id + "_byudjet_kat", "📦 Boshqa")
            byudjet[kat] = summa
            holat[chat_id] = ""
            yuborish(
                chat_id,
                f"✅ <b>{kat}</b> uchun oylik byudjet:\n<b>{formatlash(summa)} so'm</b>"
            )
            asosiy_menu(chat_id)
        except Exception:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")

    else:
        asosiy_menu(chat_id)


# ─── POLLING ─────────────────────────────────────────────────────────────────

def polling():
    offset = 0
    while True:
        try:
            url = (
                f"https://api.telegram.org/bot{TOKEN}"
                f"/getUpdates?offset={offset}&timeout=30"
            )
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
            print(f"Xato: {e}")
            time.sleep(5)


# ─── AVTOMATIK YUBORISH ───────────────────────────────────────────────────────

def kunlik_yuborish():
    while True:
        now = datetime.now()
        if now.hour == YUBORISH_SOAT and now.minute == 0:
            try:
                x, qoldi = kunlik_xisobot_matni()
                yuborish(GURUH_ID, x)
                ma_lumot["oldingi_qoldiq"] = qoldi
                ma_lumot["daromadlar"] = []
                ma_lumot["xarajatlar"] = []

                # Hafta oxiri — dushanba kuni haftalik hisobot
                if now.weekday() == 0:
                    yuborish(GURUH_ID, haftalik_xisobot_matni())
                    haftalik["daromadlar"] = []
                    haftalik["xarajatlar"] = []

                # Oy oxiri — oylik hisobot
                oxirgi_kun = calendar.monthrange(now.year, now.month)[1]
                if now.day == oxirgi_kun:
                    oy_x = oylik_xisobot_matni()
                    yuborish(GURUH_ID, f"📅 <b>OY YAKUNLANDI!</b>\n\n{oy_x}")
                    oylik["daromadlar"] = []
                    oylik["xarajatlar"] = []
            except Exception as e:
                print(f"Yuborish xatosi: {e}")
        time.sleep(60)


# ─── HTTP SERVER ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Shaxsiy moliya boti ishlayapti! 🤖".encode())

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Bot ishga tushdi...")
    threading.Thread(target=kunlik_yuborish, daemon=True).start()
    threading.Thread(target=polling, daemon=True).start()
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), Handler).serve_forever()
