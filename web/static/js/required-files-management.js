/**
 * Required Files Management Module
 * Handles adding, removing, and editing required files
 */

let requiredFiles = [];

/**
 * Add a required file to the list
 */
function addRequiredFile() {
    const input = document.getElementById('new-file-input');
    const filename = input.value.trim();
    
    if (!filename) {
        showAlert('Please enter a filename', 'warning');
        return;
    }
    
    // Check for duplicates
    if (requiredFiles.includes(filename)) {
        showAlert('This file is already in the required files list', 'warning');
        return;
    }
    
    // Validate filename format
    if (!isValidFilename(filename)) {
        showAlert('Please enter a valid filename (e.g., solution.py, data.csv)', 'warning');
        return;
    }
    
    // Add to array and update UI
    requiredFiles.push(filename);
    input.value = '';
    updateRequiredFilesDisplay();
    updateHiddenTextarea();
    
    // Trigger form validation update
    if (typeof disableGenerateButton === 'function') {
        disableGenerateButton();
    }
}

/**
 * Remove a required file from the list
 * @param {string} filename - The filename to remove
 */
function removeRequiredFile(filename) {
    const index = requiredFiles.indexOf(filename);
    if (index > -1) {
        requiredFiles.splice(index, 1);
        updateRequiredFilesDisplay();
        updateHiddenTextarea();
        
        // Trigger form validation update
        if (typeof disableGenerateButton === 'function') {
            disableGenerateButton();
        }
    }
}

/**
 * Edit a required file inline
 * @param {string} oldFilename - The current filename
 * @param {HTMLElement} element - The element being edited
 */
function editRequiredFile(oldFilename, element) {
    const currentText = element.textContent;
    
    // Create an input element
    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentText;
    input.className = 'form-control form-control-sm d-inline-block';
    input.style.width = 'auto';
    input.style.minWidth = '150px';
    
    // Replace the span with the input
    element.parentNode.replaceChild(input, element);
    input.focus();
    input.select();
    
    // Handle save on blur or enter
    const saveEdit = () => {
        const newFilename = input.value.trim();
        
        if (!newFilename) {
            showAlert('Filename cannot be empty', 'warning');
            updateRequiredFilesDisplay(); // Revert changes
            return;
        }
        
        if (newFilename !== oldFilename && requiredFiles.includes(newFilename)) {
            showAlert('This filename already exists', 'warning');
            updateRequiredFilesDisplay(); // Revert changes
            return;
        }
        
        if (!isValidFilename(newFilename)) {
            showAlert('Please enter a valid filename', 'warning');
            updateRequiredFilesDisplay(); // Revert changes
            return;
        }
        
        // Update the array
        const index = requiredFiles.indexOf(oldFilename);
        if (index > -1) {
            requiredFiles[index] = newFilename;
            updateRequiredFilesDisplay();
            updateHiddenTextarea();
            
            // Trigger form validation update
            if (typeof disableGenerateButton === 'function') {
                disableGenerateButton();
            }
        }
    };
    
    input.addEventListener('blur', saveEdit);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveEdit();
        } else if (e.key === 'Escape') {
            updateRequiredFilesDisplay(); // Revert changes
        }
    });
}

/**
 * Update the visual display of required files
 */
function updateRequiredFilesDisplay() {
    const container = document.getElementById('required-files-list');
    
    if (requiredFiles.length === 0) {
        container.innerHTML = '<small class="text-muted">No required files added yet. Students must submit these files.</small>';
        return;
    }
    
    const filesHtml = requiredFiles.map(filename => {
        const extension = filename.split('.').pop()?.toLowerCase() || '';
        const icon = getFileIcon(extension);
        
        return `
            <span class="badge bg-primary me-2 mb-2 d-inline-flex align-items-center" style="font-size: 0.9rem; padding: 0.5rem;">
                <i class="${icon} me-1"></i>
                <span class="file-name" onclick="editRequiredFile('${filename}', this)" style="cursor: pointer;" title="Click to edit">
                    ${filename}
                </span>
                <button type="button" class="btn-close btn-close-white ms-2" style="font-size: 0.7rem;" 
                        onclick="removeRequiredFile('${filename}')" title="Remove file"></button>
            </span>
        `;
    }).join('');
    
    container.innerHTML = filesHtml;
    
    // Update all target file dropdowns in marking items
    if (typeof updateAllTargetFileDropdowns === 'function') {
        updateAllTargetFileDropdowns();
    }
}

