// Copies the Boost Guide (docs/index.html) into public/guide/ so the web app serves it at /guide/index.html.
// The copy is committed because the Docker build context is web/ only; outside the repository (no ../docs) it is kept.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = resolve(web, "../docs/index.html");
const target = resolve(web, "public/guide/index.html");

if (existsSync(source)) {
  mkdirSync(dirname(target), { recursive: true });
  copyFileSync(source, target);
  console.log("Boost Guide synced to public/guide/index.html");
} else {
  console.log(
    "docs/index.html not found; using the committed public/guide/index.html",
  );
}
