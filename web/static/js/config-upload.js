/**
 * Configuration Upload and Form Population
 * Handles uploading JSON config files and populating the form fields
 */

/**
 * Handle file upload when user selects a config file
 * @param {HTMLInputElement} fileInput - The file input element
 */
function handleConfigUpload(fileInput) {
    const file = fileInput.files[0];
    if (!file) return;
    
    // Validate file type
    if (!file.name.endsWith('.json')) {
        showAlert('Please select a valid JSON file.', 'danger');
        fileInput.value = '';
        return;
    }
    
    // Show loading state
    showAlert('Uploading and processing configuration file...', 'info');
    
    // Create FormData and upload
    const formData = new FormData();
    formData.append('config_file', file);
    
    fetch('/upload-config', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            populateFormFromConfig(data.config);
            let message = 'Configuration loaded successfully!';
            if (data.warnings && data.warnings.length > 0) {
                message += ' Warnings: ' + data.warnings.join(', ');
            }
            showAlert(message, 'success');
        } else {
            let errorMsg = data.error || 'Failed to upload configuration';
            if (data.validation_errors && data.validation_errors.length > 0) {
                errorMsg += ': ' + data.validation_errors.join(', ');
            }
            showAlert(errorMsg, 'danger');
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        showAlert('Error uploading configuration file: ' + error.message, 'danger');
    })
    .finally(() => {
        // Clear the file input
        fileInput.value = '';
    });
}

/**
 * Populate the form fields based on the uploaded configuration
 * @param {Object} config - The configuration object from the uploaded JSON
 */
function populateFormFromConfig(config) {
    try {
        // Clear existing form content
        clearForm();
        
        // Populate global configuration
        if (config.language) {
            document.getElementById('language').value = config.language;
        }
        
        if (config.global_time_limit) {
            document.getElementById('global_time_limit').value = config.global_time_limit;
        }
        
        if (config.setup_commands && Array.isArray(config.setup_commands)) {
            document.getElementById('setup_commands').value = config.setup_commands.join('\n');
        }
        
        if (config.files_necessary && Array.isArray(config.files_necessary)) {
            document.getElementById('files_necessary').value = config.files_necessary.join('\n');
        }
        
        // Populate questions and marking items
        if (config.questions && Array.isArray(config.questions)) {
            config.questions.forEach((question, qIndex) => {
                addQuestion(); // This function should be available from question-management.js
                
                // Set question name
                const questionNameInput = document.querySelector(`input[name="questions[${qIndex}][name]"]`);
                if (questionNameInput && question.name) {
                    questionNameInput.value = question.name;
                }
                
                // Populate marking items
                if (question.marking_items && Array.isArray(question.marking_items)) {
                    question.marking_items.forEach((item, miIndex) => {
                        // Get the question card by index (direct children of questions-list)
                        const questionCard = document.querySelectorAll(`#questions-list > .card`)[qIndex];
                        const addBtn = questionCard ? questionCard.querySelector('button[onclick*="addMarkingItem"]') : null;
                        
                        if (addBtn) {
                            // Add a marking item for each one in the config
                            addMarkingItem(addBtn);
                            
                            // Wait a bit for the DOM to update, then populate the fields
                            setTimeout(() => {
                                populateMarkingItem(qIndex, miIndex, item);
                            }, 10);
                        }
                    });
                }
            });
        }
        
        // Trigger form change event to update button states
        const form = document.getElementById('autograder-form');
        if (form) {
            form.dispatchEvent(new Event('input', { bubbles: true }));
        }
        
    } catch (error) {
        console.error('Error populating form:', error);
        showAlert('Error populating form from configuration: ' + error.message, 'danger');
    }
}

/**
 * Populate a specific marking item with data
 * @param {number} qIndex - Question index
 * @param {number} miIndex - Marking item index
 * @param {Object} item - Marking item data
 */
