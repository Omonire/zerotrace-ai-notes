(() => {
  const form = document.getElementById("note-form");
  const titleInput = document.getElementById("note-title");
  const contentInput = document.getElementById("note-content");
  const editIdField = document.getElementById("edit-note-id");
  const editorTitle = document.getElementById("editor-title");
  const submitBtn = document.getElementById("submit-btn");
  const cancelBtn = document.getElementById("editor-cancel");
  const searchInput = document.getElementById("search-input");
  const notesGrid = document.getElementById("notes-grid");
  const emptyState = document.getElementById("empty-state");
  const noResults = document.getElementById("no-results");
  const notesCount = document.getElementById("notes-count");
  const toastContainer = document.getElementById("toast-container");
  const aiToolbar = document.getElementById("ai-toolbar");
  const aiLoading = document.getElementById("ai-loading");
  const aiResult = document.getElementById("ai-result");
  const aiResultText = document.getElementById("ai-result-text");
  const aiApply = document.getElementById("ai-apply");
  const aiDiscard = document.getElementById("ai-discard");
  const aiRemaining = document.getElementById("ai-remaining");

  let searchTimeout = null;
  let aiResultContent = "";

  function showToast(message, type = "success") {
    const toast = document.createElement("div");
    const colors = type === "error"
      ? "bg-red-500/90 text-white"
      : type === "ai"
        ? "bg-accent/90 text-white"
        : "bg-green-500/90 text-white";
    toast.className = `px-4 py-3 rounded-xl text-sm font-medium shadow-lg ${colors} backdrop-blur-sm`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.transition = "opacity 0.3s, transform 0.3s";
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  function formatDate(dateStr) {
    if (!dateStr) return "";
    const d = new Date(dateStr + "Z");
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return "Just now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function renderNotes(notes) {
    notesGrid.innerHTML = "";
    if (notes.length === 0) {
      const hasSearch = searchInput.value.trim().length > 0;
      emptyState.className = hasSearch ? "hidden" : "text-center py-20";
      noResults.className = hasSearch ? "text-center py-20" : "hidden";
      notesCount.textContent = "0 notes";
      return;
    }

    emptyState.className = "hidden";
    noResults.className = "hidden";
    notesCount.textContent = `${notes.length} note${notes.length !== 1 ? "s" : ""}`;

    notes.forEach((note) => {
      const isUpdated = note.updated_at !== note.created_at;
      const dateDisplay = isUpdated
        ? `Updated ${formatDate(note.updated_at)}`
        : formatDate(note.created_at);

      const card = document.createElement("article");
      card.className = "bg-surface border border-border rounded-2xl p-5 hover:border-accent/30 transition-colors group";
      card.dataset.id = note.id;
      card.innerHTML = `
        <div class="mb-4">
          <h3 class="font-bold mb-2 group-hover:text-accent transition-colors">${escapeHtml(note.title)}</h3>
          <p class="text-sm text-gray-400 leading-relaxed line-clamp-3">${escapeHtml(note.content)}</p>
        </div>
        <div class="flex items-center justify-between pt-3 border-t border-border">
          <time class="text-xs text-gray-500">${dateDisplay}</time>
          <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button class="btn-edit p-1.5 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors" data-id="${note.id}" title="Edit">
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125"/></svg>
            </button>
            <button class="btn-delete p-1.5 rounded-lg hover:bg-white/5 text-gray-400 hover:text-red-400 transition-colors" data-id="${note.id}" title="Delete">
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"/></svg>
            </button>
          </div>
        </div>
      `;
      notesGrid.appendChild(card);
    });
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function resetEditor() {
    form.reset();
    editIdField.value = "";
    editorTitle.textContent = "Create a note";
    submitBtn.textContent = "Save Note";
    cancelBtn.style.display = "none";
    hideAiResult();
  }

  function hideAiResult() {
    aiResult.classList.add("hidden");
    aiResultContent = "";
  }

  cancelBtn.addEventListener("click", resetEditor);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = titleInput.value.trim();
    const content = contentInput.value.trim();
    if (!title || !content) return;

    const editId = editIdField.value;
    const url = editId ? `/api/notes/${editId}` : "/api/notes";
    const method = editId ? "PUT" : "POST";

    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, content }),
      });
      const data = await res.json();
      if (data.success) {
        showToast(editId ? "Note updated" : "Note created");
        resetEditor();
        fetchAndRender();
      } else {
        showToast(data.message || "Something went wrong", "error");
      }
    } catch {
      showToast("Network error", "error");
    }
  });

  notesGrid.addEventListener("click", async (e) => {
    const editBtn = e.target.closest(".btn-edit");
    const deleteBtn = e.target.closest(".btn-delete");

    if (editBtn) {
      const id = editBtn.dataset.id;
      try {
        const res = await fetch(`/api/notes/${id}`);
        const data = await res.json();
        if (!data.success) return showToast("Note not found", "error");
        const note = data.note;

        editIdField.value = note.id;
        titleInput.value = note.title;
        contentInput.value = note.content;
        editorTitle.textContent = "Edit note";
        submitBtn.textContent = "Update Note";
        cancelBtn.style.display = "inline-flex";
        titleInput.focus();
        window.scrollTo({ top: 0, behavior: "smooth" });
      } catch {
        showToast("Failed to load note", "error");
      }
    }

    if (deleteBtn) {
      const id = deleteBtn.dataset.id;
      if (!confirm("Delete this note?")) return;

      try {
        const res = await fetch(`/api/notes/${id}`, { method: "DELETE" });
        const data = await res.json();
        if (data.success) {
          showToast("Note deleted");
          fetchAndRender();
        } else {
          showToast(data.message || "Failed to delete", "error");
        }
      } catch {
        showToast("Network error", "error");
      }
    }
  });

  // ─── AI Actions ────────────────────────────────────────────

  async function fetchAiUsage() {
    try {
      const res = await fetch("/api/ai/usage");
      const data = await res.json();
      aiRemaining.textContent = `${data.remaining}/10 uses left today`;
    } catch {
      aiRemaining.textContent = "";
    }
  }

  fetchAiUsage();

  aiToolbar.addEventListener("click", async (e) => {
    const btn = e.target.closest(".ai-btn");
    if (!btn) return;

    const action = btn.dataset.action;
    const content = contentInput.value.trim();
    if (!content) {
      showToast("Write something first, then use AI", "error");
      return;
    }

    btn.disabled = true;
    aiLoading.classList.remove("hidden");
    hideAiResult();

    try {
      const res = await fetch(`/api/ai/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      const data = await res.json();

      if (data.success) {
        aiResultContent = data.result;
        aiResultText.textContent = data.result;
        aiResult.classList.remove("hidden");
        showToast(`AI ${action} complete (${data.tokens_used} tokens)`, "ai");
        fetchAiUsage();
      } else {
        showToast(data.message || "AI failed", "error");
      }
    } catch {
      showToast("Network error", "error");
    } finally {
      btn.disabled = false;
      aiLoading.classList.add("hidden");
    }
  });

  aiApply.addEventListener("click", () => {
    contentInput.value = aiResultContent;
    hideAiResult();
    showToast("AI result applied");
  });

  aiDiscard.addEventListener("click", () => {
    hideAiResult();
  });

  // ─── Search ────────────────────────────────────────────────

  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      const q = searchInput.value.trim();
      const url = q ? `/app?search=${encodeURIComponent(q)}` : "/app";
      window.history.pushState({}, "", url);
      fetchAndRender();
    }, 300);
  });

  async function fetchAndRender() {
    const q = searchInput.value.trim();
    const url = q ? `/api/notes?search=${encodeURIComponent(q)}` : "/api/notes";
    try {
      const res = await fetch(url);
      if (res.status === 401) {
        window.location.href = "/signin";
        return;
      }
      const notes = await res.json();
      renderNotes(notes);
    } catch {
      showToast("Failed to load notes", "error");
    }
  }

  window.addEventListener("popstate", () => {
    const params = new URLSearchParams(window.location.search);
    searchInput.value = params.get("search") || "";
    fetchAndRender();
  });
})();
