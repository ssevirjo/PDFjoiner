/**
 * PDF Dokumentu Apvienotājs - Klienta lietotne
 * Pārvalda failu augšupielādi, vilkšanu un nomešanu (drag & drop),
 * secības maiņu, priekšskatījumu un apvienošanu.
 */

let documents = [];
let dragSourceIndex = null;
let currentPreview = {
  fileId: null,
  fileName: '',
  currentPage: 0,
  totalPages: 1
};

// DOM elementi
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadSpinner = document.getElementById('uploadSpinner');
const uploadStatusText = document.getElementById('uploadStatusText');
const documentsSection = document.getElementById('documentsSection');
const filesList = document.getElementById('filesList');
const statFilesCount = document.getElementById('statFilesCount');
const statPagesCount = document.getElementById('statPagesCount');
const mergeBtnText = document.getElementById('mergeBtnText');
const mergeSubmitBtn = document.getElementById('mergeSubmitBtn');

// Rīkjoslas pogas
const sortAzBtn = document.getElementById('sortAzBtn');
const sortZaBtn = document.getElementById('sortZaBtn');
const reverseOrderBtn = document.getElementById('reverseOrderBtn');
const clearAllBtn = document.getElementById('clearAllBtn');
const addMoreFilesBtn = document.getElementById('addMoreFilesBtn');

// Iestatījumi
const outputFilenameInput = document.getElementById('outputFilename');
const outputFolderInput = document.getElementById('outputFolder');
const chooseFolderBtn = document.getElementById('chooseFolderBtn');
const imageFitSelect = document.getElementById('imageFitSelect');
const openAfterCreateCb = document.getElementById('openAfterCreate');
const openInExplorerCb = document.getElementById('openInExplorer');

// Priekšskatījuma modālais logs
const previewModal = document.getElementById('previewModal');
const previewModalTitle = document.getElementById('previewModalTitle');
const previewModalSubtitle = document.getElementById('previewModalSubtitle');
const previewImage = document.getElementById('previewImage');
const pageIndicator = document.getElementById('pageIndicator');
const prevPageBtn = document.getElementById('prevPageBtn');
const nextPageBtn = document.getElementById('nextPageBtn');
const modalCloseBtn = document.getElementById('modalCloseBtn');
const modalBackdrop = document.getElementById('modalBackdrop');

// Rezultāta modālais logs
const successModal = document.getElementById('successModal');
const successDetails = document.getElementById('successDetails');
const resPages = document.getElementById('resPages');
const resSize = document.getElementById('resSize');
const resCount = document.getElementById('resCount');
const downloadMergedLink = document.getElementById('downloadMergedLink');
const openFolderBtn = document.getElementById('openFolderBtn');
const closeSuccessBtn = document.getElementById('closeSuccessBtn');

// Motīva pārslēdzējs
const themeToggleBtn = document.getElementById('themeToggleBtn');

// Inicializācija
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  setupEventListeners();
});

