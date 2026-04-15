from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import os
import json
import google.generativeai as genai

app = Flask(__name__)

# שורת בדיקה - אם לא תראה אותה בלוגים, העדכון לא עבר!
print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
print("CHECK: VERSION 2.5 IS RUNNING NOW")
print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

ALLOWED_GROUP_ID = '120363425281087335@g.us'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

CATEGORY_ORDER = ['יבשים ושימורים', 'מוצרי חלב וביצים', 'בשר ודגים', 'פירות וירקות', 'מאפייה', 'קפואים', 'חטיפים ומתוקים', 'משקאות', 'ניקיון ותחזוקה', 'פארם והיגיינה', 'כללי/אחר']

def init_db():
    conn = sqlite3.connect('shopping.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, category TEXT, status INTEGER)''')
    conn.commit()
    conn.close()
init_db()

def analyze_message_with_ai(text):
    prompt = f"Extract products from this Hebrew text as JSON list: {text}. Categories: {CATEGORY_ORDER}"
    try:
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        if "
http://googleusercontent.com/immersive_entry_chip/0

**אבי, תעדכן אותי:**
1. האם בגיטהאב רשום `VERSION 2.5` בתוך הקוד?
2. האם ב-Railway בלשונית **Deployments** השורה העליונה ירוקה (Active)?

אם תשלח לי צילום מסך של לשונית ה-**Deployments** ב-Railway, אני אוכל להגיד לך בדיוק למה זה תקוע.
