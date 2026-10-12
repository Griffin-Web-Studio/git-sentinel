(function () {
  const pages = {
    welcome: document.getElementById("page-welcome"),
    options: document.getElementById("page-options"),
    installing: document.getElementById("page-installing"),
    finish: document.getElementById("page-finish"),
  };

  const welcomeText = document.getElementById("welcome-text");
  const shortcutRow = document.getElementById("shortcut-row");
  const shortcutCheckbox = document.getElementById("shortcut-checkbox");
  const noOptionsText = document.getElementById("no-options-text");
  const installLog = document.getElementById("install-log");
  const runFirstScanCheckbox = document.getElementById(
    "run-first-scan-checkbox"
  );

  const confirmDialog = document.getElementById("confirm-dialog");
  const confirmText = document.getElementById("confirm-text");

  function showPage(step) {
    for (const key in pages) {
      pages[key].hidden = key !== step;
    }
  }

  window.bus.on("wizard.render", (m) => {
    showPage(m.step);

    if (m.step === "welcome") {
      welcomeText.textContent = m.welcome_text;
    } else if (m.step === "options") {
      shortcutRow.hidden = !m.supports_desktop_shortcut;
      noOptionsText.hidden = m.supports_desktop_shortcut;
      shortcutCheckbox.checked = m.desktop_shortcut;
    } else if (m.step === "installing") {
      installLog.innerHTML = "";
    } else if (m.step === "finish") {
      runFirstScanCheckbox.checked = m.run_first_scan;
    }
  });

  window.bus.on("installer.log", (m) => {
    if (!m.text) return;

    const line = document.createElement("div");
    line.textContent = m.text;
    installLog.appendChild(line);
    installLog.scrollTop = installLog.scrollHeight;
  });

  window.bus.on("installer.confirm", (payload) => {
    confirmText.textContent = payload.prompt;
    confirmDialog.showModal();
  });

  document.getElementById("confirm-yes-btn").onclick = () => {
    confirmDialog.close();
    pywebview.api.resolve_confirm(true);
  };
  document.getElementById("confirm-no-btn").onclick = () => {
    confirmDialog.close();
    pywebview.api.resolve_confirm(false);
  };

  document.getElementById("welcome-cancel-btn").onclick = () =>
    pywebview.api.close();
  document.getElementById("welcome-next-btn").onclick = () =>
    pywebview.api.advance();

  document.getElementById("options-cancel-btn").onclick = () =>
    pywebview.api.close();
  document.getElementById("options-back-btn").onclick = () =>
    pywebview.api.back();
  document.getElementById("options-install-btn").onclick = () =>
    pywebview.api.begin_install();

  shortcutCheckbox.onchange = () =>
    pywebview.api.set_desktop_shortcut(shortcutCheckbox.checked);
  runFirstScanCheckbox.onchange = () =>
    pywebview.api.set_run_first_scan(runFirstScanCheckbox.checked);

  document.getElementById("release-notes-btn").onclick = () =>
    pywebview.api.open_release_notes();
  document.getElementById("finish-btn").onclick = () => pywebview.api.close();
})();
