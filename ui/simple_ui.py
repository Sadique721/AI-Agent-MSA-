from flask import Flask, render_template, jsonify, render_template_string
import sqlite3
import os
import sys

# Adding project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head><title>MSA Agent UI</title></head>
<body>
<h1>MSA Agent Dashboard</h1>
<p><a href="/logs">View Logs</a></p>
<p><a href="/conversations">View Conversations</a></p>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/logs')
def logs():
    # Read log file and return last 100 lines
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/logs/app.log")
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            lines = f.readlines()[-100:]
            return jsonify({"logs": lines})
    return jsonify({"logs": []})

@app.route('/conversations')
def conversations():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/memory/msa.db")
    if not os.path.exists(db_path):
        return jsonify({"conversations": []})
        
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT timestamp, user_input, response FROM conversations ORDER BY timestamp DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()
    return jsonify({"conversations": rows})

if __name__ == '__main__':
    app.run(port=5001)
