(() => {
  const form = document.querySelector("#apply-form");
  if (!form) return;
  const list = document.querySelector("#attendee-list");
  const total = document.querySelector("#id_attendees-TOTAL_FORMS");
  const attendeeCount = document.querySelector("#attendee-count");
  const template = document.querySelector("#attendee-template");
  const alertBox = document.querySelector("#apply-alert");
  const issueCount = document.querySelector("#issue-count");
  const issueLimit = document.querySelector("#issue-limit");

  function activeAttendees() {
    return [...list.querySelectorAll(".attendee-item")].filter((item) => !item.hidden);
  }

  function refreshAttendees() {
    const active = activeAttendees();
    active.forEach((item, index) => {
      item.querySelector(".attendee-number").textContent = index + 1;
      item.querySelector(".remove-attendee").hidden = active.length === 1;
    });
    attendeeCount.textContent = active.length;
  }

  document.querySelector("#add-attendee").addEventListener("click", () => {
    const index = Number(total.value);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = template.innerHTML.replaceAll("__prefix__", index).trim();
    list.append(wrapper.firstElementChild);
    total.value = index + 1;
    refreshAttendees();
  });

  list.addEventListener("click", (event) => {
    const button = event.target.closest(".remove-attendee");
    if (!button || activeAttendees().length === 1) return;
    const item = button.closest(".attendee-item");
    const deleteInput = item.querySelector('input[name$="-DELETE"]');
    if (deleteInput) deleteInput.checked = true;
    item.querySelectorAll("input:not([name$='-DELETE'])").forEach((input) => {
      input.disabled = true;
    });
    item.hidden = true;
    refreshAttendees();
  });

  const issueInputs = [...form.querySelectorAll('input[name="priority_issues"]')];
  issueInputs.forEach((input) => input.addEventListener("change", () => {
    const checked = issueInputs.filter((item) => item.checked);
    if (checked.length > 3) {
      input.checked = false;
      issueLimit.hidden = false;
    } else {
      issueLimit.hidden = true;
    }
    issueCount.textContent = issueInputs.filter((item) => item.checked).length;
  }));

  form.addEventListener("input", (event) => {
    const container = event.target.closest(".apply-field, .attendee-item");
    if (container && event.target.checkValidity()) {
      container.classList.remove("invalid");
      container.querySelectorAll(".client-error").forEach((error) => error.remove());
    }
  });

  form.addEventListener("submit", (event) => {
    form.querySelectorAll(".client-error").forEach((error) => error.remove());
    form.querySelectorAll(".invalid").forEach((item) => item.classList.remove("invalid"));
    const invalidInputs = [...form.querySelectorAll(":invalid")].filter(
      (input) => !input.disabled && !input.closest("[hidden]")
    );
    const containers = [...new Set(invalidInputs.map((input) =>
      input.closest(".apply-field, .attendee-item")
    ).filter(Boolean))];
    if (!issueInputs.some((input) => input.checked)) {
      containers.push(document.querySelector(".issue-field"));
    }
    if (!containers.length) return;
    event.preventDefault();
    containers.forEach((container) => {
      container.classList.add("invalid");
      if (!container.querySelector(".apply-error")) {
        const error = document.createElement("p");
        error.className = "apply-error client-error";
        error.textContent = "请完成此必填项";
        container.append(error);
      }
    });
    alertBox.hidden = false;
    alertBox.querySelector("strong").textContent = `还有 ${containers.length} 处信息未完成`;
    containers[0].scrollIntoView({behavior: "smooth", block: "center"});
    window.setTimeout(() => (invalidInputs[0] || issueInputs[0])?.focus({preventScroll: true}), 350);
  });

  refreshAttendees();
  issueCount.textContent = issueInputs.filter((input) => input.checked).length;
  const serverError = form.querySelector(".invalid");
  if (serverError) window.setTimeout(() => serverError.scrollIntoView({block: "center"}), 80);
})();
