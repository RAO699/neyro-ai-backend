# 🎨 NeyroAI — AI Image Generation Platform / Платформа генерации изображений с ИИ

> Коммерческий сервис генерации изображений для Беларуси. FLUX.1, SDXL Lightning, апскейл 4K, удаление фона, редактирование объектов, оплата через ЕРИП.

---

## 🌍 Overview / Обзор

**NeyroAI** — это коммерческий сервис генерации изображений с полной монетизацией для рынка Беларуси. Платформа предоставляет пользователям доступ к передовым AI-моделям для создания, редактирования и улучшения изображений с удобной оплатой через ЕРИП, банковскую карту или Telegram бота.

**NeyroAI** is a commercial image generation service with full monetization for the Belarusian market. The platform provides users access to advanced AI models for creating, editing, and enhancing images with convenient payment via ERIP, bank card, or Telegram bot.

---

## 🏗️ Architecture / Архитектура

├── ai-assistant/ # Frontend / Фронтенд
│ ├── index.html # SPA приложение
│ └── generated/ # Готовые изображения
├── nginx.conf # Прокси, rate limiting, CORS
├── docker-compose.yml # Docker оркестрация
├── hash_checker.py # Python микросервис безопасности
├── backup.sh # Бэкап БД
├── cleanup.sh # Очистка файлов
├── .env.example # Шаблон переменных
└── README.md # Документация

---

## 🚀 Deployment / Развертывание

### Requirements / Требования:
- Docker + Docker Compose
- Domain name / Доменное имя
- SSL certificates / SSL сертификаты
- API keys: Together, Replicate, Fal.ai, Groq, SendGrid

### Installation / Установка:

```bash
# 1. Clone repository / Клонировать репозиторий
git clone git@github.com:RAO699/neyro-ai-backend.git
cd neyro-ai-backend

# 2. Configure variables / Настроить переменные
cp .env.example .env
nano .env

# 3. Generate JWT secret / Сгенерировать JWT секрет
openssl rand -hex 32

# 4. Start / Запустить
docker compose up -d

# 5. Telegram webhook
curl -X POST "https://api.telegram.org/botТОКЕН/setWebhook" \
  -d "url=https://api.neyro.by/webhook/telegram"

# 6. Cron
crontab -e
# 30 3 * * * /path/to/backup.sh
# 0 4 * * * /path/to/cleanup.sh

📝 Environment Variables / Переменные окружения
Переменная / Variable	Описание / Description
POSTGRES_DB	Database name / Имя БД
POSTGRES_USER	DB user / Пользователь БД
POSTGRES_PASSWORD	DB password / Пароль БД
JWT_SECRET	JWT secret (32 bytes)
TELEGRAM_BOT_TOKEN	Telegram bot token
N8N_CRYPTO_KEY	n8n encryption key
SENDGRID_API_KEY	SendGrid API key
SENDGRID_FROM	Sender email / Email отправителя
DOMAIN_NAME	Domain / Домен
🎯 Features / Функции
Generation / Генерация:
⚡ FLUX.1-schnell — 3 sec, 1 credit

💎 FLUX.2 Pro Ultra — 5 sec, 3 credits

🎨 SDXL Lightning — 5 sec, 1 credit

Editing / Редактирование:
✏️ Object replacement / Замена объекта

🫧 Background removal / Удаление фона

Enhancement / Улучшение:
🔍 4K Upscale / Апскейл 4K

Authorization / Авторизация:
📧 Email + password

🤖 Telegram widget

🔗 Telegram linking / Привязка Telegram

📈 Monitoring / Мониторинг
Command / Команда	Description / Описание
docker compose ps	Container status / Статус контейнеров
docker logs pipeline_n8n --tail 20	n8n logs
docker exec pipeline_n8n tail -f /home/node/.n8n/n8n.log	Live logs
docker logs pipeline_hashchecker	Hash-checker logs
🔧 Technical Details / Технические детали
Network / Сеть:
private_net — internal network / внутренняя сеть

Port 443 — static + API / статика + API

Port 8443 — n8n editor / редактор n8n

Backups / Бэкапы:
Daily at 3:30 Minsk time / Ежедневно в 3:30 по Минску

30 days retention / Хранение 30 дней

Format: backup_YYYYMMDD_HHMMSS.sql.gz

Cleanup / Очистка:
Daily at 4:00 / Ежедневно в 4:00

Files older than 7 days / Файлы старше 7 дней

📄 License / Лицензия
Private. All rights reserved. / Частная. Все права защищены.

📞 Contacts / Контакты
Channel / Канал	Link / Ссылка
Website / Сайт	https://neyro.by
Telegram Bot	@n8n_integration_ai_bot
Email	111rao111@gmail.com