function populateMarkingItem(qIndex, miIndex, item) {
    // Get the specific question and marking item containers
    const questionCard = document.querySelectorAll(`#questions-list > .card`)[qIndex];
    if (!questionCard) {
        console.error(`Question card not found for index ${qIndex}`);
        return;
    }
    
    const markingItems = questionCard.querySelectorAll('.marking-item');
    const markingItem = markingItems[miIndex];
    if (!markingItem) {
        console.error(`Marking item not found for question ${qIndex}, item ${miIndex}`);
        return;
    }
    
    // Get the marking item ID for field selection
    const markingItemId = markingItem.id;
    
    // Set the type first (this will generate the appropriate fields)
    const typeField = markingItem.querySelector('select[name*="[type]"]');
    if (typeField && item.type) {
        typeField.value = item.type;
        // Trigger the change event to generate type-specific fields
        showTypeFields(typeField);
        
        // Use setTimeout to ensure fields are rendered before populating them
        setTimeout(() => {
            const fieldMappings = {
                'target_file': 'target_file',
                'total_mark': 'total_mark',
                'time_limit': 'time_limit',
                'visibility': 'visibility',
                'expected_input': 'expected_input',
                'expected_output': 'expected_output',
                'function_name': 'function_name',
                'expected_parameters': 'expected_parameters'
            };
            
            // Populate basic fields
            Object.entries(fieldMappings).forEach(([configKey, fieldName]) => {
                if (item[configKey] !== undefined) {
                    const field = markingItem.querySelector(`[name*="[${fieldName}]"]`);
                    if (field) {
                        field.value = item[configKey];
                    }
                }
            });
            
            // Special handling for expected_parameters field (in case the general approach fails)
            if (item.expected_parameters !== undefined) {
                const expectedParamsField = markingItem.querySelector(`input[id$="-expected-params"]`);
                if (expectedParamsField) {
                    expectedParamsField.value = item.expected_parameters;
                }
            }
            
            // Handle test_cases specially (it's JSON)
            if (item.test_cases && Array.isArray(item.test_cases)) {
                const testCasesField = markingItem.querySelector(`[name*="[test_cases]"]`);
                if (testCasesField) {
                    testCasesField.value = JSON.stringify(item.test_cases, null, 2);
                }
                
                // If it's a function test, populate the test cases UI
                if (item.type === 'function_test') {
                    populateFunctionTestCases(markingItemId, item.test_cases);
                }
            }
        }, 50); // Small delay to ensure DOM is updated
    }
}

/**
 * Populate function test cases UI
 * @param {string} markingItemId - The marking item ID
 * @param {Array} testCases - Array of test case objects
 */
function populateFunctionTestCases(markingItemId, testCases) {
    const container = document.getElementById(`${markingItemId}-test-cases-container`);
    if (!container) return;
    
    // Clear existing test cases
    container.innerHTML = '';
    
    testCases.forEach((testCase, index) => {
        // Add test case
        const testCaseDiv = document.createElement('div');
        testCaseDiv.className = 'card card-body mb-2 test-case';
        const testCaseId = `${markingItemId}-testcase-${index}`;
        testCaseDiv.id = testCaseId;
        
        testCaseDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="mb-0">Test Case ${index + 1}</h6>
                <button type="button" class="btn-close btn-sm" onclick="removeTestCase('${testCaseId}', '${markingItemId}')"></button>
            </div>
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
        
        // Populate the fields
        if (testCase.args && Array.isArray(testCase.args)) {
            // For complex data structures, use JSON representation
            const argsStr = testCase.args.map(arg => {
                if (typeof arg === 'string') {
                    return `'${arg}'`;
                } else if (typeof arg === 'object' && arg !== null) {
                    return JSON.stringify(arg);
                } else {
                    return String(arg);
                }
            }).join(', ');
            document.getElementById(`${testCaseId}-args`).value = argsStr;
        }
        
        if (testCase.expected) {
            document.getElementById(`${testCaseId}-expected`).value = testCase.expected;
        }
        
        if (testCase.kwargs) {
            const kwargsStr = Object.entries(testCase.kwargs).map(([k, v]) => {
                let valueStr;
                if (typeof v === 'string') {
                    valueStr = `'${v}'`;
                } else if (typeof v === 'object' && v !== null) {
                    valueStr = JSON.stringify(v);
                } else {
                    valueStr = String(v);
                }
                return `${k}=${valueStr}`;
            }).join(', ');
            document.getElementById(`${testCaseId}-kwargs`).value = kwargsStr;
        }
    });
    
    // Update the JSON field
    updateTestCasesJson(markingItemId);
}

/**
 * Clear the entire form to prepare for new configuration
 */
function clearForm() {
    // Clear global fields
    const globalFields = ['language', 'global_time_limit', 'setup_commands', 'files_necessary'];
    globalFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            if (fieldId === 'language') {
                field.value = 'python'; // Reset to default
            } else if (fieldId === 'global_time_limit') {
                field.value = '300'; // Reset to default
            } else {
                field.value = '';
            }
        }
    });
    
    // Clear all questions
    const questionsList = document.getElementById('questions-list');
    if (questionsList) {
        questionsList.innerHTML = '';
    }
    
    // Clear any error messages
    clearAlerts();
}
