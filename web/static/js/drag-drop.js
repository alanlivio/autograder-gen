/**
 * Drag and Drop Module
 * Handles drag and drop functionality for reordering questions
 */

// Drag and drop event handlers
let draggedElement = null;

function handleDragStart(e) {
  // Find the card that contains this drag handle
  const card = e.target.closest('.card');
  if (!card) {
    e.preventDefault();
    return false;
  }
  
  // Set the dragged element to the card, not the handle
  draggedElement = card;
  card.classList.add('dragging');
  
  // Set the drag effect and data
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/html', card.innerHTML);
}

function handleDragEnd(e) {
  // Remove dragging class from the card, not the handle
  if (draggedElement) {
    draggedElement.classList.remove('dragging');
  }
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

// Initialize drag and drop for a specific element
function initializeDragAndDrop(element) {
  // Find the drag handle within the card
  const dragHandle = element.querySelector('.drag-handle');
  if (!dragHandle) return;
  
  // Remove any existing listeners to avoid duplicates
  dragHandle.removeEventListener('dragstart', handleDragStart);
  dragHandle.removeEventListener('dragend', handleDragEnd);
  element.removeEventListener('dragover', handleDragOver);
  element.removeEventListener('drop', handleDrop);
  
  // Add drag events to the drag handle
  dragHandle.addEventListener('dragstart', handleDragStart);
  dragHandle.addEventListener('dragend', handleDragEnd);
  
  // Add drop events to the card
  element.addEventListener('dragover', handleDragOver);
  element.addEventListener('drop', handleDrop);
}

// Expose functions to global scope
window.initializeDragAndDrop = initializeDragAndDrop;
