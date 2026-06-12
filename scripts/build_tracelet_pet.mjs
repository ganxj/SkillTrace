import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

const workspace = "D:\\pythonProject\\SkillTrace";
const source = "C:\\Users\\admin\\.codex\\generated_images\\019ebb30-ad32-74a2-bfcb-d67d3ed58010\\ig_070025ab284ea681016a2bd390039481999570ac230ce016b8.png";
const runDir = path.join(workspace, ".codex", "pets", "tracelet-run");
const packageDir = path.join(workspace, ".codex", "pets", "tracelet");
const cellW = 192;
const cellH = 208;
const cols = 8;
const rows = 9;

const states = [
  "idle",
  "running-right",
  "running-left",
  "waving",
  "jumping",
  "failed",
  "waiting",
  "running",
  "review",
];

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

async function keyOutGreen(input, output) {
  const src = sharp(input).ensureAlpha();
  const { data, info } = await src.raw().toBuffer({ resolveWithObject: true });
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    if (g > 170 && r < 80 && b < 110) {
      data[i] = 0;
      data[i + 1] = 0;
      data[i + 2] = 0;
      data[i + 3] = 0;
    }
  }
  await sharp(data, { raw: info }).trim({ background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toFile(output);
}

function framePlan(state, frame) {
  const wave = Math.sin((Math.PI * 2 * frame) / cols);
  const alt = frame % 2 === 0 ? -1 : 1;
  const base = { dx: 0, dy: 0, rotate: 0, scale: 1, flop: false, tint: null };
  switch (state) {
    case "idle":
      return { ...base, dy: Math.round(wave * 3), scale: 1 + wave * 0.01 };
    case "running-right":
      return { ...base, flop: true, dx: Math.round(-5 + frame * 1.4), dy: alt * 3, rotate: alt * 2 };
    case "running-left":
      return { ...base, dx: Math.round(5 - frame * 1.4), dy: alt * 3, rotate: alt * -2 };
    case "waving":
      return { ...base, rotate: Math.sin((Math.PI * frame) / 3.5) * 5, dy: Math.round(wave * 2) };
    case "jumping":
      return { ...base, dy: -Math.round(Math.max(0, Math.sin((Math.PI * frame) / 7)) * 28), scale: 1 - Math.max(0, Math.sin((Math.PI * frame) / 7)) * 0.025 };
    case "failed":
      return { ...base, rotate: alt * 4, dy: frame > 1 && frame < 6 ? 5 : 0, tint: { r: 210, g: 225, b: 235 } };
    case "waiting":
      return { ...base, dy: frame % 4 < 2 ? -3 : 2, rotate: frame % 4 < 2 ? -3 : 3 };
    case "running":
      return { ...base, dy: alt * 2, scale: 1 + (frame % 4 < 2 ? 0.015 : -0.005), rotate: alt * 1.5 };
    case "review":
      return { ...base, dx: frame % 4 < 2 ? -3 : 2, rotate: frame % 4 < 2 ? -4 : -1, scale: 1.01 };
    default:
      return base;
  }
}

async function makeFrame(cleanSource, state, frame) {
  const plan = framePlan(state, frame);
  const targetW = Math.round(150 * plan.scale);
  const targetH = Math.round(162 * plan.scale);
  let pet = sharp(cleanSource).resize({ width: targetW, height: targetH, fit: "inside" });
  if (plan.flop) {
    pet = pet.flop();
  }
  if (plan.tint) {
    pet = pet.tint(plan.tint);
  }
  pet = pet.rotate(plan.rotate, { background: { r: 0, g: 0, b: 0, alpha: 0 } });
  const buf = await pet.png().toBuffer();
  const meta = await sharp(buf).metadata();
  const left = Math.round((cellW - meta.width) / 2 + plan.dx);
  const top = Math.round((cellH - meta.height) / 2 + 8 + plan.dy);
  return sharp({
    create: {
      width: cellW,
      height: cellH,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    },
  })
    .composite([{ input: buf, left: Math.max(0, left), top: Math.max(0, top) }])
    .png()
    .toBuffer();
}

async function makeAtlas(cleanSource, atlasPng, atlasWebp, framesDir) {
  const composites = [];
  for (let row = 0; row < rows; row += 1) {
    const state = states[row];
    await ensureDir(path.join(framesDir, state));
    for (let col = 0; col < cols; col += 1) {
      const frame = await makeFrame(cleanSource, state, col);
      await fs.writeFile(path.join(framesDir, state, `${String(col).padStart(2, "0")}.png`), frame);
      composites.push({ input: frame, left: col * cellW, top: row * cellH });
    }
  }

  await sharp({
    create: {
      width: cellW * cols,
      height: cellH * rows,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    },
  })
    .composite(composites)
    .png()
    .toFile(atlasPng);

  await sharp(atlasPng).webp({ lossless: true }).toFile(atlasWebp);
}

async function makeContactSheet(atlasPng, output) {
  const labelH = 24;
  const rowH = cellH + labelH;
  const svgLabels = states
    .map((state, index) => `<text x="8" y="${index * rowH + 17}" font-family="Arial" font-size="14" fill="#334155">${index} ${state}</text>`)
    .join("");
  const atlas = await sharp(atlasPng).png().toBuffer();
  await sharp({
    create: {
      width: cellW * cols,
      height: rowH * rows,
      channels: 4,
      background: { r: 248, g: 250, b: 252, alpha: 1 },
    },
  })
    .composite([
      { input: Buffer.from(`<svg width="${cellW * cols}" height="${rowH * rows}">${svgLabels}</svg>`), left: 0, top: 0 },
      { input: atlas, left: 0, top: labelH },
    ])
    .png()
    .toFile(output);
}

async function makePreview(framesDir, state, output) {
  const inputs = [];
  for (let i = 0; i < cols; i += 1) {
    inputs.push(await fs.readFile(path.join(framesDir, state, `${String(i).padStart(2, "0")}.png`)));
  }
  const pages = await Promise.all(
    inputs.map((input) =>
      sharp(input, { animated: false })
        .extend({ top: 0, bottom: 0, left: 0, right: 0, background: { r: 0, g: 0, b: 0, alpha: 0 } })
        .webp({ lossless: true })
        .toBuffer(),
    ),
  );
  await sharp(pages, { animated: true, delay: Array(cols).fill(120) }).webp({ loop: 0, lossless: true }).toFile(output);
}

async function validateAtlas(atlasPng, output) {
  const meta = await sharp(atlasPng).metadata();
  const alpha = meta.hasAlpha === true;
  const ok = meta.width === cellW * cols && meta.height === cellH * rows && alpha;
  await fs.writeFile(
    output,
    JSON.stringify(
      {
        ok,
        width: meta.width,
        height: meta.height,
        hasAlpha: alpha,
        cellWidth: cellW,
        cellHeight: cellH,
        rows: states,
        columns: cols,
      },
      null,
      2,
    ),
  );
  if (!ok) {
    throw new Error(`Invalid atlas metadata: ${JSON.stringify(meta)}`);
  }
}

async function main() {
  const decodedDir = path.join(runDir, "decoded");
  const framesDir = path.join(runDir, "frames");
  const finalDir = path.join(runDir, "final");
  const qaDir = path.join(runDir, "qa");
  const previewsDir = path.join(qaDir, "previews");
  await Promise.all([decodedDir, framesDir, finalDir, qaDir, previewsDir, packageDir].map(ensureDir));

  const cleanSource = path.join(decodedDir, "tracelet-base.png");
  const atlasPng = path.join(finalDir, "spritesheet.png");
  const atlasWebp = path.join(finalDir, "spritesheet.webp");
  await keyOutGreen(source, cleanSource);
  await makeAtlas(cleanSource, atlasPng, atlasWebp, framesDir);
  await validateAtlas(atlasPng, path.join(finalDir, "validation.json"));
  await makeContactSheet(atlasPng, path.join(qaDir, "contact-sheet.png"));

  for (const state of states) {
    await makePreview(framesDir, state, path.join(previewsDir, `${state}.webp`));
  }

  const petJson = {
    id: "tracelet",
    displayName: "Tracelet",
    description: "A compact developer companion inspired by Python tracing, Conda workflows, and practical code review.",
    spritesheetPath: "spritesheet.webp",
  };
  await fs.copyFile(atlasWebp, path.join(packageDir, "spritesheet.webp"));
  await fs.writeFile(path.join(packageDir, "pet.json"), JSON.stringify(petJson, null, 2));
  await fs.writeFile(
    path.join(qaDir, "run-summary.json"),
    JSON.stringify(
      {
        ok: true,
        runDir,
        packageDir,
        source,
        contactSheet: path.join(qaDir, "contact-sheet.png"),
        spritesheet: atlasWebp,
        validation: path.join(finalDir, "validation.json"),
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
