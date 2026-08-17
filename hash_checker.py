import sys
import json
import hmac
import hashlib
import os
import base64
import time as time_module
import random
from http.server import HTTPServer, BaseHTTPRequestHandler

# ===== КОНФИГУРАЦИЯ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ =====
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
JWT_SECRET = os.environ.get('JWT_SECRET', '')
BEPAID_MARKET_KEY = os.environ.get('BEPAID_MARKET_KEY', '')

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
SENDGRID_FROM = os.environ.get('SENDGRID_FROM', '')

if not BOT_TOKEN or not JWT_SECRET:
    raise RuntimeError("BOT_TOKEN and JWT_SECRET must be set in environment variables")

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Empty body"}')
            return

        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
        except:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Invalid JSON"}')
            return

        if self.path == '/verify-telegram':
            self.verify_telegram(data)
        elif self.path == '/verify-bepaid':
            self.verify_bepaid(data)
        elif self.path == '/hash-password':
            self.hash_password(data)
        elif self.path == '/verify-password':
            self.verify_password(data)
        elif self.path == '/generate-token':
            self.generate_token(data)
        elif self.path == '/verify-token':
            self.verify_token(data)
        elif self.path == '/request-reset':
            self.request_reset(data)
        elif self.path == '/confirm-reset':
            self.confirm_reset(data)
        elif self.path == '/health':
            self.health_check()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not found"}')

    def health_check(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    # --- Проверка хеша Telegram ---
    def verify_telegram(self, data):
        if 'hash' not in data or not data['hash']:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Hash missing"}')
            return

        received_hash = data.pop('hash')
        keys = sorted(data.keys())
        data_check_string = '\n'.join([f"{k}={data[k]}" for k in keys])
        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if hmac.compare_digest(calc_hash, received_hash):
            auth_date = int(data.get('auth_date', 0))
            if auth_date == 0 or time_module.time() - auth_date > 86400:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"valid": false, "error": "Auth date expired"}')
                return

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"valid": true}')
        else:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Invalid hash"}')

    # --- Проверка подписи bePaid ---
    def verify_bepaid(self, data):
        if not BEPAID_MARKET_KEY:
            self.send_response(501)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "bePaid not configured"}')
            return

        if 'signature' not in data:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Signature missing"}')
            return

        received_signature = data.pop('signature')
        keys = sorted(data.keys())
        string_to_sign = '&'.join([f"{k}={data[k]}" for k in keys])
        calc_signature = hmac.new(BEPAID_MARKET_KEY.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()

        if hmac.compare_digest(calc_signature, received_signature):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"valid": true}')
        else:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Invalid signature"}')

    # --- Хеширование пароля ---
    def hash_password(self, data):
        password = data.get('password')
        if not password:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Password is required"}')
            return

        if len(password) < 8:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Password must be at least 8 characters"}')
            return

        salt = os.urandom(32).hex()
        hashed = hashlib.pbkdf2_hmac('sha512', password.encode(), salt.encode(), 600000)
        password_hash = salt + ':' + hashed.hex() + ':600000'

        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"passwordHash": password_hash}).encode())

    # --- Проверка пароля ---
    def verify_password(self, data):
        password = data.get('password')
        stored_hash = data.get('storedHash')
        if not password or not stored_hash:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Password and storedHash are required"}')
            return

        try:
            parts = stored_hash.split(':')
            if len(parts) == 3:
                salt, original_hash, iterations = parts
                iterations = int(iterations)
            elif len(parts) == 2:
                salt, original_hash = parts
                iterations = 100000
            else:
                raise ValueError("Invalid hash format")
        except:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid storedHash format"}')
            return

        hashed = hashlib.pbkdf2_hmac('sha512', password.encode(), salt.encode(), iterations)

        if hmac.compare_digest(hashed.hex(), original_hash):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"valid": true}')
        else:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Invalid password"}')

    # --- Генерация JWT-токена ---
    def generate_token(self, data):
        user_id = data.get('userId')
        if not user_id:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "userId is required"}')
            return

        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "userId": user_id,
            "iat": int(time_module.time()),
            "exp": int(time_module.time()) + 2592000
        }

        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=').decode()
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode()

        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()

        token = f"{message}.{signature_b64}"

        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"token": token, "userId": user_id}).encode())

    # --- Проверка JWT-токена ---
    def verify_token(self, data):
        token = data.get('token', '')
        if not token:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Token required"}')
            return

        try:
            parts = token.split('.')
            if len(parts) != 3:
                raise ValueError("Invalid token format")

            header_b64, payload_b64, signature_b64 = parts

            payload_b64_padded = payload_b64 + '=' * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64_padded).decode())

            if payload.get('exp', 0) < time_module.time():
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"valid": false, "error": "Token expired"}')
                return

            message = f"{header_b64}.{payload_b64}"
            calc_signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
            calc_signature_b64 = base64.urlsafe_b64encode(calc_signature).rstrip(b'=').decode()

            if hmac.compare_digest(calc_signature_b64, signature_b64):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"valid": True, "userId": payload['userId']}).encode())
            else:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'{"valid": false, "error": "Invalid signature"}')

        except Exception as e:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(json.dumps({"valid": false, "error": str(e)}).encode())

    # --- Отправка email через SendGrid ---
    def send_email(self, to_email, subject, body):
        import urllib.request as urllib2
        
        payload = json.dumps({
            "personalizations": [{
                "to": [{"email": to_email}]
            }],
            "from": {"email": SENDGRID_FROM},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}]
        }).encode('utf-8')
        
        req = urllib2.Request('https://api.sendgrid.com/v3/mail/send', data=payload, method='POST')
        req.add_header('Authorization', 'Bearer ' + SENDGRID_API_KEY)
        req.add_header('Content-Type', 'application/json')
        
        urllib2.urlopen(req, timeout=15)

    # --- Запрос на восстановление пароля ---
    def request_reset(self, data):
        email = data.get('email', '')
        if not email:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Email required"}')
            return

        if not SENDGRID_API_KEY:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error": "SendGrid not configured"}')
            return

        code = str(random.randint(100000, 999999))

        with open('/tmp/reset_codes.txt', 'a') as f:
            f.write(f"{email}:{code}:{int(time_module.time())}\n")

        try:
            self.send_email(email, 'NeyroAI — Код восстановления', f'Ваш код: {code}')
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    # --- Подтверждение кода и смена пароля ---
    def confirm_reset(self, data):
        email = data.get('email', '')
        code = data.get('code', '')
        new_password = data.get('password', '')
        
        if not email or not code or not new_password:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Email, code and password required"}')
            return
        
        # Проверяем код
        valid = False
        try:
            with open('/tmp/reset_codes.txt', 'r') as f:
                lines = f.readlines()
            for line in lines:
                parts = line.strip().split(':')
                if len(parts) >= 3:
                    stored_email, stored_code, stored_time = parts[0], parts[1], int(parts[2])
                    if stored_email == email and stored_code == code:
                        if time_module.time() - stored_time <= 900:
                            valid = True
                        break
        except:
            pass
        
        if not valid:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Invalid or expired code"}')
            return
        
        # Хешируем новый пароль
        if len(new_password) < 8:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Password must be at least 8 characters"}')
            return
        
        salt = os.urandom(32).hex()
        hashed = hashlib.pbkdf2_hmac('sha512', new_password.encode(), salt.encode(), 600000)
        password_hash = salt + ':' + hashed.hex() + ':600000'
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"passwordHash": password_hash}).encode())


if __name__ == '__main__':
    print(f'Verification service starting on port 5000...')
    print(f'BOT_TOKEN: {"set" if BOT_TOKEN else "NOT SET"}')
    print(f'JWT_SECRET: {"set" if JWT_SECRET else "NOT SET"}')
    print(f'SendGrid: {"configured" if SENDGRID_API_KEY else "NOT SET"}')
    server = HTTPServer(('0.0.0.0', 5000), RequestHandler)
    print('Verification service listening on port 5000...')
    server.serve_forever()
