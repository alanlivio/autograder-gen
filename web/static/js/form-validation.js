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
  clearFieldErrors();
  
  // Validate global required fields
  const requiredGlobalFields = ['language'];
  requiredGlobalFields.forEach(fieldName => {
    const field = document.getElementById(fieldName);
    if (field && !field.value.trim()) {
      field.classList.add('is-invalid');
      isValid = false;
    }
  });
  
  // Validate questions
  const questionCards = document.querySelectorAll('#questions-list > .card');
  if (questionCards.length === 0) {
    showAlert('At least one question is required.', 'warning');
    isValid = false;
  }
  
  questionCards.forEach((questionCard, qIdx) => {
    // Validate question name
    const nameField = questionCard.querySelector('input[id$="-name"]');
    if (nameField && !nameField.value.trim()) {
      nameField.classList.add('is-invalid');
      isValid = false;
    }
    
    // Validate marking items
    const markingItems = questionCard.querySelectorAll('.marking-item');
    if (markingItems.length === 0) {
      showAlert(`Question ${qIdx + 1} must have at least one marking item.`, 'warning');
      isValid = false;
    }
    
    markingItems.forEach((markingItem, miIdx) => {
      // Validate required marking item fields
      const typeField = markingItem.querySelector('select[id$="-type"]');
      const targetFileField = markingItem.querySelector('input[id$="-target-file"]');
      const totalMarkField = markingItem.querySelector('input[id$="-total-mark"]');
      
      if (typeField && !typeField.value) {
        typeField.classList.add('is-invalid');
        isValid = false;
      }
      
      if (targetFileField && !targetFileField.value.trim()) {
        targetFileField.classList.add('is-invalid');
        isValid = false;
      }
      
      if (totalMarkField) {
        const value = parseInt(totalMarkField.value);
        if (isNaN(value) || value < 0) {
          totalMarkField.classList.add('is-invalid');
          isValid = false;
        }
      }
      
      // Type-specific validation
      const type = typeField ? typeField.value : '';
      if (type === 'function_test' || type === 'signature_check') {
        const functionNameField = markingItem.querySelector('input[id$="-function-name"]');
        if (functionNameField && !functionNameField.value.trim()) {
          functionNameField.classList.add('is-invalid');
          isValid = false;
        }
      }
      
      if (type === 'function_test') {
        const testCasesField = markingItem.querySelector('textarea[id$="-test-cases"]');
        if (testCasesField && !testCasesField.value.trim()) {
          testCasesField.classList.add('is-invalid');
          isValid = false;
        }
      }
      
      if (type === 'output_comparison') {
        const expectedOutputField = markingItem.querySelector('textarea[id$="-expected-output"]');
        if (expectedOutputField && !expectedOutputField.value.trim()) {
          expectedOutputField.classList.add('is-invalid');
          isValid = false;
        }
      }
    });
  });
  
  // Validate number fields
  document.querySelectorAll('input[type="number"]').forEach(input => {
    const value = parseInt(input.value);
    if (input.hasAttribute('required') && (isNaN(value) || value < 0)) {
      input.classList.add('is-invalid');
      isValid = false;
    }
  });
  
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
  
  if (!isValid) {
    showAlert('Please fix the validation errors before submitting.', 'warning');
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
