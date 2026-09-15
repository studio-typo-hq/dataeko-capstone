# Triage

## 1. \`scripts/ingest.sh\` is not executable

**Symptom:** The verifier initially reported that \`scripts/ingest.sh\` was not executable.

**Cause:** The executable permission was missing.

**Fix:** Ran \`chmod +x scripts/ingest.sh\` and \`git update-index --chmod=+x scripts/ingest.sh\`.

**Proof:** The file mode is \`-rwxr-xr-x\`.

**Why \`git update-index --chmod=+x\` was also needed:** Git must record the executable bit so the permission is preserved when the repository is cloned elsewhere.

## 2. Unquoted \`$1\` in \`scripts/ingest.sh\`

**Symptom:** The script used \`$1\` without quotes.

**Cause:** An unquoted shell variable can be split when a path contains spaces.

**Fix:** Changed the file check to use \`"$1"\`.

**Proof:** \`if [ ! -f "$1" ]; then\`

## 3. Dockerfile copies source before installing dependencies

**Symptom:** The Dockerfile dependency layer was not in the required order.

**Cause:** Dependencies should be installed before copying application source.

**Fix:** Copied the requirements file, installed dependencies, then copied the source.

**Proof:** COPY requirements is line 5, RUN pip install is line 6, and COPY . . is line 8.

## 4. No `.dockerignore`

**Symptom:** \`.dockerignore\` was missing.

**Cause:** Docker had no explicit exclusions for unnecessary repository files.

**Fix:** Added \`.dockerignore\`.

**Proof:** It contains \`.git\`, \`.terraform/\`, \`__pycache__/\`, \`*.pyc\`, and \`.venv/\`.

## 5. API key committed to the repository

**Symptom:** A hardcoded API key was present in \`api/config.py\`.

**Cause:** The credential was stored directly in source code.

**Fix:** Changed \`API_KEY\` and \`ADMIN_KEY\` to use environment variables.

**Is the key gone now that you deleted the line?** It is gone from the current working tree, but deleting it does not remove it from Git history.

**What would you have to do in real life?** Revoke and rotate the exposed credential and remove the secret from repository history using an approved secret-remediation process.

## 6. \`requests\` call with no timeout

**Symptom:** The HTTP request had no timeout.

**Cause:** A request without a timeout can wait indefinitely if the remote service stops responding.

**Fix:** Added a 10-second timeout.

**Proof:** \`response = requests.get(url, timeout=10)\`

**Why a hang is worse than an error:** An explicit error can be handled or retried, while an indefinitely blocked request can keep workers occupied.

## 7. Missing index on \`orders.customer_id\`

**Symptom:** The query initially used a sequential scan.

**Plan before:** Parallel Seq Scan on orders; Execution Time: 23.278 ms.

**Plan after:** Bitmap Index Scan on idx_orders_customer_id; Index Cond: customer_id = 4242; Execution Time: 0.349 ms.

**Timings, three runs each:** Before: 25.832 ms, 24.247 ms, 23.278 ms. After: 0.349 ms, 0.510 ms, 0.497 ms.

**Why the planner changed its mind:** The index lets PostgreSQL locate matching rows without scanning the entire orders table, making the index-based plan much cheaper.

## 8. SSH open to `0.0.0.0/0`

**Symptom:** SSH port 22 was accessible from every IPv4 address.

**Why nothing warned you:** Terraform can describe an insecure network rule without automatically blocking it.

**Fix:** Restricted SSH access to \`10.0.0.0/16\`.

**Proof:** Port 22 now has \`cidr_blocks = ["10.0.0.0/16"]\`.

**What an attacker does with this:** An internet-exposed SSH service can be scanned and subjected to credential attacks or exploitation of vulnerable services.

## 9. \`count\` instead of \`for_each\`

**Plan with \`count\`, after removing staging:** The temporary plan used indexed addresses \`aws_s3_bucket.env[0]\` and \`aws_s3_bucket.env[1]\`.

**Plan with \`for_each\`, same edit:** The fixed configuration uses stable environment keys such as \`aws_s3_bucket.env["dev"]\` and \`aws_s3_bucket.env["prod"]\`.

**Why this is the most dangerous defect in the list:** With \`count\`, removing an item from the middle of a list changes the indexes of later resources. \`for_each\` gives each environment a stable key and avoids this index-based churn.
