let questionCount = 0;

// Utility function to create properly namespaced field names
function createFieldName(questionIdx, markingItemIdx, field) {
  if (markingItemIdx !== undefined) {
    return `questions[${questionIdx}][marking_items][${markingItemIdx}][${field}]`;
  }
  return `questions[${questionIdx}][${field}]`;
}

function addQuestion() {
  const qId = questionCount++;
  const qDiv = document.createElement('div');
  qDiv.className = 'card mb-3';
  qDiv.draggable = true;
  
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
        <input type="text" class="form-control" name="questions[${qId}][name]" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Points</label>
        <input type="number" class="form-control" name="questions[${qId}][points]" min="0" required 
               oninput="validatePoints(this)">
        <div class="invalid-feedback">Points must be a positive number.</div>
      </div>
      <div class="mb-3">
        <label class="form-label">Marking Items</label>
        <div class="marking-items-list"></div>
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
      
      // Get the field name (e.g., 'name', 'points')
      const fieldName = field.name.split(']')[1]?.replace(/[\[\]]/g, '') || '';
      if (fieldName) {
        field.name = `questions[${questionIndex}][${fieldName}]`;
      }
    });
    
    // Update marking items
    const markingItems = question.querySelectorAll('.marking-items-list .marking-item');
    markingItems.forEach((item, itemIndex) => {
      item.querySelectorAll('input, select, textarea').forEach(field => {
        // Get the field name (e.g., 'type', 'file_name', etc.)
        const fieldName = field.name.split(']').pop()?.replace(/[\[\]]/g, '') || '';
        if (fieldName) {
          field.name = `questions[${questionIndex}][marking_items][${itemIndex}][${fieldName}]`;
        }
      });
    });
  });
}

function addMarkingItem(btn) {
  const questionCard = btn.closest('.card');
  const questionIdx = Array.from(document.querySelectorAll('#questions-list .card')).indexOf(questionCard);
  const milist = btn.parentElement.querySelector('.marking-items-list');
  const miCount = milist.children.length;
  const miDiv = document.createElement('div');
  miDiv.className = 'marking-item card card-body mb-2';
  miDiv.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-2">
      <label class="form-label mb-0">Type</label>
      <button type="button" class="btn-close" aria-label="Remove" onclick="removeMarkingItemWithConfirm(this)"></button>
    </div>
    <div class="mb-2">
      <select class="form-select" name="${createFieldName(questionIdx, miCount, 'type')}" onchange="showTypeFields(this)">
        <option value="file_exists">File Exists</option>
        <option value="output_comparison">Output Comparison</option>
        <option value="signature_check">Signature Check</option>
        <option value="function_test">Function Test</option>
      </select>
    </div>
    <div class="type-fields"></div>
  `;
  milist.appendChild(miDiv);
  showTypeFields(miDiv.querySelector('select'));
  updateQuestionNumbers();
}

function removeMarkingItemWithConfirm(btn) {
  if (confirm('Are you sure you want to delete this marking item?')) {
    removeMarkingItem(btn);
  }
}

function removeMarkingItem(btn) {
  btn.closest('.marking-item').remove();
  updateQuestionNumbers();
}

function validatePoints(input) {
  const value = parseInt(input.value);
  if (isNaN(value)) {
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

function showTypeFields(select) {
  const type = select.value;
  const questionCard = select.closest('.card-body');
  const markingItem = select.closest('.marking-item');
  const questionIdx = Array.from(document.querySelectorAll('#questions-list .card')).indexOf(questionCard.closest('.card'));
  const markingItemIdx = Array.from(markingItem.parentElement.children).indexOf(markingItem);
  const fieldsDiv = markingItem.querySelector('.type-fields');
  
  let html = '';
  if (type === 'file_exists') {
    html = `
      <input type="text" class="form-control mb-2" 
             name="${createFieldName(questionIdx, markingItemIdx, 'file_name')}" 
             placeholder="File name" required>
    `;
  } else if (type === 'output_comparison') {
    html = `
      <input type="text" class="form-control mb-2" 
             name="${createFieldName(questionIdx, markingItemIdx, 'expected_output')}" 
             placeholder="Expected output" required>
    `;
  } else if (type === 'signature_check') {
    html = `
      <input type="text" class="form-control mb-2" 
             name="${createFieldName(questionIdx, markingItemIdx, 'function_name')}" 
             placeholder="Function name" required>
    `;
  } else if (type === 'function_test') {
    html = `
      <input type="text" class="form-control mb-2" 
             name="${createFieldName(questionIdx, markingItemIdx, 'function_name')}" 
             placeholder="Function name" required>
      <textarea class="form-control mb-2" 
                name="${createFieldName(questionIdx, markingItemIdx, 'test_cases')}" 
                placeholder="Test cases (JSON)" required
                oninput="validateJsonField(this)"></textarea>
      <div class="invalid-feedback">Please enter valid JSON</div>
    `;
  }
  fieldsDiv.innerHTML = html;
}

function submitForGeneration() {
  if (!validateForm()) {
    return;
  }
  const form = document.getElementById('autograder-form');
  form.action = '/generate';
  form.submit();
}

function validateForm() {
  let isValid = true;
  
  // Validate points
  document.querySelectorAll('input[type="number"]').forEach(input => {
    const value = parseInt(input.value);
    if (isNaN(value) || value < 0) {
      input.classList.add('is-invalid');
      isValid = false;
    }
  });
  
  // Validate JSON fields
  document.querySelectorAll('textarea[name$="[test_cases]"]').forEach(textarea => {
    try {
      if (textarea.value) {
        JSON.parse(textarea.value);
      }
    } catch (e) {
      textarea.classList.add('is-invalid');
      isValid = false;
    }
  });
  
  if (!isValid) {
    alert('Please fix the validation errors before submitting.');
  }
  
  return isValid;
}

// Drag and drop event handlers
let draggedElement = null;

function handleDragStart(e) {
  draggedElement = this;
  this.classList.add('dragging');
  
  // Set the drag effect and data
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/html', this.innerHTML);
}

function handleDragEnd(e) {
  this.classList.remove('dragging');
  draggedElement = null;
  updateQuestionNumbers();
}

function handleDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  
  if (this === draggedElement) return false;
  
  const rect = this.getBoundingClientRect();
  const midPoint = rect.top + (rect.height / 2);
  
  if (e.clientY < midPoint) {
    if (this.previousElementSibling !== draggedElement) {
      this.parentNode.insertBefore(draggedElement, this);
      updateQuestionNumbers();
    }
  } else {
    if (this.nextElementSibling !== draggedElement) {
      this.parentNode.insertBefore(draggedElement, this.nextElementSibling);
      updateQuestionNumbers();
    }
  }
  
  return false;
}

function handleDrop(e) {
  if (e.stopPropagation) {
    e.stopPropagation();
  }
  
  return false;
}

// Add CSS for drag and drop visual feedback
document.addEventListener('DOMContentLoaded', () => {
  addQuestion(); // Start with one question
}); 