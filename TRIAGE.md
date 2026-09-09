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
