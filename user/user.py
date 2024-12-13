import sqlite3
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest

app = Flask(__name__)

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Request latency', ['endpoint'])

def setup_logging():
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler('log/user.log', maxBytes=1024768, backupCount=3)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)    

def init_db():
    conn = sqlite3.connect('db/test.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT)''')
    conn.commit()
    conn.close()

@app.before_request
def log_request_info():
    app.logger.info(f"Request: {request.method} {request.path} - Headers: {dict(request.headers)} - Body: {request.get_data(as_text=True)}")

@app.after_request
def log_response_info(response):
    app.logger.info(f"Response: {response.status_code} - {response.get_data(as_text=True)}")
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({'error': 'An internal error occurred'}), 500

@app.route('/metrics')
def metrics():
    app.logger.info("GET /metrics endpoint called")
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/users', methods=['POST'])
def create_user():
    app.logger.info("POST /users endpoint called")
    
    try:
        with REQUEST_LATENCY.labels(endpoint='/users').time():
            REQUEST_COUNT.labels(method=request.method, endpoint='/users').inc()
            user = request.get_json()
            app.logger.info(f"Received user: {user}")
            
            conn = sqlite3.connect('test.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (name, email) VALUES (?, ?)", (user['name'], user['email']))
            conn.commit()
            user_id = c.lastrowid
            conn.close()
            app.logger.info(f"User created with ID: {user_id}")
            
            return jsonify({'id': user_id}), 201
        
    except Exception as e:
        app.logger.error(f"Error in /users endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/users/<int:id>', methods=['GET'])
def get_user(id):
    app.logger.info("GET /users/<id> endpoint called")
    
    try:
        with REQUEST_LATENCY.labels(endpoint='/users/<int:id>').time():
            REQUEST_COUNT.labels(method=request.method, endpoint='/users/<int:id>').inc()
            conn = sqlite3.connect('test.db')
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (id,))
            user = c.fetchone()
            conn.close()

            if user:
                user_info = {'id': user[0], 'name': user[1], 'email': user[2]}
                app.logger.info(f"Getting user info: {user_info}")
                return jsonify(user_info)
            else:
                app.logger.warning(f"User not found")
                return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Error in /users/<id> endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/users', methods=['GET'])
def get_all_users():
    app.logger.info("GET /users endpoint called")
    
    try:
        with REQUEST_LATENCY.labels(endpoint='/users').time():
            REQUEST_COUNT.labels(method=request.method, endpoint='/users').inc()
            conn = sqlite3.connect('test.db')
            c = conn.cursor()
            c.execute("SELECT * FROM users")
            users = c.fetchall()
            conn.close()
            
            app.logger.info(f"Getting users count: {len(users)}")
            return jsonify([{'id': row[0], 'name': row[1], 'email': row[2]} for row in users])

    except Exception as e:
        app.logger.error(f"Error in /users endpoint: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    setup_logging()
    init_db()
    app.run(host='0.0.0.0', port=5001)
