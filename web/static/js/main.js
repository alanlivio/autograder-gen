/**
 * Main Application Module
 * Initializes the application and provides utility functions
 */

// Utility function to create properly namespaced field names (legacy support)
function createFieldName(questionIdx, markingItemIdx, field) {
  if (markingItemIdx !== undefined) {
    return `questions[${questionIdx}][marking_items][${markingItemIdx}][${field}]`;
  }
  return `questions[${questionIdx}][${field}]`;
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
  // Start with one question
  addQuestion();
  
  // Add form change monitoring to disable generate button when form is modified
  const form = document.getElementById('autograder-form');
  if (form) {
    form.addEventListener('input', disableGenerateButton);
    form.addEventListener('change', disableGenerateButton);
  }
  
  // Add specific listener for required files field to re-validate target files
  const requiredFilesField = document.getElementById('files_necessary');
  if (requiredFilesField) {
    requiredFilesField.addEventListener('input', validateTargetFilesOnRequiredFilesChange);
  }
});

// Function to disable generate button when form changes
function disableGenerateButton() {
  const generateBtn = document.getElementById('generate-btn');
  if (generateBtn && !generateBtn.disabled) {
    generateBtn.disabled = true;
    generateBtn.classList.remove('btn-primary');
    generateBtn.classList.add('btn-secondary');
    
    // Clear any existing success alerts as form has been modified
    const alertContainer = document.getElementById('alert-container');
    if (alertContainer) {
      const successAlerts = alertContainer.querySelectorAll('.alert-success');
      successAlerts.forEach(alert => alert.remove());
    }
  }
}

// Function to validate target files when required files field changes
function validateTargetFilesOnRequiredFilesChange() {
  const requiredFilesField = document.getElementById('files_necessary');
  if (!requiredFilesField) return;
  
  const requiredFiles = requiredFilesField.value
    .split('\n')
    .map(file => file.trim())
    .filter(file => file.length > 0);
  
  // Clear existing validation errors for target files
  document.querySelectorAll('.marking-item').forEach(markingItem => {
    const targetFileField = markingItem.querySelector('input[id$="-target-file"]');
    if (targetFileField) {
      const targetFile = targetFileField.value.trim();
      
      if (targetFile && requiredFiles.includes(targetFile)) {
        // Clear error state if target file is now in required files
        targetFileField.classList.remove('is-invalid');
        markingItem.style.border = '';
        markingItem.style.borderRadius = '';
      }
    }
  });
}

// Function to validate a single target file field
function validateSingleTargetFile(event) {
  const targetFileField = event.target;
  const markingItem = targetFileField.closest('.marking-item');
  const targetFile = targetFileField.value.trim();
  
  if (!targetFile) {
    // Clear validation state for empty field
    targetFileField.classList.remove('is-invalid');
    markingItem.style.border = '';
    markingItem.style.borderRadius = '';
    return;
  }
  
  const requiredFilesField = document.getElementById('files_necessary');
  if (!requiredFilesField) return;
  
  const requiredFiles = requiredFilesField.value
    .split('\n')
    .map(file => file.trim())
    .filter(file => file.length > 0);
  
  if (!requiredFiles.includes(targetFile)) {
    // Show error state
    targetFileField.classList.add('is-invalid');
    markingItem.style.border = '2px solid #dc3545';
    markingItem.style.borderRadius = '5px';
    
    // Find the question number for better error messaging
    const questionCard = markingItem.closest('.card');
    const questionNum = questionCard ? Array.from(questionCard.parentNode.children).indexOf(questionCard) + 1 : 'Unknown';
    const markingItemNum = Array.from(questionCard.querySelectorAll('.marking-item')).indexOf(markingItem) + 1;
    
    // Show tooltip or add title attribute for immediate feedback
    targetFileField.title = `This file must be listed in the Required Files field above`;
  } else {
    // Clear error state
    targetFileField.classList.remove('is-invalid');
    markingItem.style.border = '';
    markingItem.style.borderRadius = '';
    targetFileField.title = '';
  }
}

// Expose function to global scope
window.disableGenerateButton = disableGenerateButton;
window.validateTargetFilesOnRequiredFilesChange = validateTargetFilesOnRequiredFilesChange;
window.validateSingleTargetFile = validateSingleTargetFile;



