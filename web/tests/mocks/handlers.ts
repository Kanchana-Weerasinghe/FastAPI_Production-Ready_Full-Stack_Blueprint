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
  http.get(`${BASE}/v2/todos/`, () =>
    HttpResponse.json({
      founds: [
        {
          id: "todo-1",
          title: "Test Todo",
          isCompleted: false,
          createdAt: "2024-01-01T00:00:00Z",
          updatedAt: "2024-01-01T00:00:00Z",
        },
      ],
      searchOptions: { totalCount: 1 },
    }),
  ),
  http.get(`${BASE}/v2/todos/:todoId`, ({ params }) =>
    HttpResponse.json({
      id: params.todoId,
      userId: "user-1",
      title: "Test Todo",
      isCompleted: false,
      attachments: [],
      createdAt: "2024-01-01T00:00:00Z",
      updatedAt: "2024-01-01T00:00:00Z",
    }),
  ),
  http.post(`${BASE}/v2/todos/`, () => HttpResponse.json({}, { status: 201 })),
  http.patch(`${BASE}/v2/todos/:todoId`, () => HttpResponse.json({})),
  http.delete(`${BASE}/v2/todos/:todoId`, () =>
    HttpResponse.json({}, { status: 204 }),
  ),
  http.post(`${BASE}/v2/todos/:todoId\\:archive`, () => HttpResponse.json({})),
  http.get(`${BASE}/v2/attachments/`, () =>
    HttpResponse.json({
      founds: [],
      searchOptions: { totalCount: 0, pageSize: 10, currentPage: 1 },
    }),
  ),
  http.post(`${BASE}/v2/attachments/`, () =>
    HttpResponse.json({
      id: "att-1",
      userId: "user-1",
      fileName: "test.pdf",
      downloadUrl: "/v2/attachments/att-1:download",
      fileSize: 1024,
      fileType: "application/pdf",
      createdAt: "2024-01-01T00:00:00Z",
      updatedAt: "2024-01-01T00:00:00Z",
    }),
  ),
  http.delete(`${BASE}/v2/attachments/:fileId`, () =>
    HttpResponse.json({}, { status: 204 }),
  ),
];
