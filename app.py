

from flask import Flask, render_template, request, url_for, redirect, session,flash
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt 
from functools import wraps
import joblib
import numpy as np
import json 
import os
import pickle
import joblib
from datetime import datetime

# ----------------------------------------------------
# 1. تهيئة التطبيق والإعدادات
# ----------------------------------------------------

app = Flask(__name__)
# مفتاح سري قوي لإدارة الجلسات
app.secret_key = 'your_very_secure_secret_key_here' 

# إعدادات MySQL 
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'chronic_disease_predictor'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' 

mysql = MySQL(app)
bcrypt = Bcrypt(app) 


# ----------------------------------------------------
# 2. تحميل النموذج
# ----------------------------------------------------

try:
    # يجب أن تكون هذه الملفات قد تم إنشاؤها عبر train_model.py
    diabetes_predic = joblib.load('best_decision_tree_model.pkl')
    scaler = joblib.load('scaler.pkl')

    heart_model= joblib.load('heart.pkl')
    heart_scaler=joblib.load('heart_scaler.pkl')

    
except FileNotFoundError:
   
    diabetes_predic = None
    scaler = None

# ----------------------------------------------------
# 3. دوال الأمان والتحقق
# ----------------------------------------------------

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
    # يمكن إضافة check_login هنا لتحويل المستخدم مباشرة إلى dashboard إذا كان مسجلاً الدخول
    return render_template('index.html')
####

# ----------------------------------------------------
# 4. مسارات المستخدمين (تسجيل، دخول، خروج)
# ----------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_data = request.form
        username = user_data['username']
        email = user_data['email']
        password = user_data['password']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cur = mysql.connection.cursor()
        
        try:
            cur.execute("INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)", 
                        (username, email, hashed_password, 'user'))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('login'))
        except mysql.connection.IntegrityError:
            cur.close()
            return render_template('register.html', error='البريد الإلكتروني مسجل بالفعل.')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
    

        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id, username, password,role FROM users WHERE email = %s", [email])
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            if user['role']==1:
                flash('welcome admine','success')
                return redirect(url_for('manage_users'))
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='بيانات الاعتماد غير صحيحة.')
            
    return render_template('login.html')




@app.route('/dashboard')
@is_logged_in
def dashboard():
    user_id = session['user_id']
    username = session['username']
    
    cur = mysql.connection.cursor()
    
    # جلب جميع سجلات التنبؤات للمستخدم الحالي (السكري)
    cur.execute("""
        SELECT prediction, created_at 
        FROM diabetes_results
        WHERE user_id = %s 
        ORDER BY created_at DESC
    """, [user_id])
    diabetes_records = cur.fetchall()
    
    # جلب إحصائيات للمخططات (القلب)
    cur.execute("""
        SELECT prediction, created_at 
        FROM heart_results 
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, [user_id])
    heart_records = cur.fetchall()
    
    cur.close()

    all_results = [r['prediction'] for r in diabetes_records] + [r['prediction'] for r in heart_records]
    
    positive_count = all_results.count(1)
    negative_count = all_results.count(0)

    return render_template('dashboard.html', 
                           username=session['username'], 
                           diabetes_records=diabetes_records,
                           heart_records=heart_records,
                           positive_count=positive_count, 
                           negative_count=negative_count)


# ----------------------------------------------------
# 5. مسار التنبؤ (مع حفظ السجل)
# ----------------------------------------------------

@app.route('/predictdiabetes', methods=['GET', 'POST'])
@is_logged_in
def predictdiabetes():
    if request.method == 'POST' and diabetes_predic and scaler:
        try:
            # 📚 جمع البيانات من النموذج (8 ميزات لمرض السكري كمثال)
            feature_names = ['pregnancies', 'glucose', 'blood_pressure', 'skin_thickness', 
                             'insulin', 'bmi', 'diabetes_pedigree_function', 'age']
            
            features = [float(request.form[name]) for name in feature_names]
            
            # تخزين الإدخال كقاموس لـ JSON في قاعدة البيانات
            input_dict = dict(zip(feature_names, features))
            user_input = np.array([features])
            scaled_input = scaler.transform(user_input)

            # 4. إجراء التنبؤ
            prediction_value = int(diabetes_predic.predict(scaled_input)[0]) # 0 أو 1
            
            result_text = "إيجابية (خطر مرتفع)" if prediction_value == 1 else "سلبية (خطر منخفض)"
            result_class = "text-danger" if prediction_value == 1 else "text-success"

            # 5. حفظ سجل التنبؤ في MySQL
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO diabetes_results (user_id, prediction, created_at) VALUES (%s, %s, NOW())""",
                         (session['user_id'],  prediction_value))
            mysql.connection.commit()
            cur.close()

            # 6. عرض النتيجة
            return render_template('result.html', 
                                   prediction_text=result_text, 
                                   prediction_class=result_class)

        except Exception as e:
            print(f"Prediction Error: {e}")
            return render_template('predictdiabetes.html', error_message=f"خطأ في معالجة البيانات: {e}")

    return render_template('predictdiabetes.html')


