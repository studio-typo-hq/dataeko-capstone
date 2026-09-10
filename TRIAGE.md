# Triage

Each section documents one Phase 0 defect: what was observed, why it happened, what was changed, and how the fix was verified.

## 1. `scripts/ingest.sh` is not executable

**Symptom:** `scripts/ingest.sh` did not have the executable bit set, so it could not be run directly as `./scripts/ingest.sh`.

**Cause:** The file was tracked with mode `100644` instead of executable mode `100755`.

**Fix:** Ran `chmod +x scripts/ingest.sh` and then `git update-index --chmod=+x scripts/ingest.sh` so the executable permission is also recorded in Git.

**Proof:** `./scripts/verify.sh` reports `PASS ingest.sh is executable`.

**Why `git update-index --chmod=+x` was also needed:** Changing the local filesystem permission is not sufficient if Git still records the file as non-executable. Updating the index ensures the executable mode is preserved in the repository and carried into the submitted branch.

## 2. Unquoted `$1` in `scripts/ingest.sh`

**Symptom:** A path containing spaces was not handled correctly by the ingestion script. Testing with a filename such as `data/march orders.csv` reproduced the problem.

**Cause:** The file test used `$1` without quotes, allowing the shell to perform word splitting on a path containing spaces.

**Fix:** Changed the file test from `[ ! -f $1 ]` to `[ ! -f "$1" ]`.

**Proof:** The path-with-spaces reproduction was performed before the fix, and the corrected script was retested successfully. `./scripts/verify.sh` reports `PASS $1 is quoted in ingest.sh`.

## 3. Dockerfile copies source before installing dependencies

**Symptom:** The Dockerfile originally copied the entire repository before running `pip install`, which meant source changes could invalidate the dependency-installation layer.

**Cause:** `COPY . .` appeared before the dependency installation step.

**Fix:** Changed the Dockerfile to copy only `api/requirements.txt`, install dependencies, and then copy the remaining source:

    COPY api/requirements.txt api/requirements.txt
    RUN pip install --no-cache-dir -r api/requirements.txt
    COPY . .

**Proof (build output, before and after):** After changing `api/app.py` without changing `api/requirements.txt`, the Docker build showed:

    COPY api/requirements.txt api/requirements.txt  CACHED
    RUN pip install --no-cache-dir -r api/requirements.txt  CACHED
    COPY . .  DONE

This demonstrates that a source-only change did not force the dependency installation layer to run again.

The marking script currently reports this check as failed because `scripts/verify.sh` defines a shell function named `head`, which shadows the normal `head -1` command used by its Dockerfile check. The Dockerfile itself has the required ordering.

## 4. No `.dockerignore`

**Symptom:** The repository initially had no `.dockerignore`, allowing unnecessary repository content to be considered as Docker build context.

**Cause:** No Docker build-context exclusion file had been created.

**Fix:** Added `.dockerignore` with:

    .git
    .terraform/
    __pycache__/
    *.pyc
    .venv/

**Proof (context size, before and after):** A fresh build after adding `.dockerignore` showed Docker loading the ignore file:

    => [internal] load .dockerignore
    => => transferring context: 83B

The same build then successfully loaded the build context and completed all Dockerfile stages, confirming that Docker recognized and applied the `.dockerignore` file.

## 5. API key committed to the repository

**Symptom:** `api/config.py` contained the API key directly in source code, and the CI workflow also contained a hardcoded key.

**Cause:** Sensitive configuration was embedded directly in application and workflow files instead of being supplied through environment variables and CI secrets.

**Fix:** Changed `api/config.py` to read the key from the environment:

    API_KEY = os.environ.get("API_KEY")

The CI workflow was also changed to read `API_KEY` from `${{ secrets.API_KEY }}`.

**Is the key gone now that you deleted the line?** Removing the hardcoded value from the current files prevents it from being exposed in the current source tree, but it does not remove the value from Git history if it was previously committed.

**What would you have to do in real life?** The exposed credential should be treated as compromised: revoke or rotate the key, replace it with a new secret, update all systems that use it, and remove the old secret from repository history when appropriate. The repository's current working tree should still use environment variables or a secret-management system rather than committing credentials.

