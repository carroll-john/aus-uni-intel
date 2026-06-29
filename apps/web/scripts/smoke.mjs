const base = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.API_BASE_URL || "http://127.0.0.1:8000";

async function main() {
  const endpoints = ["/providers", "/metrics", "/metric-catalog", "/overview", "/sources"];
  for (const endpoint of endpoints) {
    const response = await fetch(`${base}${endpoint}`);
    if (!response.ok) {
      throw new Error(`${endpoint} returned ${response.status}`);
    }
    const payload = await response.json();
    const size = Array.isArray(payload) ? payload.length : Object.keys(payload).length;
    if (size === 0) {
      throw new Error(`${endpoint} returned empty payload`);
    }
  }
  console.log("web smoke passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
