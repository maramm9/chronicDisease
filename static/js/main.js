function addSymptom() {
    const container = document.getElementById('symptoms-container');
    const template = document.getElementById('symptom-template').innerHTML;
    const div = document.createElement('div');
    div.innerHTML = template;
    container.appendChild(div.firstElementChild);
    updateOptions(); // تحديث الخيارات بعد الإضافة
}

function updateOptions() {
    const selects = document.querySelectorAll('select[name="symptoms[]"]');
    
    // اجمع كل القيم المختارة
    const selected = [];
    selects.forEach(select => {
        if (select.value) selected.push(select.value);
    });

    //  selects أخفي القيم المختارة من باقي الـ 
    selects.forEach(select => {
        const currentVal = select.value;
        select.querySelectorAll('option').forEach(option => {
            if (option.value === '') return; // خلي الـ placeholder
            if (selected.includes(option.value) && option.value !== currentVal) {
                option.style.display = 'none';
            } else {
                option.style.display = '';
            }
        });
    });
}

// نفّذ عند كل تغيير
document.addEventListener('change', function(e) {
    if (e.target.name === 'symptoms[]') {
        updateOptions();
    }
});




/** تابع إضافة عرض جديد */
const MAX_SYMPTOMS = 7;
  function addSymptom() {
  const container = document.getElementById("symptoms-container");
  const currentCount = container.querySelectorAll('.symptom-item').length;

  if (currentCount >= MAX_SYMPTOMS) {
    alert("لا يمكن إدخال أكثر من 7 أعراض");
    return;
  }
  const template = document.getElementById("symptom-template").innerHTML;
  container.insertAdjacentHTML("beforeend", template);
}
