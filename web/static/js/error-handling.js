/**
 * Error Handling and User Feedback Module
 * Handles error highlighting, user-friendly messages, and alerts
 */

// Alert management functions
function showAlert(message, type = 'danger') {
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
  
  // Scroll to top to show the alert
  window.scrollTo({ top: 0, behavior: 'smooth' });
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
  
  // Extract path information from error messages
  // Handle both formats: "at questions[0].marking_items[1].field" and "at questions.1.marking_items.0.target_file"
  const pathMatch = errorMessage.match(/at\s+([\w\[\]\.]+)$/) || errorMessage.match(/at\s+path:\s+([\w\[\]\.]+)$/);
  
  if (pathMatch) {
    let path = pathMatch[1];
    
    // Convert dot notation to bracket notation for easier parsing
    // questions.1.marking_items.0.target_file -> questions[1].marking_items[0].target_file
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
  
  // Fallback highlighting for global fields and legacy errors
  highlightGlobalFields(errorLower);
  highlightLegacyErrors(errorMessage, pathMatch);
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

function highlightLegacyErrors(errorMessage, pathMatch) {
  if (!pathMatch) {
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
