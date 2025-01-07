# app.py

from flask import Flask, request, jsonify
import httpx
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FAFA_BASE_URL = 'https://m.fafa138xxx.com'

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    register_data = {
        'account': data.get('username'),
        'password': data.get('password'),
        'tel': data.get('ph_number'),
        'currency': 1,
        'referral': '',
        'type': 'ajax'
    }

    try:
        with httpx.Client(follow_redirects=True) as client:
            register_response = client.post(f"{FAFA_BASE_URL}/register_submitter", data=register_data)
        
        if register_response.status_code == 200:
            # Login after successful registration
            login_data = {
                'user': data.get('username'),
                'password': data.get('password'),
                'auto': '',
                'accept': 'json',
                'lang_path': 'lang/855test/kh'
            }
            with httpx.Client(follow_redirects=True) as client:
                login_response = client.post(f"{FAFA_BASE_URL}/login_submitter", data=login_data)
                session_cookie = login_response.cookies.get('PHPSESSID')

            # Return the session cookie in the response if available
            if session_cookie:
                return jsonify({'message': 'Registration and login successful', 'PHPSESSID': session_cookie}), 200
            else:
                return jsonify({'message': 'Login successful, but session cookie not found'}), 400

    except Exception as e:
        logger.error(f"Error during registration or login: {e}")
        return jsonify({'message': 'Error during registration or login'}), 500

    return jsonify({'message': 'Registration or login failed'}), 400

if __name__ == "__main__":
    app.run(port=5000)