function initTheme() {
  const savedTheme = localStorage.getItem('pdf_joiner_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const newTheme = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('pdf_joiner_theme', newTheme);
}

function setupEventListeners() {
  // Motīvs
  themeToggleBtn.addEventListener('click', toggleTheme);

  // Vilkšanas un nomešanas zona
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesUpload(e.dataTransfer.files);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFilesUpload(e.target.files);
    }
  });

  addMoreFilesBtn.addEventListener('click', () => {
    fileInput.value = '';
    fileInput.click();
  });

  // Ielādēt saglabāto mapi
  const savedFolder = localStorage.getItem('pdf_joiner_save_folder');
  if (savedFolder && outputFolderInput) {
    outputFolderInput.value = savedFolder;
  }

  if (chooseFolderBtn) {
    chooseFolderBtn.addEventListener('click', async () => {
      try {
        const resp = await fetch('/api/choose-folder', { method: 'POST' });
        const data = await resp.json();
        if (data.folder) {
          outputFolderInput.value = data.folder;
          localStorage.setItem('pdf_joiner_save_folder', data.folder);
        }
      } catch (err) {
        console.error('Kļūda izvēloties mapi:', err);
      }
    });
  }

  if (outputFolderInput) {
    outputFolderInput.addEventListener('change', () => {
      const val = outputFolderInput.value.trim();
      if (val) {
        localStorage.setItem('pdf_joiner_save_folder', val);
      } else {
        localStorage.removeItem('pdf_joiner_save_folder');
      }
    });
  }

  // Rīkjoslas darbības
  sortAzBtn.addEventListener('click', sortByNameAsc);
  sortZaBtn.addEventListener('click', sortByNameDesc);
  reverseOrderBtn.addEventListener('click', reverseOrder);
  clearAllBtn.addEventListener('click', clearAll);

  // Apvienošanas poga
  mergeSubmitBtn.addEventListener('click', submitMerge);

  // Priekšskatījuma pogas
  modalCloseBtn.addEventListener('click', closePreviewModal);
  modalBackdrop.addEventListener('click', closePreviewModal);
  prevPageBtn.addEventListener('click', () => navigatePreview(-1));
  nextPageBtn.addEventListener('click', () => navigatePreview(1));

  closeSuccessBtn.addEventListener('click', () => {
    successModal.classList.remove('active');
  });

  openFolderBtn.addEventListener('click', async () => {
    try {
      await fetch('/api/open-output-folder', { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  });

  // Tastatūras saīsnes priekšskatījumam
  window.addEventListener('keydown', (e) => {
    if (previewModal.classList.contains('active')) {
      if (e.key === 'Escape') closePreviewModal();
      if (e.key === 'ArrowLeft') navigatePreview(-1);
      if (e.key === 'ArrowRight') navigatePreview(1);
    }
  });
}

/**
 * Failu augšupielāde
 */
async function handleFilesUpload(fileList) {
  const formData = new FormData();
  let count = 0;
  for (let i = 0; i < fileList.length; i++) {
    formData.append('files', fileList[i]);
    count++;
  }

  showUploadSpinner(`Notiek ${count} dokumentu sagatavošana un apstrāde...`);

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Kļūda augšupielādējot failus');
    }

    const data = await response.json();
    const newFiles = (data.files || []).filter(f => !f.error);
    const errors = (data.files || []).filter(f => f.error);

    if (errors.length > 0) {
      alert(`Neizdevās pievienot šādus failus:\n` + errors.map(e => `${e.original_name}: ${e.error}`).join('\n'));
    }

    newFiles.forEach(f => {
      f.page_range = 'Visas';
      documents.push(f);
    });

    renderDocumentsList();
    updateStats();

  } catch (error) {
    alert(`Kļūda augšupielādē: ${error.message}`);
  } finally {
    hideUploadSpinner();
  }
}

function showUploadSpinner(text) {
  uploadStatusText.textContent = text;
  uploadSpinner.style.display = 'flex';
}

function hideUploadSpinner() {
  uploadSpinner.style.display = 'none';
}

/**
 * Dokumentu saraksta vizualizācija ar pārkārtošanas atbalstu
 */
