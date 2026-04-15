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
    prompt = f"""
    אתה עוזר חכם לרשימת קניות משפחתית. תפקידך לנתח הודעות וואטסאפ בעברית.
    1. זהה את כל המוצרים שמופיעים בהודעה.
    2. עבור כל מוצר, נקה מילות פתיחה כמו 'תביא', 'תקנה', 'צריך', 'אל תשכח' והשאר רק את שם המוצר והפירוט (למשל: 'עמק 5% דל שומן').
    3. סווג כל מוצר לאחת מהקטגוריות הבאות בלבד: {', '.join(CATEGORY_ORDER)}.
    4. אם ההודעה היא שיחה רגילה או משפט שלא כולל מוצר לקנייה (למשל: 'מתי אתה חוזר', 'אל תשכח את הילד'), החזר רשימה ריקה.
    
    החזר את התוצאה בפורמט JSON בלבד כרשימה של אובייקטים:
    [{{"name": "שם המוצר", "category": "הקטגוריה"}}]
    
    הטקסט לניתוח: "{text}"
    """
    
    try:
        response = model.generate_content(prompt)
        # ניקוי הטקסט מה-AI כדי לוודא שזה JSON תקין
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
        # גם בהוספה מהאתר נשתמש ב-AI כדי לסווג נכון
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
                
                # ה-AI מנתח ומפרק את כל ההודעה (שורות או משפט ארוך)
                ai_results = analyze_message_with_ai(full_text)
                
                if ai_results:
                    conn = sqlite3.connect('shopping.db')
                    c = conn.cursor()
                    for item in ai_results:
                        c.execute("INSERT INTO items (name, category, status) VALUES (?, ?, 0)", (item['name'], item['category']))
                        print(f"✅ AI הוסיף: {item['name']} לקטגוריית {item['category']}")
                    conn.commit()
                    conn.close()
                else:
                    print(f"⏭️ AI החליט להתעלם מההודעה: {full_text}")
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
