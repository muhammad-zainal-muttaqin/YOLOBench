#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

function parseArgs(argv) {
  const out = {
    dataset: 'dataset_combined',
    output: path.join('analysis', 'bbox_outliers'),
    topN: 24,
    denseMin: 8,
    denseTopN: 12,
    ordinalTolerance: 0.15
  };
  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = argv[i + 1];
    if (arg === '--dataset' && next) {
      out.dataset = next;
      i += 1;
    } else if (arg === '--out' && next) {
      out.output = next;
      i += 1;
    } else if (arg === '--top-n' && next) {
      out.topN = Number(next);
      i += 1;
    } else if (arg === '--dense-min' && next) {
      out.denseMin = Number(next);
      i += 1;
    } else if (arg === '--dense-top-n' && next) {
      out.denseTopN = Number(next);
      i += 1;
    } else if (arg === '--ordinal-tolerance' && next) {
      out.ordinalTolerance = Number(next);
      i += 1;
    }
  }
  return out;
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function readDatasetConfig(datasetDir) {
  const yamlPath = path.join(datasetDir, 'data.yaml');
  const text = fs.readFileSync(yamlPath, 'utf8');
  const names = {};
  let inNames = false;
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trimEnd();
    if (!line.trim()) continue;
    if (/^names:\s*$/.test(line.trim())) {
      inNames = true;
      continue;
    }
    if (inNames) {
      const match = line.match(/^\s*(\d+)\s*:\s*(.+?)\s*$/);
      if (match) {
        names[Number(match[1])] = match[2];
        continue;
      }
      if (!/^\s+/.test(rawLine)) {
        inNames = false;
      }
    }
  }
  const ordered = Object.keys(names)
    .map(Number)
    .sort((a, b) => a - b)
    .map((k) => names[k]);
  return {
    yamlPath,
    classNames: ordered
  };
}

function percentile(sorted, p) {
  if (!sorted.length) return 0;
  const idx = Math.max(0, Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * p)));
  return sorted[idx];
}

function csvEscape(value) {
  const str = String(value ?? '');
  return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
}

function writeCsv(filePath, rows, columns) {
  const lines = [columns.join(',')];
  for (const row of rows) {
    lines.push(columns.map((key) => csvEscape(row[key])).join(','));
  }
  fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
}

function formatNumber(value, digits = 4) {
  return Number.isFinite(value) ? value.toFixed(digits) : '';
}

function getDomain(filename) {
  if (filename.startsWith('DAMIMAS_')) return 'DAMIMAS';
  if (filename.startsWith('LONSUM_')) return 'LONSUM';
  return 'UNKNOWN';
}

async function gatherDataset(datasetDir, classNames) {
  const splits = ['train', 'val', 'test'];
  const objects = [];
  const images = [];
  const missingImages = [];

  for (const split of splits) {
    const labelsDir = path.join(datasetDir, 'labels', split);
    const imagesDir = path.join(datasetDir, 'images', split);
    const labelFiles = fs.existsSync(labelsDir)
      ? fs.readdirSync(labelsDir).filter((f) => f.endsWith('.txt')).sort()
      : [];

    for (const labelFile of labelFiles) {
      const base = path.basename(labelFile, '.txt');
      const imagePath = ['.jpg', '.jpeg', '.png', '.bmp']
        .map((ext) => path.join(imagesDir, `${base}${ext}`))
        .find((full) => fs.existsSync(full));

      if (!imagePath) {
        missingImages.push(path.join(labelsDir, labelFile));
        continue;
      }

      const metadata = await sharp(imagePath).metadata();
      const imgWidth = metadata.width || 0;
      const imgHeight = metadata.height || 0;
      const lines = fs.readFileSync(path.join(labelsDir, labelFile), 'utf8')
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);

      const imageRecord = {
        split,
        filename: path.basename(imagePath),
        imagePath,
        labelPath: path.join(labelsDir, labelFile),
        width: imgWidth,
        height: imgHeight,
        objectCount: lines.length,
        domain: getDomain(base)
      };
      images.push(imageRecord);

      lines.forEach((line, idx) => {
        const parts = line.split(/\s+/);
        if (parts.length < 5) return;
        const classId = Number(parts[0]);
        const cx = Number(parts[1]);
        const cy = Number(parts[2]);
        const bw = Number(parts[3]);
        const bh = Number(parts[4]);
        const widthPx = bw * imgWidth;
        const heightPx = bh * imgHeight;
        const areaPx = widthPx * heightPx;
        const imageArea = imgWidth * imgHeight || 1;
        const x1 = Math.max(0, Math.round((cx - (bw / 2)) * imgWidth));
        const y1 = Math.max(0, Math.round((cy - (bh / 2)) * imgHeight));
        const x2 = Math.min(imgWidth, Math.round((cx + (bw / 2)) * imgWidth));
        const y2 = Math.min(imgHeight, Math.round((cy + (bh / 2)) * imgHeight));
        objects.push({
          split,
          filename: path.basename(imagePath),
          imagePath,
          labelPath: path.join(labelsDir, labelFile),
          domain: imageRecord.domain,
          classId,
          className: classNames[classId] || `class_${classId}`,
          bboxIndex: idx,
          objectCountInImage: lines.length,
          widthPx,
          heightPx,
          areaPx,
          relativeArea: areaPx / imageArea,
          aspectRatio: heightPx > 0 ? widthPx / heightPx : 0,
          x1,
          y1,
          x2,
          y2,
          imageWidth: imgWidth,
          imageHeight: imgHeight
        });
      });
    }
  }

  return { objects, images, missingImages };
}

