/**
 * Question Management Module
 * Handles adding, removing, and updating questions
 */

let questionCount = 0;

// Question management functions
function addQuestion() {
  const qId = questionCount++;
  const qDiv = document.createElement('div');
  qDiv.className = 'card mb-3';
  qDiv.draggable = true;
  qDiv.id = `question-${qId}`;
  
  // Get next question number - only count direct children cards
  const nextNum = document.querySelectorAll('#questions-list > .card').length + 1;
  
  qDiv.innerHTML = `
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div class="d-flex align-items-center">
          <div class="drag-handle me-2">⋮⋮</div>
          <h5 class="card-title mb-0">Question <span class="q-num">${nextNum}</span></h5>
        </div>
        <button type="button" class="btn-close" aria-label="Remove" onclick="removeQuestionWithConfirm(this)"></button>
      </div>
      <div class="mb-3">
        <label class="form-label">Question Name</label>
        <input type="text" class="form-control" id="question-${qId}-name" name="questions[${qId}][name]" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Marking Items</label>
        <div class="marking-items-list" id="question-${qId}-marking-items"></div>
        <button type="button" class="btn btn-secondary mt-2" onclick="addMarkingItem(this)">Add Marking Item</button>
      </div>
    </div>
  `;
  
  // Add drag and drop event listeners
  qDiv.addEventListener('dragstart', handleDragStart);
  qDiv.addEventListener('dragend', handleDragEnd);
  qDiv.addEventListener('dragover', handleDragOver);
  qDiv.addEventListener('drop', handleDrop);
  
  document.getElementById('questions-list').appendChild(qDiv);
  updateQuestionNumbers();
}

function removeQuestionWithConfirm(btn) {
  if (confirm('Are you sure you want to delete this question and all its marking items?')) {
    removeQuestion(btn);
  }
}

function removeQuestion(btn) {
  btn.closest('.card').remove();
  updateQuestionNumbers();
}

function updateQuestionNumbers() {
  // Only select direct children of questions-list to avoid marking items
  const questions = document.querySelectorAll('#questions-list > .card');
  questions.forEach((question, questionIndex) => {
    // Update display number
    question.querySelector('.q-num').textContent = questionIndex + 1;
    
    // Update question fields
    question.querySelectorAll('input[name^="questions["], select[name^="questions["], textarea[name^="questions["]').forEach(field => {
      // Skip marking item fields - we'll handle those separately
      if (field.name.includes('marking_items')) return;
      
      // Get the field name (e.g., 'name')
      const fieldName = field.name.split(']')[1]?.replace(/[\[\]]/g, '') || '';
      if (fieldName) {
        field.name = `questions[${questionIndex}][${fieldName}]`;
        // Update ID to match new question index
        const baseId = question.id;
        field.id = `${baseId}-${fieldName}`;
      }
    });
    
    // Update marking items
    const markingItems = question.querySelectorAll('.marking-items-list .marking-item');
    markingItems.forEach((item, itemIndex) => {
      // Update marking item ID
      const baseQuestionId = question.id;
      const newMarkingItemId = `${baseQuestionId}-marking-item-${itemIndex}`;
      item.id = newMarkingItemId;
      
      item.querySelectorAll('input, select, textarea').forEach(field => {
        // Get the field name (e.g., 'type', 'target_file', etc.)
        const fieldName = field.name.split(']').pop()?.replace(/[\[\]]/g, '') || '';
        if (fieldName) {
          field.name = `questions[${questionIndex}][marking_items][${itemIndex}][${fieldName}]`;
          // Update field ID to match new structure
          if (fieldName === 'type') {
            field.id = `${newMarkingItemId}-type`;
          } else {
            // Convert field name to kebab-case for ID
            const kebabFieldName = fieldName.replace(/_/g, '-');
            field.id = `${newMarkingItemId}-${kebabFieldName}`;
          }
        }
      });
      
      // Update the type-fields container ID
      const typeFieldsDiv = item.querySelector('.type-fields');
      if (typeFieldsDiv) {
        typeFieldsDiv.id = `${newMarkingItemId}-fields`;
      }
    });
  });
}

// Expose functions to global scope for HTML onclick handlers
window.addQuestion = addQuestion;
window.removeQuestionWithConfirm = removeQuestionWithConfirm;
window.removeQuestion = removeQuestion;
window.updateQuestionNumbers = updateQuestionNumbers;
