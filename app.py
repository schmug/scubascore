import sqlite3
import json
import datetime
import os
import threading
import time
import shutil
from flask import Flask, request, jsonify, render_template, g, redirect, url_for
import scubascore

app = Flask(__name__)
DB_NAME = "scubascore.db"
AUTOLOAD_DIR = "autoload"
PROCESSED_DIR = os.path.join(AUTOLOAD_DIR, "processed")

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_NAME)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                overall_score REAL,
                service_scores TEXT,
                results_json TEXT
            )
        ''')
        db.commit()

# --- Configuration Management ---
def get_service_weights_filename(profile_name):
    """Get the service weights filename for a given profile."""
    if profile_name == "default":
        return "service_weights.yaml"
    return f"service_weights_{profile_name}.yaml"

def get_available_profiles():
    """Get list of available service weight profiles."""
    profiles = ["default"]
    try:
        for filename in os.listdir('.'):
            if filename.startswith("service_weights_") and filename.endswith(".yaml"):
                # Extract profile name: service_weights_<profile>.yaml -> <profile>
                profile_name = filename[len("service_weights_"):-len(".yaml")]
                profiles.append(profile_name)
    except Exception as e:
        print(f"Warning: Error scanning for profiles: {e}")
    return profiles

def load_configs():
    try:
        w = scubascore.load_yaml("weights.yaml")
        profile = get_current_profile()
        sw_filename = get_service_weights_filename(profile)
        sw = scubascore.load_yaml(sw_filename)
        c = scubascore.load_yaml("compensating.yaml")
        return w, sw, c
    except Exception as e:
        print(f"Warning: Config load failed: {e}")
        return {}, {}, {}

def get_current_profile():
    try:
        profile_config = scubascore.load_yaml("profile_config.yaml")
        return profile_config.get("current_profile", "default")
    except Exception as e:
        print(f"Warning: Profile config load failed: {e}")
        return "default"

def set_current_profile(profile_name):
    try:
        import yaml
        with open("profile_config.yaml", "w") as f:
            yaml.dump({"current_profile": profile_name}, f)
        return True
    except Exception as e:
        print(f"Warning: Profile config save failed: {e}")
        return False

WEIGHTS, SERVICE_WEIGHTS, COMPENSATING = load_configs()

def save_score_to_db(results):
    with app.app_context():
        db = get_db()
        overall = results.get("overall_score")
        per_service = results.get("per_service", {})
        
        simple_service_scores = {
            svc: data.get("score") 
            for svc, data in per_service.items() 
            if data.get("score") is not None
        }

        cursor = db.cursor()
        cursor.execute(
            'INSERT INTO scores (overall_score, service_scores, results_json) VALUES (?, ?, ?)',
            (overall, json.dumps(simple_service_scores), json.dumps(results))
        )
        db.commit()

def process_scuba_data(data):
    # Reload configs to ensure we use latest settings
    w, sw, c = load_configs()
    results = scubascore.compute_scores(data, w, sw, c)
    
    # Calculate Top Failures
    all_failures = []
    for svc, details in results.get("per_service", {}).items():
        for fail in details.get("failed", []):
            # fail tuple: (rule_id, weight, is_compensated)
            # We want to prioritize uncompensated high weights
            rule_id, weight, is_compensated = fail
            effective_weight = weight * 0.5 if is_compensated else weight
            all_failures.append({
                "service": svc,
                "rule": rule_id,
                "weight": weight,
                "is_compensated": is_compensated,
                "effective_weight": effective_weight
            })
    
    # Sort by effective weight descending
    all_failures.sort(key=lambda x: x["effective_weight"], reverse=True)
    results["top_failures"] = all_failures[:5]
    
    return results

# --- Background Watcher ---
def autoload_watcher():
    if not os.path.exists(AUTOLOAD_DIR):
        os.makedirs(AUTOLOAD_DIR)
    if not os.path.exists(PROCESSED_DIR):
        os.makedirs(PROCESSED_DIR)

    while True:
        try:
            for filename in os.listdir(AUTOLOAD_DIR):
                if filename.endswith(".json"):
                    filepath = os.path.join(AUTOLOAD_DIR, filename)
                    print(f"Processing autoload file: {filename}")
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        
                        results = process_scuba_data(data)
                        save_score_to_db(results)
                        
                        # Move to processed
                        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                        shutil.move(filepath, os.path.join(PROCESSED_DIR, f"{timestamp}_{filename}"))
                        print(f"Successfully processed {filename}")
                    except Exception as e:
                        print(f"Error processing {filename}: {e}")
                        # Move to processed with error suffix to prevent infinite loop
                        shutil.move(filepath, os.path.join(PROCESSED_DIR, f"ERROR_{filename}"))
        except Exception as e:
            print(f"Watcher loop error: {e}")
        
        time.sleep(60)

# Start watcher in background
watcher_thread = threading.Thread(target=autoload_watcher, daemon=True)
watcher_thread.start()

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        try:
            # Check if profile is being changed
            new_profile = request.form.get('profile')
            current_profile = get_current_profile()

            if new_profile and new_profile != current_profile:
                # Profile is being switched
                set_current_profile(new_profile)
                current_profile = new_profile

            # Save weights.yaml
            with open("weights.yaml", "w") as f:
                f.write(request.form['weights_yaml'])

            # Save to the appropriate service_weights file based on current profile
            sw_filename = get_service_weights_filename(current_profile)
            with open(sw_filename, "w") as f:
                f.write(request.form['service_weights_yaml'])

            # Reload global configs
            global WEIGHTS, SERVICE_WEIGHTS, COMPENSATING
            WEIGHTS, SERVICE_WEIGHTS, COMPENSATING = load_configs()

            return redirect(url_for('settings', saved=True))
        except Exception as e:
            return render_template('settings.html', error=str(e))

    # GET
    current_profile = get_current_profile()
    available_profiles = get_available_profiles()

    try:
        with open("weights.yaml", "r") as f:
            w_content = f.read()

        # Load the service weights file for current profile
        sw_filename = get_service_weights_filename(current_profile)
        with open(sw_filename, "r") as f:
            sw_content = f.read()
    except:
        w_content = ""
        sw_content = ""

    return render_template('settings.html',
                          weights=w_content,
                          service_weights=sw_content,
                          current_profile=current_profile,
                          available_profiles=available_profiles)

@app.route('/score', methods=['GET', 'POST'])
def score_endpoint():
    db = get_db()
    
    if request.method == 'GET':
        cursor = db.cursor()
        cursor.execute('SELECT id, timestamp, overall_score, service_scores, results_json FROM scores ORDER BY timestamp ASC')
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            # We include the full results_json now for deep dives if needed
            # But to save bandwidth on the list call, we might not want the FULL json for every point
            # For now, let's just send the summary stats
            history.append({
                "timestamp": row["timestamp"],
                "overall_score": row["overall_score"],
                "service_scores": json.loads(row["service_scores"]),
                # Send the full result for the *latest* entry or handle deep retrieval separately?
                # For simplicity, let's add a separate ID-based getter or just send it all for small datasets.
                # Let's send the ID so the frontend can fetch details if needed.
                "id": row["id"]
            })
        return jsonify(history)

    elif request.method == 'POST':
        try:
            input_data = request.get_json()
            if not input_data:
                return jsonify({"error": "No JSON data provided"}), 400

            results = process_scuba_data(input_data)
            save_score_to_db(results)

            return jsonify(results)

        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/score/<int:score_id>', methods=['GET'])
def get_score_details(score_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT results_json FROM scores WHERE id = ?', (score_id,))
    row = cursor.fetchone()
    if row:
        return jsonify(json.loads(row['results_json']))
    return jsonify({"error": "Not found"}), 404

@app.route('/api/profiles/<profile_name>', methods=['GET'])
def get_profile(profile_name):
    try:
        sw_filename = get_service_weights_filename(profile_name)
        with open(sw_filename, "r") as f:
            service_weights_content = f.read()
        return jsonify({"service_weights": service_weights_content})
    except FileNotFoundError:
        return jsonify({"error": "Profile not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        input_data = request.get_json()
        if not input_data:
            return jsonify({"error": "No JSON data provided"}), 400

        results = process_scuba_data(input_data)
        save_score_to_db(results)
        return jsonify({"status": "success", "overall_score": results["overall_score"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists(DB_NAME):
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
