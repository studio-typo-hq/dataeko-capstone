# Triage

> Replace every `TODO`. One section per defect, nine in total.
> For each one: what you saw, why it happened, what you changed, and how you
> proved it is fixed. Paste real output — not a description of output.

## 1. `scripts/ingest.sh` is not executable
**Symptom:** Running ./scripts/ingest.sh data/orders.csv initially failed with permission denied.
**Cause:** The script did not have the executable permission bit set. Its file mode was 644, so the operating system would not allow it to be executed directly.
**Fix:** I ran:

chmod +x scripts/ingest.sh
git update-index --chmod=+x scripts/ingest.sh

This changed the script permissions to executable and also made Git track the executable bit.
**Proof:** After the fix, ls -l scripts/ingest.sh showed:

-rwxr-xr-x  1 himanshu  staff  730  9 Sep 18:41 scripts/ingest.sh

I then ran:

./scripts/ingest.sh data/orders.csv

and it successfully produced:

staged orders.csv — 209 data rows

The verification script also changed this check from FAIL to:

PASS  ingest.sh is executable
**Why `git update-index --chmod=+x` was also needed:** chmod changes the permission on my local filesystem, but Git also needs to record the executable bit so that the permission is preserved when the repository is cloned or checked out elsewhere. git update-index --chmod=+x makes Git track the file as executable.

## 2. Unquoted `$1` in `scripts/ingest.sh`
**Symptom:** Running the script with a filename containing spaces initially failed because the unquoted $1 was split into multiple arguments.
**Cause:** The file path was used as $1 without quotes in the file-existence test. In Bash, unquoted variables are subject to word splitting, so a path such as data/march orders.csv was interpreted as separate words.
**Fix:** I changed:

if [ ! -f $1 ]; then

to:

if [ ! -f "$1" ]; then

The other uses of $1 that pass the path to commands were already quoted.
**Proof:** I created a test copy with a space in its filename:

cp data/orders.csv "data/march orders.csv"

Then I ran:

./scripts/ingest.sh "data/march orders.csv"

The script successfully staged the file and reported:

staged march orders.csv — 209 data rows

This proves that the script now handles input paths containing spaces correctly.

## 3. Dockerfile copies source before installing dependencies
**Symptom:** The original Dockerfile copied the entire repository before running pip install. Because the dependency-install layer came after the source copy, changing application code could invalidate the layer and cause dependencies to be installed again.
**Cause:** Docker builds layers in instruction order. The original order was:

COPY . .
RUN pip install --no-cache-dir -r api/requirements.txt

Any change included by COPY . . could therefore invalidate the following dependency-install layer.
**Fix:** I changed the order so that only the dependency file is copied before installing dependencies:

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt
COPY . .

This allows Docker to reuse the dependency-install layer when only application source files change.
**Proof (build output, before and after):** Before the fix, I built the original Dockerfile with:

docker build --no-cache -t dataeko-before .

The relevant output was:

=> [internal] load build context
=> => transferring context: 46.80MB
=> [3/4] COPY . .
=> [4/4] RUN pip install --no-cache-dir -r api/requirements.txt

The dependency installation took approximately 11.6 seconds.

After the fix, I built the corrected Dockerfile with:

docker build -t dataeko-after .

The relevant output was:

=> [internal] load build context
=> => transferring context: 273.14kB
=> [3/5] COPY api/requirements.txt api/requirements.txt
=> [4/5] RUN pip install --no-cache-dir -r api/requirements.txt
=> [5/5] COPY . .

The dependency installation took approximately 11.7 seconds.

The build output confirms that the dependency file is now copied and installed before the application source. The large reduction in build context is also visible in this run, although the primary fix is the layer ordering that preserves dependency caching across source-code changes.

## 4. No `.dockerignore`
**Symptom:**The repository had no .dockerignore, so Docker included unnecessary files such as the local Python virtual environment in the build context.
**Cause:** Without a .dockerignore, Docker sends the repository contents to the Docker daemon as build context. The local .venv directory alone was approximately 50 MB.
**Fix:** I created .dockerignore with:

