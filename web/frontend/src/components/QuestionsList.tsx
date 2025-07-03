import React from 'react';
import QuestionForm from './QuestionForm';

interface QuestionsListProps {
  questions: any[];
  onChange: (questions: any[]) => void;
}

const QuestionsList: React.FC<QuestionsListProps> = ({ questions, onChange }) => {
  const handleQuestionChange = (idx: number, updated: any) => {
    const newQuestions = questions.map((q, i) => (i === idx ? updated : q));
    onChange(newQuestions);
  };

  const handleRemove = (idx: number) => {
    const newQuestions = questions.filter((_, i) => i !== idx);
    onChange(newQuestions);
  };

  const handleAdd = () => {
    onChange([
      ...questions,
      { name: '', marking_items: [] }
    ]);
  };

  return (
    <div style={{ marginBottom: 24 }}>
      <h3>Questions</h3>
      {questions.map((q, i) => (
        <QuestionForm
          key={i}
          question={q}
          onChange={updated => handleQuestionChange(i, updated)}
          onRemove={() => handleRemove(i)}
        />
      ))}
      <button onClick={handleAdd}>Add Question</button>
    </div>
  );
};

export default QuestionsList; 