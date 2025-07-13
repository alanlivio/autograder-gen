/**
 * Marking Item Management Module
 * Handles adding, removing, and configuring marking items
 */

function addMarkingItem(btn) {
  const questionCard = btn.closest('.card');
  const questionId = questionCard.id;
  const milist = btn.parentElement.querySelector('.marking-items-list');
  const miCount = milist.children.length;
  const markingItemId = `${questionId}-marking-item-${miCount}`;
  
  // Get the current question index
  const questionIdx = Array.from(document.querySelectorAll('#questions-list > .card')).indexOf(questionCard);
  
  const miDiv = document.createElement('div');
  miDiv.className = 'marking-item card card-body mb-2';
  miDiv.id = markingItemId;
  miDiv.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-2">
      <label class="form-label mb-0">Type</label>
      <button type="button" class="btn-close" aria-label="Remove" onclick="removeMarkingItemWithConfirm(this)"></button>
    </div>
    <div class="mb-2">
      <select class="form-select" id="${markingItemId}-type" name="questions[${questionIdx}][marking_items][${miCount}][type]" onchange="showTypeFields(this)">
        <option value="">Select type...</option>
        <option value="file_exists" selected>File Exists</option>
        <option value="output_comparison">Output Comparison</option>
        <option value="signature_check">Signature Check</option>
        <option value="function_test">Function Test</option>
      </select>
    </div>
    <div class="type-fields" id="${markingItemId}-fields"></div>
  `;
  milist.appendChild(miDiv);
  
  // Show type fields for the default selected option
  showTypeFields(miDiv.querySelector('select'));
  
  // Update question numbers after everything is set up
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

function showTypeFields(select) {
  const type = select.value;
  const markingItem = select.closest('.marking-item');
  const markingItemId = markingItem.id;
  const questionCard = markingItem.closest('.card');
  const fieldsDiv = markingItem.querySelector('.type-fields');
  
  // Calculate current indices dynamically
  const questionIdx = Array.from(document.querySelectorAll('#questions-list > .card')).indexOf(questionCard);
  const markingItemIdx = Array.from(markingItem.parentElement.children).indexOf(markingItem);
  
  // Common fields for all types
  let html = `
    <div class="row mb-3">
      <div class="col-md-6">
        <label class="form-label">Target File <span class="text-danger">*</span></label>
        <input type="text" class="form-control" 
               id="${markingItemId}-target-file"
               name="questions[${questionIdx}][marking_items][${markingItemIdx}][target_file]" 
               placeholder="e.g., solution.py" required>
        <div class="form-text">File that will be tested</div>
      </div>
      <div class="col-md-6">
        <label class="form-label">Points <span class="text-danger">*</span></label>
        <input type="number" class="form-control" 
               id="${markingItemId}-total-mark"
               name="questions[${questionIdx}][marking_items][${markingItemIdx}][total_mark]" 
               placeholder="0" min="0" required>
        <div class="form-text">Points awarded for this test</div>
      </div>
    </div>
    <div class="row mb-3">
      <div class="col-md-6">
        <label class="form-label">Time Limit (seconds)</label>
        <input type="number" class="form-control" 
               id="${markingItemId}-time-limit"
               name="questions[${questionIdx}][marking_items][${markingItemIdx}][time_limit]" 
               placeholder="30" min="1" value="30">
        <div class="form-text">Maximum execution time</div>
      </div>
      <div class="col-md-6">
        <label class="form-label">Visibility</label>
        <select class="form-select" 
                id="${markingItemId}-visibility"
                name="questions[${questionIdx}][marking_items][${markingItemIdx}][visibility]">
          <option value="visible">Visible - Students see results immediately</option>
          <option value="hidden">Hidden - Results not shown to students</option>
          <option value="after_due_date">After Due Date - Shown after deadline</option>
          <option value="after_published">After Published - Shown when grades published</option>
        </select>
      </div>
    </div>
  `;
  
  // Type-specific fields
  if (type === 'file_exists') {
    html += getFileExistsFields();
  } else if (type === 'output_comparison') {
    html += getOutputComparisonFields(markingItemId, questionIdx, markingItemIdx);
  } else if (type === 'signature_check') {
    html += getSignatureCheckFields(markingItemId, questionIdx, markingItemIdx);
  } else if (type === 'function_test') {
    html += getFunctionTestFields(markingItemId, questionIdx, markingItemIdx);
  }
  
  fieldsDiv.innerHTML = html;
}

function getFileExistsFields() {
  return `
    <div class="alert alert-info">
      <strong>File Exists Test:</strong> Checks if the target file exists in the submission.
      No additional configuration needed.
    </div>
  `;
}

function getOutputComparisonFields(markingItemId, questionIdx, markingItemIdx) {
  return `
    <div class="alert alert-info mb-3">
      <strong>Output Comparison Test:</strong> Runs the target file and compares its output.
    </div>
    <div class="mb-3">
      <label class="form-label">Expected Input (optional)</label>
      <textarea class="form-control" 
                id="${markingItemId}-expected-input"
                name="questions[${questionIdx}][marking_items][${markingItemIdx}][expected_input]" 
                placeholder="5&#10;10" rows="3"></textarea>
      <div class="form-text">Input to provide to the program (one line per input)</div>
    </div>
    <div class="mb-3">
      <label class="form-label">Expected Output <span class="text-danger">*</span></label>
      <textarea class="form-control" 
                id="${markingItemId}-expected-output"
                name="questions[${questionIdx}][marking_items][${markingItemIdx}][expected_output]" 
                placeholder="15" required rows="3"></textarea>
      <div class="form-text">Exact output the program should produce</div>
    </div>
    <div class="mb-3">
      <label class="form-label">Reference File (optional)</label>
      <input type="text" class="form-control" 
             id="${markingItemId}-reference-file"
             name="questions[${questionIdx}][marking_items][${markingItemIdx}][reference_file]" 
             placeholder="reference_output.txt">
      <div class="form-text">File containing expected output (alternative to Expected Output)</div>
    </div>
  `;
}

function getSignatureCheckFields(markingItemId, questionIdx, markingItemIdx) {
  return `
    <div class="alert alert-info mb-3">
      <strong>Signature Check Test:</strong> Verifies that a function exists with the correct signature.
    </div>
    <div class="mb-3">
      <label class="form-label">Function Name <span class="text-danger">*</span></label>
      <input type="text" class="form-control" 
             id="${markingItemId}-function-name"
             name="questions[${questionIdx}][marking_items][${markingItemIdx}][function_name]" 
             placeholder="add_numbers" required>
      <div class="form-text">Name of the function to check</div>
    </div>
  `;
}

function getFunctionTestFields(markingItemId, questionIdx, markingItemIdx) {
  return `
    <div class="alert alert-info mb-3">
      <strong>Function Test:</strong> Calls a function with test cases and checks the results.
    </div>
    <div class="mb-3">
      <label class="form-label">Function Name <span class="text-danger">*</span></label>
      <input type="text" class="form-control" 
             id="${markingItemId}-function-name"
             name="questions[${questionIdx}][marking_items][${markingItemIdx}][function_name]" 
             placeholder="add_numbers" required>
      <div class="form-text">Name of the function to test</div>
    </div>
    <div class="mb-3">
      <label class="form-label">Test Cases (JSON) <span class="text-danger">*</span></label>
      <textarea class="form-control" 
                id="${markingItemId}-test-cases"
                name="questions[${questionIdx}][marking_items][${markingItemIdx}][test_cases]" 
                placeholder='[{"args": [2, 3], "expected": "5"}, {"args": [-5, 10], "expected": "5"}]'
                required rows="6"
                oninput="validateJsonField(this)"></textarea>
      <div class="invalid-feedback">Please enter valid JSON array</div>
      <div class="form-text">
        <strong>Format:</strong> Array of test cases<br>
        <strong>Example:</strong> <code>[{"args": [1, 2], "expected": "3"}, {"args": [5, 10], "kwargs": {"multiply": true}, "expected": "50"}]</code>
      </div>
    </div>
  `;
}

// Expose functions to global scope for HTML onclick handlers
window.addMarkingItem = addMarkingItem;
window.removeMarkingItemWithConfirm = removeMarkingItemWithConfirm;
window.removeMarkingItem = removeMarkingItem;
window.showTypeFields = showTypeFields;
