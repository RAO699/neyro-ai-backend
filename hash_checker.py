import sys
import json
import hmac
import hashlib
import os
import base64
import time as time_module
import random
import secrets
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
    # Ограничение попыток ввода кодов
    code_attempts = {}
    MAX_ATTEMPTS = 5
    ATTEMPT_WINDOW = 600  # 10 минут

    # Ограничение частоты отправки кодов
    send_attempts = {}
    SEND_INTERVAL = 60  # секунд между отправками

    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', 'https://neyro.by')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')

    def _send_response(self, status_code, body):
        self.send_response(status_code)
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)

    def _check_code_attempts(self, email):
        """Проверяет, не превышен ли лимит попыток ввода кода."""
        now = time_module.time()
        attempts = self.code_attempts.get(email, [])
        attempts = [t for t in attempts if now - t < self.ATTEMPT_WINDOW]
        self.code_attempts[email] = attempts
        return len(attempts) < self.MAX_ATTEMPTS

    def _register_code_attempt(self, email):
        """Фиксирует неудачную попытку ввода кода."""
        now = time_module.time()
        attempts = self.code_attempts.get(email, [])
        attempts = [t for t in attempts if now - t < self.ATTEMPT_WINDOW]
        attempts.append(now)
        self.code_attempts[email] = attempts

    def _reset_code_attempts(self, email):
        """Сбрасывает попытки после успешного ввода."""
        self.code_attempts[email] = []

    def _check_send_attempts(self, email):
        """Проверяет, можно ли отправить код повторно."""
        now = time_module.time()
        last = self.send_attempts.get(email, 0)
        return (now - last) >= self.SEND_INTERVAL

    def _register_send_attempt(self, email):
        """Фиксирует отправку кода."""
        self.send_attempts[email] = time_module.time()

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._send_response(400, '{"valid": false, "error": "Empty body"}')
            return

        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
        except:
            self._send_response(400, '{"valid": false, "error": "Invalid JSON"}')
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
        elif self.path == '/verify-reset-code':
            self.verify_reset_code(data)
        elif self.path == '/send-verification-code':
            self.send_verification_code(data)
        elif self.path == '/verify-email-code':
            self.verify_email_code(data)
        elif self.path == '/send-welcome-email':
            self.send_welcome_email(data)
        elif self.path == '/health':
            self.health_check()
        else:
            self._send_response(404, '{"error": "Not found"}')

    def health_check(self):
        self._send_response(200, '{"status": "ok"}')

    def verify_telegram(self, data):
        if 'hash' not in data or not data['hash']:
            self._send_response(401, '{"valid": false, "error": "Hash missing"}')
            return

        received_hash = data.pop('hash')
        keys = sorted(data.keys())
        data_check_string = '\n'.join([f"{k}={data[k]}" for k in keys])
        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if hmac.compare_digest(calc_hash, received_hash):
            auth_date = int(data.get('auth_date', 0))
            if auth_date == 0 or time_module.time() - auth_date > 86400:
                self._send_response(401, '{"valid": false, "error": "Auth date expired"}')
                return
            self._send_response(200, '{"valid": true}')
        else:
            self._send_response(403, '{"valid": false, "error": "Invalid hash"}')

    def verify_bepaid(self, data):
        if not BEPAID_MARKET_KEY:
            self._send_response(501, '{"valid": false, "error": "bePaid not configured"}')
            return
        if 'signature' not in data:
            self._send_response(401, '{"valid": false, "error": "Signature missing"}')
            return

        received_signature = data.pop('signature')
        keys = sorted(data.keys())
        string_to_sign = '&'.join([f"{k}={data[k]}" for k in keys])
        calc_signature = hmac.new(BEPAID_MARKET_KEY.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()

        if hmac.compare_digest(calc_signature, received_signature):
            self._send_response(200, '{"valid": true}')
        else:
            self._send_response(403, '{"valid": false, "error": "Invalid signature"}')

    def hash_password(self, data):
        password = data.get('password')
        if not password:
            self._send_response(400, '{"error": "Password is required"}')
            return
        if len(password) < 8:
            self._send_response(400, '{"error": "Password must be at least 8 characters"}')
            return

        salt = os.urandom(32).hex()
        hashed = hashlib.pbkdf2_hmac('sha512', password.encode(), salt.encode(), 600000)
        password_hash = salt + ':' + hashed.hex() + ':600000'
        self._send_response(200, json.dumps({"passwordHash": password_hash}))

    def verify_password(self, data):
        password = data.get('password')
        stored_hash = data.get('storedHash')
        if not password or not stored_hash:
            self._send_response(400, '{"error": "Password and storedHash are required"}')
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
            self._send_response(400, '{"error": "Invalid storedHash format"}')
            return

        hashed = hashlib.pbkdf2_hmac('sha512', password.encode(), salt.encode(), iterations)
        if hmac.compare_digest(hashed.hex(), original_hash):
            self._send_response(200, '{"valid": true}')
        else:
            self._send_response(403, '{"valid": false, "error": "Invalid password"}')

    def generate_token(self, data):
        user_id = data.get('userId')
        if not user_id:
            self._send_response(400, '{"error": "userId is required"}')
            return

        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "userId": user_id,
            "iat": int(time_module.time()),
            "exp": int(time_module.time()) + 2592000
        }

        header_b64 = base64.urlsafe_b64encode(json.dumps(header, separators=(',', ':')).encode()).rstrip(b'=').decode()
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).rstrip(b'=').decode()

        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()

        token = f"{message}.{signature_b64}"
        self._send_response(200, json.dumps({"token": token, "userId": user_id}))

    def verify_token(self, data):
        token = data.get('token', '')
        if not token:
            self._send_response(401, '{"valid": false, "error": "Token required"}')
            return

        try:
            parts = token.split('.')
            if len(parts) != 3:
                raise ValueError("Invalid token format")
            header_b64, payload_b64, signature_b64 = parts
            payload_b64_padded = payload_b64 + '=' * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64_padded).decode())
            if payload.get('exp', 0) < time_module.time():
                self._send_response(401, '{"valid": false, "error": "Token expired"}')
                return

            message = f"{header_b64}.{payload_b64}"
            calc_signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
            calc_signature_b64 = base64.urlsafe_b64encode(calc_signature).rstrip(b'=').decode()

            if hmac.compare_digest(calc_signature_b64, signature_b64):
                self._send_response(200, json.dumps({"valid": True, "userId": payload['userId']}))
            else:
                self._send_response(403, '{"valid": false, "error": "Invalid signature"}')
        except Exception as e:
            self._send_response(401, json.dumps({"valid": false, "error": str(e)}))

    def send_email(self, to_email, subject, body):
        import urllib.request as urllib2
        payload = json.dumps({
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": SENDGRID_FROM},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}]
        }).encode('utf-8')

        req = urllib2.Request('https://api.sendgrid.com/v3/mail/send', data=payload, method='POST')
        req.add_header('Authorization', 'Bearer ' + SENDGRID_API_KEY)
        req.add_header('Content-Type', 'application/json')
        urllib2.urlopen(req, timeout=15)

    def request_reset(self, data):
        email = data.get('email', '')
        if not email:
            self._send_response(400, '{"error": "Email required"}')
            return

        if not self._check_send_attempts(email):
            self._send_response(429, '{"error": "Please wait before requesting a new code"}')
            return

        if not SENDGRID_API_KEY:
            self._send_response(500, '{"error": "SendGrid not configured"}')
            return

        code = str(secrets.randbelow(900000) + 100000)

        with open('/tmp/reset_codes.txt', 'a') as f:
            f.write(f"{email}:{code}:{int(time_module.time())}\n")

        try:
            self.send_email(email, 'NeyroAI — Код восстановления', f'Ваш код: {code}')
            self._register_send_attempt(email)
            self._send_response(200, '{"status": "ok"}')
        except Exception as e:
            self._send_response(500, json.dumps({"error": str(e)}))

    def confirm_reset(self, data):
        email = data.get('email', '')
        code = data.get('code', '')
        new_password = data.get('password', '')

        if not email or not code or not new_password:
            self._send_response(400, '{"error": "Email, code and password required"}')
            return

        if not self._check_code_attempts(email):
            self._send_response(429, '{"valid": false, "error": "Too many attempts. Try again later"}')
            return

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
            self._register_code_attempt(email)
            self._send_response(403, '{"valid": false, "error": "Invalid or expired code"}')
            return

        if len(new_password) < 8:
            self._send_response(400, '{"error": "Password must be at least 8 characters"}')
            return

        salt = os.urandom(32).hex()
        hashed = hashlib.pbkdf2_hmac('sha512', new_password.encode(), salt.encode(), 600000)
        password_hash = salt + ':' + hashed.hex() + ':600000'

        self._reset_code_attempts(email)
        self._send_response(200, json.dumps({"passwordHash": password_hash}))

    def verify_reset_code(self, data):
        email = data.get('email', '')
        code = data.get('code', '')

        if not email or not code:
            self._send_response(400, '{"valid": false, "error": "Email and code required"}')
            return

        if not self._check_code_attempts(email):
            self._send_response(429, '{"valid": false, "error": "Too many attempts. Try again later"}')
            return

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

        if valid:
            self._reset_code_attempts(email)
            self._send_response(200, '{"valid": true}')
        else:
            self._register_code_attempt(email)
            self._send_response(403, '{"valid": false, "error": "Invalid or expired code"}')

    def send_verification_code(self, data):
        email = data.get('email', '')
        if not email:
            self._send_response(400, '{"error": "Email required"}')
            return

        if not self._check_send_attempts(email):
            self._send_response(429, '{"error": "Please wait before requesting a new code"}')
            return

        if not SENDGRID_API_KEY:
            self._send_response(500, '{"error": "SendGrid not configured"}')
            return

        code = str(secrets.randbelow(900000) + 100000)

        with open('/tmp/verification_codes.txt', 'a') as f:
            f.write(f"{email}:{code}:{int(time_module.time())}\n")

        try:
            self.send_email(email, 'NeyroAI — Подтверждение email', f'Ваш код подтверждения: {code}')
            self._register_send_attempt(email)
            self._send_response(200, '{"status": "sent"}')
        except Exception as e:
            self._send_response(500, json.dumps({"error": str(e)}))

    def verify_email_code(self, data):
        email = data.get('email', '')
        code = data.get('code', '')

        if not email or not code:
            self._send_response(400, '{"valid": false, "error": "Email and code required"}')
            return

        if not self._check_code_attempts(email):
            self._send_response(429, '{"valid": false, "error": "Too many attempts. Try again later"}')
            return

        valid = False
        try:
            with open('/tmp/verification_codes.txt', 'r') as f:
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

        if valid:
            self._reset_code_attempts(email)
            self._send_response(200, '{"valid": true}')
        else:
            self._register_code_attempt(email)
            self._send_response(403, '{"valid": false, "error": "Invalid or expired code"}')

    def send_welcome_email(self, data):
        email = data.get('email', '')
        username = data.get('username', '')
        if not email:
            self._send_response(200, '{"status": "skipped", "reason": "No email"}')
            return
        try:
            self.send_email(
                email,
                'Добро пожаловать в NeyroAI!',
                f'Здравствуйте, {username}!\n\n'
                f'Ваш аккаунт успешно создан.\n'
                f'Вам начислено 10 кредитов для генерации изображений.\n\n'
                f'Приятного использования!'
            )
            self._send_response(200, '{"status": "sent"}')
        except Exception as e:
            self._send_response(500, json.dumps({"error": str(e)}))


if __name__ == '__main__':
    print(f'Verification service starting on port 5000...')
    print(f'BOT_TOKEN: {"set" if BOT_TOKEN else "NOT SET"}')
    print(f'JWT_SECRET: {"set" if JWT_SECRET else "NOT SET"}')
    print(f'SendGrid: {"configured" if SENDGRID_API_KEY else "NOT SET"}')
    server = HTTPServer(('0.0.0.0', 5000), RequestHandler)
    print('Verification service listening on port 5000...')
    server.serve_forever()
