#!/opt/homebrew/bin/bash

set -e

echo "🧨 Forcibly terminating connections to 'codeanalysis'..."

docker exec -i codeanalysis_db psql -U analyzer -d postgres -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = 'codeanalysis' AND pid <> pg_backend_pid();
"

echo "🗑️ Dropping and recreating database..."

docker exec -i codeanalysis_db psql -U analyzer -d postgres -c "DROP DATABASE IF EXISTS codeanalysis;"
docker exec -i codeanalysis_db psql -U analyzer -d postgres -c "CREATE DATABASE codeanalysis;"

echo "🛠️  Reapplying schema (init_v2)..."
cat sql/init_v2.sql | docker exec -i codeanalysis_db psql -U analyzer -d codeanalysis

echo "🌱 Seeding data (seed_v2)..."
cat sql/seed_v2.sql | docker exec -i codeanalysis_db psql -U analyzer -d codeanalysis

echo "✅ Database is wiped and reset!"
