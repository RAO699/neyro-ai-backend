
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