function computeClassStats(objects, classNames) {
  const byClass = new Map();
  for (const obj of objects) {
    if (!byClass.has(obj.classId)) byClass.set(obj.classId, []);
    byClass.get(obj.classId).push(obj);
  }

  const stats = classNames.map((className, classId) => {
    const items = (byClass.get(classId) || []).slice().sort((a, b) => a.relativeArea - b.relativeArea);
    const rels = items.map((item) => item.relativeArea);
    const widths = items.map((item) => item.widthPx).sort((a, b) => a - b);
    const heights = items.map((item) => item.heightPx).sort((a, b) => a - b);
    return {
      classId,
      className,
      count: items.length,
      p10: percentile(rels, 0.10),
      p50: percentile(rels, 0.50),
      p90: percentile(rels, 0.90),
      widthP50: percentile(widths, 0.50),
      heightP50: percentile(heights, 0.50),
      items
    };
  });

  return stats;
}

function buildOutliers(classStats, topN) {
  const outliers = [];
  for (const stat of classStats) {
    const items = stat.items;
    const left = items.slice(0, Math.min(topN, items.length));
    const right = items.slice(Math.max(0, items.length - topN));
    left.forEach((item, rank) => {
      outliers.push({
        ...item,
        outlierSide: 'left',
        rank: rank + 1,
        classCount: stat.count,
        percentile: stat.count > 1 ? rank / (stat.count - 1) : 0,
        outlierScore: 1 - (stat.p50 ? (item.relativeArea / stat.p50) : 0),
        reviewReason: `${item.className} terlalu kecil dibanding distribusi kelasnya`
      });
    });
    right.slice().reverse().forEach((item, rank) => {
      const idx = items.length - 1 - rank;
      outliers.push({
        ...item,
        outlierSide: 'right',
        rank: rank + 1,
        classCount: stat.count,
        percentile: stat.count > 1 ? idx / (stat.count - 1) : 1,
        outlierScore: stat.p50 ? (item.relativeArea / stat.p50) - 1 : 0,
        reviewReason: `${item.className} terlalu besar dibanding distribusi kelasnya`
      });
    });
  }
  return outliers.sort((a, b) => {
    if (a.classId !== b.classId) return a.classId - b.classId;
    if (a.outlierSide !== b.outlierSide) return a.outlierSide.localeCompare(b.outlierSide);
    return a.rank - b.rank;
  });
}

