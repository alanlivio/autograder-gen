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
        <option value="file_exists" selected>Mark a file exists</option>
        <option value="output_comparison">Mark Main file</option>
        <option value="signature_check">Signature Check</option>
        <option value="function_test">Mark function</option>
      </select>
    </div>
    <div class="type-fields" id="${markingItemId}-fields"></div>
  `;
  milist.appendChild(miDiv);
  
  // Show type fields for the default selected option
  showTypeFields(miDiv.querySelector('select'));
  
  // Add event listener to target file field for validation
  const targetFileField = miDiv.querySelector('input[id$="-target-file"]');
  if (targetFileField) {
    targetFileField.addEventListener('input', validateSingleTargetFile);
  }
  
  // Add event listener to total mark field for points updating
  const totalMarkField = miDiv.querySelector('input[id$="-total-mark"]');
  if (totalMarkField) {
    totalMarkField.addEventListener('input', updateQuestionNumbers);
  }
  
  // Reinitialize drag and drop for the question card to handle new form elements
  if (typeof initializeDragAndDrop === 'function') {
    initializeDragAndDrop(questionCard);
  }
  
  // Update question numbers after everything is set up
  updateQuestionNumbers();
  
  // Disable generate button as form structure has changed
  if (typeof disableGenerateButton === 'function') {
    disableGenerateButton();
  }
}

function removeMarkingItemWithConfirm(btn) {
  if (confirm('Are you sure you want to delete this marking item?')) {
    removeMarkingItem(btn);
  }
}

function removeMarkingItem(btn) {
  btn.closest('.marking-item').remove();
  updateQuestionNumbers();
  
  // Disable generate button as form structure has changed
  if (typeof disableGenerateButton === 'function') {
    disableGenerateButton();
  }
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
    <div class="mb-3">
      <label class="form-label">Name (optional)</label>
      <input type="text" class="form-control" 
             id="${markingItemId}-name"
             name="questions[${questionIdx}][marking_items][${markingItemIdx}][name]" 
             placeholder="e.g., Check file exists, Test basic addition">
      <div class="form-text">Descriptive name for this marking item (will be used in test names if provided)</div>
    </div>
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
               placeholder="e.g., 10" required>
        <div class="form-text">Points awarded (can be negative for penalties)</div>
      </div>
    </div>
    <div class="row mb-3">
      <div class="col-md-6">
        <label class="form-label">Time Limit (seconds)</label>
        <input type="number" class="form-control" 
               id="${markingItemId}-time-limit"
               name="questions[${questionIdx}][marking_items][${markingItemIdx}][time_limit]" 
               placeholder="Global time limit used if not set" min="1">
        <div class="form-text">Maximum execution time</div>
      </div>
      <div class="col-md-6">
        <label class="form-label">Visibility</label>
        <select class="form-select" 
                id="${markingItemId}-visibility"
                name="questions[${questionIdx}][marking_items][${markingItemIdx}][visibility]">
          <option value="hidden">Hidden - Results not shown to students</option>
          <option value="visible">Visible - Students see results immediately</option>
          <option value="after_due_date">After Due Date - Shown after deadline</option>
          <option value="after_published">After Published - Shown when grades published</option>
        </select>
      </div>
    </div>
  `;

   markingItem.classList.remove(
    'file-exists-border',
    'output-comparison-border',
    'signature-check-border',
    'function-test-border'
  );

  // Type-specific fields
  if (type === 'file_exists') {
    html += getFileExistsFields();
    markingItem.classList.add('file-exists-border');
  } else if (type === 'output_comparison') {
    html += getOutputComparisonFields(markingItemId, questionIdx, markingItemIdx);
    markingItem.classList.add('output-comparison-border');
  } else if (type === 'signature_check') {
    html += getSignatureCheckFields(markingItemId, questionIdx, markingItemIdx);
    markingItem.classList.add('signature-check-border');
  } else if (type === 'function_test') {
    html += getFunctionTestFields(markingItemId, questionIdx, markingItemIdx);
    markingItem.classList.add('function-test-border');
  }
  
  fieldsDiv.innerHTML = html;
  
  // Add event listener to target file field for validation
  const targetFileField = markingItem.querySelector('input[id$="-target-file"]');
  if (targetFileField && typeof validateSingleTargetFile === 'function') {
    targetFileField.addEventListener('input', validateSingleTargetFile);
  }
  
  // Add event listener to total mark field for points updating
  const totalMarkField = markingItem.querySelector('input[id$="-total-mark"]');
  if (totalMarkField && typeof updateQuestionNumbers === 'function') {
    totalMarkField.addEventListener('input', updateQuestionNumbers);
  }
  
  // Auto-add first test case for function tests
  if (type === 'function_test') {
    setTimeout(() => addTestCase(markingItemId, questionIdx, markingItemIdx), 0);
  }
}

