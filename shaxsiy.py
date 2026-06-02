import os
import json
import urllib.request
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import calendar

TOKEN = os.environ.get("8808944343:AAFNa_P6pnIKejQBal9MPavryAe8qoPrRmw")
GURUH_ID = os.environ.get("719049365")
YUBORISH_SOAT = 15

ma_lumot = {"daromadlar": [], "xarajatlar": [], "oldingi_qoldiq": 0}
holat = {}
oylik = {"daromadlar": [], "xarajatlar": []}

DAROMAD_TURLARI = ["💼 Oylik maosh", "📢 Reklamadan", "🔧 Qo'shimcha ishlardan", "💡 Boshqa"]

def formatlash(summa):
    return "{:,}".format(int(summa)).replace(",", " ")

def api(method, data):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"API xato: {e}")

def yuborish(chat_id, matn, keyboard=None):
    data = {"chat_id": chat_id, "text": matn}
    if keyboard:
        data["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True}
    api("sendMessage", data)

def asosiy_menu(chat_id):
    yuborish(chat_id, "Nima qilmoqchisiz?", [
        ["💰 Daromad", "💸 Xarajat"],
       ["💼 Oldingi qoldiq", "📊 Xisobot korish"],
