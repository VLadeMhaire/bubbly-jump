
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" }
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/event" && request.method === "POST") {
      return recordEvent(request, env);
    }

    if (url.pathname === "/api/stats" && request.method === "GET") {
      return getStats(url, env);
    }

    return env.ASSETS.fetch(request);
  }
};

async function recordEvent(request, env) {
  let event;

  try {
    event = await request.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }

  const { device_id, type, score } = event || {};

  if (
    typeof device_id !== "string" ||
    !/^[A-Za-z0-9_-]{8,64}$/.test(device_id)
  ) {
    return json({ error: "Invalid device ID" }, 422);
  }

  if (!["visit", "play", "over"].includes(type)) {
    return json({ error: "Invalid event type" }, 422);
  }

  const validScore =
    score === undefined ||
    score === null ||
    (Number.isInteger(score) && score >= 0 && score <= 10000000);

  if (!validScore) {
    return json({ error: "Invalid score" }, 422);
  }

  const now = Math.floor(Date.now() / 1000);
  const userAgent = (request.headers.get("User-Agent") || "").slice(0, 300);

  try {
    await env.DB.batch([
      env.DB.prepare(`
        INSERT INTO devices (id, first_seen, last_seen, user_agent)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          last_seen = excluded.last_seen,
          user_agent = excluded.user_agent
      `).bind(device_id, now, now, userAgent),

      env.DB.prepare(`
        INSERT INTO events (device_id, type, score, ts)
        VALUES (?, ?, ?, ?)
      `).bind(device_id, type, score ?? null, now)
    ]);

    return new Response(null, { status: 204 });
  } catch (error) {
    console.error("Event recording failed:", error);
    return json({ error: "Could not record event" }, 500);
  }
}

async function getStats(url, env) {
  if (env.STATS_TOKEN && url.searchParams.get("token") !== env.STATS_TOKEN) {
    return json({ detail: "Invalid token" }, 401);
  }

  try {
    const deviceResult = await env.DB.prepare(`
      SELECT
        d.id,
        d.user_agent,
        d.first_seen,
        d.last_seen,
        SUM(e.type = 'visit') AS visits,
        SUM(e.type = 'play') AS plays,
        MAX(CASE WHEN e.type = 'over' THEN e.score END) AS best_score,
        MAX(CASE WHEN e.type = 'play' THEN e.ts END) AS last_played
      FROM devices d
      LEFT JOIN events e ON e.device_id = d.id
      GROUP BY d.id
      ORDER BY plays DESC, d.last_seen DESC
    `).all();

    const devices = deviceResult.results || [];

    const totalPlays = devices.reduce(
      (sum, d) => sum + (d.plays || 0), 0
    );

    const devicesWhoPlayed = devices.filter(
      d => d.plays > 0
    ).length;

    const since = Math.floor(Date.now() / 1000) - 14 * 86400;

    const dailyResult = await env.DB.prepare(`
      SELECT
        date(ts, 'unixepoch') AS day,
        SUM(type = 'play') AS plays,
        COUNT(DISTINCT CASE
          WHEN type = 'play' THEN device_id
        END) AS devices
      FROM events
      WHERE ts >= ?
      GROUP BY day
      ORDER BY day
    `).bind(since).all();

    return json({
      total_devices: devices.length,
      devices_who_played: devicesWhoPlayed,
      total_plays: totalPlays,
      devices,
      daily: dailyResult.results || []
    });

  } catch (error) {
    console.error("Stats query failed:", error);
    return json({ error: "Could not load statistics" }, 500);
  }
}
