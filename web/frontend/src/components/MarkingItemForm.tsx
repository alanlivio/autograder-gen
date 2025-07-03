import React from 'react';

interface MarkingItemFormProps {
  markingItem: any;
  onChange: (markingItem: any) => void;
  onRemove: () => void;
}

const MarkingItemForm: React.FC<MarkingItemFormProps> = ({ markingItem, onChange, onRemove }) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    if (name === 'total_mark' || name === 'time_limit') {
      onChange({ ...markingItem, [name]: Number(value) });
    } else {
      onChange({ ...markingItem, [name]: value });
    }
  };

  return (
    <div style={{ border: '1px solid #ddd', padding: 8, marginBottom: 8 }}>
      <h6>Marking Item</h6>
      <div style={{ marginBottom: 6 }}>
        <label>Type:&nbsp;
          <select name="type" value={markingItem.type} onChange={handleChange}>
            <option value="">Select type</option>
            <option value="file_exists">File Exists</option>
            <option value="output_comparison">Output Comparison</option>
            <option value="signature_check">Signature Check</option>
            <option value="function_test">Function Test</option>
          </select>
        </label>
      </div>
      <div style={{ marginBottom: 6 }}>
        <label>Target File:&nbsp;
          <input type="text" name="target_file" value={markingItem.target_file} onChange={handleChange} />
        </label>
      </div>
      <div style={{ marginBottom: 6 }}>
        <label>Total Mark:&nbsp;
          <input type="number" name="total_mark" value={markingItem.total_mark} onChange={handleChange} min={0} />
        </label>
      </div>
      <div style={{ marginBottom: 6 }}>
        <label>Time Limit (s):&nbsp;
          <input type="number" name="time_limit" value={markingItem.time_limit} onChange={handleChange} min={1} />
        </label>
      </div>
      <div style={{ marginBottom: 6 }}>
        <label>Visibility:&nbsp;
          <select name="visibility" value={markingItem.visibility} onChange={handleChange}>
            <option value="visible">Visible</option>
            <option value="hidden">Hidden</option>
            <option value="after_due_date">After Due Date</option>
            <option value="after_published">After Published</option>
          </select>
        </label>
      </div>
      {/* TODO: Add extra fields for output_comparison, function_test, etc. */}
      <button onClick={onRemove}>Remove Marking Item</button>
    </div>
  );
};

export default MarkingItemForm; 