#heart prediction route
@app.route('/predictheartdisease', methods=['GET', 'POST'])
def predictheartdisease():
    if request.method == 'POST':
        try:
            # ترتيب البيانات يجب أن يكون بنفس ترتيب أعمدة الـ DataFrame في الكولاب
            input_data = [
                float(request.form['Thallium']),
                float(request.form['Number of vessels fluro']),
                float(request.form['Slope of ST']),
                float(request.form['ST depression']),
                float(request.form['Exercise angina']),
                float(request.form['Max HR']),
                float(request.form['EKG results']),
                float(request.form['FBS over 120']),
                float(request.form['Cholesterol']),
                float(request.form['BP']),
                float(request.form['Chest pain type']),
                float(request.form['Sex']),
                float(request.form['Age'])
            ]
            
            # تحويل البيانات لشكل مصفوفة وعمل Scaling
            features = np.array([input_data])
            features_scaled =  heart_scaler.transform(features)
            
            # التوقع
            prediction = heart_model.predict(features_scaled)
            result = "لديك احتمالية إصابة" if prediction[0] == 1 else "النتائج سليمة"

            if 'user_id' in session:
                cur = mysql.connection.cursor()
                cur.execute("""INSERT INTO heart_results (user_id, prediction, created_at) VALUES (%s, %s, NOW())""", (session['user_id'], int(prediction[0])))
                mysql.connection.commit()
                cur.close()
            
            return render_template('predictheartdisease.html', prediction_text=result)
        except Exception as e:
            return render_template('predictheartdisease.html', prediction_text=f"خطأ في البيانات: {str(e)}")

    return render_template('predictheartdisease.html')

   

   
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 1:
            flash("عذراً، هذه الصفحة مخصصة للمدير فقط.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# 2. مسار إدارة المستخدمين (عرض وحذف)
@app.route('/admin/users')
@admin_required
def manage_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id, username, email, role FROM users")
    users = cur.fetchall()
    cur.close()
    return render_template('admin_users.html', users=users)

@app.route('/delete_user/<string:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE user_id = %s", [user_id])
    mysql.connection.commit()
    cur.close()
    flash("تم حذف المستخدم بنجاح", "success")
    return redirect(url_for('manage_users'))

# 3. مسار إدارة البيانات (عرض نتائج الفحوصات)
@app.route('/admin/view_data')
@admin_required
def view_data():
    cur = mysql.connection.cursor()
    
    # جلب نتائج السكري 
    cur.execute("""
        SELECT users.username, diabetes_results.prediction, diabetes_results.created_at 
        FROM diabetes_results 
        JOIN users ON diabetes_results.user_id = users.user_id
    """)
    diabetes_data = cur.fetchall()

    # جلب نتائج القلب 
    cur.execute("""
        SELECT users.username, heart_results.prediction, heart_results.created_at 
        FROM heart_results 
        JOIN users ON heart_results.user_id = users.user_id
    """)
    heart_data = cur.fetchall()
    
    cur.close()
    return render_template('admin_data.html', diabetes=diabetes_data, heart=heart_data)




@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True)