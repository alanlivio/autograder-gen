/**
 * Form Data Processing Module
 * Handles form data conversion and configuration object creation
 */

// Convert form data to config object
function formToConfigObject() {
  const form = document.getElementById('autograder-form');
  const formData = new FormData(form);
  
  const config = {
    version: '1.0',
    language: formData.get('language') || 'python',
    global_time_limit: parseInt(formData.get('global_time_limit')) || 300,
    setup_commands: [],
    files_necessary: [],
    questions: []
  };
  
  // Parse setup commands (split by newlines, filter empty)
  const setupCommands = formData.get('setup_commands');
  if (setupCommands && setupCommands.trim()) {
    config.setup_commands = setupCommands.split('\n')
      .map(cmd => cmd.trim())
      .filter(cmd => cmd.length > 0);
  }
  
  // Parse necessary files (use the required files management system)
  if (typeof getRequiredFiles === 'function') {
    config.files_necessary = getRequiredFiles();
  } else {
    // Fallback to textarea method if required files management isn't loaded
    const filesNecessary = formData.get('files_necessary');
    if (filesNecessary && filesNecessary.trim()) {
      config.files_necessary = filesNecessary.split('\n')
        .map(file => file.trim())
        .filter(file => file.length > 0);
    }
  }
  
  // Build questions structure directly from DOM to ensure proper nesting
  const questionCards = document.querySelectorAll('#questions-list > .card');
  
  questionCards.forEach((questionCard, questionIndex) => {
    // Get question name
    const nameField = questionCard.querySelector('input[id$="-name"]');
    const questionName = nameField ? nameField.value.trim() : '';
    
    const question = {
      name: questionName,
      marking_items: []
    };
    
    // Get marking items for this question
    const markingItems = questionCard.querySelectorAll('.marking-item');
    markingItems.forEach((markingItem, markingItemIndex) => {
      const markingItemObj = extractMarkingItemData(markingItem);
      question.marking_items.push(markingItemObj);
    });
    
    config.questions.push(question);
  });
  
  return config;
}

function extractMarkingItemData(markingItem) {
  // Extract data from each marking item
  const typeField = markingItem.querySelector('select[id$="-type"]');
  const targetFileField = markingItem.querySelector('select[id$="-target-file"]');
  const totalMarkField = markingItem.querySelector('input[id$="-total-mark"]');
  const timeLimitField = markingItem.querySelector('input[id$="-time-limit"]');
  const visibilityField = markingItem.querySelector('select[id$="-visibility"]');
  const nameField = markingItem.querySelector('input[id$="-name"]');
  
  const markingItemObj = {
    target_file: targetFileField ? targetFileField.value.trim() : '',
    total_mark: totalMarkField ? parseInt(totalMarkField.value) || 0 : 0,
    type: typeField ? typeField.value : '',
    time_limit: timeLimitField ? parseInt(timeLimitField.value) || 30 : 30,
    visibility: visibilityField ? visibilityField.value : 'visible'
  };
  
  // Add name field if it has a value
  if (nameField && nameField.value.trim()) {
    markingItemObj.name = nameField.value.trim();
  }
  
  // Add type-specific fields
  addTypeSpecificFields(markingItem, markingItemObj);
  
  return markingItemObj;
}

function addTypeSpecificFields(markingItem, markingItemObj) {
  const expectedInputField = markingItem.querySelector('textarea[id$="-expected-input"]');
  const expectedOutputField = markingItem.querySelector('textarea[id$="-expected-output"]');
  const referenceFileField = markingItem.querySelector('input[id$="-reference-file"]');
  const functionNameField = markingItem.querySelector('input[id$="-function-name"]');
  const expectedParamsField = markingItem.querySelector('input[id$="-expected-params"]');
  const expectedReturnTypeField = markingItem.querySelector('input[id$="-expected-return-type"]');
  const testCasesField = markingItem.querySelector('textarea[id$="-test-cases"]');
  
  // Add optional fields only if they have values
  if (expectedInputField && expectedInputField.value !== '') {
    markingItemObj.expected_input = expectedInputField.value; // Preserve exact whitespace
  }
  if (expectedOutputField && expectedOutputField.value !== '') {
    markingItemObj.expected_output = expectedOutputField.value; // Preserve exact whitespace
  }
  if (referenceFileField && referenceFileField.value.trim()) {
    markingItemObj.reference_file = referenceFileField.value.trim();
  }
  if (functionNameField && functionNameField.value.trim()) {
    markingItemObj.function_name = functionNameField.value.trim();
  }
  if (expectedParamsField && expectedParamsField.value.trim()) {
    markingItemObj.expected_parameters = expectedParamsField.value.trim();
  }
  if (expectedReturnTypeField && expectedReturnTypeField.value.trim()) {
    markingItemObj.expected_return_type = expectedReturnTypeField.value.trim();
  }
  if (testCasesField && testCasesField.value.trim()) {
    try {
      const testCases = JSON.parse(testCasesField.value);
      if (Array.isArray(testCases) && testCases.length > 0) {
        markingItemObj.test_cases = testCases;
      }
    } catch (e) {
      // Invalid JSON, skip test_cases
    }
  }
}
