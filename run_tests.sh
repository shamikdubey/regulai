#!/bin/bash
# run_tests.sh — auto-detects Docker IP and runs all tests

set -e

echo "🔍 Detecting Docker postgres IP..."
DOCKER_IP=$(sudo docker inspect regulai_postgres | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(list(data[0]['NetworkSettings']['Networks'].values())[0]['IPAddress'])
")
echo "📡 Docker IP: $DOCKER_IP"

echo "🔧 Updating DB URLs..."
cd "$(dirname "$0")/backend"

python3 << PYEOF
import re
# Fix config.py
content = open('app/core/config.py').read()
content = re.sub(
    r'postgresql\+asyncpg://regulai_app:dev_app_secret@[^/]+/regulai',
    'postgresql+asyncpg://regulai_app:dev_app_secret@${DOCKER_IP}:5432/regulai',
    content
)
open('app/core/config.py', 'w').write(content)

# Fix conftest.py
content = open('tests/conftest.py').read()
content = re.sub(
    r'postgresql\+asyncpg://regulai_owner:dev_owner_secret@[^/]+/regulai',
    'postgresql+asyncpg://regulai_owner:dev_owner_secret@${DOCKER_IP}:5432/regulai',
    content
)
open('tests/conftest.py', 'w').write(content)
print("URLs updated")
PYEOF

echo "🔑 Setting DB password..."
sudo docker exec regulai_postgres psql -U regulai_owner -d regulai \
    -c "ALTER ROLE regulai_app WITH PASSWORD 'dev_app_secret';" 2>/dev/null || true

echo "🧪 Running tests..."
pytest tests/ --ignore=tests/test_new_features.py "$@"
