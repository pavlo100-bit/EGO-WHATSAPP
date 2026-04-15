from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import os
import json
import google.generativeai as genai

app = Flask(__name__)

# סימן זיהוי ברור בלוגים
print("\n" + "="*40)
print("🚀 אפליקציית קניות: גרסה 3.0 באוויר!")
print("="*40 + "\n")

ALLOWED_GROUP_ID = '120363425281087335@g.us'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# הגדרת ה-AI
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ מוח AI מחובר")
    except Exception as e:
        print(f"❌ שגיאה בחיבור AI: {e}")
else:
    print("⚠️ אזהרה: חסר GEMINI_API_KEY")

CATEGORY_ORDER = ['יבשים ושימורים', 'מוצרי חלב וביצים', 'בשר ודגים', 'פירות וירקות', 'מאפייה', 'קפואים', 'חטיפים ומתוקים', 'משקאות', 'ניקיון ותחזוקה', 'פארם והיגיינה', 'כללי/אחר']

def init_db():
    conn = sqlite3.connect('shopping.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, category TEXT, status INTEGER)''')
    conn.commit()
    conn.close()
init_db()

def analyze_message(text):
    print(f"🔍 מנתח הודעה: {text}")
    
    # ניסיון ראשון: בינה מלאכותית
    try:
        prompt = f"Identify shopping items in Hebrew. Split by 'and' or commas. Return JSON list: [{{'name': 'item', 'category': 'cat'}}]. Categories: {CATEGORY_ORDER}. Text: {text}"
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        if "
http://googleusercontent.com/immersive_entry_chip/0

---

### שלב 3: הפיקוח ב-Railway (כאן תדע אם זה עובד)
1. אחרי ה-Commit בגיטהאב, כנס ל-Railway.
2. לחץ על הלשונית **Deployments**.
3. **חכה עד שתראה V ירוק** על השורה העליונה ויהיה כתוב **Active**. 
4. אם מופיע **X אדום** – לחץ עליו, זה יגיד לנו בדיוק מה חסר.

**אבי, ברגע שזה Active בירוק, שלח הודעה וזה יעבוד. תעדכן אותי אם ראית Active!**