/**
 * Update the hidden textarea for form submission compatibility
 */
function updateHiddenTextarea() {
    const textarea = document.getElementById('files_necessary');
    textarea.value = requiredFiles.join('\n');
    
    // Trigger change event for form validation
    textarea.dispatchEvent(new Event('change', { bubbles: true }));
}

/**
 * Get appropriate icon for file extension
 * @param {string} extension - File extension
 * @returns {string} - Font Awesome icon class
 */
function getFileIcon(extension) {
    const iconMap = {
        'py': 'fab fa-python',
        'js': 'fab fa-js-square',
        'html': 'fab fa-html5',
        'css': 'fab fa-css3-alt',
        'java': 'fab fa-java',
        'cpp': 'fas fa-code',
        'c': 'fas fa-code',
        'txt': 'fas fa-file-alt',
        'csv': 'fas fa-file-csv',
        'json': 'fas fa-file-code',
        'xml': 'fas fa-file-code',
        'sql': 'fas fa-database',
        'md': 'fab fa-markdown',
        'pdf': 'fas fa-file-pdf',
        'doc': 'fas fa-file-word',
        'docx': 'fas fa-file-word',
        'xls': 'fas fa-file-excel',
        'xlsx': 'fas fa-file-excel',
        'ppt': 'fas fa-file-powerpoint',
        'pptx': 'fas fa-file-powerpoint',
        'zip': 'fas fa-file-archive',
        'rar': 'fas fa-file-archive',
        'tar': 'fas fa-file-archive',
        'gz': 'fas fa-file-archive',
        'img': 'fas fa-file-image',
        'jpg': 'fas fa-file-image',
        'jpeg': 'fas fa-file-image',
        'png': 'fas fa-file-image',
        'gif': 'fas fa-file-image',
        'svg': 'fas fa-file-image'
    };
    
    return iconMap[extension] || 'fas fa-file';
}

/**
 * Validate filename format
 * @param {string} filename - The filename to validate
 * @returns {boolean} - Whether the filename is valid
 */
function isValidFilename(filename) {
    // Basic filename validation
    if (!filename || filename.length === 0) return false;
    
    // Check for invalid characters (basic check)
    const invalidChars = /[<>:"/\\|?*\x00-\x1f]/;
    if (invalidChars.test(filename)) return false;
    
    // Should have at least one character before extension
    if (filename.startsWith('.')) return false;
    
    // Should not end with a space or period (Windows restriction)
    if (filename.endsWith(' ') || filename.endsWith('.')) return false;
    
    return true;
}

/**
 * Handle Enter key in the new file input
 */
function handleNewFileKeyPress(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        addRequiredFile();
    }
}

/**
 * Populate required files from an array (for config upload)
 * @param {string[]} files - Array of filenames
 */
function populateRequiredFiles(files) {
    requiredFiles = [...files]; // Create a copy
    updateRequiredFilesDisplay();
    updateHiddenTextarea();
}

/**
 * Get current required files array
 * @returns {string[]} - Current required files
 */
function getRequiredFiles() {
    return [...requiredFiles]; // Return a copy
}

/**
 * Clear all required files
 */
function clearRequiredFiles() {
    requiredFiles = [];
    updateRequiredFilesDisplay();
    updateHiddenTextarea();
}

// Add event listener when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const newFileInput = document.getElementById('new-file-input');
    if (newFileInput) {
        newFileInput.addEventListener('keypress', handleNewFileKeyPress);
    }
});

// Expose functions to global scope for HTML onclick handlers
window.addRequiredFile = addRequiredFile;
window.removeRequiredFile = removeRequiredFile;
window.editRequiredFile = editRequiredFile;
window.populateRequiredFiles = populateRequiredFiles;
window.getRequiredFiles = getRequiredFiles;
window.clearRequiredFiles = clearRequiredFiles;
