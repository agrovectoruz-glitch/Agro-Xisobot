import os
import json
import urllib.request
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import calendar

TOKEN = os.environ.get("8808944343:AAFNa_P6pnIKejQBal9MPavryAe8qoPrRmw")
GURUH_ID = os.environ.get("-1003966538627")
YUBORISH_SOAT = 15

ma_lumot = {"daromadlar": [], "xarajatlar": [], "oldingi_qoldiq": 0}
holat = {}
oylik = {"daromadlar": [], "xarajatlar": []}

DAROMAD_TURLARI = ["Oylik maosh", "Reklamadan", "Qoshimcha ishlardan", "Boshqa"]

def formatlash(summa):
    return "{:,}".format(int(summa)).replace(",", " ")

def api(method, data):
    url = "https://api.telegram.org/bot{}/{}".format(TOKEN, method)
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print("API xato: {}".format(e))

def yuborish(chat_id, matn, keyboard=None):
    data = {"chat_id": chat_id, "text": matn}
    if keyboard:
        data["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True}
    api("sendMessage", data)

def asosiy_menu(chat_id):
    yuborish(chat_id, "Nima qilmoqchisiz?", [
        ["Daromad", "Xarajat"],
        ["Oldingi qoldiq", "Xisobot korish"],
        ["Oylik xisobot"]
    ])

def kunlik_xisobot_matni():
    bugun = datetime.now().strftime("%d.%m.%Y")
    jami_daromad = sum(s for s, _ in ma_lumot["daromadlar"])
    jami_xarajat = sum(s for s, _ in ma_lumot["xarajatlar"])
    balans = ma_lumot["oldingi_qoldiq"] + jami_daromad
    qoldi = balans - jami_xarajat
    daromad_text = "\n".join("+{} {}".format(formatlash(s), i) for s, i in ma_lumot["daromadlar"])
    xarajat_text = "\n".join("{} {}".format(formatlash(s), i) for s, i in ma_lumot["xarajatlar"])
    x = "Kunlik xisobot: {}\n".format(bugun)
    if daromad_text:
        x += "\n{}\n".format(daromad_text)
    if xarajat_text:
        x += "\n{}\n".format(xarajat_text)
    x += "\nJami xarajat: {}\nBalans: {}\nQoldi: {}".format(
        formatlash(jami_xarajat), formatlash(balans), formatlash(qoldi))
    return x, qoldi

def oylik_xisobot_matni():
    oy = datetime.now().strftime("%B %Y")
    jami_daromad = sum(s for s, _ in oylik["daromadlar"])
    jami_xarajat = sum(s for s, _ in oylik["xarajatlar"])
    qoldi = jami_daromad - jami_xarajat
    daromad_text = "\n".join("+{} {}".format(formatlash(s), i) for s, i in oylik["daromadlar"])
    xarajat_text = "\n".join("{} {}".format(formatlash(s), i) for s, i in oylik["xarajatlar"])
    x = "Oylik xisobot: {}\n".format(oy)
    if daromad_text:
        x += "\nDaromadlar:\n{}\n".format(daromad_text)
    if xarajat_text:
        x += "\nXarajatlar:\n{}\n".format(xarajat_text)
    x += "\nJami daromad: {}\nJami xarajat: {}\nQoldi: {}".format(
        formatlash(jami_daromad), formatlash(jami_xarajat), formatlash(qoldi))
    return x

def xabar_qayta_ishlash(chat_id, matn):
    if matn in ["/start", "/menu"]:
        holat[chat_id] = ""
        asosiy_menu(chat_id)
        return

    h = holat.get(chat_id, "")

    if matn == "Daromad":
        holat[chat_id] = "daromad_tur"
        keyboard = [[t] for t in DAROMAD_TURLARI] + [["Orqaga"]]
        yuborish(chat_id, "Daromad turi?", keyboard)
    elif matn == "Xarajat":
        holat[chat_id] = "xarajat_summa"
        yuborish(chat_id, "Xarajat summasini kiriting:")
    elif matn == "Oldingi qoldiq":
        holat[chat_id] = "qoldiq_summa"
        yuborish(chat_id, "Oldingi qoldiq summasini kiriting:")
    elif matn == "Xisobot korish":
        x, _ = kunlik_xisobot_matni()
        yuborish(chat_id, x)
        asosiy_menu(chat_id)
    elif matn == "Oylik xisobot":
        x = oylik_xisobot_matni()
        yuborish(chat_id, x)
        asosiy_menu(chat_id)
    elif matn == "Orqaga":
        holat[chat_id] = ""
        asosiy_menu(chat_id)
    elif h == "daromad_tur":
        if matn in DAROMAD_TURLARI:
            holat[chat_id + "_tur"] = matn
            holat[chat_id] = "daromad_summa"
            yuborish(chat_id, "{} - summani kiriting:".format(matn))
        else:
            yuborish(chat_id, "Tugmalardan birini tanlang!")
    elif h == "daromad_summa":
        try:
            summa = int(matn.replace(" ", "").replace(",", ""))
            tur = holat.get(chat_id + "_tur", "Daromad")
            ma_lumot["daromadlar"].append((summa, tur))
            oylik["daromadlar"].append((summa, tur))
            holat[chat_id] = ""
            yuborish(chat_id, "Qoshildi: +{} {}".format(formatlash(summa), tur))
            asosiy_menu(chat_id)
        except:
            yuborish(chat_id, "Faqat raqam kiriting!")
    elif h == "xarajat_summa":
        try:
            holat[chat_id + "_summa"] = int(matn.replace(" ", "").replace(",", ""))
            holat[chat_id] = "xarajat_izoh"
            yuborish(chat_id, "Izohini kiriting:")
        except:
            yuborish(chat_id, "Faqat raqam kiriting!")
    elif h == "xarajat_izoh":
        summa = holat.get(chat_id + "_summa", 0)
        ma_lumot["xarajatlar"].append((summa, matn))
        oylik["xarajatlar"].append((summa, matn))
        holat[chat_id] = ""
        yuborish(chat_id, "Qoshildi: {} {}".format(formatlash(summa), matn))
        asosiy_menu(chat_id)
    elif h == "qoldiq_summa":
        try:
            ma_lumot["oldingi_qoldiq"] = int(matn.replace(" ", "").replace(",", ""))
            holat[chat_id] = ""
            yuborish(chat_id, "Oldingi qoldiq saqlandi!")
            asosiy_menu(chat_id)
        except:
            yuborish(chat_id, "Faqat raqam kiriting!")
    else:
        asosiy_menu(chat_id)

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
    while True:
        now = datetime.now()
        if now.hour == YUBORISH_SOAT and now.minute == 0:
            try:
                x, qoldi = kunlik_xisobot_matni()
                yuborish(GURUH_ID, x)
                ma_lumot["oldingi_qoldiq"] = qoldi
                ma_lumot["daromadlar"] = []
                ma_lumot["xarajatlar"] = []
                oxirgi_kun = calendar.monthrange(now.year, now.month)[1]
                if now.day == oxirgi_kun:
                    oy_x = oylik_xisobot_matni()
                    yuborish(GURUH_ID, "OY YAKUNLANDI!\n\n{}".format(oy_x))
                    oylik["daromadlar"] = []
                    oylik["xarajatlar"] = []
            except Exception as e:
                print("Yuborish xatosi: {}".format(e))
        time.sleep(60)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Shaxsiy bot ishlayapti!")
    def log_message(self, *args):
        pass

if __name__ == "__main__":
    threading.Thread(target=kunlik_yuborish, daemon=True).start()
    threading.Thread(target=polling, daemon=True).start()
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), Handler).serve_forever()
