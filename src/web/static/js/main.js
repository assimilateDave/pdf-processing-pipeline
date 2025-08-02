// Main JavaScript for PDF Processing Pipeline

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert-dismissible').alert('close');
    }, 5000);
    
    // Initialize file drag and drop
    initializeDragAndDrop();
    
    // Initialize real-time updates
    initializeRealTimeUpdates();
});

// Utility functions
function showAlert(type, message, autoClose = true) {
    const alertId = 'alert-' + Date.now();
    const alert = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    $('.container').first().prepend(alert);
    
    if (autoClose && type !== 'danger') {
        setTimeout(function() {
            $(`#${alertId}`).alert('close');
        }, 5000);
    }
}

function showToast(message, type = 'info') {
    const toastId = 'toast-' + Date.now();
    const toast = `
        <div id="${toastId}" class="toast" role="alert">
            <div class="toast-header">
                <i class="bi bi-info-circle me-2"></i>
                <strong class="me-auto">PDF Pipeline</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    if (!$('.toast-container').length) {
        $('body').append('<div class="toast-container"></div>');
    }
    
    $('.toast-container').append(toast);
    new bootstrap.Toast(document.getElementById(toastId)).show();
}

function showLoading(message = 'Loading...') {
    const loadingOverlay = `
        <div class="loading-overlay">
            <div class="loading-spinner">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="mt-2">${message}</div>
            </div>
        </div>
    `;
    
    $('body').append(loadingOverlay);
}

function hideLoading() {
    $('.loading-overlay').remove();
}

// File drag and drop functionality
function initializeDragAndDrop() {
    $(document).on('dragover', '.file-upload-area', function(e) {
        e.preventDefault();
        $(this).addClass('dragover');
    });
    
    $(document).on('dragleave', '.file-upload-area', function(e) {
        e.preventDefault();
        $(this).removeClass('dragover');
    });
    
    $(document).on('drop', '.file-upload-area', function(e) {
        e.preventDefault();
        $(this).removeClass('dragover');
        
        const files = e.originalEvent.dataTransfer.files;
        handleFileUpload(files);
    });
}

function handleFileUpload(files) {
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
            // Handle PDF upload
            uploadPDF(file);
        } else {
            showAlert('warning', `File ${file.name} is not a PDF file`);
        }
    }
}

function uploadPDF(file) {
    // This would typically upload the file to the server
    // For now, just show a success message
    showToast(`PDF file ${file.name} would be uploaded and processed`);
}

// Real-time updates
let updateInterval;

function initializeRealTimeUpdates() {
    // Update every 30 seconds if on dashboard
    if (window.location.pathname === '/' || window.location.pathname.includes('dashboard')) {
        updateInterval = setInterval(updateDashboardData, 30000);
    }
}

function updateDashboardData() {
    $.get('/api/status')
        .done(function(response) {
            if (response.success) {
                updateProcessingStats(response.processing_stats);
                updateSystemStatus(response.system_status);
            }
        })
        .fail(function() {
            console.log('Failed to update dashboard data');
        });
}

function updateProcessingStats(stats) {
    // Update stat cards if they exist
    $('.stats-total').text(stats.total || 0);
    $('.stats-completed').text(stats.completed || 0);
    $('.stats-failed').text(stats.failed || 0);
    $('.stats-success-rate').text((stats.success_rate || 0).toFixed(1) + '%');
}

function updateSystemStatus(status) {
    // Update component status indicators
    for (let component in status.components) {
        const componentStatus = status.components[component];
        const indicator = $(`.status-${component}`);
        
        if (indicator.length) {
            if (componentStatus.available || componentStatus.connected) {
                indicator.removeClass('text-danger').addClass('text-success');
                indicator.find('i').removeClass('bi-x-circle-fill').addClass('bi-check-circle-fill');
            } else {
                indicator.removeClass('text-success').addClass('text-danger');
                indicator.find('i').removeClass('bi-check-circle-fill').addClass('bi-x-circle-fill');
            }
        }
    }
}

// API helper functions
function apiCall(method, url, data = null) {
    const options = {
        method: method,
        url: url,
        contentType: 'application/json'
    };
    
    if (data) {
        options.data = JSON.stringify(data);
    }
    
    return $.ajax(options);
}

function apiGet(url) {
    return apiCall('GET', url);
}

function apiPost(url, data) {
    return apiCall('POST', url, data);
}

// Format helpers
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function formatDuration(seconds) {
    if (seconds < 60) {
        return seconds.toFixed(1) + 's';
    } else if (seconds < 3600) {
        return Math.floor(seconds / 60) + 'm ' + (seconds % 60).toFixed(0) + 's';
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return hours + 'h ' + minutes + 'm';
    }
}

// Search functionality
function initializeSearch() {
    $('.search-input').on('input', debounce(function() {
        const query = $(this).val();
        if (query.length >= 3 || query.length === 0) {
            performSearch(query);
        }
    }, 300));
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function performSearch(query) {
    // Implement search functionality
    console.log('Searching for:', query);
}

// Export functions for global use
window.PDFPipeline = {
    showAlert: showAlert,
    showToast: showToast,
    showLoading: showLoading,
    hideLoading: hideLoading,
    apiGet: apiGet,
    apiPost: apiPost,
    formatBytes: formatBytes,
    formatDate: formatDate,
    formatDuration: formatDuration
};

// Clean up on page unload
$(window).on('beforeunload', function() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});