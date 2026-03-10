import os
import re
import requests
import logging
from flask import Flask, request

app = Flask(__name__)

# הגדרות Green API של e-go
GREEN_API_ID = "7103540645"
GREEN_API_TOKEN = "22e83562ef1e46588d0d393232ed1ad441a8e941990646e09a"
SEND_MSG_URL = f"https://7103.api.greenapi.com/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"

logging.basicConfig(level=logging.INFO)

def send_whatsapp(phone, text):
    try:
        payload = {"chatId": phone + "@c.us", "message": text}
        requests.post(SEND_MSG_URL, json=payload, timeout=10)
        logging.info(f"Message sent to {phone}")
    except Exception as e:
        logging.error(f"Error sending message: {e}")

@app.route('/webhook', methods=['POST', 'GET'])
def woocommerce_webhook():
    # בדיקת תקינות השרת
    if request.method == "GET": 
        return "e-go Railway System is Online", 200
    
    data = request.get_json(silent=True)
    if not data or data.get("status") != "completed": 
        return "OK", 200

    try:
        order_id = str(data.get("id"))
        customer_name = data.get("billing", {}).get("first_name", "לקוח")
        phone = data.get("billing", {}).get("phone", "").replace(" ", "").replace("-", "")
        
        # תיקון פורמט טלפון לישראלי
        if phone.startswith("0"): 
            phone = "972" + phone[1:]
        if not phone.startswith("972"): 
            phone = "972" + phone

        # חילוץ ICCID וקוד LPA מההזמנה
        full_text = str(data)
        iccid_match = re.search(r'\d{18,20}', full_text)
        iccid = iccid_match.group(0) if iccid_match else "נשלח במייל"
        
        code_match = re.search(r'K2-[A-Z0-9-]+', full_text)
        code = code_match.group(0) if code_match else ""
        
        # בניית ההודעה ללקוח
        msg = f"היי {customer_name} 👋\nתודה שרכשת ב- *e-go*! מספר הזמנה: {order_id}\n\n"
        msg += f"מס' ICCID שלך:\n`{iccid}`\n\n"
        
        if code:
            lpa = f"LPA:1$smdp.io${code}"
            msg += "🚀 *התקנה מהירה בלחיצה:*\n"
            msg += f"אייפון: https://esimsetup.apple.com/esim_qrcode_provisioning?carddata={lpa}\n"
            msg += f"אנדרואיד: https://esimsetup.android.com/esim_qrcode_provisioning?carddata={lpa}\n\n"
        
        msg += "בדיקת יתרה: https://e-go.co.il/check-package-details/\n\nנסיעה טובה! 🌴"
        
        send_whatsapp(phone, msg)
        return "Success", 200
        
    except Exception as e:
        logging.error(f"Error processing order: {e}")
        return "Error", 500

if __name__ == "__main__":
    # הגדרת פורט אוטומטית עבור Railway
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
