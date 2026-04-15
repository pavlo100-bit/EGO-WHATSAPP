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
    You are a Hebrew shopping list assistant. Convert messages into a JSON list of products.
    
    STRICT RULES:
    1. SPLIT: Every product must be a separate item in the list.
    2. DELIMITERS: Split by commas (,), by the word 'וגם', and by the letter 'ו' when it connects two products (e.g. 'חלב ולחם' -> 'חלב', 'לחם').
    3. CLEAN: Remove prefixes like 'תביא', 'רק', 'לי', 'תקנה', 'צריך', 'בבקשה'.
    4. NO 'VAV': Never start a product name with 'ו'. 'ורסק' must become 'רסק'.
    5. CATEGORIES: Choose ONLY from: {', '.join(CATEGORY_ORDER)}.
    6. IF NO PRODUCTS: Return empty list [].

    Example: "תביא עמק ולחם, רסק, בננה"
    Output: [{"name": "עמק", "category": "מוצרי חלב וביצים"}, {"name": "לחם", "category": "מאפייה"}, {"name": "רסק", "category": "יבשים ושימורים"}, {"name": "בננה", "category": "פירות וירקות"}]

    Text to analyze: "{text}"
    """
    
    try:
        response = model.generate_content(prompt)
        json_text = response.text.replace('```json', '').replace('```', '').strip()
        items = json.loads(json_text)
        
        # מנגנון הגנה נוסף בפייתון - אם ה-AI החזיר פריט אחד שעדיין מכיל פסיקים
        final_items = []
        for item in items:
            if ',' in item['name']:
                sub_names = item['name'].split(',')
                for sn in sub_names:
                    if sn.strip():
                        final_items.append({"name": sn.strip(), "category": item['category']})
            else:
                final_items.append(item)
        
        return final_items
    except Exception as e:
        print(f"❌ שגיאת AI או פיענוח: {e}")
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
                print(f"📩 הודעה גולמית: {full_text}")
                
                ai_results = analyze_message_with_ai(full_text)
                print(f"🤖 תוצאת AI: {ai_results}")
                
                if ai_results:
                    conn = sqlite3.connect('shopping.db')
                    c = conn.cursor()
                    for item in ai_results:
                        c.execute("INSERT INTO items (name, category, status) VALUES (?, ?, 0)", (item['name'], item['category']))
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
