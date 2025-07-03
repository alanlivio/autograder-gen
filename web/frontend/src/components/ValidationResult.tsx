import React from 'react';

interface ValidationResultProps {
  validation: any;
}

const ValidationResult: React.FC<ValidationResultProps> = ({ validation }) => {
  if (!validation) return null;
  return (
    <div style={{ marginTop: 16 }}>
      <strong>Validation Result:</strong>
      <pre style={{ background: '#f8f8f8', padding: 12, borderRadius: 4 }}>
        {JSON.stringify(validation, null, 2)}
      </pre>
    </div>
  );
};

export default ValidationResult; 