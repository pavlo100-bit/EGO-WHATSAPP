from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import os
import json
import google.generativeai as genai

app = Flask(__name__)

# סימן זיהוי גירסה
print("!!! גירסה 4.1 - השרת עלה ומחובר ל-AI !!!", flush=True)

ALLOWED_GROUP_ID = '120363425281087335@g.us'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# הגדרת ה-AI
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ מערכת ה-AI הוגדרה בהצלחה", flush=True)
    except Exception as e:
        print(f"❌ שגיאה בחיבור ל-AI: {e}", flush=True)
else:
    print("⚠️ אזהרה: לא נמצא GEMINI_API_KEY במשתני המערכת!", flush=True)

CATEGORY_ORDER = ['יבשים ושימורים', 'מוצרי חלב וביצים', 'בשר ודגים', 'פירות וירקות', 'מאפייה', 'קפואים', 'חטיפים ומתוקים', 'משקאות', 'ניקיון ותחזוקה', 'פארם והיגיינה', 'כללי/אחר']

def init_db():
    conn = sqlite3.connect('shopping.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, category TEXT, status INTEGER)''')
    conn.commit()
    conn.close()

init_db()

def analyze_message(text):
    print(f"🔍 AI מנתח הודעה: {text}", flush=True)
    
    prompt = f"""
    You are a shopping list assistant. Extract products from the following Hebrew text.
    STRICT RULES:
    1. SPLIT: Every product must be a separate JSON object. Split by commas, 'and', or 'vav' (e.g., 'חלב ולחם' -> 'חלב', 'לחם').
    2. CLEAN: Remove 'תביא', 'רק', 'לי', 'בבקשה'.
    3. FIX PREFIX: Remove leading 'ו' from products (e.g., 'ורסק' becomes 'רסק').
    4. CATEGORIES: Choose only from {CATEGORY_ORDER}.
    
    Format: [{"name": "item", "category": "cat"}]
    Text: "{text}"
    """
    
    try:
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0].strip()
            
        print(f"🤖 AI Response: {res_text}", flush=True)
        return json.loads(res_text)
    except Exception as e:
        print(f"⚠️ AI error: {e}. Falling back to basic split.", flush=True)
        # פיצול ידני בסיסי אם ה-AI נכשל
        items = []
        parts = text.replace(' וגם ', ',').replace(' ו', ',').split(',')
        for p in parts:
            name = p.strip()
            if name.startswith('ו') and len(name) > 3: name = name[1:]
            if name: items.append({"name": name, "category": "כללי/אחר"})
        return items

@app.route('/')
def index():
    conn = sqlite3.connect('shopping.db')
    c = conn.cursor()
    # מיון לפי הקטגוריות שהגדרנו
    order_query = "CASE category "
    for i, cat in enumerate(CATEGORY_ORDER):
        order_query += f"WHEN '{cat}' THEN {i} "
    order_query += "END"
    c.execute(f"SELECT * FROM items ORDER BY status ASC, {order_query} ASC")
    items = c.fetchall()
    conn.close()
    return render_template('index.html', items=items)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    try:
        if 'messageData' in data and 'textMessageData' in data['messageData']:
            full_text = data['messageData']['textMessageData']['textMessage']
            chat_id = data['senderData']['chatId']
            
            if chat_id == ALLOWED_GROUP_ID:
                items = analyze_message(full_text)
                conn = sqlite3.connect('shopping.db')
                c = conn.cursor()
                for item in items:
                    c.execute("INSERT INTO items (name, category, status) VALUES (?, ?, 0)", (item['name'], item['category']))
                conn.commit()
                conn.close()
                print(f"✅ נוספו {len(items)} מוצרים.", flush=True)
    except Exception as e:
        print(f"❌ שגיאה: {e}", flush=True)
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