function renderDocumentsList() {
  filesList.innerHTML = '';

  if (documents.length === 0) {
    documentsSection.style.display = 'none';
    return;
  }

  documentsSection.style.display = 'block';

  documents.forEach((doc, index) => {
    const itemEl = document.createElement('div');
    itemEl.className = 'file-item';
    itemEl.draggable = true;
    itemEl.dataset.index = index;

    let extClass = 'ext-pdf';
    let extLabel = 'PDF';
    if (doc.is_docx) {
      extClass = 'ext-docx';
      extLabel = 'DOCX';
    } else if (doc.is_image) {
      extClass = 'ext-img';
      extLabel = doc.extension.replace('.', '').toUpperCase();
    }

    const thumbSrc = doc.has_thumbnail ? `/api/thumbnail/${doc.id}` : '';
    const thumbHtml = doc.has_thumbnail 
      ? `<img src="${thumbSrc}" alt="thumb">` 
      : `<span class="thumbnail-placeholder">${extLabel}</span>`;

    itemEl.innerHTML = `
      <div class="drag-handle" title="Turiet nospiestu un velciet, lai mainītu secību">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="9" cy="5" r="1"></circle>
          <circle cx="9" cy="12" r="1"></circle>
          <circle cx="9" cy="19" r="1"></circle>
          <circle cx="15" cy="5" r="1"></circle>
          <circle cx="15" cy="12" r="1"></circle>
          <circle cx="15" cy="19" r="1"></circle>
        </svg>
      </div>

      <div class="item-index-badge">${index + 1}</div>

      <div class="item-thumbnail" onclick="openPreview('${doc.id}', '${escapeHtml(doc.original_name)}', ${doc.pages_count})" title="Noklikšķiniet, lai priekšskatītu">
        ${thumbHtml}
      </div>

      <div class="item-details">
        <div class="item-name-row">
          <span class="item-filename" title="${escapeHtml(doc.original_name)}">${escapeHtml(doc.original_name)}</span>
          <span class="item-ext-badge ${extClass}">${extLabel}</span>
        </div>
        <div class="item-meta-row">
          <span>${doc.size_formatted}</span>
          <span>•</span>
          <span>${doc.pages_count} ${getPagesLabel(doc.pages_count)}</span>
          ${!doc.is_image ? `
            <span>•</span>
            <div class="item-page-range">
              <span>Lappuses:</span>
              <input type="text" class="range-input" data-index="${index}" value="${escapeHtml(doc.page_range)}" placeholder="Visas" title="Piemēram: Visas vai 1-3, 5">
            </div>
          ` : ''}
        </div>
      </div>

      <div class="item-actions">
        <button class="btn-move" onclick="openPreview('${doc.id}', '${escapeHtml(doc.original_name)}', ${doc.pages_count})" title="Priekšskatīt lappuses">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
        </button>

        <button class="btn-move" onclick="moveItem(${index}, -1)" ${index === 0 ? 'disabled' : ''} title="Pārvietot uz augšu">
          ▲
        </button>
        <button class="btn-move" onclick="moveItem(${index}, 1)" ${index === documents.length - 1 ? 'disabled' : ''} title="Pārvietot uz leju">
          ▼
        </button>

        <button class="btn-move btn-item-delete" onclick="removeItem(${index})" title="Noņemt no saraksta">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    `;

    setupDragEvents(itemEl, index);

    const rangeInput = itemEl.querySelector('.range-input');
    if (rangeInput) {
      rangeInput.addEventListener('change', (e) => {
        documents[index].page_range = e.target.value.trim() || 'Visas';
        updateStats();
      });
    }

    filesList.appendChild(itemEl);
  });
}

function setupDragEvents(el, index) {
  el.addEventListener('dragstart', (e) => {
    dragSourceIndex = index;
    el.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  });

  el.addEventListener('dragend', () => {
    el.classList.remove('dragging');
    document.querySelectorAll('.file-item').forEach(i => {
      i.classList.remove('drag-over-top', 'drag-over-bottom');
    });
  });

  el.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    const rect = el.getBoundingClientRect();
    const midPoint = rect.top + rect.height / 2;
    if (e.clientY < midPoint) {
      el.classList.add('drag-over-top');
      el.classList.remove('drag-over-bottom');
    } else {
      el.classList.add('drag-over-bottom');
      el.classList.remove('drag-over-top');
    }
  });

  el.addEventListener('dragleave', () => {
    el.classList.remove('drag-over-top', 'drag-over-bottom');
  });

  el.addEventListener('drop', (e) => {
    e.preventDefault();
    el.classList.remove('drag-over-top', 'drag-over-bottom');

    const targetIndex = parseInt(el.dataset.index, 10);
    if (dragSourceIndex === null || dragSourceIndex === targetIndex) return;

    const rect = el.getBoundingClientRect();
    const midPoint = rect.top + rect.height / 2;
    let insertIndex = e.clientY < midPoint ? targetIndex : targetIndex + 1;

    const movedItem = documents.splice(dragSourceIndex, 1)[0];
    if (dragSourceIndex < insertIndex) {
      insertIndex--;
    }
    documents.splice(insertIndex, 0, movedItem);

    renderDocumentsList();
  });
}

/**
 * Pārvietošana uz augšu (-1) vai leju (+1)
 */
function moveItem(index, direction) {
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= documents.length) return;

  const temp = documents[index];
  documents[index] = documents[targetIndex];
  documents[targetIndex] = temp;

  renderDocumentsList();
}

/**
 * Noņemt atsevišķu vienumu
 */
function removeItem(index) {
  documents.splice(index, 1);
  renderDocumentsList();
  updateStats();
}

/**
 * Notīrīt visu sarakstu
 */
async function clearAll() {
  if (documents.length === 0) return;
  if (!confirm('Vai tiešām vēlaties noņemt visus pievienotos dokumentus?')) return;

  documents = [];
  renderDocumentsList();
  updateStats();

  try {
    await fetch('/api/clear', { method: 'POST' });
  } catch (e) {
    console.error(e);
  }
}

