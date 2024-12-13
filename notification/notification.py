import os
import requests
import smtplib
import logging
from logging.handlers import RotatingFileHandler
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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

    file_handler = RotatingFileHandler('log/notification.log', maxBytes=1024768, backupCount=3)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)    

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

@app.route('/notify', methods=['POST'])
def notify_user():
    app.logger.info("POST /notify endpoint called")
    
    try:
        with REQUEST_LATENCY.labels(endpoint='/notify').time():
            REQUEST_COUNT.labels(method=request.method, endpoint='/notify').inc()

            data = request.get_json()
            app.logger.info(f"Received data from post API: {data}")
            
            email_server_address = os.environ.get('EMAIL_SERVER_ADDRESS','')
            email_server_from = os.environ.get('EMAIL_SERVER_FROM','')
            email_server_key = os.environ.get('EMAIL_SERVER_KEY','')
            email_server_port = os.environ.get('EMAIL_SERVER_PORT','')
            app.logger.info(f"Setting email sender info: {email_server_from}")

            # User 서비스로부터 사용자 정보 조회
            response = requests.get(f'http://user-service:5001/users/{data["userid"]}')
            #response = requests.get(f'http://127.0.0.1:5001/users/{data["userid"]}')
            if response.status_code == 200:
                user = response.json()
                app.logger.info(f"Received User info: {response.status_code} - {response.text}")
                app.logger.info(f'Sending notification to {user["email"]}: New post titled "{data["title"]}"')

                server = smtplib.SMTP(email_server_address, email_server_port)
                server.starttls()

                try:
                    server.login(email_server_from, email_server_key)
                    app.logger.info('Email Server login completed.')

                    msg = MIMEMultipart()
                    msg["From"] = email_server_from
                    msg["To"] = user["email"]
                    msg["Subject"] = data["title"]
                    msg.attach(MIMEText(data["content"], 'plain'))

                    server.sendmail(email_server_from, user["email"], msg.as_string())
                    app.logger.info('Email Sent')

                    return jsonify({'message': 'Notification sent'}), 200

                except smtplib.SMTPAuthenticationError as e:
                    app.logger.error(f"Error in smtp authentication error: {e}")
                    return jsonify({'error': 'Email Server not valid'}), 404

            else:
                app.logger.warning(f"User not found")
                return jsonify({'error': 'User not found'}), 404

    except Exception as e:
        app.logger.error(f"Error in /notify endpoint: {e}")
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    setup_logging()
    app.run(host='0.0.0.0', port=5003, debug=True)

