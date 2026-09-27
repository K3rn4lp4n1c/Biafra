(() => {
  const API_ENDPOINT = "/metadata";
  const MAX_FILE_BYTES = 50 * 1024 * 1024;

  const form = document.getElementById("analyzeForm");
  const fileInput = document.getElementById("fileInput");
  const dropzone = document.getElementById("dropzone");
  const submitBtn = document.getElementById("submitBtn");
  const resetBtn = document.getElementById("resetBtn");

  const preview = document.getElementById("preview");
  const thumb = document.getElementById("thumb");
  const fileBadge = document.getElementById("fileBadge");
  const fileName = document.getElementById("fileName");
  const fileSize = document.getElementById("fileSize");
  const fileType = document.getElementById("fileType");

  const progressWrap = document.getElementById("progressWrap");
  const progressBar = document.getElementById("progress");

  const resultCard = document.getElementById("resultCard");
  const pill = document.getElementById("pill");
  const raw = document.getElementById("raw");

  const about = document.getElementById("about");
  const aboutBtn = document.getElementById("aboutBtn");

  let selectedFile = null;
  let objectUrl = null;

  function humanSize(bytes) {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let size = bytes;
    let idx = 0;

    while (size >= 1024 && idx < units.length - 1) {
      size /= 1024;
      idx += 1;
    }

    const formatted = size >= 10 || idx === 0 ? size.toFixed(0) : size.toFixed(1);
    return `${formatted} ${units[idx]}`;
  }

  function getTypeLabel(file) {
    if (!file) return "Unknown type";
    if (file.type) return file.type;
    const ext = file.name.includes(".") ? file.name.split(".").pop().toUpperCase() : "FILE";
    return `${ext} file`;
  }

  function setResult(state, label, content) {
    resultCard.className = `result-card ${state}`;
    pill.textContent = label;
    raw.textContent = content;
  }

  function resetPreviewImage() {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = null;
    }

    thumb.classList.remove("visible");
    thumb.removeAttribute("src");
    thumb.alt = "Selected file preview";
    fileBadge.hidden = false;
    fileBadge.textContent = "FILE";
  }

  function resetUI() {
    selectedFile = null;
    fileInput.value = "";
    preview.hidden = true;
    submitBtn.disabled = true;
    resetBtn.disabled = true;
    progressWrap.hidden = true;
    progressBar.style.width = "0%";
    resetPreviewImage();
    setResult("muted", "Waiting", "No request made yet.");
  }

  function showPreview(file) {
    preview.hidden = false;
    fileName.textContent = file.name || "Unnamed file";
    fileSize.textContent = humanSize(file.size || 0);
    fileType.textContent = getTypeLabel(file);

    resetPreviewImage();

    if (file.type && file.type.startsWith("image/")) {
      objectUrl = URL.createObjectURL(file);
      thumb.src = objectUrl;
      thumb.alt = file.name || "Selected image";
      thumb.classList.add("visible");
      fileBadge.hidden = true;

      thumb.onerror = () => {
        resetPreviewImage();
        fileBadge.hidden = false;
        fileBadge.textContent = "IMG";
      };
    } else {
      const ext = file.name.includes(".") ? file.name.split(".").pop().toUpperCase() : "FILE";
      fileBadge.hidden = false;
      fileBadge.textContent = ext.slice(0, 4);
    }
  }

  function selectFile(file) {
    if (!file) return;

    selectedFile = file;
    showPreview(file);
    submitBtn.disabled = false;
    resetBtn.disabled = false;

    if (file.size > MAX_FILE_BYTES) {
      setResult(
        "warn",
        "File too large",
        JSON.stringify(
          {
            ok: false,
            error: "Selected file exceeds the 50 MiB limit enforced by the server."
          },
          null,
          2
        )
      );
      submitBtn.disabled = true;
    } else {
      setResult("muted", "Ready", "File selected. Submit when ready.");
    }
  }

  function handleFiles(fileList) {
    if (!fileList || !fileList.length) return;
    selectFile(fileList[0]);
  }

  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropzone.classList.add("drag");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("drag");
  });

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("drag");
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

  aboutBtn.addEventListener("click", () => {
    if (typeof about.showModal === "function") {
      about.showModal();
    }
  });

  about.addEventListener("click", (event) => {
    const rect = about.getBoundingClientRect();
    const inside =
      event.clientX >= rect.left &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom;

    if (!inside) {
      about.close();
    }
  });

  resetBtn.addEventListener("click", resetUI);

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!selectedFile || selectedFile.size > MAX_FILE_BYTES) {
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    submitBtn.disabled = true;
    resetBtn.disabled = true;
    progressWrap.hidden = false;
    progressBar.style.width = "0%";
    setResult("muted", "Uploading", "Submitting file to /metadata ...");

    const xhr = new XMLHttpRequest();
    xhr.open("POST", API_ENDPOINT, true);

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable || event.total <= 0) {
        progressBar.style.width = "30%";
        return;
      }

      const percent = Math.min(90, Math.floor((event.loaded / event.total) * 90));
      progressBar.style.width = `${percent}%`;
    };

    xhr.onload = () => {
      progressBar.style.width = "100%";

      let payload = null;
      try {
        payload = xhr.responseText ? JSON.parse(xhr.responseText) : null;
      } catch (error) {
        payload = null;
      }

      if (payload && payload.ok === true) {
        if (payload.is_image === true) {
          setResult("ok", "Image detected", JSON.stringify(payload, null, 2));
        } else {
          setResult("warn", "Not an image", JSON.stringify(payload, null, 2));
        }
      } else if (payload) {
        setResult("bad", "Server error", JSON.stringify(payload, null, 2));
      } else {
        const text = xhr.responseText || "<empty response body>";
        setResult("bad", `HTTP ${xhr.status}`, text);
      }

      submitBtn.disabled = false;
      resetBtn.disabled = false;
    };

    xhr.onerror = () => {
      progressBar.style.width = "100%";
      setResult("bad", "Network error", "The request could not be completed.");
      submitBtn.disabled = false;
      resetBtn.disabled = false;
    };

    xhr.ontimeout = () => {
      progressBar.style.width = "100%";
      setResult("bad", "Request timed out", "The server did not respond in time.");
      submitBtn.disabled = false;
      resetBtn.disabled = false;
    };

    xhr.send(formData);
  });

  resetUI();
})();