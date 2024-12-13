import sqlite3
import requests
import jwt
import datetime
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Request latency', ['endpoint'])

def setup_logging():
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler('log/post.log', maxBytes=1024768, backupCount=3)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)    

def init_db():
    conn = sqlite3.connect('db/test.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS post
                 (id INTEGER PRIMARY KEY, title TEXT, content TEXT, userid INTEGER)''')
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
    app.logger.info("GET /metrics endpoint called")
    app.logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({'error': 'An internal error occurred'}), 500

@app.route('/metrics')
def metrics():
    app.logger.info("GET /metrics endpoint called")
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

# 토큰 생성
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if data['username'] == 'admin' and data['password'] == 'password':
        token = jwt.encode({'user': data['username'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
                           app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({'token': token})
    else:
        return jsonify({"message": "Invalid credentials"}), 401

# 보호된 경로
@app.route('/protected', methods=['GET'])
def protected():
    token = request.headers.get('Authorization').split()[1]
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return jsonify({"message": "Access granted", "user": data['user']})
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

@app.route('/post', methods=['POST'])
def post():
    app.logger.info("POST /post endpoint called")
    
    try:
        with REQUEST_LATENCY.labels(endpoint='/post').time():
            REQUEST_COUNT.labels(method=request.method, endpoint='/post').inc()
            post = request.get_json()
            app.logger.info(f"Received post: {post}")

            conn = sqlite3.connect('test.db')
            c = conn.cursor()
            c.execute("INSERT INTO post (title, content, userid) VALUES (?, ?, ?)", (post['title'], post['content'], post['userid']))
            conn.commit()
            post_id = c.lastrowid
            conn.close()
            app.logger.info(f"Post created with ID: {post_id}")

        # Notification 서비스 호출
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        response = requests.post(f'http://notification-service:5003/notify', json=post, headers=headers)
        #requests.post('http://127.0.0.1:5003/notify', json=post, headers=headers)
        app.logger.info(f"Notification sent: {response.status_code} - {response.text}")

        return jsonify({'id': post_id}), 201

    except Exception as e:
        app.logger.error(f"Error in /post endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/post/<int:id>', methods=['GET'])
def get_post(id):
    app.logger.info("POST /post/<id> endpoint called")
    
    try:
        with REQUEST_LATENCY.labels(endpoint='/post/<int:id>').time():
            REQUEST_COUNT.labels(method=request.method, endpoint='/post/<int:id>').inc()
            conn = sqlite3.connect('test.db')
            c = conn.cursor()
            c.execute("SELECT * FROM post WHERE id = ?", (id,))
            post = c.fetchone()
            conn.close()

            if post:
                post_info = {'id': post[0], 'title': post[1], 'content': post[2], 'userid': post[3]}
                app.logger.info(f"Getting post info: {post_info}")
                return jsonify(post_info)
            else:
                app.logger.warning(f"Post not found")
                return jsonify({'error': 'Post not found'}), 404

    except Exception as e:
        app.logger.error(f"Error in /post/<id> endpoint: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    setup_logging()
    init_db()
    app.run(host='0.0.0.0', port=5002, debug=True)
