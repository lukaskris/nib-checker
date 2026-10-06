const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const pickBtn = document.getElementById("pickBtn");
const scanOverlay = document.getElementById("scanOverlay");
const scanFile = document.getElementById("scanFile");
const dialog = document.getElementById("resultDialog");
const verdict = document.getElementById("verdict");
const verdictStamp = document.getElementById("verdictStamp");
const verdictSub = document.getElementById("verdictSub");
const dataRows = document.getElementById("dataRows");
const errorNote = document.getElementById("errorNote");
const againBtn = document.getElementById("againBtn");

function row(dt, dd, mono = false) {
  const div = document.createElement("div");
  const t = document.createElement("dt");
  t.textContent = dt;
  const d = document.createElement("dd");
  if (mono) d.classList.add("mono");
  d.textContent = dd;
  div.append(t, d);
  return div;
}

function rowPill(dt, text, ok) {
  const div = document.createElement("div");
  const t = document.createElement("dt");
  t.textContent = dt;
  const d = document.createElement("dd");
  const pill = document.createElement("span");
  pill.className = "pill " + (ok ? "ok" : "bad");
  pill.textContent = text;
  d.append(pill);
  div.append(t, d);
  return div;
}

function renderResult(r) {
  dataRows.innerHTML = "";

  const status = r.error
    ? "fail"
    : r.nib_valid && r.nama_match?.is_match
      ? "pass"
      : r.nib_valid
        ? "partial"
        : "fail";
  verdict.className = "verdict " + status;

  if (status === "pass") {
    verdictStamp.textContent = "Verified";
    verdictSub.textContent = "The NIB is registered with OSS RBA and the company name matches the document.";
  } else if (status === "partial") {
    verdictStamp.textContent = "Needs review";
    verdictSub.textContent = "The NIB is registered, but the name in the document differs from the OSS RBA record.";
  } else if (!r.error) {
    verdictStamp.textContent = "Not valid";
    verdictSub.textContent = "The NIB was not found in the OSS RBA service.";
  } else {
    verdictStamp.textContent = "Failed";
    verdictSub.textContent = "The check did not complete.";
  }

  if (r.file) dataRows.append(row("File", r.file));
  if (r.nib) dataRows.append(row("NIB", r.nib, true));
  if (r.nama_pdf) dataRows.append(row("Name in document", r.nama_pdf));
  if (r.oss_data?.nama) dataRows.append(row("Name on OSS RBA", r.oss_data.nama));
  if (r.oss_data?.status_aktif)
    dataRows.append(rowPill("Status", r.oss_data.status_aktif, r.oss_data.status_aktif.toLowerCase() === "aktif"));
  if (r.judul_dokumen) dataRows.append(row("Document title", r.judul_dokumen));
  if (r.page_count) dataRows.append(row("Pages", String(r.page_count)));
  if (r.alamat_pdf) dataRows.append(row("Address (from document)", r.alamat_pdf));

  errorNote.hidden = !r.error;
  if (r.error) errorNote.textContent = r.error;

  scanOverlay.hidden = true;
  dialog.showModal();
}

function showError(message) {
  verdict.className = "verdict fail";
  verdictStamp.textContent = "Failed";
  verdictSub.textContent = "The check did not complete.";
  dataRows.innerHTML = "";
  errorNote.hidden = false;
  errorNote.textContent = message;
  scanOverlay.hidden = true;
  dialog.showModal();
}

async function check(file) {
  dropzone.hidden = true;
  scanOverlay.hidden = false;
  scanFile.textContent = file.name;

  const fd = new FormData();
  fd.append("file", file, file.name);

  try {
    const res = await fetch("/api/check", { method: "POST", body: fd });
    if (!res.ok) {
      const msg = await res.text();
      throw new Error(msg || `HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let result = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) !== -1) {
        const line = buf.slice(0, nl).trim();
        buf = buf.slice(nl + 1);
        if (!line) continue;
        const ev = JSON.parse(line);
        if (ev.phase === "result") result = ev.data;
      }
    }

    if (!result) throw new Error("Connection dropped before the result arrived.");
    renderResult(result);
  } catch (err) {
    showError(err.message);
  }
}

function handleFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf") || file.type !== "application/pdf") {
    showError("Only PDF files are supported.");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showError("The file exceeds 10 MB.");
    return;
  }
  check(file);
}

function reset() {
  dialog.close();
  fileInput.value = "";
}

// any close path (button, ESC) restores the dropzone
dialog.addEventListener("close", () => {
  scanOverlay.hidden = true;
  dropzone.hidden = false;
});

["dragenter", "dragover"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => handleFile(e.dataTransfer.files[0]));
dropzone.addEventListener("click", (e) => {
  if (e.target !== pickBtn) fileInput.click();
});
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});
pickBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  fileInput.click();
});
fileInput.addEventListener("change", () => handleFile(fileInput.files[0]));
againBtn.addEventListener("click", reset);
