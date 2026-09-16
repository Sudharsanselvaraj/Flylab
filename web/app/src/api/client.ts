const BASE = "/api";

export async function fetchRuns() {
  const r = await fetch(`${BASE}/experiments`);
  if (!r.ok) throw new Error(`GET /experiments ${r.status}`);
  return r.json() as Promise<{ runs: Array<{ run_id: string; stimuli: string[]; path: string }> }>;
}

export async function fetchRun(runId: string) {
  const r = await fetch(`${BASE}/experiments/${runId}`);
  if (!r.ok) throw new Error(`GET /experiments/${runId} ${r.status}`);
  return r.json();
}

export async function fetchNeural(runId: string, stimulus: string) {
  const r = await fetch(`${BASE}/experiments/${runId}/neural?stimulus=${encodeURIComponent(stimulus)}`);
  if (!r.ok) throw new Error(`GET /experiments/${runId}/neural ${r.status}`);
  return r.json();
}

export async function fetchDecoder(runId: string) {
  const r = await fetch(`${BASE}/experiments/${runId}/decoder`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchProvenance(runId: string) {
  const r = await fetch(`${BASE}/experiments/${runId}/provenance`);
  if (!r.ok) return null;
  return r.json();
}

export async function startRun(runId: string, stimulus: string) {
  const r = await fetch(`${BASE}/experiments/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId, stimulus }),
  });
  if (!r.ok) throw new Error(`POST /experiments/run ${r.status}`);
  return r.json() as Promise<{ run_id: string; mode: string; stimulus: string }>;
}

export function openStream(runId: string): WebSocket {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${proto}//${location.host}/api/experiments/${runId}/stream`);
  return ws;
}
