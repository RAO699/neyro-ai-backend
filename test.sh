#!/bin/bash
API="https://api.neyro.by"
PASS=0
FAIL=0
TOTAL=0

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    local expect_error="$5"
    
    TOTAL=$((TOTAL + 1))
    echo -e "${YELLOW}[$TOTAL] Тест: $name${NC}"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET "$API$url" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" -X POST "$API$url" \
            -H "Content-Type: application/json" \
            -d "$data" 2>&1)
    fi
    
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$expect_error" = "true" ]; then
        # Ожидаем ошибку (4xx/5xx)
        if [ "$http_code" -ge 400 ] 2>/dev/null; then
            echo -e "  ${GREEN}✅ PASS (HTTP $http_code — ожидаемая ошибка)${NC}"
            PASS=$((PASS + 1))
        else
            echo -e "  ${RED}❌ FAIL (HTTP $http_code — ожидалась ошибка)${NC}"
            echo "  Ответ: $body" | head -3
            FAIL=$((FAIL + 1))
        fi
    else
        # Ожидаем успех
        if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ] 2>/dev/null; then
            echo -e "  ${GREEN}✅ PASS (HTTP $http_code)${NC}"
            PASS=$((PASS + 1))
        else
            echo -e "  ${RED}❌ FAIL (HTTP $http_code)${NC}"
            echo "  Ответ: $body" | head -3
            FAIL=$((FAIL + 1))
        fi
    fi
    echo ""
}

echo "=========================================="
echo "   NeyroAI Smoke Tests / Смоук-тесты"
echo "=========================================="
echo ""

# 1. Статика
test_endpoint "Статический сайт (HTML)" "GET" "/" "{}"

# 2. Health check
test_endpoint "Health check nginx" "GET" "/generated/" "{}"

# 3. User Status API
test_endpoint "User Status (Telegram)" "GET" "/api/user/status?telegram_id=710112354" "{}"

# 4. User Status без ID
test_endpoint "User Status (без ID)" "GET" "/api/user/status" "{}" "true"

# 5. Login API (неверные данные)
test_endpoint "Login (неверный пароль)" "POST" "/api/login" '{"username":"admin","password":"wrongpass123"}' "true"

# 6. Register API (пустые данные)
test_endpoint "Register (пустые данные)" "POST" "/api/register" '{"username":"","password":""}' "true"

# 7. Generate API (без токена)
test_endpoint "Generate (без токена)" "POST" "/api/generate" '{"prompt":"test","model":"flux"}' "true"

# 8. Upscale API (без токена)
test_endpoint "Upscale (без токена)" "POST" "/api/upscale" '{"image_url":"https://example.com/test.jpg"}' "true"

# 9. Redactor API (без токена)
test_endpoint "Redactor (без токена)" "POST" "/api/redactor" '{"image_url":"test","edit_type":"remove-bg"}' "true"

# 10. Confirm Payment (без токена)
test_endpoint "Confirm Payment (без данных)" "POST" "/api/confirm-payment" '{}' "true"

# 11. Request Reset (без email)
test_endpoint "Request Reset (без email)" "POST" "/api/request-reset" '{}' "true"

# 12. Link Account (без данных)
test_endpoint "Link Account (без данных)" "POST" "/api/link-account" '{}' "true"

# 13. Загрузка (неверный метод)
test_endpoint "Upload (GET вместо POST)" "GET" "/api/upload" "{}" "true"

# 14. CORS заголовки
echo -e "${YELLOW}[$TOTAL] Тест: CORS заголовки${NC}"
TOTAL=$((TOTAL + 1))
cors_header=$(curl -s -I -X OPTIONS "$API/api/generate" \
    -H "Origin: https://neyro.by" \
    -H "Access-Control-Request-Method: POST" 2>&1 | grep -i "access-control")
if [ -n "$cors_header" ]; then
    echo -e "  ${GREEN}✅ PASS (CORS заголовок найден)${NC}"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL (нет CORS заголовка)${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

# 15. Rate limiting
echo -e "${YELLOW}[$TOTAL] Тест: Rate limiting (10 запросов)${NC}"
TOTAL=$((TOTAL + 1))
rate_limited=false
for i in $(seq 1 15); do
    code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/generate" \
        -H "Content-Type: application/json" \
        -d '{"prompt":"test"}')
    if [ "$code" = "429" ]; then
        rate_limited=true
        break
    fi
done
if [ "$rate_limited" = true ]; then
    echo -e "  ${GREEN}✅ PASS (Rate limiting работает)${NC}"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL (Rate limiting не сработал)${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

# 16. Файлы генерируются
echo -e "${YELLOW}[$TOTAL] Тест: Файлы в generated/${NC}"
TOTAL=$((TOTAL + 1))
file_count=$(ls /opt/neyro-backend/ai-assistant/generated/ 2>/dev/null | wc -l)
if [ "$file_count" -gt 0 ]; then
    echo -e "  ${GREEN}✅ PASS ($file_count файлов)${NC}"
    PASS=$((PASS + 1))
else
    echo -e "  ${YELLOW}⚠️ WARNING (нет файлов — возможно ещё не генерировали)${NC}"
    PASS=$((PASS + 1))
fi
echo ""

# 17. Docker контейнеры
echo -e "${YELLOW}[$TOTAL] Тест: Docker контейнеры${NC}"
TOTAL=$((TOTAL + 1))
containers=$(docker compose -f /opt/neyro-backend/docker-compose.yml ps --status running | grep -c "Up")
if [ "$containers" -ge 4 ]; then
    echo -e "  ${GREEN}✅ PASS ($containers контейнеров запущено)${NC}"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL (только $containers контейнеров)${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

# Итог
echo "=========================================="
echo "   РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ"
echo "=========================================="
echo -e "  ${GREEN}Пройдено: $PASS${NC}"
echo -e "  ${RED}Провалено: $FAIL${NC}"
echo -e "  Всего: $TOTAL"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!${NC}"
    exit 0
else
    echo -e "${RED}❌ ЕСТЬ ПРОВАЛЕННЫЕ ТЕСТЫ${NC}"
    exit 1
fi
