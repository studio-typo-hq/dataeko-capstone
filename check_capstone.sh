#!/bin/bash

echo "========================================"
echo " DATAEKO CAPSTONE - PROJECT CHECK"
echo "========================================"
echo

echo ">>> 1. Current directory"
pwd
echo

echo ">>> 2. Git status"
git status --short
echo

echo ">>> 3. TODO check"
grep -n "TODO" TRIAGE.md || echo "No TODOs found in TRIAGE.md"
echo

echo ">>> 4. Git diff check"
git diff --check
echo "git diff --check completed"
echo

echo ">>> 5. ingest.sh permissions"
ls -l scripts/ingest.sh
git ls-files -s scripts/ingest.sh
echo

echo ">>> 6. ingest.sh relevant code"
grep -n -A25 -B5 '\$1' scripts/ingest.sh
echo

echo ">>> 7. Dockerfile"
cat Dockerfile
echo

echo ">>> 8. .dockerignore"
cat .dockerignore
echo

echo ">>> 9. API configuration"
cat api/config.py
echo

echo ">>> 10. Loader imports/config"
sed -n '1,80p' ingest/loader.py
echo

echo ">>> 11. Loader database configuration"
grep -n -E 'DB_DSN|postgres|password|secret|5433|5432' ingest/loader.py api/config.py
echo

echo ">>> 12. Terraform S3 resource"
grep -n -A8 -B3 'resource "aws_s3_bucket" "env"' infra/main.tf
echo

echo ">>> 13. Terraform SSH/API rules"
grep -n -A12 -B3 'ingress' infra/main.tf
echo

echo ">>> 14. Terraform plan"
cd infra
terraform plan -var="student=testuser"
cd ..
echo

echo ">>> 15. Docker build"
docker build -t dataeko-capstone:test .
echo

echo ">>> 16. PostgreSQL orders indexes"
docker exec pg psql -U postgres -d capstone -c "\d orders"
echo

echo ">>> 17. PostgreSQL query plan"
docker exec pg psql -U postgres -d capstone -c "EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 10612;"
echo

echo ">>> 18. Project directories"
find . -maxdepth 2 -type f \
  ! -path './.git/*' \
  ! -path './.venv/*' \
  ! -path './infra/.terraform/*' \
  | sort
echo

echo "========================================"
echo " CHECK COMPLETE"
echo "========================================"
