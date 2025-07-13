/**
 * Drag and Drop Module
 * Handles drag and drop functionality for reordering questions
 */

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
