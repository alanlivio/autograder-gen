/**
 * API Communication Module
 * Handles communication with the backend API
 */

function submitForGeneration() {
  if (!validateForm()) {
    return;
  }
  
  clearAlerts();
  clearFieldErrors();
  
  const config = formToConfigObject();
  
  // Show loading state
  const generateBtn = document.querySelector('button[onclick="submitForGeneration()"]');
  const originalText = generateBtn.textContent;
  generateBtn.disabled = true;
  generateBtn.textContent = 'Generating...';
  
  fetch('/api/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config)
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(data => {
        throw new Error(data.error || 'Generation failed');
      });
    }
    return response.blob();
  })
  .then(blob => {
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = 'autograder.zip';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    showAlert('Autograder generated successfully and download started!', 'success');
  })
  .catch(error => {
    console.error('Generation error:', error);
    showAlert(`Generation failed: ${error.message}`, 'danger');
  })
  .finally(() => {
    // Restore button state
    generateBtn.disabled = false;
    generateBtn.textContent = originalText;
  });
}

function validateConfig() {
  clearAlerts();
  clearFieldErrors();
  
  const config = formToConfigObject();
  
  // Show loading state
  const validateBtn = document.querySelector('button[onclick="validateConfig()"]');
  const originalText = validateBtn.textContent;
  validateBtn.disabled = true;
  validateBtn.textContent = 'Validating...';
  
  fetch('/api/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config)
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      showAlert(`Validation failed: ${data.error}`, 'danger');
      return;
    }
    
    if (data.valid) {
      showAlert('Configuration is valid! You can now generate the autograder.', 'success');
    } else {
      let errorMessage = 'Configuration validation failed:<ul>';
      data.errors.forEach(error => {
        // Convert technical error messages to user-friendly ones
        const friendlyError = makeErrorUserFriendly(error);
        errorMessage += `<li>${friendlyError}</li>`;
        // Try to highlight specific fields with errors
        highlightFieldError(error);
      });
      errorMessage += '</ul>';
      
      if (data.warnings && data.warnings.length > 0) {
        errorMessage += '<br><strong>Warnings:</strong><ul>';
        data.warnings.forEach(warning => {
          errorMessage += `<li>${warning}</li>`;
        });
        errorMessage += '</ul>';
      }
      
      showAlert(errorMessage, 'danger');
    }
  })
  .catch(error => {
    console.error('Validation error:', error);
    showAlert('An error occurred while validating the configuration. Please try again.', 'danger');
  })
  .finally(() => {
    // Restore button state
    validateBtn.disabled = false;
    validateBtn.textContent = originalText;
  });
}

// Expose functions to global scope for HTML onclick handlers
window.submitForGeneration = submitForGeneration;
window.validateConfig = validateConfig;
