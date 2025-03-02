import os
import json
import datetime
import glob
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__, template_folder='templates', static_folder='static')

# Load configuration files
def load_config(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_config(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True

# Task history management
def load_task_history():
    task_history = load_config('data/task_history.json')
    if not task_history:
        task_history = {"tasks": []}
    return task_history

def save_task_history(task_history):
    save_config('data/task_history.json', task_history)

def add_task_record(status, response=None):
    task_history = load_task_history()
    task_history["tasks"].append({
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "response": response
    })
    # Keep only the last 100 tasks
    if len(task_history["tasks"]) > 100:
        task_history["tasks"] = task_history["tasks"][-100:]
    save_task_history(task_history)

# Routes
# Get CSV files from data/other directory
def get_csv_files():
    csv_files = []
    csv_path = os.path.join('data', 'other', '*.csv')
    for file_path in glob.glob(csv_path):
        filename = os.path.basename(file_path)
        csv_files.append(filename)
    return csv_files

@app.route('/')
def index():
    task_history = load_task_history()
    csv_files = get_csv_files()
    group_tags = load_config('config/group_tags.json') or {}
    decrypt_params = load_config('config/decrypt_params.json') or {
        "db_path": "",
        "key": "",
        "iv": "",
        "def_path": ""
    }
    return render_template('index.html', 
                          task_history=task_history,
                          csv_files=csv_files,
                          group_tags=group_tags,
                          decrypt_params=decrypt_params)

@app.route('/api/csv_files', methods=['GET'])
def get_csv_files_api():
    csv_files = get_csv_files()
    return jsonify({"files": csv_files})

@app.route('/api/group_tags', methods=['GET', 'POST'])
def manage_group_tags():
    if request.method == 'POST':
        tags = request.json
        save_config('config/group_tags.json', tags)
        return jsonify({"status": "success"})
    else:
        group_tags = load_config('config/group_tags.json') or {}
        return jsonify(group_tags)

@app.route('/api/decrypt_params', methods=['GET', 'POST'])
def manage_decrypt_params():
    if request.method == 'POST':
        params = request.json
        save_config('config/decrypt_params.json', params)
        return jsonify({"status": "success"})
    else:
        decrypt_params = load_config('config/decrypt_params.json') or {}
        return jsonify(decrypt_params)

@app.route('/api/task_history', methods=['GET'])
def get_task_history():
    task_history = load_task_history()
    return jsonify(task_history)

# This function will be called from main.py to record task execution
def record_task_execution(status, response=None):
    add_task_record(status, response)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
