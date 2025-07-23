/**
 * Error Handling and User Feedback Module
 * Handles error highlighting, user-friendly messages, and alerts
 */

// Alert management functions
function showAlert(message, type = 'danger', autoScroll = true) {
  const alertContainer = document.getElementById('alert-container');
  const alertDiv = document.createElement('div');
  alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
  alertDiv.setAttribute('role', 'alert');
  alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  
  // Clear existing alerts
  alertContainer.innerHTML = '';
  alertContainer.appendChild(alertDiv);
  
  // Only scroll to top if requested (default true for backwards compatibility)
  if (autoScroll) {
    // Smooth scroll to alert, not harsh jump to top
    alertContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function clearAlerts() {
  const alertContainer = document.getElementById('alert-container');
  alertContainer.innerHTML = '';
}

// Helper function to convert technical error messages to user-friendly ones
function makeErrorUserFriendly(errorMessage) {
  // Extract path information for better context
  const pathMatch = errorMessage.match(/at\s+([\w\[\]\.]+)$/) || errorMessage.match(/at\s+path:\s+([\w\[\]\.]+)$/);
  
  if (pathMatch) {
    let path = pathMatch[1];
    
    // Convert dot notation to more readable format
    path = path.replace(/questions\.(\d+)/, (match, num) => `Question ${parseInt(num) + 1}`);
    path = path.replace(/marking_items\.(\d+)/, (match, num) => `, Marking Item ${parseInt(num) + 1}`);
    path = path.replace(/\.target_file$/, ': Target File');
    path = path.replace(/\.total_mark$/, ': Points');
    path = path.replace(/\.function_name$/, ': Function Name');
    path = path.replace(/\.expected_output$/, ': Expected Output');
    path = path.replace(/\.expected_input$/, ': Expected Input');
    path = path.replace(/\.test_cases$/, ': Test Cases');
    path = path.replace(/\.type$/, ': Type');
    path = path.replace(/\.time_limit$/, ': Time Limit');
    path = path.replace(/\.visibility$/, ': Visibility');
    path = path.replace(/\.name$/, ': Name');
    
    // Common error message improvements
    if (errorMessage.includes("'' should be non-empty")) {
      return `${path} field is required and cannot be empty.`;
    }
    if (errorMessage.includes("should be non-empty")) {
      return `${path} field is required and cannot be empty.`;
    }
    if (errorMessage.includes("is not of type")) {
      return `${path} field has an invalid value type.`;
    }
    if (errorMessage.includes("is not valid under any of the given schemas")) {
      return `${path} field contains invalid data.`;
    }
    
    // Return with improved path context
    const baseMessage = errorMessage.replace(/\s+at\s+[\w\[\]\.]+$/, '').replace(/\s+at\s+path:\s+[\w\[\]\.]+$/, '');
    return `${path}: ${baseMessage}`;
  }
  
  // Fallback for messages without paths
  if (errorMessage.includes("'' should be non-empty")) {
    return "A required field is empty. Please fill in all required fields.";
  }
  
  return errorMessage;
}

// Helper function to highlight fields with errors
function highlightFieldError(errorMessage) {
  const errorLower = errorMessage.toLowerCase();
  
  // First try to handle structured path errors (from JSON schema validation)
  const pathMatch = errorMessage.match(/at\s+([\w\[\]\.]+)$/) || errorMessage.match(/at\s+path:\s+([\w\[\]\.]+)$/);
  
  if (pathMatch) {
    handleStructuredPathError(pathMatch[1], errorMessage);
  } else {
    // Handle custom validation errors with text patterns
    handleTextBasedError(errorMessage, errorLower);
  }
  
  // Always try fallback highlighting for global fields
  highlightGlobalFields(errorLower);
}

function handleStructuredPathError(path, errorMessage) {
  // Convert dot notation to bracket notation for easier parsing
  path = path.replace(/\.(\d+)\./g, '[$1].').replace(/\.(\d+)$/, '[$1]');
  
  // Parse structured path like "questions[0].marking_items[1].target_file"
  const questionMatch = path.match(/questions\[(\d+)\]/);
  const markingItemMatch = path.match(/marking_items\[(\d+)\]/);
  const fieldMatch = path.match(/\.(\w+)$/) || path.match(/^(\w+)$/);
  
  if (questionMatch) {
    const questionIndex = parseInt(questionMatch[1]);
    const questionCards = document.querySelectorAll('#questions-list > .card');
    
    if (questionCards[questionIndex]) {
      const targetCard = questionCards[questionIndex];
      const questionId = targetCard.id;
      
      if (markingItemMatch && fieldMatch) {
        highlightMarkingItemField(targetCard, markingItemMatch, fieldMatch, questionIndex);
      } else if (fieldMatch) {
        highlightQuestionField(questionId, fieldMatch);
      } else {
        // General question error
        targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }
}

function handleTextBasedError(errorMessage, errorLower) {
  // Handle custom validation errors like "Question 'Name', Item X: Target file..."
  const customErrorMatch = errorMessage.match(/Question\s+'([^']+)',\s*Item\s+(\d+):\s*(.+)/i);
  
  if (customErrorMatch) {
    const questionName = customErrorMatch[1];
    const itemNumber = parseInt(customErrorMatch[2]) - 1; // Convert to 0-based
    const errorDescription = customErrorMatch[3];
    
    // Find the question by name
    const questionCards = document.querySelectorAll('#questions-list > .card');
    let targetQuestionCard = null;
    let questionIndex = -1;
    
    for (let i = 0; i < questionCards.length; i++) {
      const nameField = questionCards[i].querySelector('input[id$="-name"]');
      if (nameField && nameField.value.trim() === questionName) {
        targetQuestionCard = questionCards[i];
        questionIndex = i;
        break;
      }
    }
    
    if (targetQuestionCard) {
      // Determine which field to highlight based on error description
      let fieldToHighlight = null;
      
      if (errorDescription.toLowerCase().includes('target file')) {
        fieldToHighlight = 'target-file';
      } else if (errorDescription.toLowerCase().includes('function name')) {
        fieldToHighlight = 'function-name';
      } else if (errorDescription.toLowerCase().includes('expected output')) {
        fieldToHighlight = 'expected-output';
      } else if (errorDescription.toLowerCase().includes('test cases')) {
        fieldToHighlight = 'test-cases';
      }
      
      // Highlight the specific marking item field
      const markingItems = targetQuestionCard.querySelectorAll('.marking-item');
      if (markingItems[itemNumber] && fieldToHighlight) {
        const markingItem = markingItems[itemNumber];
        const markingItemId = markingItem.id;
        const field = document.getElementById(`${markingItemId}-${fieldToHighlight}`);
        
        if (field) {
          field.classList.add('is-invalid');
          field.scrollIntoView({ behavior: 'smooth', block: 'center' });
          console.log(`Highlighted field: ${markingItemId}-${fieldToHighlight}`);
        } else {
          // Highlight the entire marking item if specific field not found
          markingItem.style.border = '2px solid #dc3545';
          markingItem.style.borderRadius = '0.375rem';
          markingItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
          console.log(`Highlighted marking item: ${markingItemId}`);
        }
      }
    }
  } else {
    // Handle other legacy error patterns
    handleLegacyErrors(errorMessage);
  }
}

function highlightMarkingItemField(targetCard, markingItemMatch, fieldMatch, questionIndex) {
  const markingItemIndex = parseInt(markingItemMatch[1]);
  const fieldName = fieldMatch[1];
  const markingItems = targetCard.querySelectorAll('.marking-item');
  
  if (markingItems[markingItemIndex]) {
    const markingItem = markingItems[markingItemIndex];
    const markingItemId = markingItem.id;
    const kebabFieldName = fieldName.replace(/_/g, '-');
    
    // Try different field ID patterns
    let field = document.getElementById(`${markingItemId}-${kebabFieldName}`);
    
    if (field) {
      field.classList.add('is-invalid');
      field.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      // Add a more descriptive error message
      const questionNum = questionIndex + 1;
      const markingItemNum = markingItemIndex + 1;
      console.log(`Highlighting field: Question ${questionNum}, Marking Item ${markingItemNum}, Field: ${fieldName}`);
    } else {
      // Highlight the entire marking item if specific field not found
      markingItem.style.border = '2px solid #dc3545';
      markingItem.style.borderRadius = '0.375rem';
      markingItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}

function highlightQuestionField(questionId, fieldMatch) {
  const fieldName = fieldMatch[1];
  const field = document.getElementById(`${questionId}-${fieldName}`);
  if (field) {
    field.classList.add('is-invalid');
    field.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function highlightGlobalFields(errorLower) {
  const globalFields = {
    'version': 'version',
    'language': 'language', 
    'global_time_limit': 'global_time_limit',
    'time limit': 'global_time_limit',
    'setup_commands': 'setup_commands',
    'files_necessary': 'files_necessary'
  };
  
  Object.entries(globalFields).forEach(([errorKey, fieldId]) => {
    if (errorLower.includes(errorKey)) {
      const field = document.getElementById(fieldId);
      if (field) field.classList.add('is-invalid');
    }
  });
}

function handleLegacyErrors(errorMessage) {
  // Try to extract question and marking item information from text
  const questionTextMatch = errorMessage.match(/question\s+(\d+)|question\s+"([^"]+)"/i);
  if (questionTextMatch) {
    const questionCards = document.querySelectorAll('#questions-list > .card');
    let targetCard = null;
    
    if (questionTextMatch[1]) {
      // Match by question number (1-based in messages, 0-based in DOM)
      const questionNum = parseInt(questionTextMatch[1]) - 1;
      if (questionCards[questionNum]) {
        targetCard = questionCards[questionNum];
      }
    } else if (questionTextMatch[2]) {
      // Match by question name
      const questionName = questionTextMatch[2];
      questionCards.forEach(card => {
        const nameField = card.querySelector('input[id$="-name"]');
        if (nameField && nameField.value === questionName) {
          targetCard = card;
        }
      });
    }
    
    if (targetCard) {
      highlightLegacyQuestionErrors(targetCard, errorMessage.toLowerCase());
      targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}

function highlightLegacyQuestionErrors(targetCard, errorLower) {
  // Highlight based on error content
  if (errorLower.includes('name') && !errorLower.includes('function')) {
    const nameField = targetCard.querySelector('input[id$="-name"]');
    if (nameField) nameField.classList.add('is-invalid');
  }
  
  if (errorLower.includes('marking_item') || errorLower.includes('target_file') || errorLower.includes('total_mark')) {
    const markingItems = targetCard.querySelectorAll('.marking-item');
    markingItems.forEach(item => {
      item.style.border = '2px solid #dc3545';
      item.style.borderRadius = '0.375rem';
    });
  }
}

// Expose functions to global scope for HTML event handlers
window.showAlert = showAlert;
window.clearAlerts = clearAlerts;
window.makeErrorUserFriendly = makeErrorUserFriendly;
window.highlightFieldError = highlightFieldError;