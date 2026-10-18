/**
 * 🐟 Quản Lý Dataset Cá Cảnh - JavaScript
 * Xử lý drag-and-drop, upload, preview, lightbox, delete
 */

// ============================================================
// GLOBAL STATE
// ============================================================
let selectedFiles = [];

// ============================================================
// DRAG & DROP
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    if (!dropZone || !fileInput) return;

    // Click to select files
    dropZone.addEventListener('click', function(e) {
        if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'LABEL') {
            fileInput.click();
        }
    });

    // File input change
    fileInput.addEventListener('change', function() {
        addFiles(this.files);
    });

    // Drag events
    ['dragenter', 'dragover'].forEach(event => {
        dropZone.addEventListener(event, function(e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(event => {
        dropZone.addEventListener(event, function(e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('drag-over');
        });
    });

    dropZone.addEventListener('drop', function(e) {
        const files = e.dataTransfer.files;
        addFiles(files);
    });
});


// ============================================================
// FILE HANDLING
// ============================================================

/**
 * Thêm files vào danh sách và hiển thị preview
 */
function addFiles(files) {
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'];

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (validTypes.includes(file.type)) {
            selectedFiles.push(file);
        } else {
            showToast(`File "${file.name}" không hợp lệ!`, 'danger');
        }
    }

    updatePreview();
    updateUploadButton();
}

/**
 * Cập nhật preview ảnh
 */
function updatePreview() {
    const previewSection = document.getElementById('previewSection');
    const previewGrid = document.getElementById('previewGrid');
    const previewCount = document.getElementById('previewCount');

    if (selectedFiles.length === 0) {
        previewSection.classList.add('d-none');
        return;
    }

    previewSection.classList.remove('d-none');
    previewCount.textContent = selectedFiles.length;
    previewGrid.innerHTML = '';

    selectedFiles.forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = function(e) {
            const col = document.createElement('div');
            col.className = 'col-xl-2 col-lg-3 col-md-4 col-6';
            col.innerHTML = `
                <div class="preview-item">
                    <img src="${e.target.result}" alt="${file.name}">
                    <button class="remove-btn" onclick="removeFile(${index})" title="Xóa">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <p class="small text-muted text-truncate mt-1 mb-0" title="${file.name}">${file.name}</p>
            `;
            previewGrid.appendChild(col);
        };
        reader.readAsDataURL(file);
    });
}

/**
 * Xóa một file khỏi danh sách preview
 */
function removeFile(index) {
    selectedFiles.splice(index, 1);
    updatePreview();
    updateUploadButton();
}

/**
 * Xóa tất cả files
 */
function clearPreview() {
    selectedFiles = [];
    updatePreview();
    updateUploadButton();
    document.getElementById('fileInput').value = '';
}

function updateUploadButton() {
    const uploadBtn = document.getElementById('uploadBtn');
    const speciesSelect = document.getElementById('speciesSelect');
    const smartNote = document.getElementById('smartAutoNote');

    if (uploadBtn) {
        const hasFiles = selectedFiles.length > 0;
        const isAuto = !speciesSelect || speciesSelect.value === 'auto' || speciesSelect.value === '';
        const hasSpecies = Boolean(speciesSelect && speciesSelect.value !== '');

        if (smartNote) {
            smartNote.style.display = isAuto ? 'block' : 'none';
        }

        uploadBtn.disabled = !(hasFiles && hasSpecies);

        if (hasFiles) {
            if (isAuto) {
                uploadBtn.className = 'btn btn-primary btn-lg shadow-sm';
                uploadBtn.innerHTML = `<i class="fas fa-bolt text-warning me-2"></i>🚀 Tải lên & AI Tự Động Phân Loại (${selectedFiles.length} ảnh)`;
            } else {
                uploadBtn.className = 'btn btn-success btn-lg';
                const sName = speciesSelect.options[speciesSelect.selectedIndex]?.text.split('(')[0].trim() || 'Loài đã chọn';
                uploadBtn.innerHTML = `<i class="fas fa-upload me-2"></i>Tải lên ${selectedFiles.length} ảnh vào ${sName}`;
            }
            const detectGroup = document.getElementById('detectBtnGroup') || document.getElementById('aiDetectBtn');
            if (detectGroup) detectGroup.style.display = 'inline-flex';
        } else {
            uploadBtn.className = 'btn btn-success btn-lg';
            uploadBtn.innerHTML = `<i class="fas fa-upload me-2"></i>Tải lên`;
            const detectGroup = document.getElementById('detectBtnGroup') || document.getElementById('aiDetectBtn');
            if (detectGroup) detectGroup.style.display = 'none';
        }
    }
}


