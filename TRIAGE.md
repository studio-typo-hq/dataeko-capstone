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
