# Triage

> Replace every `TODO`. One section per defect, nine in total.
> For each one: what you saw, why it happened, what you changed, and how you
> proved it is fixed. Paste real output — not a description of output.

## 1. `scripts/ingest.sh` is not executable

**Symptom:** `scripts/ingest.sh` did not have execute permission. `ls -l scripts/ingest.sh` showed `-rw-r--r--`.

**Cause:** The executable bit was not set on the file.

**Fix:** Ran `chmod +x scripts/ingest.sh` and then `git update-index --chmod=+x scripts/ingest.sh` so Git tracks the executable mode.

**Proof:**

```text
$ ls -l scripts/ingest.sh
-rwxr-xr-x  1 deekshithakarri  staff  730 10 Sep 22:11 scripts/ingest.sh

$ git diff --cached --summary
 mode change 100644 => 100755 scripts/ingest.sh
```

## 2. Unquoted `$1` in `scripts/ingest.sh`

**Symptom:** The script used an unquoted `$1` when checking whether the supplied CSV file existed. This caused paths containing spaces to be split into multiple arguments.

**Cause:** The file test used `$1` without quotes:

```bash
if [ ! -f $1 ]; then
```

Shell word splitting can break a path such as `data/march orders.csv` into separate arguments.

**Fix:** Quoted `$1` in the file-existence check:

```bash
if [ ! -f "$1" ]; then
```

The other uses of `$1` in the script were already inside double quotes.

**Proof:**

Tested the script with a CSV filename containing a space:

```text
$ cp data/orders.csv "data/march orders.csv"

$ ./scripts/ingest.sh "data/march orders.csv"
staged march orders.csv — 209 data rows

$ ls -l "data/staging/march orders.csv"
-rw-r--r--@ 1 deekshithakarri  staff  10105  10 Sep 22:37 data/staging/march orders.csv
```

The script successfully processed and staged the file with a space in its filename.

## 3. Dockerfile copies source before installing dependencies

**Symptom:** TODO

**Cause:** TODO

**Fix:** TODO

**Proof (build output, before and after):** TODO

## 4. No `.dockerignore`

**Symptom:** TODO

**Cause:** TODO

**Fix:** TODO

**Proof (context size, before and after):** TODO

## 5. Hardcoded API key

**Symptom:** TODO

**Cause:** TODO

**Fix:** TODO

**Proof:** TODO

## 6. `requests` call has no timeout

**Symptom:** TODO

**Cause:** TODO

**Fix:** TODO

**Proof:** TODO

## 7. Missing index migration

**Symptom:** TODO

**Cause:** TODO

**Fix:** TODO

**Proof (EXPLAIN and timing, before and after):** TODO

## 8. SSH port 22 is open to the world

**Symptom:** TODO

**Cause:** TODO

**Fix:** TODO

**Proof:** TODO

## 9. Terraform uses `count` for environment-specific buckets

**Symptom:** TODO

**Cause:** TODO

**Fix:** TODO

**Proof (plan before and after removing staging):** TODO
