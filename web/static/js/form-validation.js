/**
 * Form Validation Module
 * Handles client-side form validation
 */

function validateNumber(input) {
  const value = parseInt(input.value);
  if (isNaN(value) || value < 0) {
    input.classList.add('is-invalid');
  } else {
    input.classList.remove('is-invalid');
  }
}

function validateJsonField(input) {
  try {
    if (input.value) {
      JSON.parse(input.value);
      input.classList.remove('is-invalid');
    }
  } catch (e) {
    input.classList.add('is-invalid');
  }
}

function validateForm() {
  let isValid = true;
  let validationErrors = [];
  let validationWarnings = [];
  clearFieldErrors();
  
  // Validate global required fields
  const requiredGlobalFields = ['language'];
  requiredGlobalFields.forEach(fieldName => {
    const field = document.getElementById(fieldName);
    if (field && !field.value.trim()) {
      field.classList.add('is-invalid');
      validationErrors.push(`${fieldName} is required.`);
      isValid = false;
    }
  });
  
  // Validate questions
  const questionCards = document.querySelectorAll('#questions-list > .card');
  if (questionCards.length === 0) {
    validationErrors.push('At least one question is required.');
    isValid = false;
  }
  
  questionCards.forEach((questionCard, qIdx) => {
    // Validate question name
    const nameField = questionCard.querySelector('input[id$="-name"]');
    if (nameField && !nameField.value.trim()) {
      nameField.classList.add('is-invalid');
      validationErrors.push(`Question ${qIdx + 1}: Question name is required.`);
      isValid = false;
    }
    
    // Validate marking items
    const markingItems = questionCard.querySelectorAll('.marking-item');
    if (markingItems.length === 0) {
      validationErrors.push(`Question ${qIdx + 1} must have at least one marking item.`);
      isValid = false;
    }
    
    markingItems.forEach((markingItem, miIdx) => {
      // Validate required marking item fields
      const typeField = markingItem.querySelector('select[id$="-type"]');
      const targetFileField = markingItem.querySelector('select[id$="-target-file"]');
      const totalMarkField = markingItem.querySelector('input[id$="-total-mark"]');
      
      if (typeField && !typeField.value) {
        typeField.classList.add('is-invalid');
        validationErrors.push(`Question ${qIdx + 1}, Marking Item ${miIdx + 1}: Test type must be selected.`);
        isValid = false;
      }
      
      if (targetFileField && !targetFileField.value.trim()) {
        targetFileField.classList.add('is-invalid');
        validationErrors.push(`Question ${qIdx + 1}, Marking Item ${miIdx + 1}: Target file is required.`);
        isValid = false;
      }
      
      if (totalMarkField) {
        const value = totalMarkField.value.trim();
        if (!value) {
          // Empty points field
          totalMarkField.classList.add('is-invalid');
          validationErrors.push(`Question ${qIdx + 1}, Marking Item ${miIdx + 1}: Points field is required.`);
          isValid = false;
        } else {
          const numValue = parseInt(value);
          if (isNaN(numValue)) {
            totalMarkField.classList.add('is-invalid');
            validationErrors.push(`Question ${qIdx + 1}, Marking Item ${miIdx + 1}: Points must be a valid number.`);
            isValid = false;
          }
        }
      }
      
      // Type-specific validation
      const type = typeField ? typeField.value : '';
      if (type === 'function_test' || type === 'signature_check') {
        const functionNameField = markingItem.querySelector('input[id$="-function-name"]');
        if (functionNameField && !functionNameField.value.trim()) {
          functionNameField.classList.add('is-invalid');
          validationErrors.push(`Question ${qIdx + 1}, Marking Item ${miIdx + 1}: Function name is required for ${type.replace('_', ' ')} tests.`);
          isValid = false;
        }
      }
      
      if (type === 'function_test') {
        const testCasesField = markingItem.querySelector('textarea[id$="-test-cases"]');
        if (testCasesField && !testCasesField.value.trim()) {
          testCasesField.classList.add('is-invalid');
          validationErrors.push(`Question ${qIdx + 1}, Marking Item ${miIdx + 1}: Test cases are required for function tests.`);
          isValid = false;
        }
      }
      
      if (type === 'output_comparison') {
        const expectedOutputField = markingItem.querySelector('textarea[id$="-expected-output"]');
        if (expectedOutputField && !expectedOutputField.value.trim()) {
          expectedOutputField.classList.add('is-invalid');
          validationErrors.push(`Question ${qIdx + 1}, Marking Item ${miIdx + 1}: Expected output is required for output comparison tests.`);
          isValid = false;
        }
      }
    });
  });
  
  // Validate number fields
  document.querySelectorAll('input[type="number"]').forEach(input => {
    if (input.hasAttribute('required') && input.value.trim()) {
      const value = parseInt(input.value);
      
      // Allow negative values for points fields, but not for time limits
      if (input.id.includes('total-mark')) {
        // Points can be negative (for penalties)
        if (isNaN(value)) {
          input.classList.add('is-invalid');
          isValid = false;
        }
      } else {
        // Other number fields (like time limits) must be positive
        if (isNaN(value) || value < 0) {
          input.classList.add('is-invalid');
          isValid = false;
        }
      }
    }
  });

  // Validate that target files are included in required files
  let requiredFiles = [];
  
  // Try to get required files from the new management system first
  if (typeof getRequiredFiles === 'function') {
    requiredFiles = getRequiredFiles();
  } else {
    // Fallback to old textarea method if new system not available
    const requiredFilesField = document.getElementById('files_necessary');
    if (requiredFilesField) {
      requiredFiles = requiredFilesField.value
        .split('\n')
        .map(file => file.trim())
        .filter(file => file.length > 0);
    }
  }
  
  if (requiredFiles.length > 0) {
    
    // Check each marking item's target file
    document.querySelectorAll('.marking-item').forEach((markingItem, index) => {
      const targetFileField = markingItem.querySelector('select[id$="-target-file"]');
      if (targetFileField && targetFileField.value.trim()) {
        const targetFile = targetFileField.value.trim();
        
        if (!requiredFiles.includes(targetFile)) {
          targetFileField.classList.add('is-invalid');
          
          // Add visual indicator to the marking item
          markingItem.style.border = '2px solid #dc3545';
          markingItem.style.borderRadius = '5px';
          
          // Find the question number for better error messaging
          const questionCard = markingItem.closest('.card');
          const questionNum = questionCard ? Array.from(questionCard.parentNode.children).indexOf(questionCard) + 1 : 'Unknown';
          const markingItemNum = Array.from(questionCard.querySelectorAll('.marking-item')).indexOf(markingItem) + 1;
          
          validationWarnings.push(`Question ${questionNum}, Marking Item ${markingItemNum}: Target file "${targetFile}" must be listed in the Required Files field.`);
          isValid = false;
        }
      }
    });
  }
  
  // Validate JSON fields
  document.querySelectorAll('textarea[name$="[test_cases]"]').forEach(textarea => {
    if (textarea.value.trim()) {
      try {
        const parsed = JSON.parse(textarea.value);
        if (!Array.isArray(parsed)) {
          textarea.classList.add('is-invalid');
          isValid = false;
        }
      } catch (e) {
        textarea.classList.add('is-invalid');
        isValid = false;
      }
    }
  });
  
  // Display all validation results
  if (!isValid) {
    let errorMessage = '';
    
    if (validationErrors.length > 0) {
      errorMessage += '<strong>Errors (must fix):</strong><ul>';
      validationErrors.forEach(error => {
        errorMessage += `<li>${error}</li>`;
      });
      errorMessage += '</ul>';
    }
    
    if (validationWarnings.length > 0) {
      if (errorMessage) errorMessage += '<br>';
      errorMessage += '<strong>Warnings (should fix):</strong><ul>';
      validationWarnings.forEach(warning => {
        errorMessage += `<li>${warning}</li>`;
      });
      errorMessage += '</ul>';
    }
    
    if (errorMessage) {
      showAlert(errorMessage, validationErrors.length > 0 ? 'danger' : 'warning');
    }
  }
  
  return isValid;
}

function clearFieldErrors() {
  // Remove invalid classes from all form fields
  document.querySelectorAll('.is-invalid').forEach(field => {
    field.classList.remove('is-invalid');
  });
  
  // Remove border highlighting from marking items
  document.querySelectorAll('.marking-item').forEach(item => {
    item.style.border = '';
    item.style.borderRadius = '';
  });
}

// Expose functions to global scope for HTML event handlers
window.validateNumber = validateNumber;
window.validateJsonField = validateJsonField;
window.validateForm = validateForm;
window.clearFieldErrors = clearFieldErrors;
