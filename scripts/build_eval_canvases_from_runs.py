#!/usr/bin/env python3
"""
Build side-by-side canvases from existing YOLO val artifacts in Test/runs/detect.

Default mapping uses val..val14:
- 12 v2 models (combined/damimas/lonsum x 4)
- 2 legacy models tested on v2 test set
"""

from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np


RUNS_ROOT = Path("Test/runs/detect")
OUTDIR = Path("Test/runs/compare_canvases")

RUN_LABELS: List[Tuple[str, str]] = [
    ("val", "combined_y26l_123"),
    ("val2", "combined_y26l_42"),
    ("val3", "combined_yv9c_123"),
    ("val4", "combined_yv9c_42"),
    ("val5", "damimas_y26l_123"),
    ("val6", "damimas_y26l_42"),
    ("val7", "damimas_yv9c_123"),
    ("val8", "damimas_yv9c_42"),
    ("val9", "lonsum_y26l_123"),
    ("val10", "lonsum_y26l_42"),
    ("val11", "lonsum_yv9c_123"),
    ("val12", "lonsum_yv9c_42"),
    ("val13", "legacy_yv9c_640"),
    ("val14", "legacy_y26l_1280_damimas_only"),
]

CURVE_FILES = [
    "BoxF1_curve.png",
    "BoxP_curve.png",
    "BoxR_curve.png",
    "BoxPR_curve.png",
    "confusion_matrix_normalized.png",
]

PRED_FILES = ["val_batch0_pred.jpg", "val_batch1_pred.jpg", "val_batch2_pred.jpg"]

GRID_COLS = 4
PANEL_SIZE = 420
GAP = 12
TITLE_H = 34
HEADER_H = 54


def short_title(text: str, max_len: int = 30) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def letterbox_square(img: np.ndarray, size: int) -> np.ndarray:
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return np.zeros((size, size, 3), dtype=np.uint8)
    scale = min(size / w, size / h)
    nw = int(round(w * scale))
    nh = int(round(h * scale))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.full((size, size, 3), 18, dtype=np.uint8)
    x0 = (size - nw) // 2
    y0 = (size - nh) // 2
    canvas[y0 : y0 + nh, x0 : x0 + nw] = resized
    return canvas


def build_grid(items: List[Tuple[str, np.ndarray]], big_title: str) -> np.ndarray:
    if not items:
        return np.zeros((120, 500, 3), dtype=np.uint8)

    cols = min(GRID_COLS, len(items))
    rows = (len(items) + cols - 1) // cols
    cell_h = TITLE_H + PANEL_SIZE

    width = cols * PANEL_SIZE + (cols + 1) * GAP
    height = HEADER_H + rows * cell_h + (rows + 1) * GAP
    canvas = np.full((height, width, 3), 12, dtype=np.uint8)

    cv2.putText(
        canvas,
        big_title,
        (GAP, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (240, 240, 240),
        2,
        cv2.LINE_AA,
    )

    for idx, (label, image) in enumerate(items):
        row = idx // cols
        col = idx % cols
        x0 = GAP + col * (PANEL_SIZE + GAP)
        y0 = HEADER_H + GAP + row * (cell_h + GAP)

        cv2.putText(
            canvas,
            short_title(label),
            (x0 + 6, y0 + 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.56,
            (230, 230, 230),
            2,
            cv2.LINE_AA,
        )
        panel = letterbox_square(image, PANEL_SIZE)
        py = y0 + TITLE_H
        canvas[py : py + PANEL_SIZE, x0 : x0 + PANEL_SIZE] = panel

    return canvas


def collect_images(file_name: str) -> List[Tuple[str, np.ndarray]]:
    items: List[Tuple[str, np.ndarray]] = []
    for run_name, label in RUN_LABELS:
        path = RUNS_ROOT / run_name / file_name
        if not path.exists():
            print(f"[WARN] Missing: {path}")
            continue
        image = cv2.imread(str(path))
        if image is None:
            print(f"[WARN] Failed read: {path}")
            continue
        items.append((label, image))
    return items


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    generated: List[Path] = []

    for file_name in CURVE_FILES:
        items = collect_images(file_name)
        grid = build_grid(items, f"Same-Test Comparison: {file_name}")
        out_path = OUTDIR / f"grid_{file_name}"
        cv2.imwrite(str(out_path), grid)
        generated.append(out_path)
        print(f"[OK] {out_path}")

    for file_name in PRED_FILES:
        items = collect_images(file_name)
        grid = build_grid(items, f"Predictions Comparison: {file_name}")
        out_path = OUTDIR / f"grid_{file_name}"
        cv2.imwrite(str(out_path), grid)
        generated.append(out_path)
        print(f"[OK] {out_path}")

    readme = OUTDIR / "README.md"
    lines = [
        "# Comparison Canvases",
        "",
        "Generated from `Test/runs/detect/val..val14`.",
        "",
        "Files:",
    ]
    lines.extend([f"- `{path.name}`" for path in generated])
    readme.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] {readme}")


if __name__ == "__main__":
    main()
