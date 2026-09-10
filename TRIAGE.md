# Triage

> Replace every `TODO`. One section per defect, nine in total.
> For each one: what you saw, why it happened, what you changed, and how you
> proved it is fixed. Paste real output — not a description of output.

## 1. `scripts/ingest.sh` is not executable

**Symptom:** `scripts/ingest.sh` did not have the executable bit set.

**Cause:** The file permissions were `100644`, so Git did not mark the script as executable.

**Fix:** Set the executable bit and recorded the permission change in Git:

```text
chmod +x scripts/ingest.sh
git update-index --chmod=+x scripts/ingest.sh
```

**Proof:**

```text
$ ls -l scripts/ingest.sh
-rwxr-xr-x ... scripts/ingest.sh

$ git diff --cached --summary
mode change 100644 => 100755 scripts/ingest.sh
```

The executable-bit change was committed in:

```text
58182db fix(ingest): make ingest script executable
```

## 2. Unquoted `$1` in `scripts/ingest.sh`

**Symptom:** The input path was not quoted in the file existence check. A filename containing spaces could therefore be split into multiple arguments.

**Cause:** The original code used:

```bash
if [ ! -f $1 ]; then
```

The shell performs word splitting on an unquoted `$1`.

**Fix:** Quoted the input path:

```bash
if [ ! -f "$1" ]; then
```

**Proof:** Created a test copy with a space in its filename and passed the quoted path to the script:

```text
$ ./scripts/ingest.sh "data/march orders.csv"
staged march orders.csv — 209 data rows

$ ls -l "data/staging/march orders.csv"
-rw-r--r--@ ... data/staging/march orders.csv
```

The test file and staged copy were removed after verification.

The code fix was committed in:

```text
1910602 fix(ingest): quote input path
```

## 3. Dockerfile copies source before installing dependencies

**Symptom:** The original Dockerfile copied the entire source tree before running `pip install`. A source/context change therefore invalidated the dependency-install layer and caused dependencies to be installed again.

**Cause:** The original layer order was:

```text
COPY . .
RUN pip install --no-cache-dir -r api/requirements.txt
```

Because the `COPY . .` layer changed when source files changed, Docker also had to rerun the following `pip install` layer.

**Fix:** Copied only `api/requirements.txt` first, installed dependencies, and copied the application source afterward:

```text
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt
COPY . .
```

This keeps the dependency layer cached when only application source files change.

**Proof (build output, before and after):**

Before the fix, a normal build showed:

```text
[3/4] COPY . .
[4/4] RUN pip install --no-cache-dir -r api/requirements.txt
```

The dependency installation took approximately 6.1 seconds.

A controlled build after creating `cache-test.txt` also showed the dependency layer being rerun under the defective ordering:

```text
[3/4] COPY . .
[4/4] RUN pip install --no-cache-dir -r api/requirements.txt
```

The `pip install` step took approximately 7.3 seconds.

After the fix, the first build showed:

```text
[3/5] COPY api/requirements.txt api/requirements.txt
[4/5] RUN pip install --no-cache-dir -r api/requirements.txt
[5/5] COPY . .
```

The dependency installation took 7.0 seconds on the first build.

After creating a harmless source/context change with `touch cache-test.txt`, the second build showed:

```text
CACHED [2/5] WORKDIR /app
CACHED [3/5] COPY api/requirements.txt api/requirements.txt
CACHED [4/5] RUN pip install --no-cache-dir -r api/requirements.txt
[5/5] COPY . .
```

The second build completed in 1.6 seconds.

This proves that a source/context change no longer reruns the dependency installation layer.
## 4. No `.dockerignore`

**Symptom:** The repository did not contain a `.dockerignore` file, so unnecessary repository and local development files could be included in the Docker build context.

**Cause:** No Docker build-context exclusion rules had been configured.

**Fix:** Added `.dockerignore` with exclusions for Git metadata, Terraform state/configuration, Python bytecode/cache files, and the local virtual environment:

```text
.git
.terraform/
__pycache__/
*.pyc
.venv/
## 5. Hardcoded API key

**Symptom:** A credential was committed directly in `api/config.py` and duplicated in the GitHub Actions workflow.

**Cause:** The API key was stored as a hardcoded string instead of being supplied through an environment variable and GitHub Actions secret.

**Fix:** Updated `api/config.py` to read `API_KEY` from the `API_KEY` environment variable. Updated `.github/workflows/ci.yml` to provide the value through the GitHub Actions `secrets.API_KEY` secret.

**Proof:** The hardcoded value `dataeko-capstone-2026-secret` is no longer present in either `api/config.py` or `.github/workflows/ci.yml`. The application now uses `os.environ.get("API_KEY")`, and the CI workflow uses `${{ secrets.API_KEY }}`.
## 6. `requests` call without timeout

**Symptom:** The reference API request in `ingest/loader.py` could wait indefinitely if the server accepted the connection but stopped responding.

**Cause:** The `requests.get()` call did not specify a timeout.

**Fix:** Added a 10-second timeout to the request:

```python
response = requests.get(url, timeout=10)

## 7. Missing index on `orders(customer_id)`

**Symptom:** The `orders.customer_id` foreign-key column had no supporting index, which can make customer-based order lookups slower as the orders table grows.

**Cause:** The schema defined the foreign key but did not create an index on `orders.customer_id`.

**Fix:** Added the SQL migration `sql/migrations/001_add_orders_customer_id_index.sql` containing a `CREATE INDEX` on `orders(customer_id)`.

**Proof:** The migration exists under `sql/migrations/` and creates an index on `orders(customer_id)`. The Phase 0 verifier checks for an SQL migration containing `CREATE INDEX`.
