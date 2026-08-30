(() => {
  const form = document.querySelector("#survey-form");
  if (!form) return;
  const fields = [...form.querySelectorAll(".question")];
  const count = document.querySelector("#answered-count");
  const fill = document.querySelector("#progress-fill");
  const summary = document.querySelector("#validation-summary");

  function answered(question) {
    const inputs = [...question.querySelectorAll("input, textarea, select")].filter(
      (input) => input.name && input.name !== "csrfmiddlewaretoken"
    );
    return inputs.some((input) =>
      ["radio", "checkbox"].includes(input.type) ? input.checked : input.value.trim()
    );
  }

  function update() {
    const completed = fields.filter(answered).length;
    count.textContent = completed;
    fill.style.width = `${fields.length ? (completed / fields.length) * 100 : 0}%`;
  }

  function clearError(question) {
    question.classList.remove("invalid");
    question.querySelectorAll(".field-error").forEach((error) => error.remove());
    question.querySelectorAll("input, textarea, select").forEach((input) =>
      input.removeAttribute("aria-invalid")
    );
  }

  function markError(question) {
    question.classList.add("invalid");
    question.querySelectorAll("input, textarea, select").forEach((input) =>
      input.setAttribute("aria-invalid", "true")
    );
    if (!question.querySelector(".field-error")) {
      const error = document.createElement("div");
      error.className = "field-error client-field-error";
      error.setAttribute("role", "alert");
      error.textContent = "请完成此必填项";
      question.append(error);
    }
  }

  function refreshSummary() {
    const remaining = fields.filter(
      (question) => question.dataset.required === "true" && !answered(question)
    );
    if (!remaining.length) {
      summary.hidden = true;
    } else if (!summary.hidden) {
      summary.querySelector("strong").textContent = `还有 ${remaining.length} 个必填项未完成`;
    }
    return remaining;
  }

  function goTo(question) {
    question.scrollIntoView({ behavior: "smooth", block: "start" });
    const input = question.querySelector("input, textarea, select");
    window.setTimeout(() => input?.focus({ preventScroll: true }), 350);
  }

  form.addEventListener("input", (event) => {
    const question = event.target.closest(".question");
    if (question && answered(question)) clearError(question);
    if (!summary.hidden) refreshSummary();
    update();
  });
  form.addEventListener("change", (event) => {
    const question = event.target.closest(".question");
    if (question && answered(question)) clearError(question);
    if (!summary.hidden) refreshSummary();
    update();
  });
  form.addEventListener("submit", (event) => {
    const missing = fields.filter(
      (question) => question.dataset.required === "true" && !answered(question)
    );
    if (!missing.length) return;
    event.preventDefault();
    missing.forEach(markError);
    summary.hidden = false;
    refreshSummary();
    goTo(missing[0]);
  });

  update();
  const serverError = form.querySelector(".question.invalid");
  if (serverError) goTo(serverError);
})();