/**
 * Nhận diện loài cá bằng mô hình YOLOv8 chạy trực tiếp cục bộ (Edge IoT)
 */
function detectFishWithYOLO() {
    if (selectedFiles.length === 0) return;
    const yoloBtn = document.getElementById('yoloDetectBtn');
    const alertBox = document.getElementById('aiDetectAlert');
    const select = document.getElementById('speciesSelect');

    if (yoloBtn) {
        yoloBtn.disabled = true;
        yoloBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>YOLOv8 đang soi...';
    }

    const fd = new FormData();
    fd.append('file', selectedFiles[0]);

    fetch('/api/yolo_classify', {
        method: 'POST',
        body: fd
    })
    .then(r => r.json())
    .then(data => {
        if (yoloBtn) {
            yoloBtn.disabled = false;
            yoloBtn.innerHTML = '<i class="fas fa-bolt me-1"></i>🚀 YOLOv8 Edge AI';
        }

        if (data.success && data.species_key) {
            select.value = data.species_key;
            updateUploadButton();
            if (alertBox) {
                const hy = data.hybrid_analysis;
                let hybridHtml = '';
                if (hy) {
                    if (hy.is_hybrid_alert) {
                        hybridHtml = `<div class="mt-1 text-warning fw-semibold"><i class="fas fa-exclamation-triangle me-1"></i>${hy.verdict}</div>`;
                    } else if (hy.morph_data && hy.morph_data.common_morphs) {
                        hybridHtml = `<div class="mt-1 text-muted"><i class="fas fa-dna me-1 text-primary"></i><strong>Họ:</strong> ${hy.family_name} | <strong>Biến thể:</strong> ${hy.morph_data.common_morphs.slice(0, 3).join(', ')}...</div>`;
                    }
                }
                alertBox.className = hy && hy.is_hybrid_alert ? 'alert alert-warning py-2 px-3 small' : 'alert alert-success py-2 px-3 small';
                alertBox.innerHTML = `<strong><i class="fas fa-bolt me-1"></i>YOLOv8 Nhận diện:</strong> ${data.species_name} (Độ tin cậy: ${data.confidence}). <br><span class="text-muted">Nhiệt độ IoT: ${data.environment.temperature} | pH IoT: ${data.environment.ph}</span>${hybridHtml}`;
            }
            showToast(`YOLOv8 nhận diện: ${data.species_name} (${data.confidence})!`, 'success');
        } else {
            showToast(data.error || 'YOLOv8 không nhận diện được.', 'warning');
        }
    })
    .catch(err => {
        if (yoloBtn) {
            yoloBtn.disabled = false;
            yoloBtn.innerHTML = '<i class="fas fa-bolt me-1"></i>🚀 YOLOv8 Edge AI';
        }
        showToast('Lỗi khi gọi YOLOv8 nhận diện', 'danger');
    });
}

/**
 * AI tự động nhận diện ảnh đầu tiên và tự chọn loài cá trong dropdown
 */
function detectFishWithAI() {
    if (selectedFiles.length === 0) return;
    const aiBtn = document.getElementById('aiDetectBtn');
    const alertBox = document.getElementById('aiDetectAlert');
    const select = document.getElementById('speciesSelect');

    aiBtn.disabled = true;
    aiBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>AI đang soi ảnh...';

    const fd = new FormData();
    fd.append('file', selectedFiles[0]);

    fetch('/api/ai_classify', {
        method: 'POST',
        body: fd
    })
    .then(r => r.json())
    .then(data => {
        aiBtn.disabled = false;
        aiBtn.innerHTML = '<i class="fas fa-magic me-1"></i>👁️ Gemini Vision';

        if (data.success && data.species_key) {
            select.value = data.species_key;
            updateUploadButton();
            if (alertBox) {
                alertBox.className = 'alert alert-info py-2 px-3 small';
                alertBox.innerHTML = `<strong><i class="fas fa-robot me-1"></i>AI nhận diện:</strong> ${data.species_name} (Độ tin cậy: ${data.confidence}). <br><span class="text-muted">${data.reason}</span>`;
            }
            showToast(`AI nhận diện: ${data.species_name}!`, 'success');
        } else {
            showToast(data.error || 'AI không nhận diện được loài cá này.', 'warning');
        }
    })
    .catch(err => {
        aiBtn.disabled = false;
        aiBtn.innerHTML = '<i class="fas fa-magic me-1"></i>👁️ Gemini Vision';
        showToast('Lỗi khi gọi AI nhận diện', 'danger');
    });
}

