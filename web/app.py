from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import tempfile
import os
from autograder_core.config import ConfigParser, AutograderConfig
from autograder_core.generator import AutograderGenerator
from autograder_core.validator import ConfigValidator
import json

app = Flask(__name__)
CORS(app)

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