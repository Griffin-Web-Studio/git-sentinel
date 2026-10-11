(function () {
  const statusEl = document.getElementById("status");
  const progressEl = document.getElementById("progress");
  const logEl = document.getElementById("log");
  const promptArea = document.getElementById("prompt-area");
  const openReportBtn = document.getElementById("open-report-btn");
  const closeBtn = document.getElementById("close-btn");
  const migrationDialog = document.getElementById("migration-dialog");
  const migrationSteps = document.getElementById("migration-steps");
  const migrationConfPath = document.getElementById("migration-conf-path");
  const migrationUpdateBtn = document.getElementById("migration-update-btn");
  const migrationDismissBtn = document.getElementById(
    "migration-dismiss-btn"
  );

  let reportPath = null;

  function appendLog(text, tag) {
    const line = document.createElement("div");
    line.textContent = text;
    if (tag) line.classList.add("log-" + tag);
    logEl.appendChild(line);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function clearGate() {
    promptArea.hidden = true;
    promptArea.innerHTML = "";
  }

  function renderSshGate(payload) {
    promptArea.innerHTML =
      '<div class="gate-banner">' +
      "<strong>SSH Authorisation Required</strong>" +
      "<pre>Repository : " +
      payload.repo +
      "\nRemote URL : " +
      payload.url +
      "</pre>" +
      "<p>Approving will open an SSH connection. Authentication will be " +
      "needed once for this host; further connections this session reuse " +
      "the control socket.</p>" +
      '<div class="button-row">' +
      '<button class="btn" id="gate-skip">Skip this host</button>' +
      '<button class="btn btn-primary" id="gate-approve">Approve</button>' +
      "</div></div>";

    document.getElementById("gate-approve").onclick = () => {
      pywebview.api.resolve_ssh(true);
      clearGate();
    };
    document.getElementById("gate-skip").onclick = () => {
      pywebview.api.resolve_ssh(false);
      clearGate();
    };
  }

  function renderHttpGate(payload) {
    promptArea.innerHTML =
      '<div class="gate-banner">' +
      "<strong>HTTP Remote Unreachable</strong>" +
      "<pre>Repository : " +
      payload.repo +
      "\nRemote URL : " +
      payload.url +
      "\nError      : " +
      payload.error +
      "</pre>" +
      "<p>Retry the connection, or skip this remote?</p>" +
      '<div class="button-row">' +
      '<button class="btn" id="gate-skip">Skip</button>' +
      '<button class="btn btn-primary" id="gate-retry">Retry</button>' +
      "</div></div>";

    document.getElementById("gate-retry").onclick = () => {
      pywebview.api.resolve_http(true);
      clearGate();
    };
    document.getElementById("gate-skip").onclick = () => {
      pywebview.api.resolve_http(false);
      clearGate();
    };
  }

  window.bus.on("scan.log", (m) => appendLog(m.text, m.tag));
  window.bus.on("scan.status", (m) => {
    statusEl.textContent = m.text;
  });
  window.bus.on("scan.progress", (m) => {
    progressEl.value = m.pct;
  });

  window.bus.on("scan.gate", (payload) => {
    promptArea.hidden = false;

    if (payload.kind === "ssh") {
      renderSshGate(payload);
    } else {
      renderHttpGate(payload);
    }
  });

  window.bus.on("scan.finish", (m) => {
    progressEl.value = 100;

    if (m.issue_count === 0) {
      statusEl.textContent = "✔️ All clear - no issues found.";
      closeBtn.textContent = "Close";
    } else {
      statusEl.textContent =
        "⚠️ " +
        m.issue_count +
        " repo(s) with issues - report saved to" +
        m.location +
        ".";
      closeBtn.textContent = "Acknowledge & Close";

      if (m.report_path) {
        reportPath = m.report_path;
        openReportBtn.hidden = false;
      }
    }

    closeBtn.disabled = false;
  });

  window.bus.on("migration.pending", (m) => {
    migrationSteps.textContent = m.steps
      .map(
        (s) =>
          "v" +
          s.from_version +
          " to v" +
          s.to_version +
          (s.description ? ": " + s.description : "")
      )
      .join("\n");
    migrationConfPath.textContent = "Settings file: " + m.conf_file;
    migrationDialog.showModal();
  });

  migrationUpdateBtn.onclick = () => {
    pywebview.api.apply_migrations().then((result) => {
      if (!result.ok) {
        alert("Could not update settings.ini:\n" + result.error);
        return;
      }

      migrationDialog.close();
    });
  };

  migrationDismissBtn.onclick = () => {
    migrationDialog.close();
    pywebview.api.dismiss_migration();
  };

  openReportBtn.onclick = () => {
    if (reportPath) pywebview.api.open_report(reportPath);
  };

  closeBtn.onclick = () => pywebview.api.close();
})();
