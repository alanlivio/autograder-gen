import React, { useState } from 'react';
import GlobalSettingsForm from './GlobalSettingsForm';
import QuestionsList from './QuestionsList';
import JsonPreview from './JsonPreview';
import ValidationResult from './ValidationResult';

const API_BASE = 'http://localhost:5000/api';

const defaultConfig = {
  version: '1.0',
  language: 'python',
  global_time_limit: 300,
  setup_commands: [],
  files_necessary: [],
  questions: [],
};

const AutograderForm: React.FC = () => {
  const [config, setConfig] = useState<any>(defaultConfig);
  const [validation, setValidation] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGlobalSettingsChange = (values: any) => {
    setConfig((prev: any) => ({ ...prev, ...values }));
  };

  const handleQuestionsChange = (questions: any[]) => {
    setConfig((prev: any) => ({ ...prev, questions }));
  };

  const handleValidate = async () => {
    setLoading(true);
    setError(null);
    setValidation(null);
    try {
      const res = await fetch(`${API_BASE}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      const data = await res.json();
      setValidation(data);
    } catch (e: any) {
      setError(e.message || 'Validation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (!res.ok) throw new Error('Failed to generate autograder');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'autograder.zip';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e.message || 'Generation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ margin: '2rem', padding: 24, border: '1px solid #ccc', borderRadius: 8 }}>
      <h2>Autograder Config Builder</h2>
      <GlobalSettingsForm values={config} onChange={handleGlobalSettingsChange} />
      <QuestionsList questions={config.questions} onChange={handleQuestionsChange} />
      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button onClick={handleValidate} disabled={loading}>Validate</button>
        <button onClick={handleGenerate} disabled={loading}>Generate Autograder</button>
      </div>
      {loading && <div style={{ marginTop: 12 }}>Loading...</div>}
      {error && <div style={{ color: 'red', marginTop: 12 }}>{error}</div>}
      <ValidationResult validation={validation} />
      <JsonPreview config={config} />
    </div>
  );
};

export default AutograderForm; 