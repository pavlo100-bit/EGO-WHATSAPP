from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import os
import json
import google.generativeai as genai

app = Flask(__name__)

# --- זיהוי גירסה בלוגים ---
print("*****************************************")
print("🚀 המערכת עלתה: גירסה 2.0 - פועל עם AI")
print("*****************************************")

# --- הגדרות ---
ALLOWED_GROUP_ID = '120363425281087335@g.us'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# הגדרת Gemini
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ מפתח AI זוהה והתחבר בהצלחה")
    except Exception as e:
        print(f"❌ שגיאה בחיבור ל-Gemini: {e}")
else:
    print("⚠️ אזהרה: לא נמצא מפתח GEMINI_API_KEY ב-Variables!")

CATEGORY_ORDER = [
    'יבשים ושימורים', 'מוצרי חלב וביצים', 'בשר ודגים', 'פירות וירקות',
    'מאפייה', 'קפואים', 'חטיפים ומתוקים', 'משקאות', 'ניקיון ותחזוקה',
    'פארם והיגיינה', 'כללי/אחר'
]

def init_db():
    conn = sqlite3.connect('shopping.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items 
                 (id INTEGER PRIMARY KEY, name TEXT, category TEXT, status INTEGER)''')
    conn.commit()
    conn.close()

init_db()

def analyze_message_with_ai(text):
    print(f"🔍 ניתוח הודעה: {text}")
    
    prompt = f"""
    אתה עוזר קניות חכם. תפקידך להחזיר רשימת JSON של מוצרים.
    חוקים:
    1. פצל מוצרים: אם כתוב 'חלב ולחם', אלו שני מוצרים נפרדים.
    2. נקה מילים: הסר 'תביא', 'רק', 'בבקשה', 'אל תשכח'.
    3. הסר ו' החיבור: 'ורסק' הופך ל-'רסק'.
    4. קטגוריות מותרות: {', '.join(CATEGORY_ORDER)}.
    
    טקסט: "{text}"
    פורמט פלט: [{"name": "שם המוצר", "category": "קטגוריה"}]
    """
    
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        # ניקוי פורמט JSON
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        print(f"🤖 AI ענה: {raw_text}")
        return json.loads(raw_text)
    except Exception as e:
        print(f"❌ תקלה ב-AI: {e}")
        # גיבוי ידני
        parts = text.replace(' ו', ',').split(',')
        return [{"name": p.strip(), "category": "כללי/אחר"} for p in parts if p.strip()]

@app.route('/')
def index():
    conn = sqlite3.connect('shopping.db')
    c = conn.cursor()
    order_query = "CASE category "
    for i, cat in enumerate(CATEGORY_ORDER):
        order_query += f"WHEN '{cat}' THEN {i} "
    order_query += "END"
    c.execute(f"SELECT * FROM items ORDER BY status ASC, {order_query} ASC")
    items = c.fetchall()
    conn.close()
    return render_template('index.html', items=items)

@app.route('/add', methods=['POST'])
def add_item():
    name = request.form.get('item_name')
    if name:
        items = analyze_message_with_ai(name)
        conn = sqlite3.connect('shopping.db')
        c = conn.cursor()
        for item in items:
            c.execute("INSERT INTO items (name, category, status) VALUES (?, ?, 0)", (item['name'], item['category']))
        conn.commit()
        conn.close()
    return redirect('/')

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    try:
        if data.get('typeWebhook') == 'incomingMessageReceived':
            chat_id = data['senderData']['chatId']
            if chat_id == ALLOWED_GROUP_ID:
                full_text = data['messageData']['textMessageData']['textMessage']
                print(f"📩 וואטסאפ: {full_text}")
                
                items = analyze_message_with_ai(full_text)
                
                if items:
                    conn = sqlite3.connect('shopping.db')
                    c = conn.cursor()
                    for item in items:
                        c.execute("INSERT INTO items (name, category, status) VALUES (?, ?, 0)", (item['name'], item['category']))
                    conn.commit()
                    conn.close()
                    print(f"✅ נוספו {len(items)} מוצרים")
    except Exception as e:
        print(f"❌ שגיאה: {e}")
    return jsonify({"status": "success"}), 200

@app.route('/toggle/<int:item_id>')
def toggle_item(item_id):
    conn = sqlite3.connect('shopping.db')
    c = conn.cursor()
    c.execute("UPDATE items SET status = 1 - status WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/clear')
def clear_list():
    conn = sqlite3.connect('shopping.db')
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE status = 1")
    conn.commit()
    conn.close()
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
