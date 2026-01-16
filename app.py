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

# Configuration from environment variables with sensible defaults
DB_NAME = os.getenv("DB_NAME", "scubascore.db")
AUTOLOAD_DIR = os.getenv("AUTOLOAD_DIR", "autoload")
PROCESSED_DIR = os.path.join(AUTOLOAD_DIR, "processed")
WATCHER_INTERVAL = int(os.getenv("WATCHER_INTERVAL", "60"))
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

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
def load_configs():
    try:
        w = scubascore.load_yaml("weights.yaml")
        sw = scubascore.load_yaml("service_weights.yaml")
        c = scubascore.load_yaml("compensating.yaml")
        return w, sw, c
    except Exception as e:
        print(f"Warning: Config load failed: {e}")
        return {}, {}, {}

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

        time.sleep(WATCHER_INTERVAL)

# Start watcher in background
watcher_thread = threading.Thread(target=autoload_watcher, daemon=True)
watcher_thread.start()

# --- Routes ---

@app.route('/')
def index():
    """
    Serve the main dashboard page.

    Returns:
        Rendered index.html template showing the SCuBA score dashboard.
    """
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """
    Manage scoring configuration (weights and service weights).

    GET: Display current weights.yaml and service_weights.yaml content in editable form.
    POST: Save updated configuration files and reload global config variables.

    Returns:
        GET: Rendered settings.html with current config content.
        POST: Redirect to settings page on success, or error page on failure.
    """
    if request.method == 'POST':
        try:
            with open("weights.yaml", "w") as f:
                f.write(request.form['weights_yaml'])
            with open("service_weights.yaml", "w") as f:
                f.write(request.form['service_weights_yaml'])
            
            # Reload global configs
            global WEIGHTS, SERVICE_WEIGHTS, COMPENSATING
            WEIGHTS, SERVICE_WEIGHTS, COMPENSATING = load_configs()
            
            return redirect(url_for('settings', saved=True))
        except Exception as e:
            return render_template('settings.html', error=str(e))
            
    # GET
    try:
        with open("weights.yaml", "r") as f:
            w_content = f.read()
        with open("service_weights.yaml", "r") as f:
            sw_content = f.read()
    except:
        w_content = ""
        sw_content = ""
        
    return render_template('settings.html', weights=w_content, service_weights=sw_content)

@app.route('/score', methods=['GET', 'POST'])
def score_endpoint():
    """
    Retrieve score history or submit new SCuBA results for scoring.

    GET: Fetch all historical scores with timestamps, overall scores, service scores, and IDs.
    POST: Process submitted SCuBA JSON data, compute scores, save to database, and return results.

    Returns:
        GET: JSON array of score history entries ordered by timestamp.
        POST: JSON object with computed scores and top failures, or error with 400/500 status.
    """
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
    """
    Retrieve detailed results for a specific score by ID.

    Args:
        score_id: Database ID of the score record to retrieve.

    Returns:
        JSON object with full scoring results including per-service details and top failures,
        or error message with 404 status if not found.
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT results_json FROM scores WHERE id = ?', (score_id,))
    row = cursor.fetchone()
    if row:
        return jsonify(json.loads(row['results_json']))
    return jsonify({"error": "Not found"}), 404

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook endpoint for external systems to submit SCuBA results.

    Accepts JSON SCuBA data, processes it, saves scores to database, and returns
    a success status with the overall score. Designed for automated integrations.

    Returns:
        JSON object with status "success" and overall_score on success,
        or error message with 400/500 status on failure.
    """
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
    app.run(debug=FLASK_DEBUG, host=FLASK_HOST, port=FLASK_PORT)