.git
.terraform/
__pycache__/
*.pyc
.venv/

This prevents Git metadata, Terraform working files, Python cache files, and the local virtual environment from being sent as Docker build context.
**Proof (context size, before and after):** Before creating .dockerignore, the Docker build reported:

=> [internal] load build context
=> => transferring context: 46.80MB

After creating .dockerignore, the build reported:

=> [internal] load .dockerignore
=> => transferring context: 83B
=> [internal] load build context
=> => transferring context: 7.43kB

The build context therefore dropped from 46.80 MB to 7.43 kB, demonstrating that unnecessary files were excluded.

## 5. API key committed to the repository
**Symptom:** The API key dataeko-capstone-2026-secret was hardcoded in api/config.py and was also directly placed in the GitHub Actions workflow.
**Cause:** The API configuration stored the credential as a string in source code, and the CI workflow passed the same credential directly in the YAML file. Anyone with access to the repository could read the credential.
**Fix:** I changed api/config.py to load the API key from the environment:

import os
API_KEY = os.getenv("API_KEY", "")

I also changed .github/workflows/ci.yml to read the credential from a GitHub Actions secret:

env:
  API_KEY: ${{ secrets.DATAEKO_API_KEY }}

The old # DEFECT comments were also removed.

**Proof:** I checked the current repository with:

git grep "dataeko-capstone-2026-secret"

The output only showed the expected references in BRIEF.md and scripts/verify.sh; the hardcoded key is no longer present in the application or workflow files.

I then checked Git history with:

git log -p | grep "dataeko-capstone-2026-secret"

The output still showed the old API key in previous commits:

+          API_KEY: "dataeko-capstone-2026-secret"
+API_KEY = "dataeko-capstone-2026-secret"

This proves that the key was removed from the current source code but remains present in Git history.
**Is the key gone now that you deleted the line?** No. It is gone from the current application and workflow files, but it remains in previous Git commits. Removing a secret from the latest version does not erase it from Git history.
**What would you have to do in real life?** Treat the exposed key as compromised. I would immediately revoke or rotate the key, update the application and CI configuration with the new secret, and, if necessary, remove the secret from repository history using an appropriate Git history-rewriting tool. The repository history should be considered exposed even after the current file is cleaned.

## 6. `requests` call with no timeout

**Symptom:** The `fetch_reference()` function could wait indefinitely if the API accepted the connection but stopped responding.

**Cause:** The `requests.get(url)` call did not specify a timeout. Without a timeout, the caller can remain blocked while waiting for the server.

**Fix:** I changed the request to use a 10-second timeout:

    response = requests.get(url, timeout=10)

This gives the request a bounded amount of time to complete instead of allowing it to hang indefinitely.

**Why a hang is worse than an error:** A timeout turns an indefinite wait into a predictable failure that the application can catch, log, retry, or report. An indefinite hang can keep resources occupied, delay failure detection, and make incidents harder to diagnose.

## 7. Missing index on `orders.customer_id`

**Symptom:** Queries filtering orders by `customer_id` initially used a parallel sequential scan. The query returned only 20 rows, but PostgreSQL had to scan the orders table and remove 133327 rows by the filter.

**Plan before:** The query used a `Parallel Seq Scan` on `orders`.

The first captured run reported:

    Parallel Seq Scan on orders
    Rows Removed by Filter: 133327
    Execution Time: 77.286 ms

The other two before-index runs reported execution times of 18.921 ms and 26.858 ms. All three runs used the sequential-scan plan.

**Plan after:** I created the migration:

    sql/migrations/001_orders_customer_index.sql

with:

    CREATE INDEX orders_customer_id_idx
    ON orders(customer_id);

After applying the migration, PostgreSQL changed the plan to:

    Bitmap Index Scan on orders_customer_id_idx
    Bitmap Heap Scan on orders

