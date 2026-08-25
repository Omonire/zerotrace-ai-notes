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

  let searchTimeout = null;

  function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.classList.add("removing");
      setTimeout(() => toast.remove(), 200);
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
      emptyState.style.display = hasSearch ? "none" : "block";
      noResults.style.display = hasSearch ? "block" : "none";
      notesCount.textContent = "0 notes";
      return;
    }

    emptyState.style.display = "none";
    noResults.style.display = "none";
    notesCount.textContent = `${notes.length} note${notes.length !== 1 ? "s" : ""}`;

    notes.forEach((note) => {
      const isUpdated = note.updated_at !== note.created_at;
      const dateDisplay = isUpdated
        ? `Updated ${formatDate(note.updated_at)}`
        : formatDate(note.created_at);

      const card = document.createElement("article");
      card.className = "note-card";
      card.dataset.id = note.id;
      card.innerHTML = `
        <div class="note-card-body">
          <h3 class="note-card-title">${escapeHtml(note.title)}</h3>
          <p class="note-card-content">${escapeHtml(note.content)}</p>
        </div>
        <div class="note-card-footer">
          <time class="note-date">${dateDisplay}</time>
          <div class="note-actions">
            <button class="btn-icon btn-edit" data-id="${note.id}" title="Edit note">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>
            </button>
            <button class="btn-icon btn-delete" data-id="${note.id}" title="Delete note">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
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