function buildOrdinalViolations(images, objects, classNames, tolerance) {
  const byImage = new Map();
  for (const obj of objects) {
    const key = `${obj.split}/${obj.filename}`;
    if (!byImage.has(key)) byImage.set(key, []);
    byImage.get(key).push(obj);
  }

  const violations = [];
  for (const imageRecord of images) {
    const key = `${imageRecord.split}/${imageRecord.filename}`;
    const imageObjects = (byImage.get(key) || []).slice().sort((a, b) => a.classId - b.classId);
    for (let i = 0; i < imageObjects.length; i += 1) {
      for (let j = i + 1; j < imageObjects.length; j += 1) {
        const lhs = imageObjects[i];
        const rhs = imageObjects[j];
        if (lhs.classId === rhs.classId) continue;
        const expectedLarger = lhs.classId < rhs.classId ? lhs : rhs;
        const expectedSmaller = lhs.classId < rhs.classId ? rhs : lhs;
        if (expectedLarger.areaPx < 25 || expectedSmaller.areaPx < 25) continue;
        const minAllowed = expectedSmaller.areaPx * (1 - tolerance);
        if (expectedLarger.areaPx < minAllowed) {
          const ratio = expectedSmaller.areaPx / Math.max(expectedLarger.areaPx, 1e-9);
          violations.push({
            split: imageRecord.split,
            filename: imageRecord.filename,
            domain: imageRecord.domain,
            lhsClass: expectedLarger.className,
            rhsClass: expectedSmaller.className,
            lhsArea: expectedLarger.areaPx,
            rhsArea: expectedSmaller.areaPx,
            violationRatio: ratio,
            objectsInImage: imageRecord.objectCount,
            reviewReason: `${expectedLarger.className} lebih kecil dari ${expectedSmaller.className} dalam gambar yang sama`,
            lhsBBoxIndex: expectedLarger.bboxIndex,
            rhsBBoxIndex: expectedSmaller.bboxIndex
          });
        }
      }
    }
  }

  return violations.sort((a, b) => b.violationRatio - a.violationRatio);
}

function buildDenseImageRows(images, objects, denseMin) {
  const byImage = new Map();
  for (const obj of objects) {
    const key = `${obj.split}/${obj.filename}`;
    if (!byImage.has(key)) byImage.set(key, []);
    byImage.get(key).push(obj);
  }
  return images
    .filter((img) => img.objectCount >= denseMin)
    .map((img) => {
      const key = `${img.split}/${img.filename}`;
      const imgObjects = (byImage.get(key) || []).slice().sort((a, b) => {
        if (a.classId !== b.classId) return a.classId - b.classId;
        return b.areaPx - a.areaPx;
      });
      const classBreakdown = {};
      for (const name of ['B1', 'B2', 'B3', 'B4']) classBreakdown[name] = 0;
      imgObjects.forEach((obj) => { classBreakdown[obj.className] = (classBreakdown[obj.className] || 0) + 1; });
      return {
        ...img,
        objects: imgObjects,
        classBreakdown
      };
    })
    .sort((a, b) => {
      if (b.objectCount !== a.objectCount) return b.objectCount - a.objectCount;
      return a.filename.localeCompare(b.filename);
    });
}

function summarizeOverlap(classStats) {
  const rows = [];
  for (let i = 0; i < classStats.length; i += 1) {
    for (let j = i + 1; j < classStats.length; j += 1) {
      const a = classStats[i];
      const b = classStats[j];
      const overlap = !(a.p90 < b.p10 || b.p90 < a.p10);
      rows.push({
        lhs: a.className,
        rhs: b.className,
        lhsP10: a.p10,
        lhsP90: a.p90,
        rhsP10: b.p10,
        rhsP90: b.p90,
        overlap
      });
    }
  }
  return rows;
}

function safeName(name) {
  return name.replace(/[^a-z0-9_.-]+/gi, '_');
}

function svgTextOverlay(width, height, title, subtitle, footer) {
  const esc = (s) => String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return Buffer.from(
    `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="${width}" height="${height}" fill="rgba(0,0,0,0)"/>
      <rect x="0" y="${height - 54}" width="${width}" height="54" fill="rgba(0,0,0,0.68)"/>
      <text x="10" y="${height - 34}" font-family="Arial, sans-serif" font-size="15" fill="#ffffff">${esc(title)}</text>
      <text x="10" y="${height - 17}" font-family="Arial, sans-serif" font-size="12" fill="#d8d8d8">${esc(subtitle)}</text>
      <text x="${width - 10}" y="${height - 17}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#f3d37c">${esc(footer)}</text>
    </svg>`
  );
}

