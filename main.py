import os
import re
import requests
import json
import logging
from flask import Flask, request

app = Flask(__name__)

# הגדרות Green API - e-go
GREEN_API_ID = "7103540645"
GREEN_API_TOKEN = "22e83562ef1e46588d0d393232ed1ad441a8e941990646e09a"
SEND_MSG_URL = f"https://7103.api.greenapi.com/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"

logging.basicConfig(level=logging.INFO)

def send_whatsapp(phone, text):
    try:
        payload = {"chatId": phone + "@c.us", "message": text}
        requests.post(SEND_MSG_URL, json=payload, timeout=15)
        logging.info(f"Message sent to {phone}")
    except Exception as e:
        logging.error(f"WhatsApp Error: {e}")

@app.route('/webhook', methods=['POST', 'GET'])
def woocommerce_webhook():
    if request.method == "GET": return "e-go System Online", 200
    
    data = request.get_json(silent=True)
    if not data or data.get("status") != "completed": return "OK", 200

    try:
        order_id = str(data.get("id"))
        customer_name = data.get("billing", {}).get("first_name", "לקוח/ה")
        phone = data.get("billing", {}).get("phone", "").replace(" ", "").replace("-", "")
        
        if phone.startswith("0"): phone = "972" + phone[1:]
        if not phone.startswith("972"): phone = "972" + phone

        # --- חילוץ נתונים חכם ---
        full_dump = json.dumps(data)
        
        # חיפוש ICCID נקי
        iccid = "נשלח במייל"
        iccid_match = re.search(r'\d{18,20}', full_dump)
        if iccid_match: iccid = iccid_match.group(0)
            
        # חיפוש קוד הפעלה נקי (K2-...)
        code = ""
        code_match = re.search(r'K2-[A-Z0-9-]+', full_dump)
        if code_match: code = code_match.group(0)

        # --- בניית המלל הסופי ללא "לחיצה ארוכה להעתקה" ---
        lpa_part = f"LPA:1$smdp.io${code}" if code else ""
        
        msg = f"היי {customer_name} 👋\n\n"
        msg += f"תודה על הזמנתך ב- *e-go* 🙏🏼\n"
        msg += f"מספר הזמנתך: {order_id}\n\n"
        msg += f"מס' ה-ICCID שלך:\n" # הורדתי את המשפט על ההעתקה
        msg += f"{iccid}\n\n"
        msg += "מס' זה ישמש אותך לבדיקת יתרת החבילה וטעינת חבילה נוספת- \n"
        msg += "https://e-go.co.il/check-package-details/\n\n"
        
        if code:
            msg += "🚀 *חדש! התקנה מהירה בלחיצה:*\n"
            msg += "לחץ על הלינק לפי סוג המכשיר שברשותך וה-eSIM יותקן אוטומטית במכשירך:\n\n"
            msg += "📱 *למשתמשי Apple (אייפון):*\n"
            msg += f"https://esimsetup.apple.com/esim_qrcode_provisioning?carddata={lpa_part}\n\n"
            msg += "📱 *למשתמשי Android:*\n"
            msg += f"https://esimsetup.android.com/esim_qrcode_provisioning?carddata={lpa_part}\n\n"
        
        msg += "---\n📍 *מידע חשוב:*\n\n"
        msg += "⚠️ *חשוב מאוד:* במהלך ההתקנה נא לא לבצע הסרת חבילה היות ולא ניתן לשחזר את הברקוד.\n\n"
        msg += "📍 להתקנת ה-eSIM במכשירך, יש לסרוק את הברקוד שנשלח במייל (לבדוק במכירות)\n"
        msg += "📍 יש לבצע את ההתקנה בארץ כאשר מחוברים לאינטרנט\n\n"
        msg += "🍎 *מדריכי Apple (אייפון):*\n"
        msg += "מדריך התקנה: https://did.li/ego-iphone-install\n"
        msg += "מדריך הפעלה בחו\"ל: https://did.li/ego-iphone-use\n\n"
        msg += "🤖 *מדריכי Android:*\n"
        msg += "מדריך התקנה: https://did.li/ego-android-install\n"
        msg += "מדריך הפעלה בחו\"ל: https://did.li/ego-android-use\n\n"
        msg += "📍 מדריך מלא באתר: https://e-go.co.il/user_manual/\n\n"
        msg += "❓ בכל שאלה ניתן לפנות לווטסאפ לתמיכה טכנית בין השעות 08:00-22:00\n\n"
        msg += "נסיעה טובה וחופשה מהנה🌴\nצוות e-go"

        send_whatsapp(phone, msg)
        return "OK", 200

    except Exception as e:
        logging.error(f"Error: {e}")
        return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
