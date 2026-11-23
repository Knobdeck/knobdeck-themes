// Builds the release assets into out/: <id>.zip (the theme folder's contents at the zip root, minus
// the phone files), <id>.phone.json (+ <id>.phone-bg.<ext>) for the phone app, and registry.json
// describing them all (each entry's `zipUrl` / `phone.url` is this release's download link). Previews are not assets: each entry's `preview` is a raw GitHub
// link to previews/<id>.gif in this repo, so changing a GIF needs no release.
//   node scripts/build-registry.mjs <release tag> [dir holding the previous release's assets]
// index.json lists every theme's version (it must equal `version` in the theme's theme.json, default
// 1.0.0). A theme whose version equals the previous release's is copied over from it, not rebuilt.
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const REPO = "https://github.com/Knobdeck/knobdeck-themes";
const RAW = "https://raw.githubusercontent.com/Knobdeck/knobdeck-themes/master";
const [tag, prevDir] = process.argv.slice(2);
if (!tag) throw new Error("usage: build-registry.mjs <tag> [prev dir]");
const index = JSON.parse(readFileSync("index.json", "utf8"));
const prevPath = prevDir && `${prevDir}/registry.json`;
const prev = prevPath && existsSync(prevPath) ? JSON.parse(readFileSync(prevPath, "utf8")).themes : [];
rmSync("out", { recursive: true, force: true });
mkdirSync("out");

const PHONE_FILES = ["phone.json", "phone-bg.jpg", "phone-bg.png", "phone-bg.webp"];
const HEX = /^#[0-9a-f]{6}$/i;
const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");

/// The phone counterpart (themes/<id>/phone.json, see README "Phone themes") as release assets:
/// the JSON gets the theme's name, description and version, and its image becomes an absolute URL.
/// Built from source every release (same source, same bytes), so its checksum only changes with it.
function buildPhone(id, desc, version) {
  const path = `themes/${id}/phone.json`;
  if (!existsSync(path)) return null;
  const phone = JSON.parse(readFileSync(path, "utf8"));
  const where = `${id}: phone.json`;
  if (phone.format !== 1) throw new Error(`${where}: format must be 1`);
  if (!["dark", "light"].includes(phone.mode)) throw new Error(`${where}: mode must be dark or light`);
  for (const k of ["bg", "panel", "panelAlt", "text", "subtext", "faint", "accent", "onAccent"]) {
    if (typeof phone.colors?.[k] !== "string") throw new Error(`${where}: colors.${k} missing`);
  }
  for (const k of ["bg", "text", "accent"]) if (!HEX.test(phone.colors[k])) throw new Error(`${where}: colors.${k} must be #rrggbb`);
  if (!HEX.test(phone.cell?.icon ?? "")) throw new Error(`${where}: cell.icon must be #rrggbb`);
  if (typeof phone.background?.base !== "string") throw new Error(`${where}: background.base missing`);
  const names = desc.presets ?? [];
  const keys = Object.keys(phone.presets ?? {});
  for (const n of names) if (!keys.includes(n)) throw new Error(`${where}: no preset "${n}" (theme.json has it)`);
  for (const n of keys) if (!names.includes(n)) throw new Error(`${where}: preset "${n}" is not in theme.json`);

  const background = { ...phone.background };
  if (background.image) {
    const ext = background.image.split(".").pop();
    if (!PHONE_FILES.includes(`phone-bg.${ext}`) || background.image !== `phone-bg.${ext}`) throw new Error(`${where}: background.image must be phone-bg.jpg|png|webp`);
    const img = readFileSync(`themes/${id}/${background.image}`);
    copyFileSync(`themes/${id}/${background.image}`, `out/${id}.phone-bg.${ext}`);
    background.image = `${REPO}/releases/download/${tag}/${id}.phone-bg.${ext}`;
    background.imageSha256 = sha256(img);
  }
  const out = { id, name: desc.name ?? id, description: desc.description ?? "", version, ...phone, background };
  const text = JSON.stringify(out, null, 2) + "\n";
  writeFileSync(`out/${id}.phone.json`, text);
  return { url: `${REPO}/releases/download/${tag}/${id}.phone.json`, sha256: sha256(Buffer.from(text)) };
}

const ids = readdirSync("themes").sort();
for (const id of Object.keys(index)) if (!ids.includes(id)) throw new Error(`index.json lists ${id}, which has no themes/${id}`);
const themes = ids.map((id) => {
  if (!/^[a-z0-9-]+$/.test(id)) throw new Error(`bad theme id: ${id}`);
  if (!existsSync(`themes/${id}/theme.css`)) throw new Error(`${id}: no theme.css`);
  const desc = JSON.parse(readFileSync(`themes/${id}/theme.json`, "utf8"));
  if (!Array.isArray(desc.layers)) throw new Error(`${id}: theme.json has no layers`);
  const version = desc.version ?? "1.0.0";
  if (index[id]?.version !== version) throw new Error(`${id}: index.json says ${index[id]?.version}, themes/${id}/theme.json says ${version}`);

  const preview = existsSync(`previews/${id}.gif`) ? `${RAW}/previews/${id}.gif` : null;
  const zipUrl = `${REPO}/releases/download/${tag}/${id}.zip`;
  const phone = buildPhone(id, desc, version);
  const old = prev.find((t) => t.id === id);
  if (old?.version === version && existsSync(`${prevDir}/${id}.zip`)) {
    copyFileSync(`${prevDir}/${id}.zip`, `out/${id}.zip`);
    const { zip, phone: _oldPhone, ...rest } = old; // entries from before zipUrl carried a file name
    return { ...rest, zipUrl, preview, ...(phone ? { phone } : {}) };
  }
  const zip = resolve("out", `${id}.zip`);
  // The phone files are the phone app's: the dial's zip leaves them out.
  execFileSync("zip", ["-qr", zip, ".", "-x", ...PHONE_FILES], { cwd: `themes/${id}` });
  return {
    id,
    name: desc.name ?? id,
    author: desc.author ?? "",
    version,
    // The dial engine the theme needs (2 = slices); apps that run an older one don't offer it.
    ...(desc.engineVersion > 1 ? { engine: desc.engineVersion } : {}),
    zipUrl,
    sha256: sha256(readFileSync(zip)),
    preview,
    // The phone counterpart: { url, sha256 } of <id>.phone.json (absent: the phone uses its built-in).
    ...(phone ? { phone } : {}),
  };
});
writeFileSync("out/registry.json", JSON.stringify({ tag, themes }, null, 2) + "\n");
console.log(`${themes.length} theme(s) for ${tag}`);
