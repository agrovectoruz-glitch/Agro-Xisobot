import os
import json
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime, time as dtime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

TOKEN = os.environ.get("TOKEN")
GURUH_ID = os.environ.get("GURUH_ID")
YUBORISH_SOAT = int(os.environ.get("YUBORISH_SOAT", "21"))
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

kunlik = {"kirimlar": [], "chiqimlar": [], "oldingi_qoldiq": 0}
holat = {}

def formatlash(summa):
    return "{:,}".format(int(summa)).replace(",", " ")

def api(method, data):
    url = f"{BASE_URL}/{method}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)

def yuborish(chat_id, matn, keyboard=None):
    data = {"chat_id": chat_id, "text": matn}
    if keyboard:
        data["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True}
    api("sendMessage", data)

def asosiy_menu(chat_id):
    yuborish(chat_id, "Nima qilmoqchisiz?", [
        ["💰 Kirim", "💸 Chiqim"],
        ["💼 Oldingi qoldiq", "📊 Xisobot ko'rish"]
    ])

def xisobot_matni():
    bugun = datetime.now().strftime("%d.%m.%Y")
    jami_kirim = sum(s for s, _ in kunlik["kirimlar"])
    jami_chiqim = sum(s for s, _ in kunlik["chiqimlar"])
    balans = kunlik["oldingi_qoldiq"] + jami_kirim
    qoldi = balans - jami_chiqim
    kirim_text = "\n".join(f"+{formatlash(s)} {i}" for s, i in kunlik["kirimlar"])
    chiqim_text = "\n".join(f"{formatlash(s)} {i}" for s, i in kunlik["chiqimlar"])
    x = f"📅 {bugun}\n"
    if kirim_text:
        x += f"\n{kirim_text}\n"
    if chiqim_text:
        x += f"\n{chiqim_text}\n"
    x += f"\nJami: {formatlash(jami_chiqim)}\nBalans: {formatlash(balans)}\nQoldi: {formatlash(qoldi)}"
    return x, qoldi

def xabar_qayta_ishlash(chat_id, matn):
    h = holat.get(chat_id, "")
    
    if matn == "💰 Kirim":
        holat[chat_id] = "kirim_tur"
        yuborish(chat_id, "Kirim turi?", [["🏦 Rahbardan", "📦 Zakladdan"], ["🔙 Orqaga"]])
    elif matn == "💸 Chiqim":
        holat[chat_id] = "chiqim_summa"
        yuborish(chat_id, "Chiqim summasini kiriting:")
    elif matn == "💼 Oldingi qoldiq":
        holat[chat_id] = "qoldiq_summa"
        yuborish(chat_id, "Oldingi qoldiq summasini kiriting:")
    elif matn == "📊 Xisobot ko'rish":
        x, _ = xisobot_matni()
        yuborish(chat_id, x)
        asosiy_menu(chat_id)
    elif matn == "🔙 Orqaga":
        holat[chat_id] = ""
        asosiy_menu(chat_id)
    elif h == "kirim_tur":
        if matn == "🏦 Rahbardan":
            holat[chat_id] = "rahbar_summa"
            yuborish(chat_id, "Summani kiriting:")
        elif matn == "📦 Zakladdan":
            holat[chat_id] = "zaklad_summa"
            yuborish(chat_id, "Summani kiriting:")
    elif h == "rahbar_summa":
        try:
            summa = int(matn.replace(" ", ""))
            kunlik["kirimlar"].append((summa, "Rahbardan olingan"))
            holat[chat_id] = ""
            yuborish(chat_id, f"✅ +{formatlash(summa)} Rahbardan olingan")
            asosiy_menu(chat_id)
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
    elif h == "zaklad_summa":
        try:
            holat[chat_id + "_summa"] = int(matn.replace(" ", ""))
            holat[chat_id] = "zaklad_izoh"
            yuborish(chat_id, "Zaklad izohini kiriting:")
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
    elif h == "zaklad_izoh":
        summa = holat.get(chat_id + "_summa", 0)
        kunlik["kirimlar"].append((summa, matn))
        holat[chat_id] = ""
        yuborish(chat_id, f"✅ +{formatlash(summa)} {matn}")
        asosiy_menu(chat_id)
    elif h == "chiqim_summa":
        try:
            holat[chat_id + "_summa"] = int(matn.replace(" ", ""))
            holat[chat_id] = "chiqim_izoh"
            yuborish(chat_id, "Izohini kiriting:")
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
    elif h == "chiqim_izoh":
        summa = holat.get(chat_id + "_summa", 0)
        kunlik["chiqimlar"].append((summa, matn))
        holat[chat_id] = ""
        yuborish(chat_id, f"✅ {formatlash(summa)} {matn}")
        asosiy_menu(chat_id)
    elif h == "qoldiq_summa":
        try:
            kunlik["oldingi_qoldiq"] = int(matn.replace(" ", ""))
            holat[chat_id] = ""
            yuborish(chat_id, f"✅ Oldingi qoldiq saqlandi!")
            asosiy_menu(chat_id)
        except:
            yuborish(chat_id, "⚠️ Faqat raqam kiriting!")
    else:
        asosiy_menu(chat_id)

def polling():
    offset = 0
    while True:
        try:
            url = f"{BASE_URL}/getUpdates?offset={offset}&timeout=30"
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

def kunlik_yuborish():
    while True:
        now = datetime.now()
        if now.hour == YUBORISH_SOAT and now.minute == 0:
            try:
                x, qoldi = xisobot_matni()
                yuborish(GURUH_ID, x)
                kunlik["oldingi_qoldiq"] = qoldi
                kunlik["kirimlar"] = []
                kunlik["chiqimlar"] = []
            except Exception as e:
                print(f"Yuborish xatosi: {e}")
        import time
        time.sleep(60)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti!")
    def log_message(self, *args):
        pass

if __name__ == "__main__":
    threading.Thread(target=kunlik_yuborish, daemon=True).start()
    threading.Thread(target=polling, daemon=True).start()
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), Handler).serve_forever()
