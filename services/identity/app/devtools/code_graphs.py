"""
Swagger UI with a "Graph" button per operation (local development only).

`/docs` is served by `install_dev_docs` instead of FastAPI's default so a small script can add the button.
Clicking it calls `POST /admin/code-graphs/generate`, which traces the operation's handler with the
`codegraphs` dev dependency and returns a link into the viewer mounted at `/code-graphs`.

The graph tools are skipped (plain Swagger UI only) when `codegraphs` is not installed, e.g. in images
built with `uv sync --no-dev`. Like `/docs`, these routes are unauthenticated and hidden from the schema.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core.config import config
from app.core.errors import NotFoundError, ServiceUnavailableError

SERVICE_DIR = Path(__file__).resolve().parents[2]
CONFIG_FILE = SERVICE_DIR / "codegraphs.toml"
OUTPUT_URL = "/code-graphs"
GENERATE_URL = "/admin/code-graphs/generate"
TRACE_DEPTH = 10
# Swagger shows mounted paths ("/v1/auth/signup"); route decorators only see "/auth/signup".
VERSION_PREFIX = re.compile(r"^/v\d+(?=/)")


class GraphRequest(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
    path: str


class GraphLink(BaseModel):
    url: str
    label: str


def install_dev_docs(app: FastAPI, *, openapi_url: str) -> None:
    """Serves Swagger UI at /docs, with per-operation call graphs when `codegraphs` is installed."""
    graphs_enabled = _install_code_graphs(app)
    extras = _BUTTON_ASSETS.replace("__GENERATE_URL__", json.dumps(GENERATE_URL)).replace(
        "__CSRF__", json.dumps({"cookie": config.CSRF_COOKIE_NAME, "header": config.CSRF_HEADER_NAME})
    )

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui() -> HTMLResponse:
        page = get_swagger_ui_html(
            openapi_url=openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url="/docs/oauth2-redirect",
        )
        if not graphs_enabled:
            return page
        html = bytes(page.body).decode().replace("</body>", f"{extras}</body>")
        return HTMLResponse(html)

    @app.get("/docs/oauth2-redirect", include_in_schema=False)
    async def swagger_ui_redirect() -> HTMLResponse:
        return get_swagger_ui_oauth2_redirect_html()


def _install_code_graphs(app: FastAPI) -> bool:
    try:
        from codegraphs.config import load_config
        from codegraphs.discovery import load_modules
        from codegraphs.endpoints import build_endpoint_flow
        from codegraphs.render import GraphvizNotFoundError
        from codegraphs.run import run
    except ImportError:
        return False

    graph_config = load_config(CONFIG_FILE)
    graph_config.out.mkdir(parents=True, exist_ok=True)
    # run() rewrites index.html and its manifest; one generation at a time keeps them consistent.
    lock = asyncio.Lock()
    router = APIRouter(include_in_schema=False)

    def generate(method: str, path: str) -> GraphLink:
        modules = load_modules(graph_config.src, graph_config.prefix)
        errors: list[str] = []
        for candidate in dict.fromkeys([path, VERSION_PREFIX.sub("", path)]):
            try:
                flow = build_endpoint_flow(modules, f"{method} {candidate}", TRACE_DEPTH)
            except ValueError as e:
                errors.append(str(e))
                continue
            try:
                run(graph_config, flow_names=[flow.name], extra_flows=[flow], verbose=False)
            except GraphvizNotFoundError as e:
                raise ServiceUnavailableError(str(e), code="graphviz_not_found") from None
            return GraphLink(url=f"{OUTPUT_URL}/index.html#{flow.name}", label=flow.title)
        raise NotFoundError(errors[-1], code="endpoint_not_found")

    @router.post(GENERATE_URL)
    async def generate_code_graph(body: GraphRequest) -> GraphLink:
        """Traces one operation's handler end to end and returns a link to its graph."""
        async with lock:
            return await run_in_threadpool(generate, body.method, body.path)

    app.include_router(router)
    app.mount(OUTPUT_URL, StaticFiles(directory=graph_config.out), name="code-graphs")
    return True


_BUTTON_ASSETS = """
<style>
  .cg-graph { margin: 0 8px; padding: 4px 10px; font: 600 12px sans-serif; border: 1px solid #49cc90;
    border-radius: 4px; background: #fff; color: #2b8a5f; cursor: pointer; white-space: nowrap; }
  .cg-graph:disabled { opacity: .6; cursor: wait; }
  .cg-graph.cg-error { border-color: #f93e3e; color: #c62828; }
  a.cg-graph { text-decoration: none; }
</style>
<script>
(() => {
  const GENERATE_URL = __GENERATE_URL__;
  const CSRF = __CSRF__;

  function csrfHeaders() {
    const match = document.cookie.split("; ").find((c) => c.startsWith(CSRF.cookie + "="));
    return match ? { [CSRF.header]: decodeURIComponent(match.split("=")[1]) } : {};
  }

  async function generate(button, method, path) {
    button.disabled = true;
    button.textContent = "Graphing…";
    button.classList.remove("cg-error");
    try {
      const res = await fetch(GENERATE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...csrfHeaders() },
        body: JSON.stringify({ method, path }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText);
      const link = document.createElement("a");
      link.className = "cg-graph";
      link.href = data.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "Open graph";
      link.title = data.label;
      link.addEventListener("click", (e) => e.stopPropagation());
      button.replaceWith(link);
    } catch (err) {
      button.disabled = false;
      button.textContent = "Graph failed";
      button.title = String(err.message || err);
      button.classList.add("cg-error");
    }
  }

  function decorate(op) {
    const summary = op.querySelector(".opblock-summary");
    const methodEl = op.querySelector(".opblock-summary-method");
    // data-path holds the bare path; the .opblock-summary-path wrapper's text can include the summary.
    const pathEl = op.querySelector("[data-path]");
    if (!summary || !methodEl || !pathEl || summary.querySelector(".cg-graph")) return;
    const method = methodEl.textContent.trim().toUpperCase();
    const path = pathEl.getAttribute("data-path");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "cg-graph";
    button.textContent = "Graph";
    button.title = "Generate the call graph for " + method + " " + path;
    button.addEventListener("click", (e) => {
      e.stopPropagation();
      generate(button, method, path);
    });
    summary.appendChild(button);
  }

  const scan = () => document.querySelectorAll(".opblock").forEach(decorate);
  new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  scan();
})();
</script>
"""
