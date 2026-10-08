// Frontend Client JavaScript for Handwritten Evaluator

document.addEventListener("DOMContentLoaded", function () {
  // ---------------- Rubrics Form: Add / Remove Points ----------------
  const addPointBtn = document.getElementById("add-rubric-point-btn");
  const pointsContainer = document.getElementById("rubric-points-container");

  if (addPointBtn && pointsContainer) {
    addPointBtn.addEventListener("click", function () {
      const pointCount = pointsContainer.querySelectorAll(".rubric-point-row").length + 1;
      const row = document.createElement("div");
      row.className = "rubric-point-row mb-3 p-3 rounded glass-card border";
      row.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-2">
          <span class="badge badge-info-custom">Point #${pointCount}</span>
          <button type="button" class="btn btn-sm btn-outline-danger remove-point-btn">
            <i class="bi bi-trash"></i> Remove
          </button>
        </div>
        <div class="row g-2">
          <div class="col-md-9">
            <input type="text" name="point_text[]" class="form-control-custom" placeholder="e.g. Explains BFS queue traversal correctly..." required>
          </div>
          <div class="col-md-3">
            <div class="input-group">
              <input type="number" step="0.5" name="point_marks[]" class="form-control-custom" value="2.0" min="0.5" required>
              <span class="input-group-text bg-dark border-0 text-white">marks</span>
            </div>
          </div>
        </div>
      `;
      pointsContainer.appendChild(row);
      updateTotalMarks();
    });

    pointsContainer.addEventListener("click", function (e) {
      if (e.target.closest(".remove-point-btn")) {
        const row = e.target.closest(".rubric-point-row");
        if (pointsContainer.querySelectorAll(".rubric-point-row").length > 1) {
          row.remove();
          updateTotalMarks();
        } else {
          alert("A rubric must have at least one evaluation point!");
        }
      }
    });

    pointsContainer.addEventListener("input", function (e) {
      if (e.target.name === "point_marks[]") {
        updateTotalMarks();
      }
    });

    function updateTotalMarks() {
      const markInputs = pointsContainer.querySelectorAll("input[name='point_marks[]']");
      let total = 0;
      markInputs.forEach(input => {
        total += parseFloat(input.value) || 0;
      });
      const maxMarksInput = document.getElementById("max_marks");
      if (maxMarksInput) {
        maxMarksInput.value = total;
      }
    }
  }

  // ---------------- Review Dashboard: Image Controls ----------------
  const scanImg = document.getElementById("scan-image-elem");
  const zoomInBtn = document.getElementById("btn-zoom-in");
  const zoomOutBtn = document.getElementById("btn-zoom-out");
  const zoomResetBtn = document.getElementById("btn-zoom-reset");

  if (scanImg && zoomInBtn) {
    let currentZoom = 1.0;
    zoomInBtn.addEventListener("click", () => {
      currentZoom = Math.min(currentZoom + 0.25, 2.5);
      scanImg.style.transform = `scale(${currentZoom})`;
    });
    zoomOutBtn.addEventListener("click", () => {
      currentZoom = Math.max(currentZoom - 0.25, 0.5);
      scanImg.style.transform = `scale(${currentZoom})`;
    });
    zoomResetBtn.addEventListener("click", () => {
      currentZoom = 1.0;
      scanImg.style.transform = `scale(1.0)`;
    });
  }

  // ---------------- Save Edited OCR Text ----------------
  const saveOcrBtn = document.getElementById("btn-save-ocr");
  const ocrTextarea = document.getElementById("ocr-text-editor");

  if (saveOcrBtn && ocrTextarea) {
    saveOcrBtn.addEventListener("click", async function () {
      const sheetId = saveOcrBtn.getAttribute("data-sheet-id");
      const correctedText = ocrTextarea.value.trim();

      saveOcrBtn.disabled = true;
      saveOcrBtn.innerHTML = `<span class="spinner-pulse"></span> Saving...`;

      try {
        const resp = await fetch(`/api/ocr/${sheetId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ corrected_text: correctedText })
        });
        const result = await resp.json();

        if (resp.ok) {
          showToast("OCR text updated successfully. Ready for evaluation!", "success");
        } else {
          showToast(result.detail || "Failed to update text", "error");
        }
      } catch (err) {
        showToast("Network error updating text: " + err.message, "error");
      } finally {
        saveOcrBtn.disabled = false;
        saveOcrBtn.innerHTML = `<i class="bi bi-check-circle"></i> Save Corrected Text`;
      }
    });
  }

  // ---------------- Trigger LLM Evaluation ----------------
  const evaluateBtn = document.getElementById("btn-evaluate");

  if (evaluateBtn) {
    evaluateBtn.addEventListener("click", async function () {
      const sheetId = evaluateBtn.getAttribute("data-sheet-id");
      const rubricId = document.getElementById("rubric-selector")?.value || evaluateBtn.getAttribute("data-rubric-id");

      if (!rubricId) {
        alert("Please select or assign a rubric first!");
        return;
      }

      evaluateBtn.disabled = true;
      evaluateBtn.innerHTML = `<span class="spinner-pulse"></span> Evaluating with LLM...`;

      try {
        const resp = await fetch(`/api/evaluate/${sheetId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rubric_id: rubricId })
        });
        const data = await resp.json();

        if (resp.ok) {
          showToast("LLM evaluation completed!", "success");
          // Reload page to display full evaluation card, breakdown, and suggested score
          setTimeout(() => window.location.reload(), 600);
        } else {
          showToast(data.detail || "Evaluation failed", "error");
          evaluateBtn.disabled = false;
          evaluateBtn.innerHTML = `<i class="bi bi-cpu"></i> Run LLM Evaluation`;
        }
      } catch (err) {
        showToast("Error running evaluation: " + err.message, "error");
        evaluateBtn.disabled = false;
        evaluateBtn.innerHTML = `<i class="bi bi-cpu"></i> Run LLM Evaluation`;
      }
    });
  }

  // ---------------- Approve & Finalize Score ----------------
  const approveForm = document.getElementById("approve-score-form");
  if (approveForm) {
    approveForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      const sheetId = approveForm.getAttribute("data-sheet-id");
      const suggestedMarks = parseFloat(approveForm.getAttribute("data-suggested-marks") || "0");
      const finalMarksInput = document.getElementById("final-marks-input");
      const finalMarks = parseFloat(finalMarksInput.value);
      const overrideReasonInput = document.getElementById("override-reason-input");
      const overrideReason = overrideReasonInput ? overrideReasonInput.value.trim() : "";

      const isEdited = (Math.abs(finalMarks - suggestedMarks) > 0.01);

      const submitBtn = approveForm.querySelector("button[type='submit']");
      submitBtn.disabled = true;
      submitBtn.innerHTML = `<span class="spinner-pulse"></span> Saving Score...`;

      try {
        const resp = await fetch(`/api/scores/${sheetId}/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            final_marks: finalMarks,
            edited_flag: isEdited,
            override_reason: overrideReason
          })
        });

        const res = await resp.json();
        if (resp.ok) {
          showToast("Grade finalized and stored successfully in Firestore!", "success");
          setTimeout(() => {
            window.location.href = "/results";
          }, 800);
        } else {
          showToast(res.detail || "Could not save grade", "error");
          submitBtn.disabled = false;
          submitBtn.innerHTML = `<i class="bi bi-check2-all"></i> Approve & Save Final Score`;
        }
      } catch (err) {
        showToast("Error saving final grade: " + err.message, "error");
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<i class="bi bi-check2-all"></i> Approve & Save Final Score`;
      }
    });
  }

  // ---------------- Toast notification helper ----------------
  function showToast(message, type = "info") {
    let toast = document.getElementById("live-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "live-toast";
      toast.style.position = "fixed";
      toast.style.bottom = "2rem";
      toast.style.right = "2rem";
      toast.style.zIndex = "9999";
      toast.style.padding = "1rem 1.5rem";
      toast.style.borderRadius = "12px";
      toast.style.fontWeight = "600";
      toast.style.boxShadow = "0 10px 30px rgba(0,0,0,0.5)";
      toast.style.transition = "all 0.3s ease";
      document.body.appendChild(toast);
    }

    if (type === "success") {
      toast.style.background = "#10b981";
      toast.style.color = "#042f2e";
    } else if (type === "error") {
      toast.style.background = "#ef4444";
      toast.style.color = "#ffffff";
    } else {
      toast.style.background = "#6366f1";
      toast.style.color = "#ffffff";
    }

    toast.innerText = message;
    toast.style.display = "block";
    toast.style.opacity = "1";

    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => { toast.style.display = "none"; }, 300);
    }, 3500);
  }
});
