document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('predictForm');
  if (form) {
    form.addEventListener('submit', async function (e) {
      e.preventDefault();

      const formData = new FormData(form);
      const data = {};
      formData.forEach((value, key) => data[key] = parseFloat(value));

      const resultBox = document.getElementById('resultBox');
      resultBox.classList.remove('d-none');
      resultBox.classList.add('alert-info');
      resultBox.textContent = "⏳ يتم تحليل البيانات ...";

      const response = await fetch('/predict_api', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
      });

      const result = await response.json();
      resultBox.classList.remove('alert-info');
      resultBox.classList.add(result.result.includes("سليم") ? 'alert-success' : 'alert-danger');
      resultBox.textContent = result.result;
    });
  }
});