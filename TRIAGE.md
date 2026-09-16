# Triage

> Complete every defect section. One section per defect, nine in total.
> For each one: what you saw, why it happened, what you changed, and how you
> proved it is fixed. Paste real output — not a description of output.

## 0.1 `scripts/ingest.sh` is not executable

**Symptom:** The ingestion script did not have executable permission in the repository.
```bash
./scripts/ingest.sh data/orders.csv
# permission denied
```

**Cause:** The executable bit was not recorded correctly in Git.

**Fix:** Set the executable bit and update Git's index with:
```bash
chmod +x scripts/ingest.sh
git update-index --chmod=+x scripts/ingest.sh
```

**Proof:**
```
$ ls -l scripts/ingest.sh
-rwxr-xr-x  1 sumit  staff  732 16 Sep 10:54 scripts/ingest.sh

$ git ls-files -s scripts/ingest.sh
100755 3172fdf4a10f8cd4bfb54da7cd5860bd7fd91c06 0 scripts/ingest.sh
```

**Why `git update-index --chmod=+x` was also needed:** The executable permission must also be recorded in Git's index (`100755`) so it is preserved when the repository is cloned and checked out on other systems or in CI.

## 0.2 Unquoted `$1` in `scripts/ingest.sh`

**Symptom:** The ingestion script failed when the input file path contained spaces.
```bash
cp data/orders.csv "data/march orders.csv"
bash scripts/ingest.sh "data/march orders.csv"
# scripts/ingest.sh: line 10: [: data/march: binary operator expected
```

**Cause:** The input path `$1` was not safely quoted in shell tests like `if [ ! -f $1 ]`.

**Fix:** Quoted the positional parameter as `"$1"` wherever it is used.

**Proof:**
```
$ ./scripts/ingest.sh "data/test folder/orders test.csv"
staged orders test.csv — 209 data rows
```
The script successfully processed a file whose path contained spaces.

## 0.3 Dockerfile copies source before installing dependencies

**Symptom:** The Dockerfile copied the complete source tree before installing dependencies, invalidating the layer cache on every code change.
```
# Every code edit caused RUN pip install to rerun
```

**Cause:** `COPY . .` occurred before `RUN pip install`, making the dependency installation layer depend on the entire source tree.

**Fix:** Copied `api/requirements.txt` first, installed dependencies, and then copied the remaining source files:
```dockerfile
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt
COPY . .
```

**Proof:**
```
[3/5] COPY api/requirements.txt api/requirements.txt
[4/5] RUN pip install --no-cache-dir -r api/requirements.txt
[5/5] COPY . .
```
On subsequent builds after code changes, the `pip install` step is `CACHED` (1s rebuild vs 4s rebuild).

## 0.4 No `.dockerignore`

**Symptom:** The Docker build context was unnecessarily large (798 MB), slowing down image builds and risking "no space left on device".

**Cause:** Files such as `.venv/`, `.git/`, test cache, evidence, and `infra/.terraform` were sent to the Docker daemon.

**Fix:** Created `.dockerignore`:
```
.venv
.git
.github
.pytest_cache
__pycache__
*.pyc
data/staging
evidence
infra/.terraform
```

**Proof:**
Before:
```
transferring context: 798.13MB
```
After:
```
transferring context: 1.76kB
```
The Docker image builds in ~1.5s.

## 0.5 API key committed to the repository

**Symptom:** A production API secret `dataeko-capstone-2026-secret` was hard-coded in `api/config.py` and `.github/workflows/ci.yml`.

**Cause:** Secret was committed directly into version control rather than loaded from environment variables and GitHub Secrets.

**Fix:** Loaded the key from `os.getenv("API_KEY")` in `api/config.py` and `${{ secrets.API_KEY }}` in `.github/workflows/ci.yml`.

**Is the key gone now that you deleted the line?** No. Removing the key from the working directory does not erase it from Git commit history. Anyone with repository access can inspect past commits (`git log -p`) and retrieve it.

