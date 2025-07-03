import React from 'react';
import MarkingItemsList from './MarkingItemsList';

interface QuestionFormProps {
  question: any;
  onChange: (question: any) => void;
  onRemove: () => void;
}

const QuestionForm: React.FC<QuestionFormProps> = ({ question, onChange, onRemove }) => {
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...question, name: e.target.value });
  };

  const handleMarkingItemsChange = (marking_items: any[]) => {
    onChange({ ...question, marking_items });
  };

  return (
    <div style={{ border: '1px solid #eee', padding: 12, marginBottom: 12 }}>
      <h4>Question</h4>
      <div style={{ marginBottom: 8 }}>
        <label>Question Name:&nbsp;
          <input
            type="text"
            value={question.name}
            onChange={handleNameChange}
            style={{ width: 300 }}
          />
        </label>
      </div>
      <MarkingItemsList markingItems={question.marking_items} onChange={handleMarkingItemsChange} />
      <button onClick={onRemove}>Remove Question</button>
    </div>
  );
};

export default QuestionForm; 