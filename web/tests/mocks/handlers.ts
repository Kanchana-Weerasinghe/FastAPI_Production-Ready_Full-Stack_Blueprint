import { http, HttpResponse } from "msw";

const BASE = "http://localhost:8000";

export const handlers = [
  http.post(`${BASE}/v1/auth/signin`, () =>
    HttpResponse.json({ message: "ok" }),
  ),
  http.post(`${BASE}/v1/auth/signup`, () =>
    HttpResponse.json({ message: "ok" }),
  ),
  http.post(
    `${BASE}/v1/auth/signout`,
    () => new HttpResponse(null, { status: 204 }),
  ),
  http.get(`${BASE}/v2/user/me`, () =>
    HttpResponse.json({
      id: "user-1",
      email: "test@example.com",
      username: "testuser",
    }),
  ),
];
