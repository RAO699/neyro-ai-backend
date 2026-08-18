#!/bin/bash
API="https://api.neyro.by"
PASS=0
FAIL=0
TOTAL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    local expected_code="$5"
    local auth="$6"
    
    TOTAL=$((TOTAL + 1))
    echo -e "${YELLOW}[$TOTAL] Тест: $name${NC}"
    
    if [ "$auth" = "bearer" ]; then
        if [ "$method" = "GET" ]; then
            http_code=$(curl -s -o /dev/null -w "%{http_code}" "$API$url" \
                -H "Authorization: Bearer invalid_test_token" 2>&1)
        else
            http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API$url" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer invalid_test_token" \
                -d "$data" 2>&1)
        fi
    else
        if [ "$method" = "GET" ]; then
            http_code=$(curl -s -o /dev/null -w "%{http_code}" "$API$url" 2>&1)
        else
            http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API$url" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1)
        fi
    fi
    
    if [ "$http_code" = "$expected_code" ]; then
        echo -e "  ${GREEN}✅ PASS (HTTP $http_code)${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}❌ FAIL (HTTP $http_code, ожидался $expected_code)${NC}"
        FAIL=$((FAIL + 1))
    fi
    echo ""
    
    # Пауза между тестами чтобы не срабатывал rate limiting
    sleep 1
}

echo "=========================================="
echo "   NeyroAI Smoke Tests"
echo "=========================================="
echo ""

# 1. Статика
test_endpoint "Статический сайт" "GET" "/" "{}" "200"

# 2. User Status с ID
test_endpoint "User Status (Telegram)" "GET" "/api/user/status?telegram_id=710112354" "{}" "200"

# 3. User Status без ID
test_endpoint "User Status (без ID)" "GET" "/api/user/status" "{}" "400"

# 4. Login неверный
test_endpoint "Login (неверный)" "POST" "/api/login" '{"username":"nonexist","password":"wrong"}' "401"

# 5. Register пустые
test_endpoint "Register (пустые)" "POST" "/api/register" '{"username":"","password":""}' "400"

# 6. Generate с неверным токеном
test_endpoint "Generate (неверный токен)" "POST" "/api/generate" '{"prompt":"test","model":"flux"}' "401" "bearer"

# 7. Upscale с неверным токеном
test_endpoint "Upscale (неверный токен)" "POST" "/api/upscale" '{"image_url":"test"}' "401" "bearer"

# 8. Redactor с неверным токеном
test_endpoint "Redactor (неверный токен)" "POST" "/api/redactor" '{"edit_type":"remove-bg"}' "401" "bearer"

# 9. Confirm Payment без данных
test_endpoint "Confirm Payment" "POST" "/api/confirm-payment" '{}' "401" "bearer"

# 10. Request Reset без email
test_endpoint "Request Reset" "POST" "/api/request-reset" '{}' "400"

# 11. Link Account без данных
test_endpoint "Link Account" "POST" "/api/link-account" '{}' "401" "bearer"

# 12. CORS
echo -e "${YELLOW}[$TOTAL] Тест: CORS${NC}"
TOTAL=$((TOTAL + 1))
cors=$(curl -s -I -X OPTIONS "$API/api/generate" -H "Origin: https://neyro.by" -H "Access-Control-Request-Method: POST" | grep -i "access-control")
if [ -n "$cors" ]; then
    echo -e "  ${GREEN}✅ PASS${NC}"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""
sleep 1

# 13. Rate limiting
echo -e "${YELLOW}[$TOTAL] Тест: Rate limiting${NC}"
TOTAL=$((TOTAL + 1))
rate_limited=false
for i in $(seq 1 10); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/user/status?telegram_id=710112354")
    if [ "$code" = "429" ] || [ "$code" = "503" ]; then
        rate_limited=true
        break
    fi
done
if [ "$rate_limited" = true ]; then
    echo -e "  ${GREEN}✅ PASS (сработал $code)${NC}"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""
sleep 2

# 14. Файлы
echo -e "${YELLOW}[$TOTAL] Тест: Файлы${NC}"
TOTAL=$((TOTAL + 1))
file_count=$(ls /opt/neyro-backend/ai-assistant/generated/ 2>/dev/null | wc -l)
if [ "$file_count" -gt 0 ]; then
    echo -e "  ${GREEN}✅ PASS ($file_count файлов)${NC}"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

# 15. Docker
echo -e "${YELLOW}[$TOTAL] Тест: Docker${NC}"
TOTAL=$((TOTAL + 1))
running=$(docker compose -f /opt/neyro-backend/docker-compose.yml ps --status running | grep -c "Up")
if [ "$running" -ge 4 ]; then
    echo -e "  ${GREEN}✅ PASS ($running контейнеров)${NC}"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

echo "=========================================="
echo -e "  ${GREEN}Пройдено: $PASS${NC}"
echo -e "  ${RED}Провалено: $FAIL${NC}"
echo "  Всего: $TOTAL"
echo "=========================================="

if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!${NC}"
    exit 0
else
    echo -e "${RED}❌ ЕСТЬ ПРОВАЛЕННЫЕ ТЕСТЫ${NC}"
    exit 1
fi
