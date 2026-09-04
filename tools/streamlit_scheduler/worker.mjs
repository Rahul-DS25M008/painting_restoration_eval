// Cloudflare Cron -> GitHub workflow_dispatch -> existing browser checker.
// No token values belong in this file. Set GITHUB_TOKEN as a Worker secret.
const REPOSITORY = "Rahul-DS25M008/painting_restoration_eval";
const WORKFLOW = "streamlit-availability.yml";
const REF = "main";
const API_URL = `https://api.github.com/repos/${REPOSITORY}` +
  `/actions/workflows/${WORKFLOW}/dispatches`;

// Keep fetch attached to globalThis: Workers host methods can require their
// original receiver, unlike the permissive fetch mock used in the first tests.
export async function dispatchWorkflow(
  env,
  fetchImpl = (url, options) => globalThis.fetch(url, options),
) {
  if (typeof env.GITHUB_TOKEN !== "string" || !env.GITHUB_TOKEN.trim()) {
    throw new Error("Missing GITHUB_TOKEN Worker secret; no dispatch attempted.");
  }

  let response;
  try {
    response = await fetchImpl(API_URL, {
      method: "POST",
      // workerd supports follow/manual, not the browser's error mode.
      // Never follow redirects with Authorization; reject 3xx below instead.
      redirect: "manual",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${env.GITHUB_TOKEN.trim()}`,
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "painting-restoration-availability-scheduler",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: REF }),
      signal: AbortSignal.timeout(20000),
    });
  } catch (error) {
    // Do not print raw request/errors: they might contain credentials.
    // No automatic POST retry: a timeout can occur after GitHub accepts a run.
    const name = ["TypeError", "Error", "AbortError", "TimeoutError"].includes(error?.name)
      ? error.name : "UnknownError";
    const message = String(error?.message ?? "").toLowerCase();
    // Only fixed classifications are logged, never the raw error or token.
    let reason = "fetch_failed";
    if (message.includes("illegal invocation") || message.includes("this reference")) {
      reason = "invalid_fetch_receiver";
    } else if (message.includes("redirect")) {
      reason = "invalid_redirect_option";
    } else if (message.includes("abortsignal.timeout")) {
      reason = "timeout_api_unavailable";
    } else if (message.includes("header") || message.includes("byte string") ||
               message.includes("bytestring")) {
      reason = "invalid_request_header_check_secret_format";
    } else if (name === "TimeoutError" || name === "AbortError") {
      reason = "request_aborted_or_timed_out";
    }
    throw new Error(
      `GitHub dispatch failed [${name}/${reason}]; acceptance is unknown. ` +
      "Check Actions before manually retrying.",
    );
  }

  if (response.status !== 200 && response.status !== 204) {
    // Do not log arbitrary response bodies or headers.
    throw new Error(`GitHub dispatch rejected: HTTP ${response.status}. ` +
      "Check token expiry/Actions permission, workflow availability and API limits.");
  }

  // Current API returns 200 + run details; retain compatibility with 204.
  let details = {};
  if (response.status === 200) {
    try {
      details = (await response.json()) ?? {};
    } catch {
      // The dispatch was accepted even if its response body cannot be decoded.
    }
  }
  const runId = Number.isSafeInteger(details.workflow_run_id) &&
    details.workflow_run_id > 0 ? details.workflow_run_id : null;
  return {
    status: "dispatch_accepted_not_health_verified",
    repository: REPOSITORY,
    workflow: WORKFLOW,
    ref: REF,
    workflow_run_id: runId,
    run_url: runId
      ? `https://github.com/${REPOSITORY}/actions/runs/${runId}`
      : `https://github.com/${REPOSITORY}/actions/workflows/${WORKFLOW}`,
    dispatched_at_utc: new Date().toISOString(),
  };
}

export default {
  async scheduled(controller, env) {
    // Supported by current Cloudflare runtimes; avoid retrying ambiguous POSTs.
    if (typeof controller.noRetry === "function") controller.noRetry();
    const result = await dispatchWorkflow(env);
    console.log(JSON.stringify({ ...result, cron: controller.cron }));
  },

  async fetch() {
    // Dashboard preview / public requests never dispatch or inspect secrets.
    return new Response("Scheduled dispatcher only; HTTP requests do not trigger checks.\n", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  },
};
