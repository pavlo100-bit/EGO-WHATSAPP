import os
import re
import requests
import json
import logging
import sqlite3
from flask import Flask, request

app = Flask(__name__)

# הגדרות Green API
GREEN_API_ID = "7103540645"
GREEN_API_TOKEN = "22e83562ef1e46588d0d393232ed1ad441a8e941990646e09a"
SEND_MSG_URL = f"https://7103.api.greenapi.com/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"

logging.basicConfig(level=logging.INFO)

DB_PATH = "/app/data/orders_db.sqlite"

def init_db():
    os.makedirs("/app/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS processed_orders (order_id TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

def is_order_processed(order_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM processed_orders WHERE order_id = ?", (order_id,))
        exists = cur.fetchone() is not None
        conn.close()
        return exists
    except: return False

def mark_order_as_processed(order_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO processed_orders (order_id) VALUES (?)", (order_id,))
        conn.commit()
        conn.close()
    except: pass

init_db()

def send_whatsapp(phone, text):
    try:
        payload = {"chatId": phone + "@c.us", "message": text}
        requests.post(SEND_MSG_URL, json=payload, timeout=20)
    except: pass

@app.route('/webhook', methods=['POST', 'GET'])
def woocommerce_webhook():
    if request.method == "GET": return "e-go Smart-Reload v10 Online", 200
    
    data = request.get_json(silent=True)
    if not data or data.get("status") != "completed": return "OK", 200

    order_id = str(data.get("id"))
    if is_order_processed(order_id): return "OK", 200

    try:
        customer_name = data.get("billing", {}).get("first_name", "לקוח/ה")
        raw_phone = data.get("billing", {}).get("phone", "")
        phone = re.sub(r'\D', '', raw_phone)
        if phone.startswith("0"): phone = "972" + phone[1:]
        elif not phone.startswith("972"): phone = "972" + phone

        full_dump = json.dumps(data)
        all_iccids = list(dict.fromkeys(re.findall(r'89\d{16,18}', full_dump)))
        all_codes = list(dict.fromkeys(re.findall(r'K2-[A-Z0-9-]+', full_dump)))

        if not all_iccids: return "OK", 200

        msg = f"היי {customer_name} 👋\n\n"
        msg += f"תודה על הזמנתך ב- *e-go* 🙏🏼\n"
        msg += f"מספר הזמנתך: {order_id}\n\n"

        items = data.get("line_items", [])
        
        for i in range(len(all_iccids)):
            iccid = all_iccids[i]
            code = all_codes[i] if i < len(all_codes) else ""
            
            product_name = items[i].get("name", "") if i < len(items) else "חבילת eSIM"
            is_reload = any(word in product_name.lower() for word in ["טעינ", "top up", "topup", "reload"])

            smart_link = f"https://e-go.co.il/check-package-details/?iccid={iccid}"

            if is_reload:
                msg += f"🔄 *עדכון חבילה (טעינה):*\n"
                msg += f"שם החבילה: {product_name}\n"
                msg += f"החבילה הוטענה בהצלחה ל-ICCID:\n`{iccid}`\n\n"
                msg += "החבילה מעודכנת כעת במכשירך. **אין צורך לבצע התקנה מחדש** או לסרוק שוב ברקוד.\n\n"
                msg += "💡 *טיפ:* במידה והחבילה לא מופיעה מיד, יש להעביר את המכשיר למצב טיסה ל-5 שניות, להחזיר ולנסות שוב.\n\n"
                msg += "✅ *בדיקת יתרה מעודכנת:* \n"
                msg += f"{smart_link}\n\n"
            else:
                msg += f"📦 *פרטי ה-eSIM החדש שלך:*\n"
                msg += f"מס' ה-ICCID:\n`{iccid}`\n\n"
                msg += "✅ *בדיקת יתרה וטעינה בלחיצה אחת:*\n"
                msg += f"{smart_link}\n\n"
                
                if code:
                    lpa = f"LPA:1$smdp.io${code}"
                    msg += "🚀 *חדש! התקנה מהירה בלחיצה:*\n"
                    msg += "לחץ על הלינק וה-eSIM יותקן אוטומטית במכשירך:\n\n"
                    msg += f"📱 *למשתמשי Apple (אייפון):*\n"
                    msg += f"https://esimsetup.apple.com/esim_qrcode_provisioning?carddata={lpa}\n\n"
                    msg += f"📱 *למשתמשי Android:*\n"
                    msg += f"https://esimsetup.android.com/esim_qrcode_provisioning?carddata={lpa}\n\n"

            if len(all_iccids) > 1:
                msg += "--------------------------\n\n"

        msg += "---\n📍 *מידע חשוב:*\n\n"
        msg += "⚠️ *חשוב מאוד:* במהלך ההתקנה נא לא לבצע הסרת חבילה היות ולא ניתן לשחזר את הברקוד.\n\n"
        msg += "📍 להתקנת ה-eSIM במכשירך, יש לסרוק את הברקוד שנשלח במייל\n"
        msg += "📍 יש לבצע את ההתקנה בארץ כאשר מחוברים לאינטרנט\n\n"
        msg += "🍎 *מדריכי Apple:*\nhttps://did.li/ego-iphone-install\nhttps://did.li/ego-iphone-use\n\n"
        msg += "🤖 *מדריכי Android:*\nhttps://did.li/ego-android-install\nhttps://did.li/ego-android-use\n\n"
        msg += "❓ לתמיכה טכנית בווטסאפ: 08:00-22:00\n\n"
        msg += "נסיעה טובה🌴\nצוות e-go"

        mark_order_as_processed(order_id)
        send_whatsapp(phone, msg)
        return "OK", 200

    except Exception as e:
        logging.error(f"Error: {e}")
        return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