The index was verified with `\d orders`:

    "orders_customer_id_idx" btree (customer_id)

**Timings, three runs each:**

Before index:

    Run 1: 77.286 ms
    Run 2: 18.921 ms
    Run 3: 26.858 ms

After index:

    Run 1: 0.617 ms
    Run 2: 3.072 ms
    Run 3: 0.595 ms

The indexed runs were substantially faster and all used `orders_customer_id_idx`.

**Why the planner changed its mind:** Without an index, PostgreSQL had to scan the `orders` table to find rows matching `customer_id = 12345`. The index provides a direct lookup path for that column, so PostgreSQL estimated that using the index would require much less work than scanning the entire table. It therefore selected a `Bitmap Index Scan` followed by a `Bitmap Heap Scan`.

## 8. SSH open to `0.0.0.0/0`

**Symptom:** The API security group allowed SSH traffic on port 22 from `0.0.0.0/0`, meaning any IPv4 address could attempt to connect to the instance.

**Cause:** The SSH ingress rule was configured with an unrestricted CIDR block:

    cidr_blocks = ["0.0.0.0/0"]

This exposes the SSH service to the entire internet and increases the attack surface for password guessing, key attacks, and other unauthorized connection attempts.

**Fix:** I restricted the SSH ingress rule to the VPC CIDR:

    cidr_blocks = ["10.0.0.0/16"]

The application port 8000 was already restricted to the same VPC CIDR and was left unchanged.

**Proof:** The corrected `infra/main.tf` contains:

    ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["10.0.0.0/16"]
    }

I also checked the Git diff to confirm that the only functional change in the security group was the SSH CIDR restriction.

**Why this matters:** SSH should not normally be exposed to the entire internet. Restricting the source range limits which networks can reach the SSH service and reduces the security group's attack surface. In a real deployment, the allowed CIDR should be the smallest trusted administrative network or access path required.

## 9. `count` instead of `for_each`

**Symptom:** The S3 buckets were created using `count` with a list of environments. This means Terraform identified resources by their numeric position in the list rather than by the environment name.

With the original configuration:

    aws_s3_bucket.env[0] -> dev
    aws_s3_bucket.env[1] -> staging
    aws_s3_bucket.env[2] -> prod

When `staging` is removed, `prod` moves from index `2` to index `1`. In a populated Terraform state, this can make Terraform treat the existing `prod` resource as a different resource and potentially cause resource churn.

**Plan with `count`, after removing `staging`:** The plan used positional addresses:

    aws_s3_bucket.env[0] -> himanshu-capstone-dev
    aws_s3_bucket.env[1] -> himanshu-capstone-prod

The important issue is that `prod` moved from `env[2]` to `env[1]`. Because this exercise did not apply the Terraform configuration, the state was empty, so the plan showed creates rather than an actual destroy/recreate operation.

**Fix:** I changed the S3 resource from `count` to:

    for_each = toset(var.environments)

and changed the bucket name to use:

    each.value

I also updated the output to use a `for` expression because `for_each` creates a map of resources.

**Plan with `for_each`, after removing `staging`:** The plan uses stable environment names as resource keys:

    aws_s3_bucket.env["dev"]  -> himanshu-capstone-dev
    aws_s3_bucket.env["prod"] -> himanshu-capstone-prod

The plan reported:

    Plan: 3 to add, 0 to change, 0 to destroy.

The state was empty because the resources were not applied, so Terraform had no existing `staging` resource to destroy. The important difference is that `prod` keeps the stable address `env["prod"]` instead of changing its numeric position.

**Why this matters:** `count` is positional and is therefore fragile when items are inserted, removed, or reordered in a list. `for_each` uses stable keys such as `dev`, `staging`, and `prod`, so removing one environment does not change the identity of the remaining resources. This reduces the risk of accidental resource replacement and makes Terraform plans safer and more predictable.
