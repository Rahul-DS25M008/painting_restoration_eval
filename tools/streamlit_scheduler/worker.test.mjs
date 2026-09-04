import assert from "node:assert/strict";
import test from "node:test";
import worker, { dispatchWorkflow } from "./worker.mjs";

const env = { GITHUB_TOKEN: "fake-unit-test-token-not-a-credential" };

test("dispatches only the fixed repository, workflow and main branch", async () => {
  let calls = 0;
  const result = await dispatchWorkflow(env, async (url, options) => {
    calls++;
    assert.equal(url, "https://api.github.com/repos/Rahul-DS25M008/" +
      "painting_restoration_eval/actions/workflows/streamlit-availability.yml/dispatches");
    assert.equal(options.method, "POST");
    assert.equal(options.redirect, "manual");
    assert.equal(options.headers.Authorization, `Bearer ${env.GITHUB_TOKEN}`);
    assert.equal(options.headers["X-GitHub-Api-Version"], "2026-03-10");
    assert.deepEqual(JSON.parse(options.body), { ref: "main" });
    assert.ok(options.signal instanceof AbortSignal);
    return Response.json({ workflow_run_id: 123, html_url: "untrusted-url" });
  });
  assert.equal(calls, 1);
  assert.equal(result.status, "dispatch_accepted_not_health_verified");
  assert.equal(result.workflow_run_id, 123);
  assert.equal(result.run_url,
    "https://github.com/Rahul-DS25M008/painting_restoration_eval/actions/runs/123");
  assert.ok(!JSON.stringify(result).includes(env.GITHUB_TOKEN));
});

test("handles 204 without trying to decode an empty body", async () => {
  const result = await dispatchWorkflow(env, async () => new Response(null, { status: 204 }));
  assert.equal(result.workflow_run_id, null);
  assert.match(result.run_url, /actions\/workflows\/streamlit-availability.yml$/);
});

test("accepted response with malformed body does not cause a duplicate dispatch", async () => {
  let calls = 0;
  const result = await dispatchWorkflow(env, async () => {
    calls++;
    return new Response("not json", { status: 200 });
  });
  assert.equal(calls, 1);
  assert.equal(result.workflow_run_id, null);
});

test("rejects missing and empty secrets before any network call", async () => {
  for (const secret of [undefined, "", "  "]) {
    await assert.rejects(dispatchWorkflow({ GITHUB_TOKEN: secret }, async () => {
      assert.fail("Network must not be called");
    }), /Missing GITHUB_TOKEN/);
  }
});

test("rejects API errors without exposing their body or retrying", async () => {
  for (const status of [301, 302, 303, 307, 308, 401, 403, 404, 422, 429, 500]) {
    let calls = 0;
    await assert.rejects(dispatchWorkflow(env, async () => {
      calls++;
      return new Response(env.GITHUB_TOKEN, { status });
    }), (error) => error.message.includes(`HTTP ${status}`) &&
      !error.message.includes(env.GITHUB_TOKEN));
    assert.equal(calls, 1);
  }
});

test("network errors are redacted and not retried", async () => {
  let calls = 0;
  await assert.rejects(dispatchWorkflow(env, async () => {
    calls++;
    throw new Error(env.GITHUB_TOKEN);
  }), (error) => error.message.includes("acceptance is unknown") &&
    !error.message.includes(env.GITHUB_TOKEN));
  assert.equal(calls, 1);
});

test("ordinary HTTP requests never dispatch", async () => {
  const result = await worker.fetch();
  assert.equal(result.status, 404);
  assert.match(await result.text(), /do not trigger checks/);
});

test("default fetch preserves the Workers host-method receiver", async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async function () {
      if (this !== globalThis) {
        throw new TypeError("Illegal invocation: function called with incorrect this reference");
      }
      return Response.json({ workflow_run_id: 789 });
    };
    // Reproduce the old detached-call defect, then check the production default.
    await assert.rejects(dispatchWorkflow(env, globalThis.fetch), /invalid_fetch_receiver/);
    const result = await dispatchWorkflow(env);
    assert.equal(result.workflow_run_id, 789);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("diagnostic classifications never disclose raw exception text", async () => {
  for (const [message, classification] of [
    ["Invalid header value", "invalid_request_header_check_secret_format"],
    ["Invalid redirect value, must be one of follow or manual", "invalid_redirect_option"],
    ["AbortSignal.timeout is not a function", "timeout_api_unavailable"],
  ]) {
    await assert.rejects(dispatchWorkflow(env, async () => {
      throw new TypeError(`${message}: ${env.GITHUB_TOKEN}`);
    }), (error) => error.message.includes(classification) &&
      !error.message.includes(env.GITHUB_TOKEN));
  }
});

test("scheduled handler awaits dispatch, logs only safe details and disables retries", async () => {
  const originalFetch = globalThis.fetch;
  const originalLog = console.log;
  let noRetryCalled = false;
  const logs = [];
  try {
    globalThis.fetch = async () => Response.json({ workflow_run_id: 456 });
    console.log = (message) => logs.push(JSON.parse(message));
    await worker.scheduled({ cron: "17 */3 * * *", noRetry() { noRetryCalled = true; } }, env);
    assert.equal(noRetryCalled, true);
    assert.equal(logs.length, 1);
    assert.equal(logs[0].workflow_run_id, 456);
    assert.equal(logs[0].cron, "17 */3 * * *");
    assert.ok(!JSON.stringify(logs).includes(env.GITHUB_TOKEN));
    await assert.rejects(worker.scheduled({ cron: "17 */3 * * *" }, {}), /Missing GITHUB_TOKEN/);
  } finally {
    globalThis.fetch = originalFetch;
    console.log = originalLog;
  }
});
