import sys
import json
import hmac
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler

# ВНИМАНИЕ: Обязательно замените этот токен на НОВЫЙ, 
# так как старый был скомпрометирован в истории чата!
BOT_TOKEN = '8797210108:AAGaHi_hrmuaJwHrJHG6_UBjM00g0LV1zrE'

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Invalid JSON"}')
            return

        # 1. ЗАЩИТА: Если хеш отсутствует или пустой — жестко блокируем запрос
        if 'hash' not in data or not data['hash']:
            print("[ЗАБЛОКИРОВАНО] Попытка запроса без хэша безопасности.")
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Unauthorized: Hash missing"}')
            return

        # Создаем копию данных, чтобы не портить исходный объект при удалении хэша
        check_data = data.copy()
        received_hash = check_data.pop('hash')

        # 2. Сборка строки проверки (Data Check String) по правилам Telegram
        # Сортируем ключи по алфавиту
        keys = sorted(check_data.keys())
        data_check_string = '\n'.join([f"{k}={check_data[k]}" for k in keys])

        # 3. Вычисление валидного HMAC-SHA256 хэша
        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        # 4. Проверка совпадения хэшей
        if calc_hash == received_hash:
            print(f"[УСПЕХ] Хэш валиден для пользователя ID: {data.get('id' or 'telegram_id')}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"valid": true}')
        else:
            print(f"[ОТКЛОНЕНО] Неверный хэш безопасности для пользователя ID: {data.get('id' or 'telegram_id')}")
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"valid": false, "error": "Forbidden: Invalid hash"}')

if __name__ == '__main__':
    # Сервер слушает на всех интерфейсах (0.0.0.0) на порту 5000
    server = HTTPServer(('0.0.0.0', 5000), Handler)
    print('Hash checker listening on port 5000...')
    server.serve_forever()
