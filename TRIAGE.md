# Triage

> For each one: what you saw, why it happened, what you changed, and how you
> proved it is fixed. Paste real output — not a description of output.

## 1. `scripts/ingest.sh` is not executable
**Symptom:** `scripts/ingest.sh` was tracked as mode 644 and wasn't executable
**Cause:** The executable bit was missing from the file.
**Fix:** i ran the cammand "chmod +x scripts/ingest.sh" to give execution access.
**Proof:** `git diff --cached --summary` showed `mode change 100644 => 100755`
**Why `git update-index --chmod=+x` was also needed:** "chmod +x scripts/ingest.sh" cammand only changes the permission for my mac so to make sure it will preserve its executable permission whenever someone else pull it from git we had to run this cammand. 

## 2. Unquoted `$1` in `scripts/ingest.sh`
**Symptom:** Paths containing spaces could be interpreted as multiple shell arguments.

**Cause:** `$1` was used without quotes in the file existence test.

**Fix:** Changed `$1` to `"$1"`.

**Proof:** Tested with `data/my orders.csv`; the script successfully staged the file and reported `209 data rows`.

## 3. Dockerfile copies source before installing dependencies
**Symptom:** Docker could reinstall Python dependencies after ordinary source-code changes.

**Cause:** `COPY . .` occurred before dependency installation, invalidating the dependency layer whenever source changed.

**Fix:** Copied `api/requirements.txt`, installed dependencies, then copied the application source.

**Proof (build output, before and after):** Dockerfile order is now `COPY requirements → RUN pip install → COPY . .`.

## 4. No `.dockerignore`
**Symptom:** The Docker build context could include the Git repository and unnecessary local files.

**Cause:** No `.dockerignore` file existed.

**Fix:** Added `.dockerignore` and excluded `.git`, `.venv`, `__pycache__`, `*.pyc`, and Terraform state files.

**Proof (context size, before and after):** `.dockerignore` exists and excludes `.git`.

## 5. API key committed to the repository
**Symptom:** The repository contained the hardcoded API key `dataeko-capstone-2026-secret`.

**Cause:** The API key was written directly in application/configuration files.

**Fix:** Changed the application to read `API_KEY` from the environment and changed CI to read it from `${{ secrets.API_KEY }}`.

**Is the key gone now that you deleted the line?** No. Removing it from the current files does not remove it from Git history.

**What would you have to do in real life?** Immediately rotate/revoke the exposed key, create a new secret, update applications to use the new secret, and remove the leaked secret from repository history if appropriate.

## 6. `requests` call with no timeout
**Symptom:** An HTTP request could wait indefinitely.

**Cause:** The `requests` call did not specify a timeout.

**Fix:** Added `timeout=10` to the request.

**Why a hang is worse than an error:** A controlled error allows the application to recover or report failure, while an indefinite hang can consume resources and leave workers stuck.

## 7. Missing index on `orders.customer_id`
**Symptom:** Queries filtering orders by `customer_id` could require a sequential scan.

**Plan before:** `EXPLAIN ANALYZE` showed a sequential scan.

**Plan after:** After adding the index, `EXPLAIN ANALYZE` showed an index scan.

**Timings, three runs each:** Recorded in `evidence/explain-before.txt` and `evidence/explain-after.txt`.

**Why the planner changed its mind:** The index provides a faster way to locate rows matching `customer_id`, so PostgreSQL can avoid scanning the entire table.

## 8. SSH open to `0.0.0.0/0`
**Symptom:** The Terraform security rule allowed SSH connections from any IPv4 address.

**Why nothing warned you:** Infrastructure-as-Code does not automatically make an insecure network rule safe; the configuration can be syntactically valid while still being a security risk.

**Fix:** Restricted the SSH ingress CIDR to the private network range instead of `0.0.0.0/0`.

**What an attacker does with this:** An exposed SSH service can be continuously scanned and attacked through password guessing, credential theft, or exploitation of vulnerabilities.

## 9. `count` instead of `for_each`
**Plan with `count`, after removing `staging`:** Removing an item from a list can change resource indexes and cause Terraform to plan resource replacement/churn.

**Plan with `for_each`, same edit:** Resources are identified by stable environment keys, so removing `staging` does not change the identity of `dev` or `prod`.

**Why this is the most dangerous defect in the list:** Incorrect resource identity handling can cause Terraform to destroy and recreate real infrastructure unexpectedly.