// Watch species selection change
document.addEventListener('DOMContentLoaded', function() {
    const speciesSelect = document.getElementById('speciesSelect');
    if (speciesSelect) {
        speciesSelect.addEventListener('change', updateUploadButton);
    }
});


// ============================================================
// UPLOAD
// ============================================================

/**
 * Upload files lên server
 */
function uploadFiles() {
    const speciesSelect = document.getElementById('speciesSelect');
    const species = speciesSelect.value;

    if (!species) {
        showToast('Vui lòng chọn loài cá!', 'warning');
        return;
    }

    if (selectedFiles.length === 0) {
        showToast('Vui lòng chọn ảnh!', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('species', species);
    selectedFiles.forEach(file => {
        formData.append('files', file);
    });

    const progressDiv = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('uploadProgressBar');
    const percentText = document.getElementById('uploadPercent');
    const uploadBtn = document.getElementById('uploadBtn');
    const resultDiv = document.getElementById('uploadResult');

    progressDiv.classList.remove('d-none');
    resultDiv.classList.add('d-none');
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Đang tải lên...';

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload', true);

    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            progressBar.style.width = percent + '%';
            percentText.textContent = percent + '%';
        }
    };

    xhr.onload = function() {
        progressDiv.classList.add('d-none');
        resultDiv.classList.remove('d-none');

        if (xhr.status === 200) {
            const data = JSON.parse(xhr.responseText);
            if (data.mode === 'auto') {
                let summaryBadges = '';
                if (data.species_summary) {
                    for (const [sKey, sCount] of Object.entries(data.species_summary)) {
                        summaryBadges += `<a href="/gallery/${sKey}" class="badge bg-primary text-decoration-none p-2 me-2 mb-2"><i class="fas fa-fish me-1"></i>${sKey}: <strong>+${sCount}</strong> ảnh</a>`;
                    }
                }

                let itemsTable = '';
                if (data.items && data.items.length > 0) {
                    itemsTable = `
                        <div class="table-responsive mt-3" style="max-height: 250px; overflow-y: auto;">
                            <table class="table table-sm table-hover align-middle mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th>Tên file</th>
                                        <th>AI Nhận diện</th>
                                        <th>Độ tin cậy</th>
                                        <th>Độ nét (Laplacian)</th>
                                        <th>Trạng thái</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.items.map(it => `
                                        <tr>
                                            <td class="small text-truncate" style="max-width: 160px;" title="${it.original_name}">${it.original_name}</td>
                                            <td><span class="badge bg-success-subtle text-success border border-success">${it.species_name}</span></td>
                                            <td><strong>${it.confidence.toFixed(1)}%</strong></td>
                                            <td><span class="badge ${it.is_sharp ? 'bg-light text-dark' : 'bg-warning text-dark'}">${it.blur_score}</span></td>
                                            <td><i class="fas fa-check-circle text-success me-1"></i>Đã nạp</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                }

                resultDiv.innerHTML = `
                    <div class="alert alert-success border-0 shadow-sm p-3">
                        <div class="d-flex align-items-center mb-2">
                            <i class="fas fa-bolt fa-2x text-warning me-3"></i>
                            <div>
                                <h5 class="mb-0 text-success fw-bold">🚀 AI Tự Động Phân Loại Thành Công!</h5>
                                <small class="text-muted">Đã nhận diện & nạp ${data.uploaded_count} ảnh vào các thư mục tương ứng trong ~vài mili-giây</small>
                            </div>
                        </div>
                        <hr class="my-2">
                        <div class="d-flex flex-wrap align-items-center mt-2 mb-1">
                            <span class="fw-semibold me-2 small">Phân bố loài:</span>
                            ${summaryBadges}
                        </div>
                        ${itemsTable}
                        ${data.errors.length > 0 ? '<div class="alert alert-warning py-1 px-2 mt-2 mb-0 small">' + data.errors.join('<br>') + '</div>' : ''}
                        <div class="mt-3 d-flex justify-content-between">
                            <button class="btn btn-sm btn-outline-primary" onclick="clearPreview(); document.getElementById('uploadResult').classList.add('d-none');">
                                <i class="fas fa-plus me-1"></i>Thêm tiếp đợt ảnh khác
                            </button>
                            <a href="/" class="btn btn-sm btn-success">
                                <i class="fas fa-chart-line me-1"></i>Về Dashboard xem tiến độ
                            </a>
                        </div>
                    </div>
                `;
            } else {
                resultDiv.innerHTML = `
                    <div class="alert alert-success">
                        <h6><i class="fas fa-check-circle me-2"></i>Tải lên thành công!</h6>
                        <p class="mb-1">Đã thêm <strong>${data.uploaded_count}</strong> ảnh vào <strong>${data.species_name}</strong></p>
                        ${data.errors.length > 0 ? '<p class="text-danger mb-0"><small>' + data.errors.join('<br>') + '</small></p>' : ''}
                        <hr>
                        <a href="/gallery/${data.species}" class="btn btn-sm btn-outline-success me-2">
                            <i class="fas fa-images me-1"></i>Xem ảnh
                        </a>
                        <button class="btn btn-sm btn-outline-primary" onclick="location.reload()">
                            <i class="fas fa-plus me-1"></i>Thêm ảnh tiếp
                        </button>
                    </div>
                `;
            }
            clearPreview();
        } else {
            const data = JSON.parse(xhr.responseText);
            resultDiv.innerHTML = `
                <div class="alert alert-danger">
                    <h6><i class="fas fa-times-circle me-2"></i>Lỗi!</h6>
                    <p class="mb-0">${data.error || 'Đã xảy ra lỗi khi tải lên.'}</p>
                </div>
            `;
        }

        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="fas fa-upload me-2"></i>Tải lên';
        progressBar.style.width = '0%';
    };

    xhr.onerror = function() {
        progressDiv.classList.add('d-none');
        showToast('Lỗi kết nối! Vui lòng thử lại.', 'danger');
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="fas fa-upload me-2"></i>Tải lên';
    };

    xhr.send(formData);
}