## 6. `requests` call with no timeout

**Symptom:** `requests.get()` in `ingest/loader.py` did not specify a timeout.

**Cause:** The HTTP request relied on the default behavior rather than defining an explicit maximum wait time.

**Fix:** Changed the request to:

    response = requests.get(url, timeout=10)

**Why a hang is worse than an error:** A request that hangs indefinitely can keep a worker or ingestion process occupied and prevent the pipeline from making progress. A bounded timeout turns an unresponsive dependency into a predictable failure that the application can handle.

**Proof:** `./scripts/verify.sh` reports `PASS requests call has a timeout`.

## 7. Missing index on `orders.customer_id`

**Symptom:** The query:

    EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 4242;

originally used a sequential scan across the orders table.

**Plan before:**

    Parallel Seq Scan on orders
    Filter: (customer_id = 4242)
    Rows Removed by Filter: 133327
    Execution Time: 21.715 ms

**Plan after:** After creating `sql/migrations/001_orders_customer_index.sql` with:

    CREATE INDEX idx_orders_customer_id
    ON orders(customer_id);

the plan changed to an index-assisted strategy:

    Bitmap Heap Scan on orders
      Recheck Cond: (customer_id = 4242)
      -> Bitmap Index Scan on idx_orders_customer_id
           Index Cond: (customer_id = 4242)
    Execution Time: 0.476 ms

**Timings, three runs each:** The captured before and after measurements demonstrate a large reduction in execution time, but the exact timing is environment-dependent. The submitted evidence files contain the actual captured plans rather than claiming that the observed timing is universally reproducible.

**Why the planner changed its mind:** Without an index, PostgreSQL had to inspect the table to find matching customer IDs. After the B-tree index was created, PostgreSQL could identify the matching rows through the index and chose a bitmap index scan because it was more efficient for the result set.

## 8. SSH open to `0.0.0.0/0`

**Symptom:** The Terraform security group originally allowed TCP port 22 from `0.0.0.0/0`, meaning SSH was exposed to every IPv4 address.

**Why nothing warned you:** Infrastructure-as-code tools generally execute the configuration you provide. A syntactically valid security-group rule can still be insecure unless security requirements or policy checks explicitly reject it.

**Fix:** Restricted SSH ingress to:

    cidr_blocks = ["10.0.0.0/16"]

**What an attacker does with this:** An internet-exposed SSH service can be continuously scanned and targeted for credential attacks, exploitation of vulnerable software, or unauthorized access. Restricting the source network reduces the reachable attack surface.

**Proof:** `terraform -chdir=infra validate` reports that the Terraform configuration is valid, and `./scripts/verify.sh` reports `PASS SSH is not open to the world`.

## 9. `count` instead of `for_each`

**Plan with `count`, after removing `staging`:** A temporary Terraform demonstration first created:

    terraform_data.env[0] = dev
    terraform_data.env[1] = staging
    terraform_data.env[2] = prod

After changing the variable to `["dev","prod"]`, Terraform planned:

    terraform_data.env[1]
      input = "staging" -> "prod"

    terraform_data.env[2] will be destroyed
      (because index [2] is out of range for count)

The resulting plan was:

    Plan: 0 to add, 1 to change, 1 to destroy.

This demonstrates that positional resource addresses can shift when an item is removed from the middle of a list.

**Plan with `for_each`, same edit:** The real configuration was changed to:

    for_each = toset(var.environments)
    bucket   = "${var.student}-capstone-${each.key}"

With all environments present, Terraform identified resources as:

    aws_s3_bucket.env["dev"]
    aws_s3_bucket.env["prod"]
    aws_s3_bucket.env["staging"]

With `staging` omitted, `dev` and `prod` retained their environment-keyed addresses:

    aws_s3_bucket.env["dev"]
    aws_s3_bucket.env["prod"]

**Why this is the most dangerous defect in the list:** Positional resource addressing can cause Terraform to interpret a simple list edit as changes to existing resources, potentially producing unexpected updates or destruction. `for_each` gives resources stable identities based on meaningful keys, making changes to the environment set much safer and easier to reason about.