function getFileExistsFields() {
  return `
    <div class="alert alert-info">
      <strong>Mark a file exists :</strong> Mark if a file exists in the submission  (e.g. README.md).
      No additional configuration needed.
    </div>
  `;
}

function getOutputComparisonFields(markingItemId, questionIdx, markingItemIdx) {
  return `
    <div class="alert alert-info mb-3">
      <strong>Mark main file:</strong> Runs main file comparing its stdout using an input as stdin.
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
      <div class="form-text">Output the program should produce (newline will be added automatically for print() statements)</div>
    </div>
  `;
}

function getSignatureCheckFields(markingItemId, questionIdx, markingItemIdx) {
  return `
    <div class="alert alert-info mb-3">
      <strong>📋 Signature Check Test:</strong> Validates that a function exists, is callable, and has proper signature.
    </div>
    
    <div class="mb-3">
      <label class="form-label">Function Name <span class="text-danger">*</span></label>
      <input type="text" class="form-control" 
             id="${markingItemId}-function-name"
             name="questions[${questionIdx}][marking_items][${markingItemIdx}][function_name]" 
             placeholder="calculate_average" required>
      <div class="form-text">Exact name of the function to check</div>
    </div>
    
    <div class="mb-3">
      <label class="form-label">Expected Parameters (Optional)</label>
      <input type="text" class="form-control" 
             id="${markingItemId}-expected-params"
             name="questions[${questionIdx}][marking_items][${markingItemIdx}][expected_parameters]" 
             placeholder="x, y, z=5">
      <div class="form-text">Parameter names and defaults</div>
    </div>
  `;
}

function getFunctionTestFields(markingItemId, questionIdx, markingItemIdx) {
  return `
    <div class="alert alert-info mb-3">
      <strong>Mark function:</strong> Mark function comparing its return using an input as args.
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
      <div id="${markingItemId}-test-cases-container" class="test-cases-container">
        <!-- Test cases will be dynamically added here -->
      </div>
      <!-- Hidden field to store the JSON data -->
      <textarea class="d-none" 
                id="${markingItemId}-test-cases"
                name="questions[${questionIdx}][marking_items][${markingItemIdx}][test_cases]" 
      required></textarea>
    </div>
  `;
}

// Expose functions to global scope for HTML onclick handlers
window.addMarkingItem = addMarkingItem;
window.removeMarkingItemWithConfirm = removeMarkingItemWithConfirm;
window.removeMarkingItem = removeMarkingItem;
window.showTypeFields = showTypeFields;
window.addTestCase = addTestCase;
window.removeTestCase = removeTestCase;
window.updateTestCasesJson = updateTestCasesJson;

// Test Case Management Functions
function addTestCase(markingItemId, questionIdx, markingItemIdx) {
  const container = document.getElementById(`${markingItemId}-test-cases-container`);
  const testCaseCount = container.children.length;
  const testCaseId = `${markingItemId}-testcase-${testCaseCount}`;
  
  const testCaseDiv = document.createElement('div');
  testCaseDiv.className = 'mb-2 test-case';
  testCaseDiv.id = testCaseId;
  testCaseDiv.innerHTML = `
    <div class="row mb-2">
      <div class="col-md-8">
        <label class="form-label">Arguments (comma-separated)</label>
        <input type="text" class="form-control" 
               id="${testCaseId}-args"
               placeholder="2, 3, 'hello'"
               onchange="updateTestCasesJson('${markingItemId}')">
        <div class="form-text">Enter function arguments. Use quotes for strings, separate with commas.</div>
      </div>
      <div class="col-md-4">
        <label class="form-label">Expected Result <span class="text-danger">*</span></label>
        <input type="text" class="form-control" 
               id="${testCaseId}-expected"
               placeholder="5"
               required
               onchange="updateTestCasesJson('${markingItemId}')">
        <div class="form-text">Expected function return value</div>
      </div>
    </div>
    <div class="mb-2">
      <label class="form-label">Keyword Arguments (optional)</label>
      <input type="text" class="form-control" 
             id="${testCaseId}-kwargs"
             placeholder="multiply=True, precision=2"
             onchange="updateTestCasesJson('${markingItemId}')">
      <div class="form-text">Enter keyword arguments as key=value pairs, separated by commas.</div>
    </div>
  `;
  
  container.appendChild(testCaseDiv);
  updateTestCasesJson(markingItemId);
  
  // If this is the first test case, add it automatically
  if (testCaseCount === 0) {
    // Set some example values
    document.getElementById(`${testCaseId}-args`).value = "";
    document.getElementById(`${testCaseId}-expected`).value = "";
    updateTestCasesJson(markingItemId);
  }
}

