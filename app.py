#استدعاء جميع المكتبات اللازمة
from translation import SYMPTOMS_AR,DISEASE_AR
from recommendations import DISEASE_RECOMMENDATIONS
from flask import Flask, render_template, request, url_for, redirect, session,flash, jsonify, render_template
import sqlite3
from flask_bcrypt import Bcrypt 
from functools import wraps
import joblib
import pandas as pd
import os




#تهيئة التطبيق والإعدادات
app = Flask(__name__)
# مفتاح سري قوي لإدارة الجلسات
app.secret_key = 'your_very_secure_secret_key_here' 

bcrypt = Bcrypt(app)

# --- إعدادات قاعدة البيانات SQLite ---
def get_db_connection():
    # سيقوم بإنشاء ملف باسم mrp.db في مجلد المشروع
    conn = sqlite3.connect('mrp.db')
    conn.row_factory = sqlite3.Row  # لجعل النتائج تعود كقاموس
    return conn

def init_db():
    """إنشاء الجداول تلقائياً إذا لم تكن موجودة"""
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role INTEGER DEFAULT 0)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS predictions (
                    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    prediction TEXT,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    conn.commit()
    conn.close()

# تهيئة قاعدة البيانات عند تشغيل الكود
init_db()

 #تحميل النموذج
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    svm_model = joblib.load(os.path.join(BASE_DIR, "svm_model.pkl"))
    le = joblib.load(os.path.join(BASE_DIR, "le.pkl"))
    symptoms_list = joblib.load(os.path.join(BASE_DIR, "symptoms_list.pkl"))


    
except FileNotFoundError:
   
    svm_model = None
    le = None
    symptoms_list = None
    

def is_logged_in(f):
    """ديكوراتور لحماية المسارات."""
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        conn = get_db_connection()
        
        
        try:
            conn.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)", 
                         (username, email, hashed_password, 0))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error='البريد الإلكتروني مسجل بالفعل.')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
    

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            if user['role'] == 1:
                flash('Welcome Admin', 'success')
                return redirect(url_for('admin_users'))
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='بيانات الاعتماد غير صحيحة.')
    return render_template('login.html')




@app.route('/dashboard')
@is_logged_in
def dashboard():
    conn = get_db_connection()
    disease_records = conn.execute("""
        SELECT prediction, created_at FROM predictions 
        WHERE user_id = ? ORDER BY created_at DESC
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('dashboard.html', username=session['username'], disease_records=disease_records)


@app.route('/prediction', methods=['GET', 'POST'])
@is_logged_in
def prediction():
    result = None
    error = None
    recommendation={"tips":[],"links":[]}


    if request.method == 'POST':
        try:
            selected_symptoms = request.form.getlist('symptoms[]')
            # حذف القيم الفارغة
            selected_symptoms = [s for s in selected_symptoms if s]

            if not selected_symptoms :
                error = "يرجى اختيار عرض واحد على الأقل"
                return render_template(
                    'prediction.html',
                    symptoms_list=symptoms_list,
                    result=None,
                    symptoms_ar=SYMPTOMS_AR,
                    tips=recommendation["tips"],
                    links=recommendation["links"],
                    error=error
                )
            if len(selected_symptoms) > 7:
                error ="الحد الأقصى المسموح به 7 أعرض"
                return render_template(
                    'prediction.html',
                    symptoms_list=symptoms_list,
                    result=None,
                    symptoms_ar=SYMPTOMS_AR,
                    tips=recommendation["tips"],
                    links=recommendation["links"],
                    error=error
                )

            #  بناء DataFrame بنفس أعمدة التدريب
            input_df = pd.DataFrame(0, index=[0], columns=symptoms_list)
            #تفعيل الأعراض المختارة
            for symptom in selected_symptoms:
                if symptom in input_df.columns:
                    input_df.at[0, symptom] = 1

            #  التنبؤ
            pred_num = svm_model.predict(input_df)[0]
            disease_name = le.inverse_transform([pred_num])[0]
            #ترجمة اسم المرض للعربية
            disease_ar = DISEASE_AR.get(disease_name,disease_name)
            recommendation = DISEASE_RECOMMENDATIONS.get(disease_name, {
              "tips": [],
              "links": []
              })

            result = disease_ar

            #  حفظ النتيجة 
            conn = get_db_connection()
            conn.execute("INSERT INTO predictions (user_id, prediction, created_at) VALUES (?, ?, datetime('now'))",
                             (session['user_id'], result))
            conn.commit()
            conn.close()

        except Exception as e:
            print("Error:", e)
            error = "حدث خطأ أثناء التنبؤ"

    # GET أو POST
    return render_template(
        'prediction.html',
        symptoms_list=symptoms_list,
        result=result,
        error=error,
        symptoms_ar=SYMPTOMS_AR,
        tips=recommendation["tips"],
        links=recommendation["links"]
    )

  

#مسارات الادمن
# 2. مسار إدارة المستخدمين (عرض وحذف)
@app.route('/admin/data')
@is_logged_in
def admin_data():
    if session.get('role') != 1:
        return "غير مسموح لك بالدخول", 403

    conn = get_db_connection()
    all_predictions = conn.execute("""
        SELECT users.username, predictions.prediction, predictions.created_at, predictions.prediction_id
        FROM predictions 
        JOIN users ON predictions.user_id = users.user_id 
        ORDER BY predictions.created_at DESC
    """).fetchall()

    stats = conn.execute("SELECT prediction, COUNT(*) as count FROM predictions GROUP BY prediction").fetchall()
    conn.close()
    
    return render_template('admin_data.html', predictions=all_predictions, stats=stats)


@app.route('/admin/users')
@is_logged_in
def admin_users():
    if session.get('role') != 1:
        return "غير مسموح لك بالدخول", 403

    conn = get_db_connection()
    users = conn.execute("SELECT user_id, username, email, role FROM users").fetchall()
    conn.close()
    
    return render_template('admin_users.html', users=users)

# مسار حذف مستخدم
@app.route('/delete_user/<int:user_id>', methods=['POST'])
@is_logged_in
def delete_user(user_id):
    if session.get('role') == 1:
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(url_for('admin_users'))

@app.route('/delete_prediction/<int:prediction_id>', methods=['POST'])
@is_logged_in
def delete_prediction(prediction_id):
    # تحقق أن المستخدم مدير
    if session.get('role') == 1:
        conn = get_db_connection()
        conn.execute("DELETE FROM predictions WHERE prediction_id = ?", (prediction_id,))
        conn.commit()
        conn.close()
    return redirect(url_for('admin_data'))   




@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)