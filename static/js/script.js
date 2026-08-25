(() => {
  const form = document.getElementById("note-form");
  const titleInput = document.getElementById("note-title");
  const contentInput = document.getElementById("note-content");
  const editIdField = document.getElementById("edit-note-id");
  const editorTitle = document.getElementById("editor-title");
  const submitBtn = document.getElementById("submit-btn");
  const cancelBtn = document.getElementById("editor-cancel");
  const searchInput = document.getElementById("search-input");
  const filterTag = document.getElementById("filter-tag");
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
  const addTagBtn = document.getElementById("add-tag-btn");
  const tagDropdown = document.getElementById("tag-dropdown");
  const tagList = document.getElementById("tag-list");
  const selectedTags = document.getElementById("selected-tags");
  const newTagName = document.getElementById("new-tag-name");
  const newTagColor = document.getElementById("new-tag-color");
  const createTagBtn = document.getElementById("create-tag-btn");
  const shortcutsModal = document.getElementById("shortcuts-modal");
  const closeShortcuts = document.getElementById("close-shortcuts");

  let searchTimeout = null;
  let aiResultContent = "";
  let allTags = [];
  let selectedTagIds = [];
  let quill;

  // ─── Quill Editor ────────────────────────────────────────
  function initQuill() {
    quill = new Quill("#editor-container", {
      theme: "snow",
      placeholder: "Start writing...",
      modules: {
        toolbar: [
          ["bold", "italic", "underline", "strike"],
          [{ header: [1, 2, 3, false] }],
          ["blockquote", "code-block"],
          [{ list: "ordered" }, { list: "bullet" }],
          ["clean"]
        ]
      }
    });
  }
  initQuill();

  // ─── Toast ───────────────────────────────────────────────
  function showToast(message, type = "success") {
    const toast = document.createElement("div");
    const colors = type === "error"
      ? "bg-red-500/90 text-white"
      : type === "ai" ? "bg-accent/90 text-white" : "bg-green-500/90 text-white";
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

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function stripHtml(html) {
    const div = document.createElement("div");
    div.innerHTML = html;
    return div.textContent || div.innerText || "";
  }

  // ─── Tags ────────────────────────────────────────────────
  async function loadTags() {
    try {
      const res = await fetch("/api/tags");
      allTags = await res.json();
      renderTagDropdown();
      renderFilterTag();
    } catch {}
  }

  function renderTagDropdown() {
    tagList.innerHTML = allTags.length === 0
      ? '<div class="text-xs text-gray-500 px-2 py-1">No tags yet</div>'
      : allTags.map(t => `
          <div class="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-white/5 cursor-pointer group" data-tag-id="${t.id}">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full" style="background:${t.color}"></span>
              <span class="text-xs text-gray-300">${escapeHtml(t.name)}</span>
            </div>
            <button class="delete-tag opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all" data-tag-id="${t.id}">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/></svg>
            </button>
          </div>
        `).join("");
  }

  function renderFilterTag() {
    const val = filterTag.value;
    filterTag.innerHTML = '<option value="">All tags</option>' +
      allTags.map(t => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join("");
    filterTag.value = val;
  }

  function renderSelectedTags() {
    selectedTags.innerHTML = selectedTagIds.map(id => {
      const t = allTags.find(x => x.id === id);
      if (!t) return "";
      return `<span class="inline-flex items-center gap-1 bg-accent/10 border border-accent/20 text-accent text-xs px-2 py-1 rounded-lg">
        <span class="w-1.5 h-1.5 rounded-full" style="background:${t.color}"></span>
        ${escapeHtml(t.name)}
        <button type="button" class="remove-tag ml-0.5 hover:text-white transition-colors" data-tag-id="${t.id}">&times;</button>
      </span>`;
    }).join("");
  }

  addTagBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    tagDropdown.classList.toggle("hidden");
    renderTagDropdown();
  });

  tagList.addEventListener("click", async (e) => {
    const del = e.target.closest(".delete-tag");
    if (del) {
      e.stopPropagation();
      const tagId = parseInt(del.dataset.tagId);
      try {
        const res = await fetch(`/api/tags/${tagId}`, { method: "DELETE" });
        const data = await res.json();
        if (data.success) {
          allTags = allTags.filter(t => t.id !== tagId);
          selectedTagIds = selectedTagIds.filter(id => id !== tagId);
          renderTagDropdown();
          renderSelectedTags();
          renderFilterTag();
          showToast("Tag deleted");
        }
      } catch { showToast("Failed to delete tag", "error"); }
      return;
    }
    const item = e.target.closest("[data-tag-id]");
    if (item) {
      const tagId = parseInt(item.dataset.tagId);
      if (!selectedTagIds.includes(tagId)) {
        selectedTagIds.push(tagId);
        renderSelectedTags();
      }
      tagDropdown.classList.add("hidden");
    }
  });

  selectedTags.addEventListener("click", (e) => {
    const btn = e.target.closest(".remove-tag");
    if (btn) {
      selectedTagIds = selectedTagIds.filter(id => id !== parseInt(btn.dataset.tagId));
      renderSelectedTags();
    }
  });

  createTagBtn.addEventListener("click", async () => {
    const name = newTagName.value.trim();
    const color = newTagColor.value;
    if (!name) return;
    try {
      const res = await fetch("/api/tags", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, color })
      });
      const data = await res.json();
      if (data.success) {
        allTags.push(data.tag);
        selectedTagIds.push(data.tag.id);
        renderTagDropdown();
        renderSelectedTags();
        renderFilterTag();
        newTagName.value = "";
        showToast("Tag created");
      } else {
        showToast(data.message, "error");
      }
    } catch { showToast("Failed to create tag", "error"); }
  });

  document.addEventListener("click", (e) => {
    if (!tagDropdown.contains(e.target) && !addTagBtn.contains(e.target)) {
      tagDropdown.classList.add("hidden");
    }
  });

  // ─── Editor ──────────────────────────────────────────────
  function resetEditor() {
    form.reset();
    editIdField.value = "";
    editorTitle.textContent = "Create a note";
    submitBtn.textContent = "Save Note";
    cancelBtn.style.display = "none";
    quill.setContents([]);
    selectedTagIds = [];
    renderSelectedTags();
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
    const content = quill.root.innerHTML.trim();
    const plainText = stripHtml(content).trim();
    if (!title || !plainText) {
      showToast("Title and content are required", "error");
      return;
    }

    const editId = editIdField.value;
    const url = editId ? `/api/notes/${editId}` : "/api/notes";
    const method = editId ? "PUT" : "POST";

    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, content, content_format: "html", tag_ids: selectedTagIds }),
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

  // ─── Notes Events ────────────────────────────────────────
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
        if (note.content_format === "html") {
          quill.root.innerHTML = note.content;
        } else {
          quill.setText(note.content);
        }
        selectedTagIds = (note.tags || []).map(t => t.id);
        renderSelectedTags();
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

  function renderNotes(notes) {
    notesGrid.innerHTML = "";
    if (notes.length === 0) {
      const hasSearch = searchInput.value.trim().length > 0;
      const hasFilter = filterTag.value !== "";
      emptyState.className = (hasSearch || hasFilter) ? "hidden" : "text-center py-20";
      noResults.className = (hasSearch || hasFilter) ? "text-center py-20" : "hidden";
      notesCount.textContent = "0 notes";
      return;
    }

    emptyState.className = "hidden";
    noResults.className = "hidden";
    notesCount.textContent = `${notes.length} note${notes.length !== 1 ? "s" : ""}`;

    notes.forEach((note) => {
      const isUpdated = note.updated_at !== note.created_at;
      const dateDisplay = isUpdated ? `Updated ${formatDate(note.updated_at)}` : formatDate(note.created_at);
      const contentPreview = note.content_format === "html" ? stripHtml(note.content) : note.content;

      const card = document.createElement("article");
      card.className = "bg-surface border border-border rounded-2xl p-5 hover:border-accent/30 transition-colors group";
      card.dataset.id = note.id;
      card.innerHTML = `
        <div class="mb-4">
          <h3 class="font-bold mb-2 group-hover:text-accent transition-colors">${escapeHtml(note.title)}</h3>
          <p class="text-sm text-gray-400 leading-relaxed line-clamp-3">${escapeHtml(contentPreview)}</p>
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

  // ─── AI Actions ──────────────────────────────────────────
  async function fetchAiUsage() {
    try {
      const res = await fetch("/api/ai/usage");
      const data = await res.json();
      aiRemaining.textContent = `${data.remaining}/10 left today`;
    } catch { aiRemaining.textContent = ""; }
  }
  fetchAiUsage();

  aiToolbar.addEventListener("click", async (e) => {
    const btn = e.target.closest(".ai-btn");
    if (!btn) return;
    const action = btn.dataset.action;
    const content = stripHtml(quill.root.innerHTML).trim();
    if (!content) { showToast("Write something first", "error"); return; }

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
        showToast(`AI ${action} complete`, "ai");
        fetchAiUsage();
      } else {
        showToast(data.message || "AI failed", "error");
      }
    } catch { showToast("Network error", "error"); }
    finally { btn.disabled = false; aiLoading.classList.add("hidden"); }
  });

  aiApply.addEventListener("click", () => {
    quill.setText(aiResultContent);
    hideAiResult();
    showToast("AI result applied");
  });

  aiDiscard.addEventListener("click", hideAiResult);

  // ─── Search & Filter ─────────────────────────────────────
  function buildUrl() {
    const q = searchInput.value.trim();
    const tag = filterTag.value;
    const params = new URLSearchParams();
    if (q) params.set("search", q);
    if (tag) params.set("tag", tag);
    const qs = params.toString();
    return qs ? `/app?${qs}` : "/app";
  }

  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      window.history.pushState({}, "", buildUrl());
      fetchAndRender();
    }, 300);
  });

  filterTag.addEventListener("change", () => {
    window.history.pushState({}, "", buildUrl());
    fetchAndRender();
  });

  async function fetchAndRender() {
    const q = searchInput.value.trim();
    const tag = filterTag.value;
    const params = new URLSearchParams();
    if (q) params.set("search", q);
    if (tag) params.set("tag", tag);
    const qs = params.toString();
    const url = qs ? `/api/notes?${qs}` : "/api/notes";

    try {
      const res = await fetch(url);
      if (res.status === 401) { window.location.href = "/signin"; return; }
      const notes = await res.json();
      renderNotes(notes);
    } catch { showToast("Failed to load notes", "error"); }
  }

  window.addEventListener("popstate", () => {
    const params = new URLSearchParams(window.location.search);
    searchInput.value = params.get("search") || "";
    filterTag.value = params.get("tag") || "";
    fetchAndRender();
  });

  // ─── Keyboard Shortcuts ──────────────────────────────────
  document.addEventListener("keydown", (e) => {
    const isInput = e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.isContentEditable;

    // Ctrl+S - Save
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      form.dispatchEvent(new Event("submit", { cancelable: true }));
    }

    // Ctrl+N - New note
    if ((e.ctrlKey || e.metaKey) && e.key === "n") {
      e.preventDefault();
      resetEditor();
      titleInput.focus();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // Ctrl+K - Search
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    }

    // Ctrl+/ - Show shortcuts
    if ((e.ctrlKey || e.metaKey) && e.key === "/") {
      e.preventDefault();
      shortcutsModal.classList.toggle("hidden");
    }

    // Escape - Close
    if (e.key === "Escape") {
      if (!shortcutsModal.classList.contains("hidden")) {
        shortcutsModal.classList.add("hidden");
      } else if (tagDropdown && !tagDropdown.classList.contains("hidden")) {
        tagDropdown.classList.add("hidden");
      } else if (cancelBtn.style.display !== "none") {
        resetEditor();
      }
    }
  });

  closeShortcuts.addEventListener("click", () => shortcutsModal.classList.add("hidden"));
  shortcutsModal.addEventListener("click", (e) => {
    if (e.target === shortcutsModal) shortcutsModal.classList.add("hidden");
  });

  // ─── Init ────────────────────────────────────────────────
  loadTags();
})();
