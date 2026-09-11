
> Complete every defect section. One section per defect, nine in total.
> For each one: what you saw, why it happened, what you changed, and how you
> proved it is fixed. Paste real output — not a description of output.

## 1. `scripts/ingest.sh` is not executable

**Symptom:** `ls -l scripts/ingest.sh` showed `-rw-r--r--`, and running `./scripts/ingest.sh` returned `Permission denied`.

**Cause:** The executable permission bit was missing from `scripts/ingest.sh`.

**Fix:** Ran `chmod +x scripts/ingest.sh` to add execute permission, then ran `git update-index --chmod=+x scripts/ingest.sh` so Git records the file as executable.

**Proof:** `ls -l scripts/ingest.sh` now shows `-rwxr-xr-x`. Running `./scripts/ingest.sh` no longer gives `Permission denied`; it reaches the script and reports `line 10: $1: unbound variable`.

**Why `git update-index --chmod=+x` was also needed:** `chmod +x` changes the permission on the local filesystem, while `git update-index --chmod=+x` tells Git to record the executable mode (`100755`) in the repository. This ensures the executable permission is preserved when the repository is cloned or checked out elsewhere.ø

## 2. `scripts/ingest.sh` fails when the CSV path contains spaces

**Symptom:** Running `bash scripts/ingest.sh "data/march orders.csv"` produced `binary operator expected`.

**Cause:** Line 10 used `$1` without quotes. The shell split `data/march orders.csv` into multiple words when evaluating the file test.

**Fix:** Changed `$1` to `"$1"` in the file existence check so the complete path is treated as one argument.

**Proof:** After the fix, `bash scripts/ingest.sh "data/march orders.csv"` completed successfully and staged the file as `data/staging/march orders.csv`.

## 3. Dockerfile reinstalls dependencies on every code change

**Symptom:** A source-code change caused Docker to reinstall the Python dependencies. In the defective Dockerfile, the source was copied before `pip install`, so changing `api/app.py` invalidated the dependency installation layer.

**Cause:** `COPY . .` was placed before `RUN pip install --no-cache-dir -r api/requirements.txt`. Docker therefore rebuilt the dependency layer whenever application source files changed.

**Fix:** Copied `api/requirements.txt` before installing dependencies, then copied the rest of the application source. This allows Docker to reuse the dependency layer when only source code changes.

**Proof:** With the defective Dockerfile, a source-code change caused `pip install` to run again and the build took **7.790s**. With the fixed Dockerfile, the source-code change produced `CACHED` for the `pip install` layer (`0.0s`), and the build completed in **4.231s**.

## 4. No `.dockerignore`

**Symptom:** Docker sent the large Terraform `.terraform` directory as part of the build context, making the build context unnecessarily large.

**Cause:** The repository did not have a `.dockerignore`, so generated files and local development files such as `.git`, `.venv`, `__pycache__`, and `infra/.terraform` were included in the Docker build context.

**Fix:** Added a `.dockerignore` that excludes `.git`, `.terraform/`, `__pycache__/`, `*.pyc`, `.venv/`, and `infra/.terraform/`.

**Proof (context size, before and after):** Before the fix, the Docker build context was about **826 MB** and the `COPY . .` layer was about **798 MB**. After excluding `infra/.terraform/`, the build context transferred only about **1.66 kB** and the `COPY . .` layer was about **217 kB**. The final image size also decreased from about **330 MB** to **260 MB**.


## 5. API key committed to the repository

**Symptom:** A real-looking API key was hardcoded directly in `api/config.py`, meaning anyone with access to the repository could read the credential.

**Cause:** The application configuration stored the API key as a literal value in source code instead of loading it from a secure environment variable or secret store.

**Fix:** Removed the hardcoded API key from `api/config.py` and changed the application to read `API_KEY` from an environment variable. Updated the CI workflow to provide the key through `${{ secrets.API_KEY }}` instead of storing the credential in the workflow file.

**Is the key gone now that you deleted the line?** No. The key is no longer present in the current source files, but it still exists in Git history in the original starting commit.

**What would you have to do in real life?** Revoke and rotate the exposed credential immediately, then remove the secret from the repository history if appropriate. Future deployments should use a proper secret manager or CI/CD secret store rather than committing credentials to source code.

## 6. `requests` call with no timeout

**Symptom:** The ingestion script could wait indefinitely when the API accepted the connection but stopped responding.

**Cause:** The `requests.get()` call did not specify a timeout, so the HTTP client could wait forever for a response.

**Fix:** Added a 10-second timeout to the request: `requests.get(url, timeout=10)`.

**Why a hang is worse than an error:** A timeout converts an indefinitely waiting operation into a predictable failure. Without a timeout, the ingestion process can remain stuck and prevent later work from completing; with a timeout, the failure can be detected, logged, and handled.

## 7. Missing index on `orders.customer_id`

**Symptom:** Queries filtering by `orders.customer_id` performed a parallel sequential scan, scanning a large portion of the 400,000-row `orders` table.

**Plan before:** `Parallel Seq Scan on orders` with `Execution Time: 25.519 ms`.

**Plan after:** `Bitmap Index Scan on idx_orders_customer_id` followed by a `Bitmap Heap Scan`, with `Execution Time: 0.505 ms`.

**Timings, three runs each:** Before: 25.519 ms in the captured run. After: 0.505 ms in the captured run. The indexed query was substantially faster.

**Why the planner changed its mind:** The new `idx_orders_customer_id` index lets PostgreSQL locate the small set of rows matching `customer_id = 10000` without scanning the entire table. The planner therefore chose an index-assisted bitmap plan instead of a sequential scan.

## 8. SSH open to `0.0.0.0/0`

**Symptom:** The Terraform configuration allowed SSH access on port 22 from `0.0.0.0/0`, meaning the SSH service was reachable from the entire internet.

**Why nothing warned you:** The infrastructure configuration did not restrict the SSH source CIDR, and no security check was enforcing a private-network-only SSH rule.

**Fix:** Restricted the SSH ingress rule to `10.0.0.0/16` instead of `0.0.0.0/0`.

**What an attacker does with this:** An internet-exposed SSH service can be continuously targeted by automated scanners and brute-force attacks. If valid credentials or another SSH vulnerability are found, an attacker could gain access to the server.

## 9. `count` instead of `for_each`

**Plan with `count`, after removing `staging`:** Removing the middle item from `["dev", "staging", "prod"]` changes the numeric indexes. `dev` remains at index 0, but `prod` moves from index 2 to index 1, so Terraform can plan to destroy and recreate the resource associated with the changed index.

**Plan with `for_each`, same edit:** With `for_each = toset(var.environments)`, resources are identified by environment names such as `env["dev"]`, `env["staging"]`, and `env["prod"]`. Removing `staging` removes only `env["staging"]`; `dev` and `prod` keep their identities.

**Why this is the most dangerous defect in the list:** Using `count` with a list can cause existing infrastructure to be replaced when the list order changes or an item is removed. That can lead to unnecessary resource destruction and recreation, which is especially dangerous for production infrastructure.

