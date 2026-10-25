// k6 load test with the performance budget as pass/fail thresholds.
//   k6 run -e BASE_URL=https://staging.app.example.com -e EMAIL=load@example.com -e PASSWORD=... tests/load/smoke.js
// Use a dedicated load-test account on staging; never run against production without an agreed window.
import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  scenarios: {
    steady: { executor: "ramping-vus", startVUs: 1, stages: [
      { duration: "1m", target: 20 },
      { duration: "3m", target: 20 },
      { duration: "1m", target: 0 },
    ] },
  },
  thresholds: {
    // Performance budget (docs/operations/slo.md): p95 < 300 ms, p99 < 1 s, < 1% errors.
    http_req_duration: ["p(95)<300", "p(99)<1000"],
    http_req_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

export function setup() {
  const res = http.post(
    `${BASE_URL}/v1/auth/signin`,
    JSON.stringify({ email: __ENV.EMAIL, password: __ENV.PASSWORD }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(res, { "signed in": (r) => r.status === 200 });
  const jar = http.cookieJar();
  return { cookies: jar.cookiesForURL(BASE_URL) };
}

export default function (data) {
  const jar = http.cookieJar();
  for (const [name, values] of Object.entries(data.cookies)) jar.set(BASE_URL, name, values[0]);

  const me = http.get(`${BASE_URL}/v2/user/me`, { tags: { name: "me" } });
  check(me, { "me 200": (r) => r.status === 200 });

  sleep(1);
}
