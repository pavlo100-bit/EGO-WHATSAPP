import os
import re
import requests
import json
import logging
from flask import Flask, request

app = Flask(__name__)

# הגדרות Green API - e-go.co.il
GREEN_API_ID = "7103540645"
GREEN_API_TOKEN = "22e83562ef1e46588d0d393232ed1ad441a8e941990646e09a"
SEND_MSG_URL = f"https://7103.api.greenapi.com/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"

logging.basicConfig(level=logging.INFO)

# --- ניהול זיכרון קבוע ב-Volume (מניעת כפילויות) ---
DB_FILE = "/app/data/processed_orders.txt"

def is_order_processed(order_id):
    if not os.path.exists(DB_FILE): return False
    try:
        with open(DB_FILE, "r") as f:
            return order_id in f.read().splitlines()
    except: return False

def mark_order_as_processed(order_id):
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    try:
        with open(DB_FILE, "a") as f:
            f.write(f"{order_id}\n")
    except Exception as e:
        logging.error(f"Save Error: {e}")

def send_whatsapp(phone, text):
    try:
        payload = {"chatId": phone + "@c.us", "message": text}
        requests.post(SEND_MSG_URL, json=payload, timeout=15)
        logging.info(f"Message sent to {phone}")
    except Exception as e:
        logging.error(f"WhatsApp Error: {e}")

@app.route('/webhook', methods=['POST', 'GET'])
def woocommerce_webhook():
    if request.method == "GET": return "e-go Multi-Package System Online", 200
    
    data = request.get_json(silent=True)
    if not data or data.get("status") != "completed": return "OK", 200

    order_id = str(data.get("id"))
    
    # 1. מניעת כפילויות הרמטית (מול הדיסק ב-Railway)
    if is_order_processed(order_id):
        logging.info(f"Duplicate order {order_id} blocked.")
        return "OK", 200
    
    mark_order_as_processed(order_id)

    try:
        customer_name = data.get("billing", {}).get("first_name", "לקוח/ה")
        
        # 2. ניקוי מספר טלפון
        raw_phone = data.get("billing", {}).get("phone", "")
        phone = re.sub(r'\D', '', raw_phone)
        if phone.startswith("0"): phone = "972" + phone[1:]
        elif not phone.startswith("972"): phone = "972" + phone

        # 3. איסוף כל ה-ICCID והקודים מכל ההזמנה (חיפוש גלובלי)
        full_dump = json.dumps(data)
        all_iccids = list(dict.fromkeys(re.findall(r'\d{18,20}', full_dump)))
        all_codes = list(dict.fromkeys(re.findall(r'K2-[A-Z0-9-]+', full_dump)))

        # 4. בניית ההודעה
        msg = f"היי {customer_name} 👋\n\n"
        msg += f"תודה על הזמנתך ב- *e-go* 🙏🏼\n"
        msg += f"מספר הזמנתך: {order_id}\n\n"
        msg += "להלן פרטי החבילות שהזמנת:\n"
        msg += "--------------------------\n\n"

        items = data.get("line_items", [])
        for i, item in enumerate(items):
            product_name = item.get("name", "חבילת eSIM")
            
            # התאמת ICCID וקוד לפי סדר הופעתם
            current_iccid = all_iccids[i] if i < len(all_iccids) else "נשלח במייל"
            current_code = all_codes[i] if i < len(all_codes) else ""

            msg += f"📦 *{product_name}:*\n"
            msg += f"מס' ICCID: `{current_iccid}`\n"
            
            if current_code:
                lpa = f"LPA:1$smdp.io${current_code}"
                msg += "🚀 *חדש! התקנה מהירה בלחיצה:*\n"
                msg += f"📱 Apple: https://esimsetup.apple.com/esim_qrcode_provisioning?carddata={lpa}\n"
                msg += f"📱 Android: https://esimsetup.android.com/esim_qrcode_provisioning?carddata={lpa}\n"
            msg += "\n"

        msg += "--------------------------\n"
        msg += "📍 *בדיקת יתרה וטעינה:* https://e-go.co.il/check-package-details/\n\n"
        msg += "⚠️ *חשוב:* נא לא להסיר את החבילה מהמכשיר לאחר ההתקנה.\n"
        msg += "📍 יש לבצע את ההתקנה בארץ בחיבור ל-WiFi.\n\n"
        msg += "🍎 מדריכי Apple: https://did.li/ego-iphone-install\n"
        msg += "🤖 מדריכי Android: https://did.li/ego-android-install\n\n"
        msg += "📍 מדריך מלא באתר: https://e-go.co.il/user_manual/\n\n"
        msg += "נסיעה טובה וחופשה מהנה! 🌴\nצוות e-go"

        send_whatsapp(phone, msg)
        return "OK", 200

    except Exception as e:
        logging.error(f"Error building message: {e}")
        return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
