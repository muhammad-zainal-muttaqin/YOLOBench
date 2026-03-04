# YOLO Research Logbook

An interactive web dashboard for tracking and analyzing YOLO object detection experiments — from planning to evaluation.

## Overview

Single-page dashboard that visualizes experiment progress as a research logbook: calendar view, daily timeline, run leaderboard, and detailed per-class metrics with overfitting/leakage detection.

### Features

- **Calendar & Timeline** — Track daily research activities (meetings, dataset prep, training, evaluation)
- **Run Leaderboard** — Ranked comparison of experiments by mAP@50, mAP@50-95, Precision, or Recall
- **Detailed Metrics** — Per-class breakdown (B1-B4), radar charts, and train/val/test split comparison
- **Overfitting Detection** — Train–Val gap indicator
- **Leakage Detection** — Val–Test gap indicator
- **Filters** — By status, type, dataset, model, seed, generation (legacy/v2)
- **Responsive** — Desktop 3-column grid, mobile vertical scroll

## Models

| Model | Architecture | Notes |
| :--- | :--- | :--- |
| **YOLO26l** | End-to-End (NMS-free) | Latest gen, optimized for edge/CPU |
| **YOLOv9c** | Compact (~25.5M params) | Standard base model |
| **YOLOv9m** | Medium (~20.1M params) | Speed-accuracy balance |

## Datasets

| Scenario | Generation | Description |
| :--- | :--- | :--- |
| stratifikasi | legacy | Stratified class-proportional split |
| sawit-yolo | legacy | Original sawit dataset split |
| damimas-full | legacy | Full Damimas dataset, old split |
| all_data | v2 | Combined Damimas + Lonsum, tree-level split (no leakage) |
| damimas_only | v2 | Damimas only, tree-level split |
| lonsum_only | v2 | Lonsum only, tree-level split |

## Usage

### Online
Deployed on Cloudflare Pages — just open the URL.

### Local
```bash
git clone https://github.com/muhammad-zainal-muttaqin/YOLOBench.git
cd YOLOBench
# Open index.html in browser (works offline via inline data fallback)
```

## Data Structure

```
data/
├── index.json       # Manifest: months list + project metadata
└── YYYY-MM.json     # Monthly events + experiment runs + metrics
```

See **[DATA_GUIDE.md](DATA_GUIDE.md)** for the complete schema and instructions on adding new data.

## Adding New Experiment Data

1. Edit `data/YYYY-MM.json` (or create new month file)
2. Update `data/index.json` metadata
3. Run `node scripts/update_inline.js` to sync inline fallback
4. See [DATA_GUIDE.md](DATA_GUIDE.md) for detailed steps

---
*Created for the Assistive Teaching project — Universitas Riau.*
