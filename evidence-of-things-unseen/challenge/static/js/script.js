(() => {
  const MAX_BYTES = 10 * 1024 * 1024;
  const form = document.getElementById("uploadForm");
  const fileInput = document.getElementById("fileInput");
  const dropzone = document.getElementById("dropzone");
  const preview = document.getElementById("preview");
  const previewImage = document.getElementById("previewImage");
  const previewName = document.getElementById("previewName");
  const previewSize = document.getElementById("previewSize");
  const previewType = document.getElementById("previewType");
  const submitBtn = document.getElementById("submitBtn");
  const resetBtn = document.getElementById("resetBtn");
  const progressWrap = document.getElementById("progressWrap");
  const progressBar = document.getElementById("progressBar");
  const resultPill = document.getElementById("resultPill");
  const resultSummary = document.getElementById("resultSummary");
  const scoreGrid = document.getElementById("scoreGrid");
  const templateScore = document.getElementById("templateScore");
  const editScore = document.getElementById("editScore");
  const overallScore = document.getElementById("overallScore");
  const feedbackList = document.getElementById("feedbackList");
  const regionTableBody = document.getElementById("regionTableBody");
  const flagWrap = document.getElementById("flagWrap");
  const flagValue = document.getElementById("flagValue");
  const formState = document.getElementById("formState");
  const helpBtn = document.getElementById("helpBtn");
  const helpDialog = document.getElementById("helpDialog");

  let selectedFile = null;
  let objectUrl = null;

  function humanSize(bytes) {
    if (!Number.isFinite(bytes) || bytes < 1) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    let value = bytes;
    let index = 0;

    while (value >= 1024 && index < units.length - 1) {
      value /= 1024;
      index += 1;
    }

    return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
  }

  function setPill(type, text) {
    resultPill.className = `pill ${type}`;
    resultPill.textContent = text;
  }

  function setFormState(type, text) {
    formState.className = `pill ${type}`;
    formState.textContent = text;
  }

  function resetPreview() {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = null;
    }

    previewImage.removeAttribute("src");
  }

  function resetResults() {
    setPill("neutral", "Idle");
    resultSummary.textContent = "No submission yet.";
    scoreGrid.hidden = true;
    flagWrap.hidden = true;
    flagValue.textContent = "";
    feedbackList.innerHTML = "<li>Submit an invoice image to begin.</li>";
    regionTableBody.innerHTML =
      '<tr><td colspan="4" class="muted-cell">No region data yet.</td></tr>';
  }

  function resetForm() {
    selectedFile = null;
    fileInput.value = "";
    preview.hidden = true;
    submitBtn.disabled = true;
    resetBtn.disabled = true;
    progressWrap.hidden = true;
    progressBar.style.width = "0%";
    setFormState("neutral", "Waiting");
    resetPreview();
    resetResults();
  }

  function renderPreview(file) {
    preview.hidden = false;
    previewName.textContent = file.name || "Unnamed file";
    previewSize.textContent = humanSize(file.size || 0);
    previewType.textContent = file.type || "Unknown type";

    resetPreview();

    objectUrl = URL.createObjectURL(file);
    previewImage.src = objectUrl;
  }

  function selectFile(file) {
    if (!file) return;

    selectedFile = file;
    renderPreview(file);
    resetBtn.disabled = false;

    if (file.size > MAX_BYTES) {
      submitBtn.disabled = true;
      setFormState("warn", "Too large");
      setPill("warn", "File too large");
      resultSummary.textContent = "That file exceeds the 10 MiB upload limit.";
      return;
    }

    submitBtn.disabled = false;
    setFormState("neutral", "Ready");
    setPill("neutral", "Ready");
    resultSummary.textContent = "File selected. Submit when ready.";
  }

  function setFeedback(items) {
    feedbackList.innerHTML = "";

    if (!items || !items.length) {
      feedbackList.innerHTML = "<li>No feedback returned.</li>";
      return;
    }

    for (const item of items) {
      const li = document.createElement("li");
      li.textContent = item;
      feedbackList.appendChild(li);
    }
  }

  function formatScore(value) {
    const num = Number(value);
    return Number.isFinite(num) ? num.toFixed(3) : "0.000";
  }

  function renderRegionTable(regionScores) {
    regionTableBody.innerHTML = "";

    const entries = Object.entries(regionScores || {});
    if (!entries.length) {
      regionTableBody.innerHTML =
        '<tr><td colspan="4" class="muted-cell">No region data returned.</td></tr>';
      return;
    }

    for (const [name, values] of entries) {
      const row = document.createElement("tr");

      const nameCell = document.createElement("td");
      nameCell.textContent = name;

      const targetCell = document.createElement("td");
      targetCell.textContent = formatScore(values.target_similarity);

      const wornCell = document.createElement("td");
      wornCell.textContent = formatScore(values.worn_similarity);

      const deltaCell = document.createElement("td");
      deltaCell.textContent = formatScore(values.delta);

      row.appendChild(nameCell);
      row.appendChild(targetCell);
      row.appendChild(wornCell);
      row.appendChild(deltaCell);
      regionTableBody.appendChild(row);
    }
  }

  function renderResponse(payload) {
    scoreGrid.hidden = false;

    templateScore.textContent = formatScore(payload.layout_score);
    editScore.textContent = formatScore(payload.edit_score);
    overallScore.textContent = formatScore(payload.overall_score);

    setFeedback(payload.feedback || []);
    renderRegionTable(payload.region_scores || {});

    if (payload.passed) {
      setPill("ok", "Passed");
      setFormState("ok", "Accepted");
      resultSummary.textContent =
        payload.message || "The invoice passed verification.";

      if (payload.flag) {
        flagWrap.hidden = false;
        flagValue.textContent = payload.flag;
      } else {
        flagWrap.hidden = true;
        flagValue.textContent = "";
      }

      return;
    }

    flagWrap.hidden = true;
    flagValue.textContent = "";
    setPill("bad", "Rejected");
    setFormState("warn", "Try again");
    resultSummary.textContent =
      payload.message || "The invoice did not pass verification.";
  }

  function handleFiles(fileList) {
    if (!fileList || !fileList.length) return;
    selectFile(fileList[0]);
  }

  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
    handleFiles(event.dataTransfer.files);
  });

  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", (event) => {
    handleFiles(event.target.files);
  });

  resetBtn.addEventListener("click", resetForm);

  helpBtn.addEventListener("click", () => {
    if (typeof helpDialog.showModal === "function") {
      helpDialog.showModal();
    }
  });

  helpDialog.addEventListener("click", (event) => {
    const rect = helpDialog.getBoundingClientRect();
    const inside =
      event.clientX >= rect.left &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom;

    if (!inside) {
      helpDialog.close();
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!selectedFile || selectedFile.size > MAX_BYTES) {
      return;
    }

    submitBtn.disabled = true;
    resetBtn.disabled = true;
    progressWrap.hidden = false;
    progressBar.style.width = "18%";
    setPill("neutral", "Uploading");
    setFormState("neutral", "Checking");
    resultSummary.textContent = "Submitting invoice for verification...";

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("/submit", {
        method: "POST",
        body: formData
      });

      progressBar.style.width = "78%";

      const payload = await response.json();
      progressBar.style.width = "100%";

      if (!response.ok) {
        setPill("bad", "Error");
        setFormState("bad", "Error");
        resultSummary.textContent = payload.error || "Request failed.";
        setFeedback(payload.feedback || ["The request could not be processed."]);
        scoreGrid.hidden = true;
        flagWrap.hidden = true;
        return;
      }

      renderResponse(payload);
    } catch (error) {
      setPill("bad", "Network error");
      setFormState("bad", "Error");
      resultSummary.textContent = "The request could not be completed.";
      setFeedback(["Check the server and try again."]);
      scoreGrid.hidden = true;
      flagWrap.hidden = true;
    } finally {
      submitBtn.disabled = false;
      resetBtn.disabled = false;
    }
  });

  resetForm();
})();