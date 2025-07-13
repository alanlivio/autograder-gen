# JavaScript Module Structure

The autograder form JavaScript has been refactored into modular components for better maintainability and organization.

## Module Structure

### `/web/static/js/`

- **`main.js`** - Application initialization and utility functions
- **`question-management.js`** - Question CRUD operations and numbering
- **`marking-item-management.js`** - Marking item CRUD operations and type-specific field generation
- **`form-validation.js`** - Client-side form validation logic
- **`form-data-processing.js`** - Form data extraction and configuration object creation
- **`api-communication.js`** - Backend API calls for validation and generation
- **`error-handling.js`** - Error highlighting, user-friendly messages, and alerts
- **`drag-drop.js`** - Drag and drop functionality for question reordering

## Module Dependencies

The modules should be loaded in the following order to ensure proper dependency resolution:

1. `drag-drop.js` - Independent drag/drop handlers
2. `error-handling.js` - Alert and error highlighting functions
3. `form-validation.js` - Validation functions (depends on error-handling)
4. `form-data-processing.js` - Form data extraction (independent)
5. `marking-item-management.js` - Marking item operations (depends on form-validation)
6. `question-management.js` - Question operations (depends on marking-item-management)
7. `api-communication.js` - API calls (depends on form-data-processing, form-validation, error-handling)
8. `main.js` - Application initialization (depends on question-management)

## Key Functions by Module

### Question Management
- `addQuestion()` - Creates new question cards
- `removeQuestion()` - Removes question cards
- `updateQuestionNumbers()` - Renumbers questions and updates field names

### Marking Item Management
- `addMarkingItem()` - Creates new marking items
- `removeMarkingItem()` - Removes marking items
- `showTypeFields()` - Displays type-specific fields based on selection

### Form Validation
- `validateForm()` - Client-side validation before submission
- `validateNumber()` - Number field validation
- `validateJsonField()` - JSON syntax validation

### Form Data Processing
- `formToConfigObject()` - Converts DOM form data to configuration object
- `extractMarkingItemData()` - Extracts data from individual marking items

### API Communication
- `submitForGeneration()` - Calls backend to generate autograder
- `validateConfig()` - Calls backend to validate configuration

### Error Handling
- `showAlert()` - Displays user notifications
- `highlightFieldError()` - Highlights form fields with errors
- `makeErrorUserFriendly()` - Converts technical errors to user-friendly messages

### Drag and Drop
- `handleDragStart()`, `handleDragEnd()`, `handleDragOver()`, `handleDrop()` - Drag/drop event handlers

## Benefits of Modular Structure

1. **Maintainability** - Each module has a single responsibility
2. **Testability** - Individual modules can be unit tested
3. **Reusability** - Modules can be reused in other parts of the application
4. **Debugging** - Easier to isolate and fix issues in specific functionality
5. **Code Organization** - Related functions are grouped together
6. **Performance** - Modules can be loaded conditionally if needed

## Migration Notes

- The original `autograder_form.js` has been completely replaced by the modular structure
- All function names and interfaces remain the same for backward compatibility
- HTML templates reference the same function names (`onclick="addQuestion()"` etc.)
- No changes needed to the backend API or validation logic
