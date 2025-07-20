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
    
    if (data.valid) {
      let successMessage = 'Configuration is valid! You can now generate the autograder.';
      
      // Add warnings if they exist
      if (data.warnings && data.warnings.length > 0) {
        successMessage += '<br><br><strong>Warnings (consider addressing):</strong><ul>';
        data.warnings.forEach(warning => {
          successMessage += `<li>${warning}</li>`;
        });
        successMessage += '</ul>';
      }
      
      showAlert(successMessage, 'success');
      // Enable the generate button
      const generateBtn = document.getElementById('generate-btn');
      if (generateBtn) {
        generateBtn.disabled = false;
        generateBtn.classList.remove('btn-secondary');
        generateBtn.classList.add('btn-primary');
      }
    } else {
      let errorMessage = 'Configuration validation failed:<ul>';
      
      // Build error message first
      data.errors.forEach(error => {
        const friendlyError = makeErrorUserFriendly(error);
        errorMessage += `<li>${friendlyError}</li>`;
      });
      errorMessage += '</ul>';
      
      // Then highlight all fields after DOM is ready
      setTimeout(() => {
        console.log(`Highlighting ${data.errors.length} validation errors:`);
        data.errors.forEach((error, index) => {
          console.log(`  ${index + 1}. ${error}`);
          highlightFieldError(error);
        });
      }, 100); // Small delay to ensure DOM is updated
      
      if (data.warnings && data.warnings.length > 0) {
        errorMessage += '<br><strong>Warnings:</strong><ul>';
        data.warnings.forEach(warning => {
          errorMessage += `<li>${warning}</li>`;
        });
        errorMessage += '</ul>';
      }
      
      showAlert(errorMessage, 'danger');
      
      // Disable the generate button on validation failure
      const generateBtn = document.getElementById('generate-btn');
      if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.classList.remove('btn-primary');
        generateBtn.classList.add('btn-secondary');
      }
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

function downloadJsonConfig() {
  if (!validateForm()) {
    showAlert('Please fix form validation errors before downloading the config.', 'warning');
    return;
  }
  
  clearAlerts();
  
  const config = formToConfigObject();
  
  try {
    // Create a blob with the JSON data
    const jsonString = JSON.stringify(config, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = 'autograder_config.json';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    showAlert('Configuration JSON downloaded successfully!', 'success');
  } catch (error) {
    console.error('JSON download error:', error);
    showAlert('Failed to download configuration JSON. Please try again.', 'danger');
  }
}

// Expose functions to global scope for HTML onclick handlers
window.submitForGeneration = submitForGeneration;
window.validateConfig = validateConfig;
window.downloadJsonConfig = downloadJsonConfig;
