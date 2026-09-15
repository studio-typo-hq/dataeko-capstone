[![CI](https://github.com/ThecrewLord/dataeko-capstone/actions/workflows/ci.yml/badge.svg)](https://github.com/ThecrewLord/dataeko-capstone/actions/workflows/ci.yml)

# DATAEKO Capstone — Ship the Coffee Company

Final assignment for the Studio Typo × DATAEKO five-week internship.

**→ Read [BRIEF.md](BRIEF.md). Everything is in there.**

This repository is **deliberately broken**. It contains nine defects, one per
thing you were taught. Phase 0 is finding and fixing them.

```
scripts/ingest.sh      staging script          (Week 1)
ingest/loader.py       CSV -> Postgres         (Week 2)
api/app.py             the API + /metrics      (Weeks 2, 4)
sql/                   schema, seed, queries   (Week 4)
observability/         Prometheus + Grafana    (Week 4)
Dockerfile             the image               (Week 3)
.github/workflows/     CI and Pages            (Week 3)
infra/                 Terraform -> LocalStack (Week 5)
evidence/              your submission
```

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r api/requirements.txt -r ingest/requirements.txt pytest

docker start pg
docker exec pg psql -U postgres -c "CREATE DATABASE capstone;"
docker exec -i pg psql -U postgres -d capstone < sql/schema.sql
docker exec -i pg psql -U postgres -d capstone < sql/seed.sql

./scripts/verify.sh          # you will score 0/27. That is the starting line.
```

Everything runs locally. No AWS account, no credit card, no spend.
