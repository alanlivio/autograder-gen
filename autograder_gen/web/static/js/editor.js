let editor = null;
let currentMode = 'text';

function initEditor(initialData) {
    if (editor) {
        editor.destroy();
    }
    const container = document.getElementById('json-editor-container');
    const schemaEl = document.getElementById('schema-data');
    const configSchema = schemaEl ? JSON.parse(schemaEl.textContent) : {};

    const options = {
        schema: configSchema,
        theme: 'bootstrap5',
        iconlib: 'fontawesome5',
        compact: true,
        disable_edit_json: true,
        disable_properties: true,
        disable_collapse: false,
        show_errors: 'change',
        prompt_before_delete: false,
        object_layout: 'grid',
        array_controls_top: true
    };
    if (initialData) {
        options.startval = initialData;
    }

    editor = new JSONEditor(container, options);

    editor.on('ready', () => {
        const val = editor.getValue();
        if (val && val.language) {
            updateRuntimeAlert(val.language);
        }
        if (!document.getElementById('yaml-textarea').value.trim()) {
            updateYamlFromEditor();
        }
    });

    editor.on('change', () => {
        const val = editor.getValue();
        if (val && val.language) {
            updateRuntimeAlert(val.language);
        }
        if (currentMode === 'form') {
            updateYamlFromEditor();
        }
    });
}

function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    alertContainer.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function getRuntimesData() {
    const el = document.getElementById('runtimes-data');
    if (el) {
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
        }
    }
    return {};
}

function getRuntimeSummary() {
    const el = document.getElementById('runtime-summary-data');
    if (el) {
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
        }
    }
    return '';
}

function updateRuntimeAlert(lang) {
    const alertEl = document.getElementById('default-runtime-alert');
    const titleEl = document.getElementById('runtime-alert-title');
    const textEl = document.getElementById('runtime-alert-text');
    if (!alertEl || !titleEl || !textEl) return;

    const runtimes = getRuntimesData();
    const normalizedLang = (lang || '').toString().toLowerCase().trim();
    const runtimeInfo = runtimes[normalizedLang];

    if (runtimeInfo) {
        titleEl.textContent = runtimeInfo.title || `Default Environment: ${runtimeInfo.name}`;
        textEl.innerHTML = runtimeInfo.html_details || runtimeInfo.details;
    } else {
        titleEl.textContent = 'Default Execution Environment';
        textEl.innerHTML = getRuntimeSummary();
    }
}

function updateLanguageFromYaml() {
    const yamlText = document.getElementById('yaml-textarea').value;
    try {
        const parsed = jsyaml.load(yamlText);
        if (parsed && typeof parsed === 'object') {
            updateRuntimeAlert(parsed.language);
        }
    } catch (e) {
    }
}

function switchEditorMode(mode) {
    currentMode = mode;
    const textContainer = document.getElementById('text-mode-container');
    const formContainer = document.getElementById('form-mode-container');
    const textBtn = document.getElementById('mode-text-btn');
    const formBtn = document.getElementById('mode-form-btn');

    if (mode === 'form') {
        textContainer.classList.add('d-none');
        formContainer.classList.remove('d-none');
        textBtn.className = 'btn btn-outline-primary mode-toggle-btn px-4';
        formBtn.className = 'btn btn-primary mode-toggle-btn px-4';
    } else {
        formContainer.classList.add('d-none');
        textContainer.classList.remove('d-none');
        textBtn.className = 'btn btn-primary mode-toggle-btn px-4';
        formBtn.className = 'btn btn-outline-primary mode-toggle-btn px-4';
    }
}

function setMode(mode) {
    if (mode === currentMode) {
        return;
    }
    if (mode === 'form') {
        const yamlText = document.getElementById('yaml-textarea').value;
        if (yamlText && yamlText.trim()) {
            try {
                const parsed = jsyaml.load(yamlText);
                if (parsed && typeof parsed === 'object') {
                    if (editor) {
                        editor.setValue(parsed);
                    } else {
                        initEditor(parsed);
                    }
                }
            } catch (e) {
                showAlert('Cannot switch to Form Mode. Invalid YAML: ' + e.message, 'danger');
                return;
            }
        }
    } else {
        updateYamlFromEditor();
    }
    switchEditorMode(mode);
}

function updateYamlFromEditor() {
    if (!editor) return;
    const val = editor.getValue();
    const yamlString = jsyaml.dump(val, {
        schema: jsyaml.DEFAULT_SCHEMA,
        noRefs: true,
        lineWidth: -1,
        styles: {
            '!!null': 'empty'
        }
    });
    document.getElementById('yaml-textarea').value = yamlString;
    updateYamlStats();
}

function updateYamlStats() {
    const statusBadge = document.getElementById('yaml-status-badge');
    const questionsCountSpan = document.getElementById('text-questions-count');
    const totalScoreSpan = document.getElementById('text-total-score');
    if (!statusBadge && !questionsCountSpan) return;

    const yamlText = document.getElementById('yaml-textarea').value;

    try {
        const config = jsyaml.load(yamlText);
        if (config && typeof config === 'object') {
            statusBadge.textContent = 'Valid YAML';
            statusBadge.className = 'badge bg-success py-2 px-3';
            const questions = config.questions || [];
            questionsCountSpan.textContent = questions.length;
            let totalScore = 0;
            questions.forEach(q => {
                (q.marking_items || []).forEach(item => {
                    const mark = Number(item.total_mark);
                    if (!isNaN(mark)) totalScore += mark;
                });
            });
            totalScoreSpan.textContent = totalScore;
        } else {
            statusBadge.textContent = 'Empty / Invalid';
            statusBadge.className = 'badge bg-warning text-dark py-2 px-3';
        }
    } catch (e) {
        statusBadge.textContent = 'Invalid YAML';
        statusBadge.className = 'badge bg-danger py-2 px-3';
    }
}

