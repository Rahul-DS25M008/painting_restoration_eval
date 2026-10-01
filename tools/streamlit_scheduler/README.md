# Independent Streamlit availability scheduler

This small Cloudflare Worker replaces reliance on GitHub's native scheduled
trigger, not the successful GitHub Actions browser check.

Cloudflare Cron -> GitHub `workflow_dispatch` -> existing Playwright check ->
rendered Streamlit dashboard (including its normal public wake-up button).

No notebooks, scientific outputs, application UI or model inference are changed.
This is best-effort availability maintenance, not a 24/7 uptime guarantee. It
still depends on Cloudflare, GitHub runners, the token and Streamlit being available.

Status as of 2026-09-04: three dispatched GitHub runs completed successfully
(33864857726, 33865632846 and 33866417033). These verified the ten-minute test
schedule. The owner subsequently changed Cloudflare to a 30-minute interval;
that interval is owner-reported, not independently verified here. The repository
now removes the canary and native GitHub schedule, retaining the dispatch workflow.

## Controlled-300 target update — 2026-10-01

The workflow on `main` now targets
https://fhtw-painting-restoration-main.streamlit.app/. The checked-in Worker
already sets `const REF = "main"`. The owner also changed the deployed Worker to
`main` and confirmed a successful scheduled invocation. GitHub records successful
push run [36858527530](https://github.com/Rahul-DS25M008/painting_restoration_eval/actions/runs/36858527530)
and workflow-dispatch run [36859028102](https://github.com/Rahul-DS25M008/painting_restoration_eval/actions/runs/36859028102),
both at `e2b54a695a99ace715adbaee8a7ff21f7a407780`. The latter's automatic
Cloudflare attribution is owner-confirmed; GitHub verifies the dispatch event
and successful result. No further branch migration is pending.
A GitHub push does not update dashboard-managed Worker code. Its existing
secret, cron interval and permissions remain unchanged. The Worker
dispatches the workflow; the Python checker owns the app URL.

The checker waits for the full-version Foyer, all eight room links and a decoded
painting, opens/dismisses the visitor guide, then follows Case Explorer and
requires five decoded evidence images plus its model/metric controls. It retains
the public wake button, stable-ready interval and bounded timeout. It does not
download reports, sweep all filters, compute science, or certify N35. Recurring
visits remain best-effort, not an indefinite uptime guarantee.

Changes to the workflow/checker/tests on `main` also trigger a one-off `push`
verification. This does not add another periodic schedule. A successful push
run proves Actions and the new target work; the next Cloudflare-triggered
`workflow_dispatch` run separately verifies continuing scheduled dispatch.

Retargeting this monitor does **not** redirect or rename the old public app.
The `pilot-50-dashboard` branch and old Streamlit deployment are left intact;
URL promotion is a separate owner-controlled step.

## Files

- `worker.mjs`: complete Worker code to paste into the Cloudflare editor.
- `worker.test.mjs`: offline Node tests with mocked requests; no real token needed.
- `.gitignore`: excludes local secret files and optional tool caches.

## Recommended setup: Cloudflare dashboard only

No Node installation, deployment CLI, custom domain, paid plan or GitHub
repository integration is needed for this route. Do not import the thesis repo
into Cloudflare Builds; only the Worker code is needed. UI labels may vary slightly.

### 1. Keep the existing workflow available

Keep `.github/workflows/streamlit-availability.yml` enabled on `main` with
`workflow_dispatch`. The Worker calls this exact workflow in
`Rahul-DS25M008/painting_restoration_eval`. The workflow already checks the fixed
public app URL: https://fhtw-painting-restoration-main.streamlit.app/.

Do not delete or disable the availability workflow after setup. It remains the
execution engine. The canary and native GitHub cron were removed and committed
after successful verification. The Cloudflare dashboard owns the live schedule.

### 2. Create a narrowly scoped GitHub token

In GitHub, open your personal Settings -> Developer settings -> Personal access
tokens -> Fine-grained tokens -> Generate new token.

- Token name: `Cloudflare Streamlit scheduler`.
- Resource owner: `Rahul-DS25M008`.
- Repository access: **Only select repositories**, then `painting_restoration_eval`.
- Repository permission: **Actions: Read and write**.
- Leave other permissions unchanged; Metadata read access is automatic.
- Set an explicit expiry (for example, 90 days), and record a reminder to rotate
  it before that date. Do not use a broader classic token for convenience.

Generate and copy the token directly into the Cloudflare secret in step 4.
Do not paste it into chat, source code, a screenshot, a commit, a terminal command
or a plaintext Cloudflare variable. Actions write is required to dispatch; it is
not restricted to this one workflow by GitHub, so keep repository access narrow.

### 3. Create the Worker and paste its code

1. Sign in to https://dash.cloudflare.com/ and use the Workers Free plan.
2. Go to **Workers & Pages** and create a new Worker using the basic starter
   (the Hello World/editor route if offered), not a GitHub repository import.
3. Name it `streamlit-keepalive-dispatcher` and create/deploy the starter.
4. Open **Edit code**. Replace the entire starter JavaScript module with the
   contents of `worker.mjs` in this directory. It can remain named `worker.js`
   in the dashboard; the source is standard module JavaScript.
5. Deploy the updated code.

An HTTP preview returning **404 with "Scheduled dispatcher only" is intentional**.
Opening its URL cannot dispatch a workflow. No authenticated HTTP trigger or
public dispatch endpoint is required. You can disable workers.dev and preview
URLs under Domains & Routes if the dashboard offers those options; cron still works.

### 4. Add the secret and enable logs

In the Worker -> **Settings -> Variables and Secrets -> Add**:

- Type: **Secret**.
- Name: `GITHUB_TOKEN` (exact spelling).
- Value: the fine-grained token from step 2.
- Deploy/save the change.

Return to **Deployments** and confirm that the version containing `Add secret:
GITHUB_TOKEN` is the active deployment at 100%. If it appears only in Version
History, deploy/promote that version; saving a version is not proof it is active.

Enable **Workers Logs** in the Worker's observability settings if not already
enabled. The Worker logs safe dispatch metadata, including the resulting GitHub
run link when returned. It never prints the token or arbitrary API response bodies.

Do not add the token as a GitHub Actions secret. Cloudflare, not the workflow,
uses it. The workflow retains its existing read-only repository permissions.

### 5. Prove automatic triggering before switching to the final schedule

Open Worker -> **Settings -> Triggers -> Cron Triggers** (some screens label this
Trigger Events). Add **one temporary test schedule**:

```text
7,17,27,37,47,57 * * * *
```

This fires at those UTC minutes. Allow up to 15 minutes for trigger propagation;
the Past Cron Events view can lag by up to 30 minutes for a new Worker. Leave the
configuration unchanged while testing, and check Workers Logs and GitHub Actions.
Do not leave this ten-minute schedule running after the test.

Verify the complete chain:

1. Cloudflare records an automatic cron invocation and a log with
   `status: dispatch_accepted_not_health_verified` and a `run_url`.
2. A new run appears in [GitHub Actions](https://github.com/Rahul-DS25M008/painting_restoration_eval/actions/workflows/streamlit-availability.yml).
3. Its event is **workflow_dispatch**, not schedule. That is correct: Cloudflare
   called the same API used to dispatch a workflow manually.
4. That run finishes successfully and the browser-check log reports `status: ready`.
5. Repeat for a second automatic invocation to demonstrate recurrence.

A successful Worker invocation only proves dispatch acceptance, not app readiness.
The Worker does not poll the resulting job. Use the GitHub run result for that.
A manually launched Actions run does not prove that Cloudflare cron works.

### 6. Set the operating schedule

After two successful automatic tests, **replace**, rather than supplement, the
temporary schedule with:

```text
*/30 * * * *
```

The current chosen interval is every 30 minutes: 48 checks per day. The example
above fires at minutes 00 and 30 UTC. The owner reported the interval, not the
dashboard's exact minute offset. The actual schedule is configured exclusively
in Cloudflare; this guide does not create or override it.

For the planned later change to hourly checks, replace the Cloudflare trigger with
`0 * * * *` (24 checks per day). No GitHub workflow change or Worker-code redeploy
is needed for a dashboard-only cron change. Update this guide when the operating
interval changes so the documentation stays accurate. Vienna summer time is UTC+2;
winter is UTC+1. All cron times are UTC.

Confirm there is exactly **one** Cloudflare cron trigger, then verify at least one
automatic run after each interval change. No local deployment configuration is
required for this dashboard-managed setup.

### 7. Verified cleanup and retained execution workflow

After three successful automatic test runs, the following cleanup was committed
in `4e47ef0f` and `7a035468`:

- The owner deleted `.github/workflows/schedule-canary.yml`.
- The native `schedule:` block was removed from `.github/workflows/streamlit-availability.yml`.
- `workflow_dispatch`, the job, its tests, permissions and concurrency remain intact.
- The workflow comments now describe the Cloudflare trigger.
- The unused local deployment configuration was deleted; scheduling is dashboard-only.

The previously verified runs predate these cleanup commits. A subsequent successful
Cloudflare-triggered run confirms operation against the cleaned-up workflow.

**Do not delete or disable `streamlit-availability.yml`.** That would break this
method. Existing workflow concurrency serializes runs; it does not deduplicate
visits if multiple triggers fire. Keep the browser checker, its tests and this
scheduler directory. Do not recreate the canary for normal operation.

## Maintenance and troubleshooting

| Observation | What to check |
| --- | --- |
| No Cloudflare invocation | Cron saved, correct Worker/account, UTC time and propagation/log delay. |
| Missing GITHUB_TOKEN | Add a Secret with the exact name and deploy it. |
| GitHub HTTP 401 | Token expired, revoked or entered incorrectly. |
| GitHub HTTP 403/404 | Repository selection, Actions write permission, workflow enabled on main, account policy or rate limit. A 404 can also hide inaccessible resources. |
| GitHub HTTP 422 | Workflow/branch/dispatch configuration does not match the fixed target. |
| Network timeout or GitHub server error | Check Actions before retrying: GitHub might already have accepted the dispatch. There is no automatic POST retry. |
| invalid_fetch_receiver | Redeploy the latest worker.mjs; it preserves globalThis as the fetch receiver. |
| invalid_redirect_option | Redeploy the latest worker.mjs: it uses manual redirect handling, not error. The workerd runtime rejects error mode before sending the request. All 3xx responses are rejected without following them or forwarding the token. |
| invalid_request_header_check_secret_format | Re-enter the Secret as the raw token only, with no quotes, Bearer prefix or line breaks. Do not share its value. |
| timeout_api_unavailable | Check the deployed runtime compatibility date and share only the safe error classification. |
| Dispatch accepted, Actions failed | Read the GitHub job log; dispatch success is not dashboard health. |
| Actions succeeded, app later sleeps | Review gaps in successful runs, token expiry and Streamlit service state; this does not guarantee always-on hosting. |
| Preview returns 404 | Expected: ordinary HTTP requests cannot trigger the scheduled check. |

Enable GitHub Actions failure notifications in your account's notification
settings. Those report failed runs, not absent invocations; periodically check
that recent runs actually exist. No separate dead-man's-switch monitor is included.
Rotate the token before expiry by updating the Cloudflare Secret and deploying it.
Revoke the old token after a successful test. Never share secret-bearing screenshots.

To stop the schedule, remove the Cloudflare cron trigger; for complete retirement,
also revoke its GitHub token. Before an important presentation, independently open
the Streamlit app and confirm it is ready.

## Optional local checks

The dashboard route above is sufficient. No npm packages are required for the
offline tests; Node 22+ can run these from this directory:

```powershell
node --check worker.mjs
node --test worker.test.mjs
```

These commands only check local code; they do not deploy or change the schedule.
Manage deployments, secrets and cron through the Cloudflare dashboard. Dashboard
code edits do not update this repository automatically; keep `worker.mjs` in sync.
Local tests mock GitHub and are not evidence of a live Cloudflare deployment.
Node's request implementation is not a substitute for workerd runtime validation:
in particular, Node accepts redirect error mode while workerd rejects it. The
Worker therefore uses manual mode and explicitly rejects redirects.

## Official references (checked 2026-09-04)

- [Cloudflare dashboard setup](https://developers.cloudflare.com/workers/get-started/dashboard/).
- [Cron setup, UTC scheduling, propagation and event history](https://developers.cloudflare.com/workers/configuration/cron-triggers/).
- [Cloudflare secrets](https://developers.cloudflare.com/workers/configuration/secrets/).
- [Cloudflare scheduled handler](https://developers.cloudflare.com/workers/runtime-apis/handlers/scheduled/).
- [Cloudflare free-tier limits](https://developers.cloudflare.com/workers/platform/limits/).
- [GitHub dispatch API and fine-grained token permissions](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).
- [GitHub personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).
