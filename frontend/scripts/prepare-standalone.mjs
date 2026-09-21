import { cpSync, existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const standalone = join(root, ".next", "standalone");
const staticSource = join(root, ".next", "static");
const publicSource = join(root, "public");

if (!existsSync(join(standalone, "server.js"))) {
  throw new Error("缺少 .next/standalone/server.js，请先执行 next build");
}
if (!existsSync(staticSource)) {
  throw new Error("缺少 .next/static，无法准备 standalone 部署产物");
}

mkdirSync(join(standalone, ".next"), { recursive: true });
cpSync(staticSource, join(standalone, ".next", "static"), {
  recursive: true,
  force: true,
});

if (existsSync(publicSource)) {
  cpSync(publicSource, join(standalone, "public"), {
    recursive: true,
    force: true,
  });
}

console.log("standalone 部署产物已包含 .next/static 和 public");