function getCurrentConfig() {
    if (currentMode === 'form' && editor) {
        return editor.getValue();
    }
    const yamlText = document.getElementById('yaml-textarea').value;
    try {
        return jsyaml.load(yamlText);
    } catch (e) {
        return null;
    }
}

function createNewConfig() {
    if (confirm('Create new configuration? Any unsaved changes will be lost.')) {
        document.getElementById('yaml-textarea').value = '';
        initEditor();
        document.getElementById('export-section').classList.add('d-none');
        showAlert('Created new configuration template.', 'info');
    }
}

function handleConfigUpload(input) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const raw = e.target.result;
            let config;
            if (file.name.endsWith('.yaml') || file.name.endsWith('.yml')) {
                config = jsyaml.load(raw);
            } else {
                config = JSON.parse(raw);
            }
            if (config && typeof config === 'object') {
                if (editor) editor.setValue(config);
                updateRuntimeAlert(config.language);
                document.getElementById('yaml-textarea').value = jsyaml.dump(config, {
                    schema: jsyaml.DEFAULT_SCHEMA,
                    noRefs: true,
                    lineWidth: -1
                });
                updateYamlStats();
                document.getElementById('export-section').classList.add('d-none');
                showAlert('Configuration imported successfully.', 'success');
            } else {
                showAlert('Import Error: File does not contain a valid configuration object.', 'danger');
            }
        } catch (err) {
            showAlert('Import Error: ' + err.message, 'danger');
        }
    };
    reader.readAsText(file);
    input.value = '';
}

function downloadYamlConfig() {
    const config = getCurrentConfig();
    if (!config) {
        showAlert('Cannot download: Invalid configuration.', 'danger');
        return;
    }
    const yamlString = jsyaml.dump(config, {
        schema: jsyaml.DEFAULT_SCHEMA,
        noRefs: true,
        lineWidth: -1,
        styles: { '!!null': 'empty' }
    });
    const blob = new Blob([yamlString], { type: 'application/x-yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'autograder_gen.yaml';
    a.click();
    URL.revokeObjectURL(url);
}

async function validateConfig() {
    const config = getCurrentConfig();
    if (!config) {
        showAlert('Cannot validate: Invalid YAML or form data.', 'danger');
        return;
    }

    const validateBtn = document.getElementById('validate-btn');
    const exportSection = document.getElementById('export-section');
    const logPre = document.getElementById('validation-log');

    validateBtn.disabled = true;
    validateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Validating...';

    try {
        const resp = await fetch('/api/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const data = await resp.json();

        exportSection.classList.remove('d-none');

        if (data.valid) {
            logPre.textContent = 'Configuration is valid!\n' + (data.warnings && data.warnings.length > 0 ? '\nWarnings:\n- ' + data.warnings.join('\n- ') : 'No warnings.\nReady to export all assessment assets.');
            showAlert('Configuration is valid!', 'success');
        } else {
            logPre.textContent = 'Configuration validation failed:\n- ' + (data.errors || []).join('\n- ');
            showAlert('Validation failed. Please check the log below.', 'danger');
        }
    } catch (err) {
        showAlert('Error validating configuration: ' + err.message, 'danger');
    } finally {
        validateBtn.disabled = false;
        validateBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Validate & Export';
    }
}

async function downloadExport(type) {
    const config = getCurrentConfig();
    if (!config) {
        showAlert('Cannot export: Invalid configuration.', 'danger');
        return;
    }

    try {
        const resp = await fetch('/api/export/bundle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (!resp.ok) {
            const errData = await resp.json();
            throw new Error(errData.error || 'Export failed');
        }

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'all_assets.zip';
        a.click();
        URL.revokeObjectURL(url);
        showAlert('All assets exported successfully!', 'success');
    } catch (err) {
        showAlert('Export error: ' + err.message, 'danger');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initEditor();
    const yamlTextarea = document.getElementById('yaml-textarea');
    yamlTextarea.addEventListener('input', () => {
        updateYamlStats();
        updateLanguageFromYaml();
    });
    updateLanguageFromYaml();

    const urlParams = new URLSearchParams(window.location.search);
    const loadExample = urlParams.get('load_example');
    if (loadExample) {
        fetch(`/api/example/${loadExample}`)
            .then(res => res.json())
            .then(data => {
                if (data.success && data.config) {
                    if (editor) editor.setValue(data.config);
                    yamlTextarea.value = data.yaml || jsyaml.dump(data.config, { schema: jsyaml.DEFAULT_SCHEMA, noRefs: true, lineWidth: -1 });
                    updateYamlStats();
                    updateRuntimeAlert(data.config.language);
                    showAlert(`Example '${loadExample}' loaded successfully.`, 'success');
                }
            })
            .catch(err => console.error('Failed to load example:', err));
    }
});
