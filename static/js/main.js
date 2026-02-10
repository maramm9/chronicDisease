const selects = document.querySelectorAll("select");
selects.forEach((sel, i) => {
    sel.addEventListener("change", function() {
        selects.forEach((s, j) => {
            if(i !== j) {
                const option = s.querySelector(option[value="${this.value}"]);
                if(option) option.disabled = true;
            }
        });
    });
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
