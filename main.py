from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import os
import json
import google.generativeai as genai

app = Flask(__name__)

# --- הגדרות ---
ALLOWED_GROUP_ID = '120363425281087335@g.us'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# הגדרת Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

CATEGORY_ORDER = [
    'יבשים ושימורים', 'מוצרי חלב וביצים', 'בשר ודגים', 'פירות וירקות',
    'מאפייה', 'קפואים', 'חטיפים ומתוקים', 'משקאות', 'ניקיון ותחזוקה',
    'פארם והיגיינה', 'כללי/אחר'
]

# --- יצירת בסיס הנתונים ---
def init_db():
    conn = sqlite3.connect('shopping.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items 
                 (id INTEGER PRIMARY KEY, name TEXT, category TEXT, status INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- לוגיקת AI לניתוח הודעה ---
def analyze_message_with_ai(text):
    # הנחיה משופרת וקשוחה יותר ל-AI
    prompt = f"""
    אתה מומחה לניתוח רשימות קניות. תפקידך לחלץ מוצרים נטו מטקסט חופשי.
    
    חוקים נוקשים:
    1. פצל מוצרים: אם מופיעים כמה מוצרים (למשל עם 'ו' החיבור או פסיק), פצל אותם לאובייקטים נפרדים.
    2. ניקוי מוחלט: הסר מילים כמו 'תביא', 'רק', 'לי', 'בבקשה', 'אל תשכח', 'תקנה'. השאר רק את שם המוצר.
    3. דוגמה: עבור המשפט 'תביא לי רק עמק פרוס דק ולחם', עליך להחזיר שני פריטים: 'עמק פרוס דק' ו-'לחם'.
    4. סיווג: בחר רק מהקטגוריות האלו: {', '.join(CATEGORY_ORDER)}.
    5. אם אין מוצר ברור בטקסט, החזר רשימה ריקה [].

    החזר JSON בלבד במבנה:
    [{{"name": "שם המוצר", "category": "הקטגוריה"}}]

    הטקסט לניתוח: "{text}"
    """
    
    try:
        response = model.generate_content(prompt)
        json_text = response.text.replace('```json', '').replace('```', '').strip()
        items = json.loads(json_text)
        return items
    except Exception as e:
        print(f"❌ שגיאת AI: {e}")
        return []

# --- נתיבי האתר ---

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
        ai_results = analyze_message_with_ai(name)
        conn = sqlite3.connect('shopping.db')
        c = conn.cursor()
        for item in ai_results:
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
                
                ai_results = analyze_message_with_ai(full_text)
                
                if ai_results:
                    conn = sqlite3.connect('shopping.db')
                    c = conn.cursor()
                    for item in ai_results:
                        c.execute("INSERT INTO items (name, category, status) VALUES (?, ?, 0)", (item['name'], item['category']))
                        print(f"✅ AI הוסיף: {item['name']} ({item['category']})")
                    conn.commit()
                    conn.close()
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