/**
 * Kārtošana ar latviešu valodas alfabēta atbalstu
 */
function sortByNameAsc() {
  documents.sort((a, b) => a.original_name.localeCompare(b.original_name, 'lv', { numeric: true, sensitivity: 'base' }));
  renderDocumentsList();
}

function sortByNameDesc() {
  documents.sort((a, b) => b.original_name.localeCompare(a.original_name, 'lv', { numeric: true, sensitivity: 'base' }));
  renderDocumentsList();
}

function reverseOrder() {
  documents.reverse();
  renderDocumentsList();
}

/**
 * Statistika
 */
function updateStats() {
  const totalFiles = documents.length;
  let totalPages = 0;

  documents.forEach(doc => {
    totalPages += doc.pages_count || 1;
  });

  statFilesCount.textContent = `${totalFiles} ${getFilesLabel(totalFiles)}`;
  statPagesCount.textContent = `~${totalPages} ${getPagesLabel(totalPages)}`;

  if (totalFiles > 0) {
    mergeBtnText.textContent = `APVIENOT VISUS DOKUMENTUS VIENĀ PDF (${totalFiles} ${getFilesLabel(totalFiles)})`;
  }
}

function getPagesLabel(count) {
  if (count === 1) return 'lappuse';
  return 'lappuses';
}

function getFilesLabel(count) {
  if (count === 1) return 'fails';
  return 'faili';
}

/**
 * Priekšskatījuma modālais logs
 */
function openPreview(fileId, fileName, totalPages) {
  currentPreview = {
    fileId,
    fileName,
    currentPage: 0,
    totalPages: totalPages || 1
  };

  previewModalTitle.textContent = fileName;
  updatePreviewImage();
  previewModal.classList.add('active');
}

function updatePreviewImage() {
  previewModalSubtitle.textContent = `Lappuse ${currentPreview.currentPage + 1} no ${currentPreview.totalPages}`;
  pageIndicator.textContent = `${currentPreview.currentPage + 1} / ${currentPreview.totalPages}`;

  prevPageBtn.disabled = currentPreview.currentPage <= 0;
  nextPageBtn.disabled = currentPreview.currentPage >= currentPreview.totalPages - 1;

  previewImage.src = `/api/preview/${currentPreview.fileId}/${currentPreview.currentPage}`;
}

function navigatePreview(direction) {
  const newPage = currentPreview.currentPage + direction;
  if (newPage >= 0 && newPage < currentPreview.totalPages) {
    currentPreview.currentPage = newPage;
    updatePreviewImage();
  }
}

function closePreviewModal() {
  previewModal.classList.remove('active');
}

/**
 * Apvienošanas pieprasījums
 */
async function submitMerge() {
  if (documents.length === 0) {
    alert('Lūdzu, vispirms pievienojiet vismaz vienu dokumentu apvienošanai.');
    return;
  }

  const chosenFolder = outputFolderInput ? outputFolderInput.value.trim() : null;

  const payload = {
    items: documents.map(d => ({
      id: d.id,
      page_range: d.page_range || 'all'
    })),
    output_filename: outputFilenameInput.value.trim() || 'Apvienotais_dokuments.pdf',
    output_folder: chosenFolder || null,
    image_fit: imageFitSelect.value,
    open_after_create: openAfterCreateCb.checked,
    open_explorer: openInExplorerCb.checked
  };

  mergeSubmitBtn.disabled = true;
  mergeBtnText.textContent = 'Notiek dokumentu apvienošana un PDF veidošana...';

  try {
    const response = await fetch('/api/merge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Kļūda dokumentu apvienošanā');
    }

    const result = await response.json();

    resPages.textContent = result.stats.total_pages;
    resSize.textContent = result.stats.size_formatted;
    resCount.textContent = result.stats.items_count;
    downloadMergedLink.href = result.download_url;
    downloadMergedLink.download = result.filename;
    
    const saveLocationText = result.saved_folder ? `\nSaglabāts mapē: ${result.saved_folder}` : '';
    successDetails.textContent = `Fails "${result.filename}" ir veiksmīgi izveidots ar pilnīgu latviešu valodas diakritikas un teksta saglabāšanu.${saveLocationText}`;

    successModal.classList.add('active');

  } catch (error) {
    alert(`Kļūda: ${error.message}`);
  } finally {
    mergeSubmitBtn.disabled = false;
    updateStats();
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
}
