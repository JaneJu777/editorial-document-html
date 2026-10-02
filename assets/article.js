(() => {
  const root = document.documentElement;
  const language = document.getElementById('language');
  const views = [...document.querySelectorAll('[data-language-view]')];
  const theme = document.getElementById('theme');
  const fontSteps = [0.88, 0.94, 1, 1.08, 1.16, 1.24];
  const fontDown = document.getElementById('font-down');
  const fontUp = document.getElementById('font-up');
  const edit = document.getElementById('edit');
  const editActions = document.getElementById('edit-actions');
  const editSave = document.getElementById('edit-save');
  const editCancel = document.getElementById('edit-cancel');
  const editStatus = document.getElementById('edit-status');
  const editStorageKey = `editorial-content-edits:v1:${location.pathname}`;
  let editing = false;
  let editSnapshot = {};
  let fontIndex = 2;
  try {
    const savedScale = Number(localStorage.getItem('editorial-font-scale'));
    const savedIndex = fontSteps.indexOf(savedScale);
    if (savedIndex >= 0) fontIndex = savedIndex;
  } catch (error) { /* Optional persistence. */ }

  function showLanguage(code) {
    views.forEach(view => view.classList.toggle('is-active', view.dataset.languageView === code));
    document.body.dataset.language = code;
    root.lang = code;
    const title = document.querySelector(`.language-view[data-language-view="${CSS.escape(code)}"] h1`);
    if (title) document.title = title.textContent;
  }

  language.value = document.body.dataset.language;
  language.addEventListener('change', () => showLanguage(language.value));
  showLanguage(language.value);

  theme.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    theme.setAttribute('aria-pressed', String(next === 'dark'));
    try { localStorage.setItem('editorial-theme', next); } catch (error) { /* Optional persistence. */ }
  });

  function setFont(index) {
    fontIndex = Math.min(fontSteps.length - 1, Math.max(0, index));
    root.style.setProperty('--font-scale', fontSteps[fontIndex]);
    fontDown.disabled = fontIndex === 0;
    fontUp.disabled = fontIndex === fontSteps.length - 1;
    try { localStorage.setItem('editorial-font-scale', String(fontSteps[fontIndex])); } catch (error) { /* Optional persistence. */ }
  }
  theme.setAttribute('aria-pressed', String(root.dataset.theme === 'dark'));
  fontDown.addEventListener('click', () => setFont(fontIndex - 1));
  fontUp.addEventListener('click', () => setFont(fontIndex + 1));
  setFont(fontIndex);

  function excludedTextNode(node) {
    const parent = node.parentElement;
    if (!parent || !node.nodeValue.trim()) return true;
    if (parent.closest('.topbar,.toc,script,style,[aria-hidden="true"],.generated-label,.flow-index,.chapter-number')) return true;
    return parent.matches('.article-chapter>h2>span:first-child');
  }

  function prepareEditableText() {
    views.forEach(view => {
      const code = view.dataset.languageView;
      const walker = document.createTreeWalker(view, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walker.nextNode()) if (!excludedTextNode(walker.currentNode)) nodes.push(walker.currentNode);
      nodes.forEach((node, index) => {
        const field = document.createElement('span');
        field.className = 'editable-text';
        field.dataset.editKey = `${code}:${index}`;
        field.textContent = node.nodeValue;
        node.replaceWith(field);
      });
    });
  }

  function editableFields() {
    return [...document.querySelectorAll('.editable-text[data-edit-key]')];
  }

  function valuesFromFields() {
    return Object.fromEntries(editableFields().map(field => [field.dataset.editKey, field.textContent]));
  }

  function applyValues(values) {
    editableFields().forEach(field => {
      if (Object.prototype.hasOwnProperty.call(values, field.dataset.editKey)) field.textContent = values[field.dataset.editKey];
    });
  }

  function loadSavedEdits() {
    try {
      const saved = JSON.parse(localStorage.getItem(editStorageKey) || '{}');
      if (saved && typeof saved === 'object') applyValues(saved);
    } catch (error) { /* Invalid or unavailable local storage falls back to source text. */ }
  }

  function refreshDerivedText() {
    views.forEach(view => {
      const links = [...view.querySelectorAll('.toc a')];
      [...view.querySelectorAll('.article-chapter')].forEach((chapter, index) => {
        const heading = chapter.querySelector(':scope>h2, :scope>.chapter-band h2');
        if (!heading || !links[index]) return;
        const title = heading.textContent.replace(/^\s*\d+\s*/, '').trim();
        links[index].textContent = `${String(index + 1).padStart(2, '0')} ${title}`;
      });
    });
    const activeTitle = document.querySelector('.language-view.is-active h1');
    if (activeTitle) document.title = activeTitle.textContent.trim();
  }

  function setEditMode(next) {
    editing = next;
    root.classList.toggle('is-editing', next);
    edit.setAttribute('aria-pressed', String(next));
    edit.setAttribute('aria-label', next ? 'Editing article text' : 'Edit article text');
    editActions.hidden = !next;
    language.disabled = next || views.length === 1;
    editableFields().forEach(field => {
      if (next) {
        field.setAttribute('contenteditable', 'true');
        field.spellcheck = true;
      } else {
        field.removeAttribute('contenteditable');
        field.removeAttribute('spellcheck');
      }
    });
    editStatus.textContent = next ? 'Editing text only' : '';
  }

  function beginEditing() {
    if (editing) return;
    editSnapshot = valuesFromFields();
    setEditMode(true);
    const first = document.querySelector('.language-view.is-active .editable-text');
    if (first) first.focus();
  }

  function saveEditing() {
    if (!editing) return;
    let status = 'Saved in this browser';
    try {
      localStorage.setItem(editStorageKey, JSON.stringify(valuesFromFields()));
    } catch (error) {
      status = 'Could not save locally';
    }
    setEditMode(false);
    editStatus.textContent = status;
    refreshDerivedText();
  }

  function cancelEditing() {
    if (!editing) return;
    applyValues(editSnapshot);
    setEditMode(false);
    refreshDerivedText();
  }

  prepareEditableText();
  loadSavedEdits();
  refreshDerivedText();

  document.addEventListener('click', event => {
    const action = event.target.closest('#edit,#edit-save,#edit-cancel');
    if (action?.id === 'edit') beginEditing();
    if (action?.id === 'edit-save') saveEditing();
    if (action?.id === 'edit-cancel') cancelEditing();
    if (editing && event.target.closest('.language-view a')) event.preventDefault();
  });

  document.addEventListener('beforeinput', event => {
    if (!editing || !event.target.matches('.editable-text')) return;
    if (event.inputType === 'insertParagraph' || event.inputType === 'insertLineBreak' || event.inputType === 'formatBold' || event.inputType === 'formatItalic') {
      event.preventDefault();
    }
  });

  document.addEventListener('paste', event => {
    if (!editing || !event.target.matches('.editable-text')) return;
    event.preventDefault();
    const text = event.clipboardData.getData('text/plain').replace(/\s*\n+\s*/g, ' ');
    document.execCommand('insertText', false, text);
  });

  document.addEventListener('drop', event => {
    if (editing && event.target.matches('.editable-text')) event.preventDefault();
  });

  document.addEventListener('keydown', event => {
    if (!editing) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      cancelEditing();
    } else if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
      event.preventDefault();
      saveEditing();
    }
  });

  if (location.hash && document.fonts) {
    document.fonts.ready.then(() => requestAnimationFrame(() => {
      const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (target) target.scrollIntoView();
    }));
  }
})();