async function createObjectTile(item, tileWidth, tileHeight) {
  const paddingRatio = 0.18;
  const bw = Math.max(1, item.x2 - item.x1);
  const bh = Math.max(1, item.y2 - item.y1);
  const padX = Math.round(bw * paddingRatio);
  const padY = Math.round(bh * paddingRatio);
  const left = Math.max(0, item.x1 - padX);
  const top = Math.max(0, item.y1 - padY);
  const width = Math.min(item.imageWidth - left, bw + (padX * 2));
  const height = Math.min(item.imageHeight - top, bh + (padY * 2));

  const cropBuffer = await sharp(item.imagePath)
    .extract({ left, top, width: Math.max(1, width), height: Math.max(1, height) })
    .resize(tileWidth, tileHeight - 54, { fit: 'contain', background: { r: 245, g: 245, b: 245, alpha: 1 } })
    .extend({ bottom: 54, background: { r: 18, g: 18, b: 18, alpha: 1 } })
    .png()
    .toBuffer();

  const title = `${item.className} | ${item.split} | ${item.domain}`;
  const subtitle = `${item.filename} #${item.bboxIndex} | ${(item.relativeArea * 100).toFixed(2)}% area`;
  const footer = `${Math.round(item.widthPx)}x${Math.round(item.heightPx)} px`;

  return sharp(cropBuffer)
    .composite([{ input: svgTextOverlay(tileWidth, tileHeight, title, subtitle, footer), top: 0, left: 0 }])
    .png()
    .toBuffer();
}

async function createCanvas(items, outputPath, title) {
  if (!items.length) return;
  const tileWidth = 240;
  const tileHeight = 240;
  const cols = Math.min(4, items.length);
  const rows = Math.ceil(items.length / cols);
  const headerHeight = 56;
  const width = cols * tileWidth;
  const height = headerHeight + (rows * tileHeight);
  const canvas = sharp({
    create: {
      width,
      height,
      channels: 4,
      background: { r: 252, g: 252, b: 252, alpha: 1 }
    }
  });
  const composites = [];

  const header = Buffer.from(
    `<svg width="${width}" height="${headerHeight}" xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="${width}" height="${headerHeight}" fill="#17202a"/>
      <text x="16" y="32" font-family="Arial, sans-serif" font-size="22" fill="#ffffff">${title.replace(/&/g, '&amp;')}</text>
      <text x="${width - 16}" y="34" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#d6dbdf">${items.length} tiles</text>
    </svg>`
  );
  composites.push({ input: header, top: 0, left: 0 });

  for (let idx = 0; idx < items.length; idx += 1) {
    const tile = await createObjectTile(items[idx], tileWidth, tileHeight);
    const row = Math.floor(idx / cols);
    const col = idx % cols;
    composites.push({
      input: tile,
      top: headerHeight + (row * tileHeight),
      left: col * tileWidth
    });
  }

  await canvas.composite(composites).jpeg({ quality: 92 }).toFile(outputPath);
}

async function createDenseCanvas(denseImage, outputPath) {
  return createCanvas(
    denseImage.objects,
    outputPath,
    `${denseImage.filename} | ${denseImage.split} | ${denseImage.objectCount} boxes`
  );
}

function topRows(rows, n, selector) {
  return rows.slice().sort(selector).slice(0, n);
}

