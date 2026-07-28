#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const HARTREE_TO_EV = 27.211386245988;

function fail(message) {
  throw new Error(message);
}

function parseEigenvalues(filename) {
  const lines = fs.readFileSync(filename, "utf8").split(/\r?\n/);
  const header = lines[0]?.match(/#\s+(\d+)\s+eigenvalues\s+(\d+)\s+kpoints/);
  const fermi = lines[1]?.match(/Ef:\s+([-+0-9.eE]+)/);
  if (!header || !fermi) fail(`Cannot parse ${filename}`);
  const nBands = Number(header[1]);
  const nKpoints = Number(header[2]);
  const points = [];
  let cursor = 3;
  while (cursor < lines.length && points.length < nKpoints) {
    const kFields = lines[cursor++].trim().split(/\s+/).map(Number);
    if (kFields.length < 5 || kFields.some(Number.isNaN)) continue;
    const eigenvalues = [];
    for (let band = 0; band < nBands; band += 1) {
      const fields = lines[cursor++].trim().split(/\s+/);
      eigenvalues.push(Number(fields[1]));
    }
    points.push({ k: kFields.slice(1, 4), eigenvalues });
  }
  if (points.length !== nKpoints) {
    fail(`Expected ${nKpoints} k-points in ${filename}, parsed ${points.length}`);
  }
  return { nBands, nKpoints, fermi: Number(fermi[1]), points };
}

function parseTable(filename) {
  return fs
    .readFileSync(filename, "utf8")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#") && line !== "&")
    .map((line) => line.split(/\s+/).map(Number))
    .filter((row) => row.length >= 2 && row.every(Number.isFinite));
}

function parseDos(filename) {
  const text = fs.readFileSync(filename, "utf8");
  const fermi = text.match(/Original Fermi-level:\s+([-+0-9.eE]+)\s+eV/);
  if (!fermi) fail(`Cannot find the original Fermi level in ${filename}`);
  return { rows: parseTable(filename), fermiEv: Number(fermi[1]) };
}

function inverse3(matrix) {
  const [[a, b, c], [d, e, f], [g, h, i]] = matrix;
  const det =
    a * (e * i - f * h) -
    b * (d * i - f * g) +
    c * (d * h - e * g);
  if (Math.abs(det) < 1e-14) fail("Singular lattice matrix");
  return [
    [(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
    [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
    [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det],
  ];
}

function reciprocalRows(coordsFilename) {
  const rows = fs
    .readFileSync(coordsFilename, "utf8")
    .split(/\r?\n/)
    .slice(0, 3)
    .map((line) => line.trim().split(/\s+/).map(Number));
  const inv = inverse3(rows);
  return [
    [inv[0][0], inv[1][0], inv[2][0]],
    [inv[0][1], inv[1][1], inv[2][1]],
    [inv[0][2], inv[1][2], inv[2][2]],
  ];
}

function reciprocalDistance(a, b, reciprocal) {
  const delta = b.map((value, index) => value - a[index]);
  const cart = [0, 1, 2].map((component) =>
    delta.reduce((sum, value, row) => sum + value * reciprocal[row][component], 0),
  );
  return Math.hypot(...cart);
}

function esc(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function linePath(points) {
  return points
    .map(([x, y], index) => `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(" ");
}

function sumProjectedDos(directory, energies) {
  const files = fs
    .readdirSync(directory)
    .filter((name) => /^Atom\d+DOS_l\.dat$/.test(name))
    .sort();
  if (!files.length) fail(`No Atom*DOS_l.dat files found in ${directory}`);
  const s = Array(energies.length).fill(0);
  const p = Array(energies.length).fill(0);
  const d = Array(energies.length).fill(0);
  for (const name of files) {
    const rows = parseTable(path.join(directory, name));
    if (rows.length !== energies.length) fail(`Energy-grid mismatch in ${name}`);
    rows.forEach((row, index) => {
      if (Math.abs(row[0] - energies[index]) > 1e-4) fail(`Energy-grid mismatch in ${name}`);
      s[index] += row[2] ?? 0;
      p[index] += row[3] ?? 0;
      d[index] += row[4] ?? 0;
    });
  }
  return { s, p, d, nAtoms: files.length };
}

async function renderPng(svg, output) {
  try {
    const sharp = require("sharp");
    await sharp(Buffer.from(svg)).png().toFile(output);
    return true;
  } catch (error) {
    if (error?.code !== "MODULE_NOT_FOUND") {
      console.warn(`PNG conversion skipped: ${error.message}`);
    }
    return false;
  }
}

async function main() {
  if (process.argv.length !== 10) {
    fail(
      "Usage: plot_band_pdos.js material eigenvalues.dat DOS.dat pdos_dir output_prefix points_per_segment segments occupied_bands",
    );
  }
  const [, , material, eigenFile, dosFile, pdosDirectory, outputPrefix, nPerSegmentArg, nSegmentsArg, occupiedArg] =
    process.argv;
  const nPerSegment = Number(nPerSegmentArg);
  const nSegments = Number(nSegmentsArg);
  const occupiedBands = Number(occupiedArg);
  const meta =
    material === "graphite"
      ? {
          title: "AB graphite — band structure and projected DOS",
          subtitle: "PBE · 4-carbon primitive cell · 15 × 15 × 5 SCF mesh",
          labels: ["Γ", "M", "K", "Γ", "A"],
        }
      : {
          title: "Graphene — band structure and projected DOS",
          subtitle: "PBE · 2-carbon primitive cell · 21 × 21 × 1 SCF mesh",
          labels: ["Γ", "M", "K", "Γ"],
        };

  const bands = parseEigenvalues(eigenFile);
  const expectedKpoints = nSegments * (nPerSegment - 1) + 1;
  if (bands.nKpoints !== expectedKpoints) {
    fail(`Expected ${expectedKpoints} band k-points, found ${bands.nKpoints}`);
  }
  const reciprocal = reciprocalRows(path.join(path.dirname(eigenFile), "coords.dat"));
  const distances = [0];
  for (let index = 1; index < bands.points.length; index += 1) {
    distances.push(
      distances[index - 1] +
        reciprocalDistance(bands.points[index - 1].k, bands.points[index].k, reciprocal),
    );
  }

  const dos = parseDos(dosFile);
  const totalRows = dos.rows;
  const energies = totalRows.map((row) => row[0]);
  const totalDos = totalRows.map((row) => row[1]);
  const projected = sumProjectedDos(pdosDirectory, energies);

  const width = 1800;
  const height = 1100;
  const top = 150;
  const bottom = 125;
  const bandLeft = 145;
  const bandRight = 1190;
  const dosLeft = 1285;
  const dosRight = 1740;
  const plotHeight = height - top - bottom;
  const yMin = -12;
  const yMax = 8;
  const sy = (energy) => top + ((yMax - energy) / (yMax - yMin)) * plotHeight;
  const sxBand = (distance) =>
    bandLeft + (distance / distances.at(-1)) * (bandRight - bandLeft);
  const visibleIndices = energies
    .map((energy, index) => ({ energy, index }))
    .filter(({ energy }) => energy >= yMin && energy <= yMax)
    .map(({ index }) => index);
  const dosMax =
    Math.max(
      0,
      ...visibleIndices.flatMap((index) => [
        totalDos[index],
        projected.s[index],
        projected.p[index],
        projected.d[index],
      ]),
    ) * 1.08;
  const sxDos = (value) => dosLeft + (Math.max(0, value) / dosMax) * (dosRight - dosLeft);
  const boundaries = Array.from({ length: nSegments + 1 }, (_, index) =>
    index * (nPerSegment - 1),
  );

  const svg = [];
  svg.push(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
    `<rect width="${width}" height="${height}" fill="#ffffff"/>`,
    `<defs>`,
    `<clipPath id="bands-clip"><rect x="${bandLeft}" y="${top}" width="${bandRight - bandLeft}" height="${plotHeight}"/></clipPath>`,
    `<clipPath id="dos-clip"><rect x="${dosLeft}" y="${top}" width="${dosRight - dosLeft}" height="${plotHeight}"/></clipPath>`,
    `</defs>`,
    `<text x="${width / 2}" y="52" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="34" font-weight="500" fill="#111827">${esc(meta.title)}</text>`,
    `<text x="${width / 2}" y="88" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="19" fill="#4b5563">${esc(meta.subtitle)}</text>`,
  );

  for (let energy = yMin; energy <= yMax; energy += 2) {
    const y = sy(energy);
    svg.push(
      `<line x1="${bandLeft}" y1="${y}" x2="${bandRight}" y2="${y}" stroke="#e5e7eb" stroke-width="1"/>`,
      `<line x1="${dosLeft}" y1="${y}" x2="${dosRight}" y2="${y}" stroke="#e5e7eb" stroke-width="1"/>`,
      `<text x="${bandLeft - 20}" y="${y + 7}" text-anchor="end" font-family="Helvetica,Arial,sans-serif" font-size="20" fill="#374151">${energy}</text>`,
    );
  }

  for (let band = 0; band < bands.nBands; band += 1) {
    const points = bands.points.map((point, index) => [
      sxBand(distances[index]),
      sy(point.eigenvalues[band] * HARTREE_TO_EV - dos.fermiEv),
    ]);
    svg.push(
      `<path d="${linePath(points)}" clip-path="url(#bands-clip)" fill="none" stroke="#155e75" stroke-width="2.05" stroke-linejoin="round" stroke-linecap="round"/>`,
    );
  }

  boundaries.forEach((index, labelIndex) => {
    const x = sxBand(distances[index]);
    svg.push(
      `<line x1="${x}" y1="${top}" x2="${x}" y2="${top + plotHeight}" stroke="#9ca3af" stroke-width="1.3"/>`,
      `<text x="${x}" y="${top + plotHeight + 44}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="25" fill="#111827">${esc(meta.labels[labelIndex])}</text>`,
    );
  });

  const kIndex = 2 * (nPerSegment - 1);
  const conductionK =
    bands.points[kIndex].eigenvalues[occupiedBands] * HARTREE_TO_EV - dos.fermiEv;
  const valenceKCommon =
    bands.points[kIndex].eigenvalues[occupiedBands - 1] * HARTREE_TO_EV - dos.fermiEv;
  const directGapMeV = (conductionK - valenceKCommon) * 1000;
  const kX = sxBand(distances[kIndex]);
  const kY = sy((valenceKCommon + conductionK) / 2);
  svg.push(
    `<circle cx="${kX}" cy="${kY}" r="7" fill="#dc2626" stroke="#ffffff" stroke-width="3"/>`,
    `<text x="${Math.min(kX + 22, bandRight - 250)}" y="${kY - 20}" font-family="Helvetica,Arial,sans-serif" font-size="18" fill="#111827">K direct gap: ${directGapMeV.toFixed(2)} meV</text>`,
  );

  const dosPoints = visibleIndices.map((index) => [
    sxDos(totalDos[index]),
    sy(energies[index]),
  ]);
  const sPoints = visibleIndices.map((index) => [sxDos(projected.s[index]), sy(energies[index])]);
  const pPoints = visibleIndices.map((index) => [sxDos(projected.p[index]), sy(energies[index])]);
  const dPoints = visibleIndices.map((index) => [sxDos(projected.d[index]), sy(energies[index])]);
  const pArea = [
    `M${dosLeft},${sy(energies[visibleIndices[0]]).toFixed(2)}`,
    ...pPoints.map(([x, y]) => `L${x.toFixed(2)},${y.toFixed(2)}`),
    `L${dosLeft},${sy(energies[visibleIndices.at(-1)]).toFixed(2)}`,
    "Z",
  ].join(" ");
  svg.push(
    `<path d="${pArea}" clip-path="url(#dos-clip)" fill="#f59e0b" fill-opacity="0.16" stroke="none"/>`,
    `<path d="${linePath(dosPoints)}" clip-path="url(#dos-clip)" fill="none" stroke="#111827" stroke-width="2.8"/>`,
    `<path d="${linePath(sPoints)}" clip-path="url(#dos-clip)" fill="none" stroke="#16a34a" stroke-width="2.4" stroke-dasharray="10 7"/>`,
    `<path d="${linePath(pPoints)}" clip-path="url(#dos-clip)" fill="none" stroke="#d97706" stroke-width="2.6"/>`,
    `<path d="${linePath(dPoints)}" clip-path="url(#dos-clip)" fill="none" stroke="#7c3aed" stroke-width="2.2" stroke-dasharray="3 6"/>`,
  );

  const fermiY = sy(0);
  svg.push(
    `<line x1="${bandLeft}" y1="${fermiY}" x2="${bandRight}" y2="${fermiY}" stroke="#dc2626" stroke-width="2.2" stroke-dasharray="11 8"/>`,
    `<line x1="${dosLeft}" y1="${fermiY}" x2="${dosRight}" y2="${fermiY}" stroke="#dc2626" stroke-width="2.2" stroke-dasharray="11 8"/>`,
    `<text x="${bandRight - 10}" y="${fermiY - 12}" text-anchor="end" font-family="Helvetica,Arial,sans-serif" font-size="18" fill="#b91c1c">E<tspan baseline-shift="sub" font-size="14">F</tspan></text>`,
    `<rect x="${bandLeft}" y="${top}" width="${bandRight - bandLeft}" height="${plotHeight}" fill="none" stroke="#111827" stroke-width="2"/>`,
    `<rect x="${dosLeft}" y="${top}" width="${dosRight - dosLeft}" height="${plotHeight}" fill="none" stroke="#111827" stroke-width="2"/>`,
    `<text x="${(bandLeft + bandRight) / 2}" y="${top - 22}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="24" font-weight="500" fill="#111827">Band structure</text>`,
    `<text x="${(dosLeft + dosRight) / 2}" y="${top - 22}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="24" font-weight="500" fill="#111827">Density of states</text>`,
    `<text x="40" y="${top + plotHeight / 2}" transform="rotate(-90 40 ${top + plotHeight / 2})" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="25" fill="#111827">Energy − E<tspan baseline-shift="sub" font-size="18">F</tspan> (eV)</text>`,
    `<text x="${(bandLeft + bandRight) / 2}" y="${height - 34}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="22" fill="#374151">Wave-vector path</text>`,
    `<text x="${(dosLeft + dosRight) / 2}" y="${height - 34}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="22" fill="#374151">DOS (states/eV)</text>`,
  );

  const legendX = dosLeft + 24;
  const legendY = top + 36;
  [
    ["#111827", "", "Total DOS"],
    ["#16a34a", "10 7", `C s (${projected.nAtoms} atoms)`],
    ["#d97706", "", `C p (${projected.nAtoms} atoms)`],
    ["#7c3aed", "3 6", `C d (${projected.nAtoms} atoms)`],
  ].forEach(([color, dash, label], index) => {
    const y = legendY + index * 32;
    svg.push(
      `<line x1="${legendX}" y1="${y}" x2="${legendX + 46}" y2="${y}" stroke="${color}" stroke-width="3"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`,
      `<text x="${legendX + 58}" y="${y + 7}" font-family="Helvetica,Arial,sans-serif" font-size="18" fill="#111827">${esc(label)}</text>`,
    );
  });
  svg.push("</svg>");

  const svgText = svg.join("\n");
  const svgFilename = `${outputPrefix}.svg`;
  const pngFilename = `${outputPrefix}.png`;
  fs.writeFileSync(svgFilename, svgText);
  const wrotePng = await renderPng(svgText, pngFilename);
  console.log(`Wrote ${svgFilename}`);
  if (wrotePng) console.log(`Wrote ${pngFilename}`);
}

main().catch((error) => {
  console.error(`ERROR: ${error.message}`);
  process.exitCode = 1;
});
