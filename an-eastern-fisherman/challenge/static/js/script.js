const statusBox = document.getElementById("status-box");
const downloadButtons = document.querySelectorAll("[data-filetype]");

function setStatus(message, kind = "") {
  statusBox.textContent = message;
  statusBox.className = "status-box";
  if (kind) {
    statusBox.classList.add(kind);
  }
}

// @ts-check 
async function downloadArtifact(filetype = "", button = null) {
  if (typeof filetype !== "string") {
    setStatus("Invalid filetype specified.", "error");
    return;
  }
  if (filetype.includes("..") || filetype.includes("/") || filetype.includes("\\")) {
    setStatus("Invalid filetype.", "error");
    return;
  }
  if (filetype.length === 0 || filetype.length > 255) {
    setStatus("Filetype must be between 1 and 255 characters.", "error");
    return;
  }
  if (!button || !(button instanceof HTMLButtonElement)) {
    setStatus("Invalid button element.", "error");
    return;
  }

  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "Preparing...";
  setStatus("Preparing client package...");

  try {
    const response = await fetch("/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ filetype })
    });

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`;
      try {
        const data = await response.json();
        if (data && data.error) {
          message = data.error;
        }
      } catch (e) {
        setStatus(e.message || "Parsing response failed", "error");
        return;
      }

      throw new Error(message);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "an-eastern-fisherman";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);

    setStatus(`${filetype} client downloaded successfully.`, "success");
  } catch (error) {
    setStatus(error.message || "Download failed.", "error");
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

for (const button of downloadButtons) {
  button.addEventListener("click", () => {
    const filetype = button.dataset.filetype;
    downloadArtifact(filetype, button);
  });
}