function removeTestCase(testCaseId, markingItemId) {
  document.getElementById(testCaseId).remove();
  updateTestCaseNumbers(markingItemId);
  updateTestCasesJson(markingItemId);
}

function updateTestCaseNumbers(markingItemId) {
  const container = document.getElementById(`${markingItemId}-test-cases-container`);
  const testCases = container.querySelectorAll('.test-case');
  testCases.forEach((testCase, index) => {
    const title = testCase.querySelector('h6');
    title.textContent = `Test Case ${index + 1}`;
  });
}

function updateTestCasesJson(markingItemId) {
  const container = document.getElementById(`${markingItemId}-test-cases-container`);
  const jsonField = document.getElementById(`${markingItemId}-test-cases`);
  const testCases = container.querySelectorAll('.test-case');
  
  const testCasesArray = [];
  
  testCases.forEach((testCase) => {
    const argsInput = testCase.querySelector('[id$="-args"]');
    const expectedInput = testCase.querySelector('[id$="-expected"]');
    const kwargsInput = testCase.querySelector('[id$="-kwargs"]');
    
    if (expectedInput && expectedInput.value.trim()) {
      const testCaseObj = {
        expected: expectedInput.value.trim()
      };
      
      // Parse arguments
      if (argsInput && argsInput.value.trim()) {
        try {
          // Try to parse as a complete JSON array
          const argsStr = '[' + argsInput.value.trim() + ']';
          testCaseObj.args = JSON.parse(argsStr);
        } catch (e) {
          try {
            // Try to parse individual arguments and handle complex structures
            const argValues = [];
            const args = argsInput.value.split(',');
            
            for (let arg of args) {
              arg = arg.trim();
              if (!arg) continue;
              
              try {
                // Try to parse as JSON first (for objects, arrays, etc.)
                argValues.push(JSON.parse(arg));
              } catch (jsonError) {
                // If not valid JSON, try to evaluate simple expressions
                if (arg.startsWith("'") && arg.endsWith("'")) {
                  // String literal
                  argValues.push(arg.slice(1, -1));
                } else if (arg.startsWith('"') && arg.endsWith('"')) {
                  // String literal
                  argValues.push(arg.slice(1, -1));
                } else if (!isNaN(arg) && !isNaN(parseFloat(arg))) {
                  // Number
                  argValues.push(parseFloat(arg));
                } else if (arg === 'true') {
                  argValues.push(true);
                } else if (arg === 'false') {
                  argValues.push(false);
                } else if (arg === 'null') {
                  argValues.push(null);
                } else {
                  // Default to string
                  argValues.push(arg);
                }
              }
            }
            testCaseObj.args = argValues;
          } catch (e2) {
            // Final fallback: split by comma and treat as strings
            testCaseObj.args = argsInput.value.split(',').map(arg => arg.trim()).filter(arg => arg);
          }
        }
      }
      
      // Parse keyword arguments
      if (kwargsInput && kwargsInput.value.trim()) {
        const kwargsObj = {};
        const pairs = kwargsInput.value.split(',');
        pairs.forEach(pair => {
          const equalIndex = pair.indexOf('=');
          if (equalIndex > 0) {
            const key = pair.substring(0, equalIndex).trim();
            let value = pair.substring(equalIndex + 1).trim();
            
            if (key && value) {
              // Try to parse the value as JSON first
              try {
                kwargsObj[key] = JSON.parse(value);
              } catch (e) {
                // Handle string literals
                if ((value.startsWith("'") && value.endsWith("'")) || 
                    (value.startsWith('"') && value.endsWith('"'))) {
                  kwargsObj[key] = value.slice(1, -1);
                } else if (!isNaN(value) && !isNaN(parseFloat(value))) {
                  kwargsObj[key] = parseFloat(value);
                } else if (value === 'true') {
                  kwargsObj[key] = true;
                } else if (value === 'false') {
                  kwargsObj[key] = false;
                } else if (value === 'null') {
                  kwargsObj[key] = null;
                } else {
                  kwargsObj[key] = value;
                }
              }
            }
          }
        });
        if (Object.keys(kwargsObj).length > 0) {
          testCaseObj.kwargs = kwargsObj;
        }
      }
      
      testCasesArray.push(testCaseObj);
    }
  });
  
  jsonField.value = JSON.stringify(testCasesArray);
}
