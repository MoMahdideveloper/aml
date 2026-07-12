/**
 * AI form assist panel — idle → collecting → processing → reviewing → applied/error.
 * Applies only allowlisted input_name values; never overwrites non-empty fields automatically.
 * MediaRecorder when supported; file upload always available as fallback.
 */
(function () {
  function csrfToken() {
    var m = document.querySelector('meta[name="csrf-token"]');
    if (m && m.content) return m.content;
    var inp = document.querySelector('input[name="csrf_token"]');
    return inp ? inp.value : "";
  }

  function setStatus(root, text) {
    var el = root.querySelector("[data-ai-status]");
    if (el) el.textContent = text;
  }

  function findForm(root) {
    var sel = root.getAttribute("data-form-selector") || "form";
    var form = document.querySelector(sel);
    if (form) return form;
    return root.closest("form") || document.querySelector("form");
  }

  function existingValues(form) {
    var out = {};
    if (!form) return out;
    Array.prototype.forEach.call(form.elements || [], function (el) {
      if (!el.name) return;
      if (el.type === "file" || el.type === "submit" || el.type === "button") return;
      out[el.name] = el.value;
    });
    return out;
  }

  function applyValue(form, inputName, value, force) {
    if (!form || !inputName) return false;
    var el = form.querySelector('[name="' + inputName + '"]');
    if (!el) return false;
    var cur = (el.value || "").trim();
    if (cur && !force) return false;
    if (!el.hasAttribute("data-ai-undo")) {
      el.setAttribute("data-ai-undo", el.value || "");
    }
    el.value = value == null ? "" : String(value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  function undoValue(form, inputName) {
    if (!form || !inputName) return;
    var el = form.querySelector('[name="' + inputName + '"]');
    if (!el) return;
    if (el.hasAttribute("data-ai-undo")) {
      el.value = el.getAttribute("data-ai-undo") || "";
      el.removeAttribute("data-ai-undo");
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function renderSuggestions(root, form, data) {
    var list = root.querySelector("[data-ai-review-list]");
    if (!list) return;
    list.innerHTML = "";
    var suggestions = (data && data.suggestions) || [];
    if (!suggestions.length) {
      list.innerHTML = '<li class="text-xs text-on-surface-variant">No suggestions.</li>';
      return;
    }
    suggestions.forEach(function (s) {
      var li = document.createElement("li");
      li.className = "border border-outline-variant rounded-lg p-2";
      var conf = Math.round((s.confidence || 0) * 100);
      li.innerHTML =
        '<div class="flex flex-wrap justify-between gap-2">' +
        "<span><strong>" +
        (s.field || "") +
        "</strong> → " +
        String(s.value == null ? "" : s.value) +
        ' <span class="text-xs text-on-surface-variant">(' +
        conf +
        "% · " +
        (s.action || "") +
        ")</span></span>" +
        '<span class="flex gap-2">' +
        '<button type="button" class="text-xs underline" data-ai-accept>Accept</button>' +
        '<button type="button" class="text-xs underline" data-ai-reject>Reject</button>' +
        '<button type="button" class="text-xs underline" data-ai-undo-btn>Undo</button>' +
        "</span></div>";
      var accept = li.querySelector("[data-ai-accept]");
      var reject = li.querySelector("[data-ai-reject]");
      var undoBtn = li.querySelector("[data-ai-undo-btn]");
      accept.addEventListener("click", function () {
        applyValue(form, s.input_name || s.field, s.value, true);
        postReview(root, data.id, [
          { suggestion_id: s.id, field: s.field, decision: "accept" },
        ]);
        setStatus(root, "Applied " + s.field);
      });
      reject.addEventListener("click", function () {
        postReview(root, data.id, [
          { suggestion_id: s.id, field: s.field, decision: "reject" },
        ]);
        li.remove();
      });
      undoBtn.addEventListener("click", function () {
        undoValue(form, s.input_name || s.field);
        postReview(root, data.id, [
          { suggestion_id: s.id, field: s.field, decision: "undo" },
        ]);
      });
      list.appendChild(li);

      if (s.action === "auto_fill") {
        applyValue(form, s.input_name || s.field, s.value, false);
      }
    });
  }

  function postReview(root, extractionId, decisions) {
    if (!extractionId) return;
    fetch("/api/ai-form-assist/extractions/" + extractionId + "/review", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
      credentials: "same-origin",
      body: JSON.stringify({ decisions: decisions }),
    }).catch(function () {});
  }

  function recordedBlob(root) {
    return root._aiRecordedBlob || null;
  }

  function process(root) {
    var form = findForm(root);
    var consent = root.querySelector("[data-ai-consent]");
    if (consent && !consent.checked) {
      setStatus(root, "Consent required");
      return;
    }
    var textEl = root.querySelector("[data-ai-text]");
    var imgEl = root.querySelector("[data-ai-images]");
    var audEl = root.querySelector("[data-ai-audio]");
    var text = textEl ? textEl.value : "";
    var fd = new FormData();
    fd.append("form", root.getAttribute("data-form-name") || "property");
    fd.append("text", text || "");
    fd.append("existing_values_json", JSON.stringify(existingValues(form)));
    if (imgEl && imgEl.files) {
      Array.prototype.forEach.call(imgEl.files, function (f) {
        fd.append("images", f);
      });
    }
    var rec = recordedBlob(root);
    if (rec) {
      fd.append("audios", rec, "recording.webm");
    } else if (audEl && audEl.files && audEl.files[0]) {
      fd.append("audios", audEl.files[0]);
    }
    setStatus(root, "Processing…");
    var btn = root.querySelector("[data-ai-process]");
    if (btn) btn.disabled = true;
    fetch(root.getAttribute("data-endpoint") || "/api/ai-form-assist/extractions", {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken(), "X-Idempotency-Key": String(Date.now()) },
      credentials: "same-origin",
      body: fd,
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, status: r.status, body: j };
        });
      })
      .then(function (res) {
        if (!res.ok) {
          setStatus(root, (res.body && (res.body.message || res.body.error)) || "Error " + res.status);
          return;
        }
        setStatus(root, "Review suggestions");
        renderSuggestions(root, form, res.body);
      })
      .catch(function () {
        setStatus(root, "Network error");
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  function bindRecorder(root) {
    var recBtn = root.querySelector("[data-ai-record]");
    var stopBtn = root.querySelector("[data-ai-record-stop]");
    if (!recBtn) return;
    var supported =
      typeof navigator !== "undefined" &&
      navigator.mediaDevices &&
      typeof MediaRecorder !== "undefined";
    if (!supported) {
      recBtn.disabled = true;
      recBtn.title = "Recording not supported — use audio file upload";
      if (stopBtn) stopBtn.disabled = true;
      return;
    }
    var mediaRecorder = null;
    var chunks = [];
    recBtn.addEventListener("click", function () {
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then(function (stream) {
          chunks = [];
          mediaRecorder = new MediaRecorder(stream);
          mediaRecorder.ondataavailable = function (e) {
            if (e.data && e.data.size) chunks.push(e.data);
          };
          mediaRecorder.onstop = function () {
            stream.getTracks().forEach(function (t) {
              t.stop();
            });
            root._aiRecordedBlob = new Blob(chunks, { type: "audio/webm" });
            setStatus(root, "Recording ready (" + Math.round(root._aiRecordedBlob.size / 1024) + " KB)");
            recBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
          };
          mediaRecorder.start();
          recBtn.disabled = true;
          if (stopBtn) stopBtn.disabled = false;
          setStatus(root, "Recording…");
        })
        .catch(function () {
          setStatus(root, "Microphone permission denied — use file upload");
        });
    });
    if (stopBtn) {
      stopBtn.disabled = true;
      stopBtn.addEventListener("click", function () {
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
          mediaRecorder.stop();
        }
      });
    }
  }

  function bind(root) {
    if (root.getAttribute("data-ai-bound") === "1") return;
    root.setAttribute("data-ai-bound", "1");
    var btn = root.querySelector("[data-ai-process]");
    if (btn) {
      btn.addEventListener("click", function () {
        process(root);
      });
    }
    bindRecorder(root);
  }

  function init() {
    document.querySelectorAll("[data-ai-form-assist]").forEach(bind);
  }

  // Re-bind when modals inject/show panels after first paint
  if (typeof MutationObserver !== "undefined") {
    var mo = new MutationObserver(function () {
      init();
    });
    if (document.documentElement) {
      mo.observe(document.documentElement, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.AIFormAssist = { init: init, bind: bind };
})();
