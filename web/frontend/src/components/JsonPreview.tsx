import React from 'react';

interface JsonPreviewProps {
  config: any;
}

const JsonPreview: React.FC<JsonPreviewProps> = ({ config }) => {
  return (
    <div style={{ marginTop: 24 }}>
      <h4>JSON Preview</h4>
      <pre style={{ background: '#f8f8f8', padding: 12, borderRadius: 4 }}>
        {JSON.stringify(config, null, 2)}
      </pre>
    </div>
  );
};

export default JsonPreview; 