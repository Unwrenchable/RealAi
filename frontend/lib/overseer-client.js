const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function fetchWorldstate() {
  const res = await fetch(${API_BASE}/overseer/worldstate);
  if (!res.ok) throw new Error("Failed to fetch worldstate");
  return res.json();
}

export async function pushPlayerEvent(event) {
  const res = await fetch(${API_BASE}/overseer/event, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event),
  });
  if (!res.ok) throw new Error("Failed to push event");
  return res.json();
}
