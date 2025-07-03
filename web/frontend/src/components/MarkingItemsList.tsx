import React from 'react';
import MarkingItemForm from './MarkingItemForm';

interface MarkingItemsListProps {
  markingItems: any[];
  onChange: (markingItems: any[]) => void;
}

const MarkingItemsList: React.FC<MarkingItemsListProps> = ({ markingItems, onChange }) => {
  const handleMarkingItemChange = (idx: number, updated: any) => {
    const newItems = markingItems.map((item, i) => (i === idx ? updated : item));
    onChange(newItems);
  };

  const handleRemove = (idx: number) => {
    const newItems = markingItems.filter((_, i) => i !== idx);
    onChange(newItems);
  };

  const handleAdd = () => {
    onChange([
      ...markingItems,
      { type: '', target_file: '', total_mark: 0, time_limit: 30, visibility: 'visible' }
    ]);
  };

  return (
    <div style={{ marginBottom: 12 }}>
      <h5>Marking Items</h5>
      {markingItems.map((item, i) => (
        <MarkingItemForm
          key={i}
          markingItem={item}
          onChange={updated => handleMarkingItemChange(i, updated)}
          onRemove={() => handleRemove(i)}
        />
      ))}
      <button onClick={handleAdd}>Add Marking Item</button>
    </div>
  );
};

export default MarkingItemsList; 