// ============================================================
// LIGHTBOX
// ============================================================

/**
 * Mở lightbox xem ảnh lớn
 */
function openLightbox(src, title) {
    document.getElementById('lightboxImage').src = src;
    document.getElementById('lightboxTitle').textContent = title;
    const modal = new bootstrap.Modal(document.getElementById('lightboxModal'));
    modal.show();
}


// ============================================================
// DELETE IMAGE
// ============================================================

/**
 * Xóa ảnh với xác nhận
 */
function deleteImage(species, filename, elementId) {
    if (!confirm(`Bạn có chắc muốn xóa ảnh "${filename}"?`)) {
        return;
    }

    fetch(`/api/delete/${species}/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Animate removal
            const element = document.getElementById(elementId);
            if (element) {
                element.style.transition = 'all 0.3s ease';
                element.style.opacity = '0';
                element.style.transform = 'scale(0.8)';
                setTimeout(() => element.remove(), 300);
            }
            showToast('Đã xóa ảnh thành công!', 'success');
        } else {
            showToast('Lỗi: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        showToast('Lỗi kết nối!', 'danger');
    });
}


// ============================================================
// TOAST NOTIFICATIONS
// ============================================================

/**
 * Hiển thị toast notification
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: 'fa-check-circle',
        danger: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center border-0 text-bg-${type}" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas ${icons[type] || icons.info} me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', toastHtml);

    const toastEl = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();

    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}


// ============================================================
// MOVE IMAGE MODAL LOGIC (CHUYỂN LOÀI CÁ TOÀN DIỆN)
// ============================================================
let currentMoveState = {
    fromSpecies: '',
    filename: '',
    elementId: '',
    suggestedSpecies: ''
};

function openMoveModal(fromSpecies, filename, suggestedSpeciesKey, elementId) {
    currentMoveState = {
        fromSpecies: fromSpecies,
        filename: filename,
        elementId: elementId,
        suggestedSpecies: suggestedSpeciesKey || ''
    };

    const modalEl = document.getElementById('moveImageModal');
    if (!modalEl) {
        console.error('Modal #moveImageModal không tồn tại');
        return;
    }

    const speciesMap = window.GLOBAL_SPECIES_MAP || {};
    const imgPreview = document.getElementById('moveModalImg');
    const filenameEl = document.getElementById('moveModalFilename');
    const currentSpeciesEl = document.getElementById('moveModalCurrentSpecies');
    const selectEl = document.getElementById('moveModalSelect');
    const suggestionEl = document.getElementById('moveModalAiSuggestion');

    // Cập nhật thông tin preview
    imgPreview.src = `/image_preview?species=${encodeURIComponent(fromSpecies)}&file=${encodeURIComponent(filename)}`;
    imgPreview.alt = filename;
    filenameEl.textContent = filename;
    filenameEl.title = filename;
    currentSpeciesEl.textContent = speciesMap[fromSpecies] || fromSpecies;

    // Đổ danh sách 19 loài còn lại vào select
    selectEl.innerHTML = '';
    const sortedEntries = Object.entries(speciesMap).sort((a, b) => a[1].localeCompare(b[1]));

    sortedEntries.forEach(([key, name]) => {
        if (key !== fromSpecies) {
            const opt = document.createElement('option');
            opt.value = key;
            opt.textContent = name;
            if (suggestedSpeciesKey && key === suggestedSpeciesKey) {
                opt.selected = true;
            }
            selectEl.appendChild(opt);
        }
    });

    if (suggestedSpeciesKey && speciesMap[suggestedSpeciesKey]) {
        suggestionEl.innerHTML = `<span class="badge bg-info text-dark me-1"><i class="fas fa-robot me-1"></i>AI Gợi ý:</span> Chuyển sang <strong>${speciesMap[suggestedSpeciesKey]}</strong>`;
    } else {
        suggestionEl.textContent = 'Chọn loài đúng từ danh sách trên để chuyển ảnh.';
    }

    const btn = document.getElementById('confirmMoveBtn');
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-check me-1"></i> Xác nhận chuyển ngay';

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
}

function submitMoveImage() {
    const selectEl = document.getElementById('moveModalSelect');
    const toSpecies = selectEl.value;
    const btn = document.getElementById('confirmMoveBtn');

    if (!toSpecies) {
        showToast('Vui lòng chọn loài cá đích!', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Đang chuyển...';

    fetch('/api/move_image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            from_species: currentMoveState.fromSpecies,
            to_species: toSpecies,
            filename: currentMoveState.filename
        })
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check me-1"></i> Xác nhận chuyển ngay';

        if (data.success) {
            const modalEl = document.getElementById('moveImageModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();

            // Xóa phần tử khỏi giao diện nếu có
            if (currentMoveState.elementId) {
                const el = document.getElementById(currentMoveState.elementId);
                if (el) {
                    el.style.transition = 'all 0.3s ease';
                    el.style.opacity = '0';
                    el.style.transform = 'scale(0.8)';
                    setTimeout(() => el.remove(), 300);
                }
            }

            // Cập nhật số đếm nếu ở trang dashboard
            if (typeof updateFlaggedBadgeCount === 'function') {
                setTimeout(updateFlaggedBadgeCount, 350);
            }

            showToast(data.message || 'Chuyển loài thành công!', 'success');
        } else {
            showToast(data.error || 'Lỗi khi chuyển ảnh!', 'danger');
        }
    })
    .catch(err => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check me-1"></i> Xác nhận chuyển ngay';
        showToast('Lỗi kết nối máy chủ!', 'danger');
    });
}

function deleteFlaggedImage(species, filename, cardId) {
    if (!confirm(`Bạn có chắc muốn xóa vĩnh viễn ảnh "${filename}" vì sai loài?`)) return;
    fetch(`/api/delete/${encodeURIComponent(species)}/${encodeURIComponent(filename)}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                const el = document.getElementById(cardId);
                if (el) {
                    el.style.transition = 'all 0.3s ease';
                    el.style.opacity = '0';
                    setTimeout(() => el.remove(), 300);
                }
                showToast('Đã xóa ảnh nhầm lẫn thành công!', 'success');
                setTimeout(updateFlaggedBadgeCount, 350);
            } else {
                showToast(d.error || 'Lỗi khi xóa', 'danger');
            }
        });
}

function updateFlaggedBadgeCount() {
    const list = document.getElementById('flaggedWrongList');
    const badge = document.getElementById('flaggedCountBadge');
    if (list && badge) {
        const count = list.querySelectorAll('[id^="flag-card-"]').length;
        badge.textContent = `${count} ảnh`;
        if (count === 0) {
            list.innerHTML = `
                <div class="text-center py-4 text-success">
                    <i class="fas fa-check-circle fa-2x mb-2"></i>
                    <p class="mb-0 small fw-semibold">Tuyệt vời! Hiện không có ảnh nào bị nghi ngờ sai loài.</p>
                </div>
            `;
        }
    }
}


