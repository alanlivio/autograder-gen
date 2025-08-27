from flask import Flask, request, send_file, jsonify, render_template
import tempfile
import os
from autograder_gen.config import ConfigParser, AutograderConfig
from autograder_gen.generator import AutograderGenerator
from autograder_gen.validator import ConfigValidator
import json
from flask_cors import CORS

app = Flask(__name__, static_url_path='/static', static_folder='static')
CORS(app)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload-config', methods=['POST'])
def upload_config():
    """Handle JSON config file upload and return the parsed configuration."""
    if 'config_file' not in request.files:
        return jsonify({'error': 'No config file provided'}), 400
    
    file = request.files['config_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename or not file.filename.endswith('.json'):
        return jsonify({'error': 'File must be a JSON file'}), 400
    
    try:
        # Read and parse the JSON content
        content = file.read().decode('utf-8')
        config_data = json.loads(content)
        
        # Validate the configuration
        validator = ConfigValidator()
        if not validator.validate_json(config_data):
            return jsonify({
                'error': 'Invalid configuration file',
                'validation_errors': validator.get_errors()
            }), 400
        
        return jsonify({
            'success': True,
            'config': config_data,
            'warnings': validator.get_warnings()
        })
        
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON format: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

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
        from autograder_gen.config import ConfigParser
        config = ConfigParser(config_path).parse()
        generator = AutograderGenerator(config, config_dict)  # Pass original config dict
        zip_path = generator.generate(tmp_dir)
        # Read the file into memory before sending to avoid file locking issues
        with open(zip_path, 'rb') as zip_file:
            zip_data = zip_file.read()
        # Create a BytesIO object to send the file data
        from io import BytesIO
        zip_buffer = BytesIO(zip_data)
        zip_buffer.seek(0)
        return send_file(
            zip_buffer, 
            as_attachment=True, 
            download_name='autograder.zip',
            mimetype='application/zip'
        )
    except Exception as e:
        return render_template('download.html', message=f'Error: {str(e)}')
    finally:
        if os.path.exists(tmp_dir):
            try:
                import shutil
                shutil.rmtree(tmp_dir)
            except OSError:
                pass  # Ignore cleanup errors

def form_to_config_dict(form):
    # Convert flat form data to nested config dict matching sample_config.json structure
    config = {
        'version': '0.1',  # Auto-populated by backend
        'language': form.get('language', 'python'),
        'global_time_limit': int(form.get('global_time_limit', 300)),
        'setup_commands': [],
        'files_necessary': [],
        'questions': []
    }
    
    # Parse setup commands
    setup_commands = form.get('setup_commands', '')
    if setup_commands and setup_commands.strip():
        config['setup_commands'] = [cmd.strip() for cmd in setup_commands.split('\n') if cmd.strip()]
    
    # Parse necessary files
    files_necessary = form.get('files_necessary', '')
    if files_necessary and files_necessary.strip():
        config['files_necessary'] = [file.strip() for file in files_necessary.split('\n') if file.strip()]
    
    # Group form data by questions and marking items
    questions = {}
    marking_items = {}
    
    for key, value in form.items():
        if key.startswith('questions['):
            # Parse question field: questions[0][name] -> qidx=0, field=name
            parts = key.split('[')
            if len(parts) >= 3:
                qidx = parts[1].rstrip(']')
                
                if 'marking_items' in key:
                    # Marking item field: questions[0][marking_items][1][type]
                    if len(parts) >= 5:
                        miidx = parts[3].rstrip(']')
                        field = parts[4].rstrip(']')
                        
                        # Initialize nested structure
                        if qidx not in marking_items:
                            marking_items[qidx] = {}
                        if miidx not in marking_items[qidx]:
                            marking_items[qidx][miidx] = {}
                        
                        # Process the value based on field type
                        if field == 'test_cases' and value and value.strip():
                            try:
                                marking_items[qidx][miidx][field] = json.loads(value)
                            except json.JSONDecodeError:
                                marking_items[qidx][miidx][field] = []
                        elif field == 'total_mark':
                            marking_items[qidx][miidx][field] = int(value) if value else 0
                        elif field == 'time_limit':
                            marking_items[qidx][miidx][field] = int(value) if value else 30
                        elif value and value.strip():
                            # Only include non-empty values
                            marking_items[qidx][miidx][field] = value.strip()
                else:
                    # Question field: questions[0][name]
                    field = parts[2].rstrip(']')
                    if qidx not in questions:
                        questions[qidx] = {}
                    if value and value.strip():
                        questions[qidx][field] = value.strip()
    
    # Build the final structure matching sample_config.json
    for qidx in sorted(questions.keys(), key=int):
        question = {
            'name': questions[qidx].get('name', ''),
            'marking_items': []
        }
        
        # Add marking items for this question
        if qidx in marking_items:
            for miidx in sorted(marking_items[qidx].keys(), key=int):
                item = marking_items[qidx][miidx]
                
                # Build marking item with required fields
                marking_item = {
                    'target_file': item.get('target_file', ''),
                    'total_mark': item.get('total_mark', 0),
                    'type': item.get('type', 'file_exists'),
                    'time_limit': item.get('time_limit', 30),
                    'visibility': item.get('visibility', 'visible')
                }
                
                # Add optional fields only if they exist and have values
                if item.get('name'):
                    marking_item['name'] = item['name']
                if item.get('expected_input'):
                    marking_item['expected_input'] = item['expected_input']
                if item.get('expected_output'):
                    marking_item['expected_output'] = item['expected_output']
                if item.get('function_name'):
                    marking_item['function_name'] = item['function_name']
                if item.get('test_cases') and isinstance(item['test_cases'], list) and len(item['test_cases']) > 0:
                    marking_item['test_cases'] = item['test_cases']
                
                question['marking_items'].append(marking_item)
        
        config['questions'].append(question)
    
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
        generator = AutograderGenerator(config, data)  # Pass original config dict
        with tempfile.TemporaryDirectory() as out_dir:
            zip_path = generator.generate(out_dir)
            # Read the file into memory before sending to avoid file locking issues
            with open(zip_path, 'rb') as zip_file:
                zip_data = zip_file.read()
            # Create a BytesIO object to send the file data
            from io import BytesIO
            zip_buffer = BytesIO(zip_data)
            zip_buffer.seek(0)
            return send_file(
                zip_buffer, 
                as_attachment=True, 
                download_name='autograder.zip',
                mimetype='application/zip'
            )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass  # Ignore file deletion errors

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