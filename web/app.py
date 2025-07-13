from flask import Flask, request, send_file, jsonify, render_template
import tempfile
import os
from autograder_core.config import ConfigParser, AutograderConfig
from autograder_core.generator import AutograderGenerator
from autograder_core.validator import ConfigValidator
import json
from flask_cors import CORS

app = Flask(__name__, static_url_path='/static', static_folder='static')
CORS(app)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/validate', methods=['POST'])
def validate_form():
    # Convert form data to config dict
    config_dict = form_to_config_dict(request.form)
    validator = ConfigValidator()
    valid = validator.validate_json(config_dict)
    errors = validator.get_errors()
    warnings = validator.get_warnings()
    return render_template('validation_result.html', valid=valid, errors=errors, warnings=warnings, config=config_dict)

@app.route('/generate', methods=['POST'])
def generate_form():
    config_dict = form_to_config_dict(request.form)
    validator = ConfigValidator()
    if not validator.validate_json(config_dict):
        errors = validator.get_errors()
        warnings = validator.get_warnings()
        return render_template('validation_result.html', valid=False, errors=errors, warnings=warnings, config=config_dict)
    # Generate autograder zip
    tmp_dir = tempfile.mkdtemp()
    try:
        config_path = os.path.join(tmp_dir, 'config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f)
        from autograder_core.config import ConfigParser
        config = ConfigParser(config_path).parse()
        generator = AutograderGenerator(config)
        zip_path = generator.generate(tmp_dir)
        return send_file(zip_path, as_attachment=True, download_name='autograder.zip')
    except Exception as e:
        return render_template('download.html', message=f'Error: {str(e)}')
    finally:
        if os.path.exists(tmp_dir):
            try:
                import shutil
                shutil.rmtree(tmp_dir)
            except Exception:
                pass

def form_to_config_dict(form):
    # Convert flat form data to nested config dict
    # This is a simplified parser for the dynamic form structure
    config = {
        'version': '0',
        'language': 'python',
        'questions': []
    }
    config['assignment_name'] = form.get('assignment_name', '')
    config['total_points'] = int(form.get('total_points', 0))
    # Parse questions
    questions = {}
    for key in form:
        if key.startswith('questions['):
            import re
            m = re.match(r'questions\[(\d+)\]\[(\w+)\]', key)
            if m:
                qidx, field = m.groups()
                if qidx not in questions:
                    questions[qidx] = {'marking_items': []}
                questions[qidx][field] = form.get(key)
    # Parse marking items
    for qidx in questions:
        marking_items = []
        for key in form:
            if key.startswith(f'questions[{qidx}][marking_items]'):
                # Not used in this structure, handled below
                continue
        # Find all marking_items for this question
        mi_keys = [k for k in form if k.startswith(f'questions[{qidx}][marking_items[')]
        mi_dict = {}
        for k in mi_keys:
            import re
            m = re.match(rf'questions\[{qidx}\]\[marking_items\[(\d+)\]\]\[(\w+)\]', k)
            if m:
                miidx, field = m.groups()
                if miidx not in mi_dict:
                    mi_dict[miidx] = {}
                mi_dict[miidx][field] = form.get(k)
        for miidx in sorted(mi_dict.keys(), key=int):
            marking_items.append(mi_dict[miidx])
        questions[qidx]['marking_items'] = marking_items
    # Build questions list
    for qidx in sorted(questions.keys(), key=int):
        q = questions[qidx]
        q['points'] = int(q.get('points', 0))
        q['marking_items'] = q.get('marking_items', [])
        config['questions'].append(q)
    return config

@app.route('/api/generate', methods=['POST'])
def generate_autograder():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No config data provided'}), 400
    tmp_path = None
    try:
        # Write config to a temp file
        with tempfile.NamedTemporaryFile('w+', delete=False, suffix='.json') as tmp:
            json.dump(data, tmp)
            tmp_path = tmp.name
        # Parse and validate config
        config_parser = ConfigParser(tmp_path)
        config: AutograderConfig = config_parser.parse()
        generator = AutograderGenerator(config)
        with tempfile.TemporaryDirectory() as out_dir:
            zip_path = generator.generate(out_dir)
            return send_file(zip_path, as_attachment=True, download_name='autograder.zip')
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.route('/api/validate', methods=['POST'])
def validate_config():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No config data provided'}), 400
    try:
        validator = ConfigValidator()
        valid = validator.validate_json(data)
        return jsonify({
            'valid': valid,
            'errors': validator.get_errors(),
            'warnings': validator.get_warnings()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 