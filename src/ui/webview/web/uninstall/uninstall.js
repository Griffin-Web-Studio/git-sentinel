(function () {
  const pageConfirm = document.getElementById("page-confirm");
  const pageProgress = document.getElementById("page-progress");
  const uninstallLog = document.getElementById("uninstall-log");
  const closeBtn = document.getElementById("progress-close-btn");

  const confirmDialog = document.getElementById("confirm-dialog");
  const confirmDialogText = document.getElementById("confirm-dialog-text");

  window.bus.on("uninstall.started", () => {
    pageConfirm.hidden = true;
    pageProgress.hidden = false;
  });

  window.bus.on("installer.log", (m) => {
    if (!m.text) return;

    const line = document.createElement("div");
    line.textContent = m.text;
    uninstallLog.appendChild(line);
    uninstallLog.scrollTop = uninstallLog.scrollHeight;
  });

  window.bus.on("installer.confirm", (payload) => {
    confirmDialogText.textContent = payload.prompt;
    confirmDialog.showModal();
  });

  window.bus.on("uninstall.finish", () => {
    closeBtn.textContent = "Close";
    closeBtn.disabled = false;
  });

  document.getElementById("confirm-dialog-yes-btn").onclick = () => {
    confirmDialog.close();
    pywebview.api.resolve_confirm(true);
  };
  document.getElementById("confirm-dialog-no-btn").onclick = () => {
    confirmDialog.close();
    pywebview.api.resolve_confirm(false);
  };

  document.getElementById("confirm-cancel-btn").onclick = () =>
    pywebview.api.close();
  document.getElementById("confirm-uninstall-btn").onclick = () =>
    pywebview.api.begin_uninstall();
  closeBtn.onclick = () => pywebview.api.close();
})();
