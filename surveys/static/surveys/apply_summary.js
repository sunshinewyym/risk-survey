(() => {
  const text = document.querySelector("#registration-summary")?.textContent || "";
  const copy = document.querySelector("#copy-summary");
  if (!copy) return;
  copy.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(text);
      copy.textContent = "已复制 ✓";
      window.setTimeout(() => copy.textContent = "一键复制", 1500);
    } catch (error) {
      alert("复制失败，请手动长按选择复制");
    }
  });
  document.querySelector("#print-summary").addEventListener("click", () => window.print());
})();