**What would you have to do in real life?** The exposed credential must immediately be revoked and rotated. The application and CI must be updated to use the new secret via environment variables or secret managers (e.g. AWS Secrets Manager, Vault). Finally, repository history should be scrubbed (e.g. with `git-filter-repo` or BFG) if policy requires.

## 0.6 `requests` call with no timeout

**Symptom:** `fetch_reference()` in `ingest/loader.py` made HTTP requests without specifying a timeout.

**Cause:** Default `requests.get()` without `timeout` waits indefinitely if the remote server accepts the TCP connection but never sends a response.

**Fix:** Added a 5-second timeout:
```python
response = requests.get(url, timeout=5)
```

**Why a hang is worse than an error:** An indefinite hang causes threads/workers to lock up, exhausts connection pools, and leaves processes unresponsive without any diagnostic error or failure alerting. A timeout raises an exception that can be caught, logged, retried, or alerted on.

## 0.7 Missing index on `orders.customer_id`

**Symptom:** Querying orders by `customer_id` performed a sequential table scan:
```
Seq Scan on orders (cost=0.00..4.50 rows=1 width=35)
Filter: (customer_id = 10612)
```

**Fix:** Created migration `sql/migrations/001_orders_customer_id.sql`:
```sql
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
```

**Proof:**
```
$ docker exec pg psql -U postgres -d capstone -c "\d orders"
Indexes:
    "orders_pkey" PRIMARY KEY, btree (id)
    "idx_orders_customer_id" btree (customer_id)
```
On the 400,000-row dataset, `EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 10612;` switches from a `Seq Scan` to a `Bitmap Index Scan` on `idx_orders_customer_id`, dropping query execution time dramatically.

## 0.8 SSH open to `0.0.0.0/0`

**Symptom:** Security group `aws_security_group.api` had ingress port 22 open to `0.0.0.0/0`.

**Cause:** Ingress rule CIDR block was set to all public IPs instead of restricted internal/bastion IP ranges.

**Fix:** Restricted SSH CIDR blocks to `127.0.0.1/32` (or VPC CIDR `10.0.0.0/16`):
```hcl
ingress {
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["127.0.0.1/32"]
}
```

**Why nothing warned you:** `terraform validate` only validates HCL syntax and provider schema definitions, not security best practices. `0.0.0.0/0` is syntactically valid CIDR notation.

**What an attacker could do with the original configuration:** An attacker could scan port 22 across public IP space, run automated brute-force attacks or exploit SSH service vulnerabilities to compromise the host.

## 0.9 `count` where `for_each` belongs

**Symptom:** S3 buckets were defined using `count = length(var.environments)`. When `"staging"` was removed from the list `["dev", "staging", "prod"]`, Terraform planned to destroy and replace production:
```
# aws_s3_bucket.env[1] must be replaced
    ~ bucket = "testuser-capstone-staging" -> "testuser-capstone-prod" # forces replacement
# aws_s3_bucket.env[2] will be destroyed

Plan: 1 to add, 0 to change, 2 to destroy.
```
Deleting staging destroys and rebuilds prod, causing catastrophic data loss!

**Cause:** `count` indexes resources by numeric position (`env[0]`, `env[1]`, `env[2]`). Removing an item from the middle shifts all subsequent indexes.

**Fix:** Converted `aws_s3_bucket.env` to use `for_each = toset(var.environments)`:
```hcl
resource "aws_s3_bucket" "env" {
  for_each = toset(var.environments)
  bucket   = "${var.student}-capstone-${each.key}"
}
```

**Proof:**
With `for_each`, removing `"staging"` results in:
```
# aws_s3_bucket.env["staging"] will be destroyed

Plan: 0 to add, 0 to change, 1 to destroy.
```
Only the deleted environment is targeted; all other resources remain untouched.
