import React from 'react';

interface GlobalSettingsProps {
  values: any;
  onChange: (values: any) => void;
}

const GlobalSettingsForm: React.FC<GlobalSettingsProps> = ({ values, onChange }) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    if (name === 'global_time_limit') {
      onChange({ [name]: Number(value) });
    } else {
      onChange({ [name]: value });
    }
  };

  const handleListChange = (name: string, value: string) => {
    // Split by newlines, filter empty
    const items = value.split('\n').map(s => s.trim()).filter(Boolean);
    onChange({ [name]: items });
  };

  return (
    <div style={{ marginBottom: 24 }}>
      <h3>Global Settings</h3>
      <div style={{ marginBottom: 12 }}>
        <label>Language:&nbsp;
          <select name="language" value={values.language} onChange={handleChange}>
            <option value="python">Python</option>
            <option value="java">Java</option>
            <option value="r">R</option>
          </select>
        </label>
      </div>
      <div style={{ marginBottom: 12 }}>
        <label>Global Time Limit (seconds):&nbsp;
          <input
            type="number"
            name="global_time_limit"
            value={values.global_time_limit}
            onChange={handleChange}
            min={1}
            style={{ width: 100 }}
          />
        </label>
      </div>
      <div style={{ marginBottom: 12 }}>
        <label>Setup Commands (one per line):<br />
          <textarea
            name="setup_commands"
            value={values.setup_commands?.join('\n') || ''}
            onChange={e => handleListChange('setup_commands', e.target.value)}
            rows={3}
            style={{ width: '100%', fontFamily: 'monospace' }}
          />
        </label>
      </div>
      <div style={{ marginBottom: 12 }}>
        <label>Files Necessary (one per line):<br />
          <textarea
            name="files_necessary"
            value={values.files_necessary?.join('\n') || ''}
            onChange={e => handleListChange('files_necessary', e.target.value)}
            rows={2}
            style={{ width: '100%', fontFamily: 'monospace' }}
          />
        </label>
      </div>
    </div>
  );
};

export default GlobalSettingsForm; 