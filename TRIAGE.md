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


## 2. Unquoted `$1` in `scripts/ingest.sh`
**Symptom:** TODO
**Cause:** TODO
**Fix:** TODO
**Proof:** TODO

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

## 5. API key committed to the repository
**Symptom:** TODO
**Cause:** TODO
**Fix:** TODO
**Is the key gone now that you deleted the line?** TODO
**What would you have to do in real life?** TODO

## 6. `requests` call with no timeout
**Symptom:** TODO
**Cause:** TODO
**Fix:** TODO
**Why a hang is worse than an error:** TODO

## 7. Missing index on `orders.customer_id`
**Symptom:** TODO
**Plan before:** TODO
**Plan after:** TODO
**Timings, three runs each:** TODO
**Why the planner changed its mind:** TODO

## 8. SSH open to `0.0.0.0/0`
**Symptom:** TODO
**Why nothing warned you:** TODO
**Fix:** TODO
**What an attacker does with this:** TODO

## 9. `count` instead of `for_each`
**Plan with `count`, after removing `staging`:** TODO
**Plan with `for_each`, same edit:** TODO
**Why this is the most dangerous defect in the list:** TODO