function buildSummaryMarkdown(params) {
  const {
    datasetDir,
    outputDir,
    classStats,
    outliers,
    violations,
    denseImages,
    overlapRows,
    missingImages
  } = params;

  const lines = [];
  lines.push('# BBox Outlier Audit');
  lines.push('');
  lines.push(`Dataset: \`${datasetDir}\``);
  lines.push(`Output: \`${outputDir}\``);
  lines.push('');
  lines.push('## Distribusi per kelas');
  lines.push('');
  lines.push('| Class | Count | P10 rel_area | Median rel_area | P90 rel_area | Median width px | Median height px |');
  lines.push('|---|---:|---:|---:|---:|---:|---:|');
  classStats.forEach((stat) => {
    lines.push(`| ${stat.className} | ${stat.count} | ${formatNumber(stat.p10)} | ${formatNumber(stat.p50)} | ${formatNumber(stat.p90)} | ${Math.round(stat.widthP50)} | ${Math.round(stat.heightP50)} |`);
  });
  lines.push('');
  lines.push('## Overlap antarkelas (P10-P90)');
  lines.push('');
  lines.push('| Pair | Overlap | LHS range | RHS range |');
  lines.push('|---|---|---|---|');
  overlapRows.forEach((row) => {
    lines.push(`| ${row.lhs} vs ${row.rhs} | ${row.overlap ? 'YES' : 'NO'} | ${formatNumber(row.lhsP10)} - ${formatNumber(row.lhsP90)} | ${formatNumber(row.rhsP10)} - ${formatNumber(row.rhsP90)} |`);
  });
  lines.push('');
  lines.push('## Kandidat review utama');
  lines.push('');
  const notable = outliers
    .slice()
    .sort((a, b) => Math.abs(b.outlierScore) - Math.abs(a.outlierScore))
    .slice(0, 12);
  notable.forEach((item, idx) => {
    lines.push(`${idx + 1}. ${item.className} ${item.outlierSide} | ${item.filename} | split=${item.split} | rel_area=${formatNumber(item.relativeArea)} | reason=${item.reviewReason}`);
  });
  lines.push('');
  lines.push('## Pelanggaran ordinal teratas');
  lines.push('');
  violations.slice(0, 12).forEach((row, idx) => {
    lines.push(`${idx + 1}. ${row.filename} | ${row.lhsClass} < ${row.rhsClass} by size | ratio=${formatNumber(row.violationRatio, 3)} | split=${row.split}`);
  });
  lines.push('');
  lines.push('## Gambar padat');
  lines.push('');
  denseImages.slice(0, 12).forEach((img, idx) => {
    const breakdown = ['B1', 'B2', 'B3', 'B4']
      .map((name) => `${name}:${img.classBreakdown[name] || 0}`)
      .join(', ');
    lines.push(`${idx + 1}. ${img.filename} | split=${img.split} | boxes=${img.objectCount} | ${breakdown}`);
  });
  lines.push('');
  if (missingImages.length) {
    lines.push('## Missing image pairs');
    lines.push('');
    missingImages.slice(0, 20).forEach((item) => lines.push(`- ${item}`));
    lines.push('');
  }
  lines.push('## Canvas');
  lines.push('');
  lines.push('- `canvases/class_left_*.jpg`: outlier kecil per kelas');
  lines.push('- `canvases/class_right_*.jpg`: outlier besar per kelas');
  lines.push('- `canvases/dense_*.jpg`: satu gambar multi-bbox, semua object crop dijajarkan urut kelas');
  return `${lines.join('\n')}\n`;
}

