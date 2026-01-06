import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score

df = pd.read_csv("C:\\Python\\flaskapps\\chronic_disease_dataset.csv", sep=';')

disease_names = {
    0: 'سليم',
    1: 'اضطراب القلب والأوعية الدموية',
    2: 'السكري',
    3: 'السرطان',
    4: 'حالات متعددة'
}

X = df.drop('target', axis=1)
y = df['target']


X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)


numerical_cols = X.columns
scaler = StandardScaler()


X_train[numerical_cols] = scaler.fit_transform(X_train[numerical_cols])
X_test[numerical_cols] = scaler.transform(X_test[numerical_cols])

print("✅ تم تقسيم وتحضير البيانات بنجاح.")

log_reg = LogisticRegression(max_iter=1000, random_state=42)
log_reg.fit(X_train, y_train)

dt_classifier = DecisionTreeClassifier(random_state=42)
dt_classifier.fit(X_train, y_train)

mlp_classifier = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42, early_stopping=True)
mlp_classifier.fit(X_train, y_train)


models = {
    "الانحدار اللوجستي": log_reg,
    "شجرة القرار": dt_classifier,
    "الشبكة العصبونية (MLP)": mlp_classifier
}

results = {}
predictions_df = pd.DataFrame(y_test).reset_index(drop=True)
predictions_df.rename(columns={'target': 'الفئة الحقيقية (رقم)'}, inplace=True)
predictions_df['الفئة الحقيقية (اسم)'] = predictions_df['الفئة الحقيقية (رقم)'].map(disease_names)

print("\n--- نتائج دقة النماذج ---")
for name, model in models.items():
    # التنبؤ على بيانات الاختبار
    y_pred = model.predict(X_test)

    # حساب الدقة
    accuracy = accuracy_score(y_test, y_pred)
    results[name] = accuracy

    # إضافة التنبؤات بالاسم إلى جدول النتائج
    predictions_df[f'تنبؤ {name} (رقم)'] = y_pred
    predictions_df[f'تنبؤ {name} (اسم)'] =pd.Series(y_pred).map(disease_names)

    print(f"{name}: الدقة = {accuracy:.4f}")

print("\nالشبكة العصبونية (MLP) حققت أعلى دقة في هذا التدريب.")

import pickle
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
import numpy as np

best_model = dt_classifier
data_scaler = scaler

model_filename = 'best_decision_tree_model.pkl'
with open(model_filename, 'wb') as file:
    pickle.dump(best_model, file)

scaler_filename = 'scaler.pkl'
with open(scaler_filename, 'wb') as file:
    pickle.dump(data_scaler, file)

disease_names = {
    0: 'سليم',
    1: 'اضطراب القلب والأوعية الدموية',
    2: 'السكري',
    3: 'السرطان',
    4: 'حالات متعددة'
}
names_filename = 'disease_names_map.pkl'
with open(names_filename, 'wb') as file:
    pickle.dump(disease_names, file)

print(f"✅ تم حفظ أفضل نموذج (شجرة القرار) في الملف: {model_filename}")
print(f"✅ تم حفظ مُوَحِّد المقاييس في الملف: {scaler_filename}")
print(f"✅ تم حفظ خريطة أسماء الأمراض في الملف: {names_filename}")

with open('best_decision_tree_model.pkl', 'rb') as file:
    loaded_model = pickle.load(file)

with open('scaler.pkl', 'rb') as file:
    loaded_scaler = pickle.load(file)

with open('disease_names_map.pkl', 'rb') as file:
    loaded_disease_names = pickle.load(file)

# age, gender, bmi, blood_pressure, ..., biomarker_D
new_patient_data = np.array([[
    55, 0, 25.5, 120, 200, 100, 2.5, 1, 1.0, 0,
    50.0, 90.0, 70.0, 110.0
]])

# 2. تحضير البيانات: تطبيق نفس توحيد المقاييس (Standardization)
# يتم استخدام loaded_scaler لتطبيق التحويل، وليس fit_transform
scaled_new_data = loaded_scaler.transform(new_patient_data)

# 3. التنبؤ
prediction_code = loaded_model.predict(scaled_new_data)[0]

# 4. تحويل التنبؤ إلى اسم
predicted_disease_name = loaded_disease_names[prediction_code]

print(f"\n⬅️ رمز التنبؤ الرقمي: {prediction_code}")
print(f"✨ اسم المرض المتوقع للمريض الجديد هو: {predicted_disease_name}")
