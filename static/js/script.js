(() => {
  const form = document.getElementById("note-form");
  const titleInput = document.getElementById("note-title");
  const contentInput = document.getElementById("note-content");
  const editIdField = document.getElementById("edit-note-id");
  const editorTitle = document.getElementById("editor-title");
  const submitBtn = document.getElementById("submit-btn");
  const cancelBtn = document.getElementById("editor-cancel");
  const searchInput = document.getElementById("search-input");
  const sortSelect = document.getElementById("sort-select");
  const filterTag = document.getElementById("filter-tag");
  const notesGrid = document.getElementById("notes-grid");
  const loadingSkeletons = document.getElementById("loading-skeletons");
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
  const selectedTagsEl = document.getElementById("selected-tags");
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

  function showToast(message, type = "success") {
    const toast = document.createElement("div");
    const colors = type === "error" ? "bg-red-500/90 text-white" : type === "ai" ? "bg-accent/90 text-white" : "bg-green-500/90 text-white";
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

  function renderSelectedTags() {
    selectedTagsEl.innerHTML = selectedTagIds.map(id => {
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
          showToast("Tag deleted");
        }
      } catch { showToast("Failed", "error"); }
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

  selectedTagsEl.addEventListener("click", (e) => {
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
        newTagName.value = "";
        showToast("Tag created");
      } else { showToast(data.message, "error"); }
    } catch { showToast("Failed", "error"); }
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
    if (!title || !plainText) { showToast("Title and content required", "error"); return; }

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
      } else { showToast(data.message || "Failed", "error"); }
    } catch { showToast("Network error", "error"); }
  });

  // ─── Notes Events ────────────────────────────────────────
  notesGrid.addEventListener("click", async (e) => {
    const editBtn = e.target.closest(".btn-edit");
    const deleteBtn = e.target.closest(".btn-delete");
    const pinBtn = e.target.closest(".btn-pin");

    if (pinBtn) {
      const id = pinBtn.dataset.id;
      try {
        const res = await fetch(`/api/notes/${id}/pin`, { method: "PUT" });
        const data = await res.json();
        if (data.success) {
          showToast(data.is_pinned ? "Note pinned" : "Note unpinned");
          fetchAndRender();
        }
      } catch { showToast("Failed", "error"); }
      return;
    }

    if (editBtn) {
      const id = editBtn.dataset.id;
      try {
        const res = await fetch(`/api/notes/${id}`);
        const data = await res.json();
        if (!data.success) return showToast("Note not found", "error");
        const note = data.note;
        editIdField.value = note.id;
        titleInput.value = note.title;
        if (note.content_format === "html") { quill.root.innerHTML = note.content; }
        else { quill.setText(note.content); }
        selectedTagIds = (note.tags || []).map(t => t.id);
        renderSelectedTags();
        editorTitle.textContent = "Edit note";
        submitBtn.textContent = "Update Note";
        cancelBtn.style.display = "inline-flex";
        titleInput.focus();
        window.scrollTo({ top: 0, behavior: "smooth" });
      } catch { showToast("Failed to load note", "error"); }
    }

    if (deleteBtn) {
      const id = deleteBtn.dataset.id;
      if (!confirm("Move this note to trash?")) return;
      try {
        const res = await fetch(`/api/notes/${id}`, { method: "DELETE" });
        const data = await res.json();
        if (data.success) { showToast("Note moved to trash"); fetchAndRender(); }
        else { showToast(data.message || "Failed", "error"); }
      } catch { showToast("Network error", "error"); }
    }
  });

  function renderNotes(notes) {
    notesGrid.innerHTML = "";
    loadingSkeletons.classList.add("hidden");
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
      const isPinned = note.is_pinned;

      const card = document.createElement("article");
      card.className = `bg-surface border border-border rounded-2xl p-5 hover:border-accent/30 transition-colors group ${isPinned ? "border-accent/40 bg-accent/5" : ""}`;
      card.dataset.id = note.id;
      card.innerHTML = `
        <div class="mb-4">
          <div class="flex items-center gap-2 mb-2">
            ${isPinned ? '<svg class="w-3.5 h-3.5 text-accent flex-shrink-0" fill="currentColor" viewBox="0 0 24 24"><path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z"/></svg>' : ''}
            <h3 class="font-bold group-hover:text-accent transition-colors ${isPinned ? "text-accent" : ""}">${escapeHtml(note.title)}</h3>
          </div>
          <p class="text-sm text-gray-400 leading-relaxed line-clamp-3">${escapeHtml(contentPreview)}</p>
        </div>
        <div class="flex items-center justify-between pt-3 border-t border-border">
          <time class="text-xs text-gray-500">${dateDisplay}</time>
          <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button class="btn-pin p-1.5 rounded-lg hover:bg-white/5 text-gray-400 hover:text-accent transition-colors" data-id="${note.id}" title="${isPinned ? "Unpin" : "Pin"}">
              <svg width="14" height="14" fill="${isPinned ? "currentColor" : "none"}" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z"/></svg>
            </button>
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

  // ─── AI ──────────────────────────────────────────────────
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
      } else { showToast(data.message || "AI failed", "error"); }
    } catch { showToast("Network error", "error"); }
    finally { btn.disabled = false; aiLoading.classList.add("hidden"); }
  });

  aiApply.addEventListener("click", () => { quill.setText(aiResultContent); hideAiResult(); showToast("AI result applied"); });
  aiDiscard.addEventListener("click", hideAiResult);

  // ─── Search, Sort, Filter ────────────────────────────────
  function buildUrl() {
    const q = searchInput.value.trim();
    const sort = sortSelect.value;
    const tag = filterTag.value;
    const params = new URLSearchParams();
    if (q) params.set("search", q);
    if (sort !== "newest") params.set("sort", sort);
    if (tag) params.set("tag", tag);
    const qs = params.toString();
    return qs ? `/app?${qs}` : "/app";
  }

  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { window.history.pushState({}, "", buildUrl()); fetchAndRender(); }, 300);
  });

  sortSelect.addEventListener("change", () => { window.history.pushState({}, "", buildUrl()); fetchAndRender(); });
  filterTag.addEventListener("change", () => { window.history.pushState({}, "", buildUrl()); fetchAndRender(); });

  async function fetchAndRender() {
    const q = searchInput.value.trim();
    const sort = sortSelect.value;
    const tag = filterTag.value;
    const params = new URLSearchParams();
    if (q) params.set("search", q);
    if (sort !== "newest") params.set("sort", sort);
    if (tag) params.set("tag", tag);
    const qs = params.toString();
    const url = qs ? `/api/notes?${qs}` : "/api/notes";

    loadingSkeletons.classList.remove("hidden");
    notesGrid.innerHTML = "";

    try {
      const res = await fetch(url);
      if (res.status === 401) { window.location.href = "/signin"; return; }
      const notes = await res.json();
      renderNotes(notes);
    } catch { showToast("Failed to load notes", "error"); loadingSkeletons.classList.add("hidden"); }
  }

  window.addEventListener("popstate", () => {
    const params = new URLSearchParams(window.location.search);
    searchInput.value = params.get("search") || "";
    sortSelect.value = params.get("sort") || "newest";
    filterTag.value = params.get("tag") || "";
    fetchAndRender();
  });

  // ─── Keyboard Shortcuts ──────────────────────────────────
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); form.dispatchEvent(new Event("submit", { cancelable: true })); }
    if ((e.ctrlKey || e.metaKey) && e.key === "n") { e.preventDefault(); resetEditor(); titleInput.focus(); window.scrollTo({ top: 0, behavior: "smooth" }); }
    if ((e.ctrlKey || e.metaKey) && e.key === "k") { e.preventDefault(); searchInput.focus(); searchInput.select(); }
    if ((e.ctrlKey || e.metaKey) && e.key === "/") { e.preventDefault(); shortcutsModal.classList.toggle("hidden"); }
    if (e.key === "Escape") {
      if (!shortcutsModal.classList.contains("hidden")) shortcutsModal.classList.add("hidden");
      else if (chatPanel && !chatPanel.classList.contains("hidden")) closeChat();
      else if (!tagDropdown.classList.contains("hidden")) tagDropdown.classList.add("hidden");
      else if (cancelBtn.style.display !== "none") resetEditor();
    }
  });

  closeShortcuts.addEventListener("click", () => shortcutsModal.classList.add("hidden"));
  shortcutsModal.addEventListener("click", (e) => { if (e.target === shortcutsModal) shortcutsModal.classList.add("hidden"); });

  // ─── AI Chat ─────────────────────────────────────────────
  const chatLauncher = document.getElementById("chat-launcher");
  const chatPanel = document.getElementById("chat-panel");
  const chatMessages = document.getElementById("chat-messages");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatSend = document.getElementById("chat-send");
  const chatClose = document.getElementById("chat-close");
  const chatClear = document.getElementById("chat-clear");
  let chatHistory = [];
  let chatBusy = false;

  function renderMarkdown(text) {
    const parts = escapeHtml(text).split("```");
    return parts.map((chunk, i) => {
      if (i % 2 === 1) {
        return `<pre class="bg-bg border border-border rounded-lg p-2 my-2 overflow-x-auto text-xs text-gray-300"><code>${chunk.replace(/^\n|\n$/g, "")}</code></pre>`;
      }
      const s = chunk
        .replace(/`([^`]+)`/g, '<code class="bg-bg px-1 py-0.5 rounded text-accent2 text-[0.8em]">$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      let html = "";
      let listOpen = false;
      for (const line of s.split("\n")) {
        const t = line.trim();
        if (/^[-*]\s+/.test(t)) {
          if (!listOpen) { html += '<ul class="list-disc pl-4 space-y-0.5 my-1">'; listOpen = true; }
          html += `<li>${t.replace(/^[-*]\s+/, "")}</li>`;
        } else {
          if (listOpen) { html += "</ul>"; listOpen = false; }
          html += t ? line + "<br>" : "<br>";
        }
      }
      if (listOpen) html += "</ul>";
      return html;
    }).join("");
  }

  function addMessage(role, text) {
    const empty = document.getElementById("chat-empty");
    if (empty) empty.remove();
    const row = document.createElement("div");
    row.className = role === "user" ? "flex justify-end" : "flex justify-start";
    const bubble = document.createElement("div");
    bubble.className = role === "user"
      ? "max-w-[85%] bg-accent text-white rounded-2xl rounded-br-md px-3.5 py-2 text-sm whitespace-pre-wrap break-words"
      : "max-w-[92%] bg-surface2 border border-border text-gray-200 rounded-2xl rounded-bl-md px-3.5 py-2 text-sm leading-relaxed break-words";
    if (role === "user") bubble.textContent = text;
    else bubble.innerHTML = renderMarkdown(text);
    row.appendChild(bubble);
    chatMessages.appendChild(row);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
  }

  function addTyping() {
    const row = document.createElement("div");
    row.className = "flex justify-start";
    row.innerHTML = '<div class="bg-surface2 border border-border rounded-2xl rounded-bl-md px-3.5 py-2.5 flex items-center gap-1.5">' +
      '<span class="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce"></span>' +
      '<span class="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style="animation-delay:0.15s"></span>' +
      '<span class="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style="animation-delay:0.3s"></span></div>';
    chatMessages.appendChild(row);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return row;
  }

  function autoGrow() {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 128) + "px";
  }

  function openChat() {
    chatPanel.classList.remove("hidden");
    chatPanel.classList.add("flex");
    chatInput.focus();
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function closeChat() {
    chatPanel.classList.add("hidden");
    chatPanel.classList.remove("flex");
  }

  chatLauncher.addEventListener("click", () => {
    if (chatPanel.classList.contains("hidden")) openChat(); else closeChat();
  });
  chatClose.addEventListener("click", closeChat);
  chatClear.addEventListener("click", () => {
    chatHistory = [];
    chatMessages.innerHTML = '<div id="chat-empty" class="text-center py-10">' +
      '<p class="text-sm text-gray-400 mb-1">Ask me anything about your notes.</p>' +
      '<p class="text-xs text-gray-500">"Summarize my meeting notes" &middot; "What did I plan for Porto?"</p></div>';
  });
  chatInput.addEventListener("input", autoGrow);
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); chatForm.requestSubmit(); }
  });

  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text || chatBusy) return;
    chatBusy = true;
    chatSend.disabled = true;
    chatHistory.push({ role: "user", content: text });
    addMessage("user", text);
    chatInput.value = "";
    autoGrow();
    const typing = addTyping();
    try {
      const res = await fetch("/api/bot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: chatHistory }),
      });
      const data = await res.json();
      typing.remove();
      if (data.success) {
        chatHistory.push({ role: "assistant", content: data.reply });
        const bubble = addMessage("assistant", data.reply);
        if (Array.isArray(data.sources) && data.sources.length) {
          const src = document.createElement("div");
          src.className = "mt-2 pt-2 border-t border-border text-[11px] text-gray-500";
          src.textContent = "From: " + data.sources.slice(0, 4).map((s) => '"' + s.title + '"').join(", ");
          bubble.appendChild(src);
        }
      } else {
        addMessage("assistant", "⚠️ " + (data.message || "Something went wrong."));
      }
    } catch {
      typing.remove();
      addMessage("assistant", "⚠️ Network error. Please try again.");
    } finally {
      chatBusy = false;
      chatSend.disabled = false;
      if (!chatPanel.classList.contains("hidden")) chatInput.focus();
    }
  });

  // ─── Init ────────────────────────────────────────────────
  loadTags();
})();