async function main() {
  const opts = parseArgs(process.argv);
  const root = process.cwd();
  const datasetDir = path.resolve(root, opts.dataset);
  const outputDir = path.resolve(root, opts.output);
  const canvasesDir = path.join(outputDir, 'canvases');
  ensureDir(outputDir);
  ensureDir(canvasesDir);

  const config = readDatasetConfig(datasetDir);
  const { objects, images, missingImages } = await gatherDataset(datasetDir, config.classNames);
  const classStats = computeClassStats(objects, config.classNames);
  const outliers = buildOutliers(classStats, opts.topN);
  const violations = buildOrdinalViolations(images, objects, config.classNames, opts.ordinalTolerance);
  const denseImages = buildDenseImageRows(images, objects, opts.denseMin);
  const overlapRows = summarizeOverlap(classStats);

  const outlierRows = outliers.map((row) => ({
    split: row.split,
    filename: row.filename,
    class_name: row.className,
    bbox_index: row.bboxIndex,
    width_px: Math.round(row.widthPx),
    height_px: Math.round(row.heightPx),
    area_px: Math.round(row.areaPx),
    relative_area: formatNumber(row.relativeArea),
    aspect_ratio: formatNumber(row.aspectRatio),
    objects_in_image: row.objectCountInImage,
    domain: row.domain,
    outlier_side: row.outlierSide,
    rank: row.rank,
    percentile: formatNumber(row.percentile),
    outlier_score: formatNumber(row.outlierScore),
    review_reason: row.reviewReason
  }));

  const violationRows = violations.map((row) => ({
    split: row.split,
    filename: row.filename,
    domain: row.domain,
    lhs_class: row.lhsClass,
    rhs_class: row.rhsClass,
    lhs_area: Math.round(row.lhsArea),
    rhs_area: Math.round(row.rhsArea),
    violation_ratio: formatNumber(row.violationRatio, 3),
    objects_in_image: row.objectsInImage,
    lhs_bbox_index: row.lhsBBoxIndex,
    rhs_bbox_index: row.rhsBBoxIndex,
    review_reason: row.reviewReason
  }));

  const denseRows = denseImages.map((img) => ({
    split: img.split,
    filename: img.filename,
    domain: img.domain,
    objects_in_image: img.objectCount,
    B1: img.classBreakdown.B1 || 0,
    B2: img.classBreakdown.B2 || 0,
    B3: img.classBreakdown.B3 || 0,
    B4: img.classBreakdown.B4 || 0
  }));

  writeCsv(path.join(outputDir, 'outliers.csv'), outlierRows, [
    'split', 'filename', 'class_name', 'bbox_index', 'width_px', 'height_px',
    'area_px', 'relative_area', 'aspect_ratio', 'objects_in_image', 'domain',
    'outlier_side', 'rank', 'percentile', 'outlier_score', 'review_reason'
  ]);
  writeCsv(path.join(outputDir, 'ordinal_violations.csv'), violationRows, [
    'split', 'filename', 'domain', 'lhs_class', 'rhs_class', 'lhs_area', 'rhs_area',
    'violation_ratio', 'objects_in_image', 'lhs_bbox_index', 'rhs_bbox_index', 'review_reason'
  ]);
  writeCsv(path.join(outputDir, 'dense_images.csv'), denseRows, [
    'split', 'filename', 'domain', 'objects_in_image', 'B1', 'B2', 'B3', 'B4'
  ]);

  fs.writeFileSync(
    path.join(outputDir, 'summary.json'),
    JSON.stringify({
      datasetDir,
      outputDir,
      objectCount: objects.length,
      imageCount: images.length,
      missingImages,
      classStats: classStats.map((stat) => ({
        classId: stat.classId,
        className: stat.className,
        count: stat.count,
        p10: stat.p10,
        p50: stat.p50,
        p90: stat.p90,
        widthP50: stat.widthP50,
        heightP50: stat.heightP50
      })),
      overlapRows,
      denseImageCount: denseImages.length,
      violationCount: violations.length
    }, null, 2),
    'utf8'
  );

  fs.writeFileSync(
    path.join(outputDir, 'summary.md'),
    buildSummaryMarkdown({
      datasetDir,
      outputDir,
      classStats,
      outliers,
      violations,
      denseImages,
      overlapRows,
      missingImages
    }),
    'utf8'
  );

  for (const stat of classStats) {
    const leftItems = outliers
      .filter((row) => row.classId === stat.classId && row.outlierSide === 'left')
      .slice(0, opts.topN);
    const rightItems = outliers
      .filter((row) => row.classId === stat.classId && row.outlierSide === 'right')
      .slice(0, opts.topN);
    await createCanvas(leftItems, path.join(canvasesDir, `class_left_${safeName(stat.className)}.jpg`), `${stat.className} left-tail outliers`);
    await createCanvas(rightItems, path.join(canvasesDir, `class_right_${safeName(stat.className)}.jpg`), `${stat.className} right-tail outliers`);
  }

  for (const denseImage of denseImages.slice(0, opts.denseTopN)) {
    const denseBase = path.basename(denseImage.filename, path.extname(denseImage.filename));
    await createDenseCanvas(denseImage, path.join(canvasesDir, `dense_${safeName(denseImage.split)}_${safeName(denseBase)}.jpg`));
  }

  console.log(`Analyzed ${images.length} images and ${objects.length} boxes`);
  console.log(`Output written to ${outputDir}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
