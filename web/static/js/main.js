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
});



