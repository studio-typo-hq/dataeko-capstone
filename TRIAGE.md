Triage


For each one: what you saw, why it happened, what you changed, and how you

proved it is fixed. Paste real output — not a description of output.

## 1. scripts/ingest.sh is not executable

Symptom: Before the fix, ls -l scripts/ingest.sh showed:

-rw-r--r--  scripts/ingest.sh

Running the script produced:
zsh: permission denied

Cause: The executable permission bit was missing from the script.

Fix: Made the script executable:
chmod +x scripts/ingest.sh
git update-index --chmod=+x scripts/ingest.sh

Proof: After the fix, ls -l scripts/ingest.sh showed executable permissions:
-rwxr-xr-x  scripts/ingest.sh

The script then ran successfully:
staged orders.csv — 209 data rows

Why git update-index --chmod=+x was also needed: chmod changes the local filesystem permission, while git update-index --chmod=+x records the executable mode in Git so the permission is preserved when another user checks out the repository.

## 2. Unquoted $1 in scripts/ingest.sh

Symptom: Running the script with a filename containing a space:
./scripts/ingest.sh "data/march orders.csv"

produced:
./scripts/ingest.sh: line 10: [: data/march: binary operator expected

Cause: The input variable $1 was not quoted in the file-existence test, so the shell split the filename at the space.

Fix: Changed:
if [ ! -f $1 ]; then
to:
if [ ! -f "$1" ]; then

Proof: The same command succeeded after the fix:
staged march orders.csv — 209 data rows
The temporary test file was then removed.

## 3. Dockerfile copies source before installing dependencies
Symptom: The original Dockerfile used:
COPY . .
RUN pip install --no-cache-dir -r api/requirements.txt

A source-only change caused the dependency installation layer to run again. Before the fix, the cache test showed:
COPY . .
RUN pip install --no-cache-dir -r api/requirements.txt

with the pip installation taking approximately:
6.3s

Cause: The entire source tree was copied before the dependency installation layer. Any source change invalidated that layer and forced pip install to run again.

Fix: Reordered the Dockerfile:
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt
COPY . .

Proof (build output, before and after): After the fix, a source-only change produced cached dependency layers:
CACHED [3/5] COPY api/requirements.txt api/requirements.txt
CACHED [4/5] RUN pip install --no-cache-dir -r api/requirements.txt
[5/5] COPY . .

The cached pip installation took:
0.0s

The Dockerfile was also checked directly:
5:COPY api/requirements.txt api/requirements.txt
7:RUN pip install --no-cache-dir -r api/requirements.txt
9:COPY . .

## 4. No .dockerignore
Symptom: The repository did not contain a .dockerignore file, so unnecessary files could be included in the Docker build context.

Cause: No Docker build-context exclusion file had been created.

Fix: Created .dockerignore with:
.git
.terraform/
__pycache__/
*.pyc
.venv/

Proof (context size, before and after): Before the fix, Docker transferred:
transferring context: 12.34kB

After adding .dockerignore, Docker transferred:
transferring context: 1.85kB

The build context was reduced from 12.34 kB to 1.85 kB.


## 5. API key committed to the repository
Symptom: The API key was hardcoded in the application and CI configuration:
api/config.py: API_KEY = "dataeko-capstone-2026-secret"
.github/workflows/ci.yml: API_KEY: "dataeko-capstone-2026-secret"

Cause: The application configuration and GitHub Actions workflow contained the API key directly in source code.

Fix: Changed the application configuration to read the key from an environment variable:
import os
API_KEY = os.environ.get("API_KEY", "")

Changed the GitHub Actions workflow to use a GitHub secret:

API_KEY: ${{ secrets.API_KEY }}

Is the key gone now that you deleted the line? No. The key was removed from the current application and workflow files, but it remains in Git history. This was proved by searching Git history for:
dataeko-capstone-2026-secret

The current verifier confirmed:
PASS  no hardcoded API key in the repo

What would you have to do in real life? The exposed key should be revoked or rotated immediately. The replacement secret should be stored in the appropriate secret manager or GitHub Actions secret rather than committed to source control. Removing the line from the latest commit does not make the old secret safe because it remains in repository history.


## 6. requests call with no timeout
Symptom: The HTTP request in ingest/loader.py did not specify a timeout:
response = requests.get(url)

Cause: Without a timeout, the request could wait indefinitely if the remote server or network stopped responding.

Fix: Added a 10-second timeout:
response = requests.get(url, timeout=10)

Proof: The Phase 0 verifier reported:
PASS  requests call has a timeout

Why a hang is worse than an error: An error can be caught and handled, while a request that waits indefinitely can keep a worker or process occupied and prevent the system from progressing.


## 7. Missing index on orders.customer_id
Symptom: Before the index was added, PostgreSQL used a parallel sequential scan:
Gather  (cost=1000.00..6657.33 rows=20 width=36) (actual time=1.374..13.758 rows=20 loops=1)
  Workers Planned: 2
  Workers Launched: 2
  ->  Parallel Seq Scan on orders  (cost=0.00..5655.33 rows=8 width=36) (actual time=0.718..9.874 rows=7 loops=3)
        Filter: (customer_id = 1)
        Rows Removed by Filter: 133327
  Planning Time: 0.350 ms
  Execution Time: 13.839 ms

Plan before:
Parallel Seq Scan on orders
Filter: (customer_id = 1)
Rows Removed by Filter: 133327
Execution Time: 13.839 ms

Plan after: Added sql/migrations/001_orders_customer_index.sql:
CREATE INDEX IF NOT EXISTS idx_orders_customer_id
ON orders(customer_id);
The resulting plan used the new index:
Bitmap Heap Scan on orders
  Recheck Cond: (customer_id = 1)
  ->  Bitmap Index Scan on idx_orders_customer_id
        Index Cond: (customer_id = 1)
Planning Time: 0.308 ms
Execution Time: 0.190 ms

Timings, three runs each: Before the index, the captured execution time was:
13.839 ms

After the index, three observed execution times were:
0.190 ms
0.435 ms
0.119 ms

Why the planner changed its mind: Without an index, PostgreSQL had to scan many rows to find matching customer_id values. After the index was created, PostgreSQL could use idx_orders_customer_id to locate matching rows much more efficiently, so it selected an index-based plan.


## 8. SSH open to 0.0.0.0/0
Symptom: The original Terraform security rule allowed SSH from every IPv4 address:
ingress {
  from_port = 22
  to_port = 22
  protocol = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
}

Why nothing warned you: A configuration that is syntactically valid can still be insecure. Terraform can successfully plan an overly broad network rule unless an explicit security check or policy detects it.

Fix: Restricted SSH access to the required private network:
cidr_blocks = ["10.0.0.0/16"]

Proof: The Terraform configuration now restricts port 22 to:
10.0.0.0/16

The Phase 0 verifier reported:
PASS  SSH is not open to the world

What an attacker does with this: An SSH service exposed to the entire internet can be continuously scanned and attacked through password guessing, stolen credentials, or vulnerable SSH configurations. Restricting the source network reduces the reachable attack surface.


## 9. count instead of for_each
Plan with count, after removing staging: The original resource used numeric addresses:
aws_s3_bucket.env[0]
aws_s3_bucket.env[1]
aws_s3_bucket.env[2]

The temporary count-based plan showed:
aws_s3_bucket.env[0]
aws_s3_bucket.env[1]
aws_s3_bucket.env[2]

The important problem with count is that resources are identified by list position. Removing staging from the middle changes the indexes of later environments.

Plan with for_each, same edit: The corrected resource uses stable environment keys:
resource "aws_s3_bucket" "env" {
  for_each = toset(var.environments)
  bucket   = "${var.student}-capstone-${each.key}"
}

The for_each plan showed stable addresses:
aws_s3_bucket.env["dev"]
aws_s3_bucket.env["prod"]
aws_s3_bucket.env["staging"]

After removing staging, the plan showed:
aws_s3_bucket.env["dev"]
aws_s3_bucket.env["prod"

Why this is the most dangerous defect in the list: With count, removing an item from the middle of a list can change resource addresses for the remaining items. Terraform can then interpret an unchanged real-world resource as a different resource and plan destructive or replacement changes. for_each uses meaningful keys such as "dev" and "prod", so removing "staging" does not renumber the remaining environments.
