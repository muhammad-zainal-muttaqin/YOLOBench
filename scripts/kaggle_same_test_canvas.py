#!/usr/bin/env python3
"""
Kaggle-ready same-test comparison script.

Purpose:
- Compare multiple models on the exact same test set
- Export global and per-class metrics
- Generate side-by-side canvases (GT + all models) per sampled image
- Generate one master canvas for presentation

Usage in Kaggle notebook (single cell):
!pip install -q ultralytics pyyaml opencv-python
!python /kaggle/working/YOLOBench/scripts/kaggle_same_test_canvas.py

You can edit the CONFIG section below directly before running.
"""

import contextlib
import csv
import io
import random
import re
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
import yaml
from ultralytics import YOLO


# =========================
# CONFIG (edit this part)
# =========================
DATASET_ROOT = "/kaggle/input/datasets/mzainalmuttaqin2/dataset-combined-test-only/dataset_combined_test"

# 12 model V2 root (3 folder x 4 model)
MODEL_ROOT_12 = "/kaggle/input/models/mzainalmuttaqin2/model-test-4th-march-2026/tensorflow2/default/1/Model-4th March 2026"
MODEL_GROUPS = ["combined", "damimas", "lonsum"]
MODEL_FILES = ["y26l_123.pt", "y26l_42.pt", "yv9c_123.pt", "yv9c_42.pt"]

# Extra legacy models => total jadi 14
EXTRA_MODELS = {
    "legacy_yv9c_640": "/kaggle/input/models/mzainalmuttaqin2/yv9c-640/tensorflow2/default/1/yv9c_640.pt",
    "legacy_y26l_1280_damimas_only": "/kaggle/input/models/mzainalmuttaqin2/y26l-damimas-only/tensorflow2/default/1/y26l_1280_damimas_only.pt",
}

# If True, missing model path only warning (skip), not hard error.
ALLOW_MISSING_MODELS = True

CLASS_NAMES = ["B1", "B2", "B3", "B4"]
OUTDIR = "/kaggle/working/compare_same_test"

IMGSZ = 640
BATCH = 16
VAL_CONF = 0.001
PRED_CONF = 0.25
IOU = 0.6
DEVICE = 0

NUM_SAMPLES = 8
PANEL_SIZE = 360
PANELS_PER_ROW = 5
SEED = 42

SAVE_FULL_VAL_LOG = True


FLOAT_RE = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
VAL_ROW_RE = re.compile(
    rf"^\s*(?P<class>\S+)\s+(?P<images>\d+)\s+(?P<instances>\d+)\s+(?P<P>{FLOAT_RE})\s+(?P<R>{FLOAT_RE})\s+(?P<mAP50>{FLOAT_RE})\s+(?P<mAP5095>{FLOAT_RE})\s*$"
)
ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def clean_log_text(raw_text: str) -> str:
    text = ANSI_RE.sub("", raw_text)
    text = text.replace("\r", "\n")
    text = text.replace("\u2501", " ")
    return text


def parse_val_rows(log_text: str, class_names: List[str]) -> Dict[str, Dict[str, float]]:
    rows: Dict[str, Dict[str, float]] = {}
    allowed = {"all", *class_names}
    for line in clean_log_text(log_text).splitlines():
        match = VAL_ROW_RE.match(line.strip())
        if not match:
            continue
        row_name = match.group("class")
        if row_name not in allowed:
            continue
        rows[row_name] = {
            "images": int(match.group("images")),
            "instances": int(match.group("instances")),
            "P": float(match.group("P")),
            "R": float(match.group("R")),
            "mAP50": float(match.group("mAP50")),
            "mAP5095": float(match.group("mAP5095")),
        }
    return rows


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_data_yaml(dataset_root: Path, class_names: List[str], outdir: Path) -> Path:
    data = {
        "path": str(dataset_root),
        "train": "images/test",
        "val": "images/test",
        "test": "images/test",
        "nc": len(class_names),
        "names": {idx: name for idx, name in enumerate(class_names)},
    }
    yaml_path = outdir / "data_fixed.yaml"
    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    return yaml_path


def build_models() -> Dict[str, str]:
    models: Dict[str, str] = {}

    for group in MODEL_GROUPS:
        for file_name in MODEL_FILES:
            label = f"{group}_{file_name.replace('.pt', '')}"
            full_path = str(Path(MODEL_ROOT_12) / group / file_name)
            models[label] = full_path

    for label, path in EXTRA_MODELS.items():
        models[label] = path

    return models


def collect_images(images_dir: Path) -> List[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return sorted([p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in exts])


def read_gt_yolo_labels(label_path: Path, width: int, height: int) -> List[Dict[str, object]]:
    if not label_path.exists():
        return []

    boxes: List[Dict[str, object]] = []
    with label_path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 5:
                continue
            cls_id = int(float(parts[0]))
            x_center = float(parts[1]) * width
            y_center = float(parts[2]) * height
            box_w = float(parts[3]) * width
            box_h = float(parts[4]) * height
            x1 = max(0.0, x_center - box_w / 2.0)
            y1 = max(0.0, y_center - box_h / 2.0)
            x2 = min(float(width - 1), x_center + box_w / 2.0)
            y2 = min(float(height - 1), y_center + box_h / 2.0)
            boxes.append({"cls": cls_id, "conf": None, "xyxy": [x1, y1, x2, y2]})
    return boxes


def sample_images(images: List[Path], labels_dir: Path, n: int, seed: int) -> List[Path]:
    random.seed(seed)
    scored: List[Tuple[int, int, float, Path]] = []
    for p in images:
        lp = labels_dir / f"{p.stem}.txt"
        class_set = set()
        box_count = 0
        if lp.exists():
            with lp.open("r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) != 5:
                        continue
                    class_set.add(int(float(parts[0])))
                    box_count += 1
        scored.append((len(class_set), box_count, random.random(), p))
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return [x[3] for x in scored[:n]]


def get_color(idx: int) -> Tuple[int, int, int]:
    palette = [
        (66, 135, 245),
        (52, 168, 83),
        (245, 189, 66),
        (234, 67, 53),
        (171, 71, 188),
        (0, 172, 193),
    ]
    return palette[idx % len(palette)]


def draw_boxes(img: np.ndarray, boxes: List[Dict[str, object]], class_names: List[str], is_gt: bool) -> np.ndarray:
    out = img.copy()
    for item in boxes:
        class_idx = int(item["cls"])
        x1, y1, x2, y2 = item["xyxy"]
        color = get_color(class_idx)
        p1 = (int(round(x1)), int(round(y1)))
        p2 = (int(round(x2)), int(round(y2)))
        cv2.rectangle(out, p1, p2, color, 2)

        class_name = class_names[class_idx] if 0 <= class_idx < len(class_names) else str(class_idx)
        if is_gt:
            label = f"{class_name} GT"
        else:
            conf = item.get("conf")
            label = f"{class_name} {conf:.2f}" if conf is not None else class_name

        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
        tx1 = p1[0]
        ty1 = max(0, p1[1] - th - 6)
        tx2 = tx1 + tw + 6
        ty2 = ty1 + th + 6
        cv2.rectangle(out, (tx1, ty1), (tx2, ty2), color, -1)
        cv2.putText(out, label, (tx1 + 3, ty2 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 1, cv2.LINE_AA)
    return out


def predict_boxes(model: YOLO, image_path: Path, imgsz: int, conf: float, iou: float, device: int) -> List[Dict[str, object]]:
    result = model.predict(
        source=str(image_path),
        imgsz=imgsz,
        conf=conf,
        iou=iou,
        device=device,
        verbose=False,
    )[0]
    out: List[Dict[str, object]] = []
    if result.boxes is None:
        return out
    for box in result.boxes:
        xyxy = box.xyxy[0].detach().cpu().numpy().tolist()
        cls_id = int(box.cls.item())
        confv = float(box.conf.item())
        out.append({"cls": cls_id, "conf": confv, "xyxy": xyxy})
    return out


def letterbox_square(img: np.ndarray, size: int) -> np.ndarray:
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return np.zeros((size, size, 3), dtype=np.uint8)
    scale = min(size / w, size / h)
    nw = int(round(w * scale))
    nh = int(round(h * scale))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.full((size, size, 3), 20, dtype=np.uint8)
    x0 = (size - nw) // 2
    y0 = (size - nh) // 2
    canvas[y0 : y0 + nh, x0 : x0 + nw] = resized
    return canvas


def _short_title(text: str, max_len: int = 26) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def compose_row_canvas(
    panels: List[np.ndarray], titles: List[str], panel_size: int, panels_per_row: int
) -> np.ndarray:
    count = len(panels)
    gap = 12
    title_h = 34
    cols = max(1, min(panels_per_row, count))
    rows = int(np.ceil(count / cols))
    cell_h = title_h + panel_size

    width = cols * panel_size + (cols + 1) * gap
    height = rows * cell_h + (rows + 1) * gap
    canvas = np.full((height, width, 3), 15, dtype=np.uint8)

    for idx, (panel, title) in enumerate(zip(panels, titles)):
        row = idx // cols
        col = idx % cols
        x0 = gap + col * (panel_size + gap)
        y0 = gap + row * (cell_h + gap)

        cv2.putText(
            canvas,
            _short_title(title),
            (x0 + 6, y0 + 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (235, 235, 235),
            2,
            cv2.LINE_AA,
        )
        py = y0 + title_h
        canvas[py : py + panel_size, x0 : x0 + panel_size] = letterbox_square(panel, panel_size)
    return canvas


def compose_master_canvas(rows: List[np.ndarray], row_names: List[str]) -> np.ndarray:
    if not rows:
        return np.zeros((100, 400, 3), dtype=np.uint8)
    gap = 12
    title_w = 360
    row_h = rows[0].shape[0]
    row_w = rows[0].shape[1]
    header_h = 56
    total_h = header_h + len(rows) * row_h + (len(rows) + 1) * gap
    total_w = title_w + row_w + 2 * gap
    master = np.full((total_h, total_w, 3), 10, dtype=np.uint8)

    cv2.putText(
        master,
        "Same-Test Comparison (GT + Models)",
        (16, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.05,
        (240, 240, 240),
        2,
        cv2.LINE_AA,
    )

    for i, (row_img, row_name) in enumerate(zip(rows, row_names)):
        y0 = header_h + gap + i * (row_h + gap)
        x0 = title_w
        master[y0 : y0 + row_h, x0 : x0 + row_w] = row_img
        cv2.putText(
            master,
            f"{i+1:02d}. {row_name}",
            (16, y0 + 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
            (220, 220, 220),
            2,
            cv2.LINE_AA,
        )
    return master


def main() -> None:
    dataset_root = Path(DATASET_ROOT)
    outdir = Path(OUTDIR)
    outdir.mkdir(parents=True, exist_ok=True)
    canvases_dir = outdir / "canvases"
    canvases_dir.mkdir(parents=True, exist_ok=True)

    images_dir = dataset_root / "images" / "test"
    labels_dir = dataset_root / "labels" / "test"
    if not images_dir.exists() or not labels_dir.exists():
        raise FileNotFoundError(f"Dataset path invalid: {dataset_root}")

    models = build_models()
    valid_models: Dict[str, str] = {}
    for label, path in models.items():
        if Path(path).exists():
            valid_models[label] = path
        else:
            msg = f"Model path not found for '{label}': {path}"
            if ALLOW_MISSING_MODELS:
                print(f"[WARN] {msg} (skipped)")
            else:
                raise FileNotFoundError(msg)

    if not valid_models:
        raise RuntimeError("No valid models found. Check your model paths.")

    yaml_path = make_data_yaml(dataset_root, CLASS_NAMES, outdir)
    print(f"YAML saved: {yaml_path}")

    model_objs: Dict[str, YOLO] = {}
    global_rows: List[Dict[str, object]] = []
    class_rows: List[Dict[str, object]] = []

    print(f"Models requested: {len(models)}")
    print(f"Models loaded   : {len(valid_models)}")

    for label, model_path in valid_models.items():
        print("\n" + "=" * 72)
        print(f"Evaluating: {label}")
        print("=" * 72)

        model = YOLO(model_path)
        model_objs[label] = model

        buff = io.StringIO()
        with contextlib.redirect_stdout(buff):
            metrics = model.val(
                data=str(yaml_path),
                split="test",
                imgsz=IMGSZ,
                batch=BATCH,
                conf=VAL_CONF,
                iou=IOU,
                device=DEVICE,
                verbose=True,
            )
        log = buff.getvalue()
        clean_log = clean_log_text(log)

        if SAVE_FULL_VAL_LOG:
            (outdir / f"val_log_{label}.txt").write_text(clean_log, encoding="utf-8")

        parsed = parse_val_rows(clean_log, CLASS_NAMES)
        if "all" not in parsed:
            parsed["all"] = {
                "images": "",
                "instances": "",
                "P": float(metrics.box.mp),
                "R": float(metrics.box.mr),
                "mAP50": float(metrics.box.map50),
                "mAP5095": float(metrics.box.map),
            }

        g = parsed["all"]
        global_rows.append(
            {
                "model_label": label,
                "model_path": model_path,
                "images": g["images"],
                "instances": g["instances"],
                "P": round(float(g["P"]), 4),
                "R": round(float(g["R"]), 4),
                "mAP50": round(float(g["mAP50"]), 4),
                "mAP5095": round(float(g["mAP5095"]), 4),
            }
        )

        for cname in CLASS_NAMES:
            row = parsed.get(cname)
            if not row:
                continue
            class_rows.append(
                {
                    "model_label": label,
                    "class": cname,
                    "images": row["images"],
                    "instances": row["instances"],
                    "P": round(float(row["P"]), 4),
                    "R": round(float(row["R"]), 4),
                    "mAP50": round(float(row["mAP50"]), 4),
                    "mAP5095": round(float(row["mAP5095"]), 4),
                }
            )

        print(
            f"{label} -> mAP50={float(g['mAP50']):.4f}, "
            f"mAP50-95={float(g['mAP5095']):.4f}, P={float(g['P']):.4f}, R={float(g['R']):.4f}"
        )

    global_csv = outdir / "global_metrics.csv"
    per_class_csv = outdir / "per_class_metrics.csv"

    write_csv(
        global_csv,
        global_rows,
        ["model_label", "model_path", "images", "instances", "P", "R", "mAP50", "mAP5095"],
    )
    write_csv(
        per_class_csv,
        class_rows,
        ["model_label", "class", "images", "instances", "P", "R", "mAP50", "mAP5095"],
    )

    all_images = collect_images(images_dir)
    picked_images = sample_images(all_images, labels_dir, NUM_SAMPLES, SEED)

    canvas_manifest_rows: List[Dict[str, object]] = []
    row_canvases: List[np.ndarray] = []
    row_names: List[str] = []

    print("\nGenerating side-by-side canvases...")
    for idx, img_path in enumerate(picked_images, start=1):
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        gt_boxes = read_gt_yolo_labels(labels_dir / f"{img_path.stem}.txt", img.shape[1], img.shape[0])

        panels = [draw_boxes(img, gt_boxes, CLASS_NAMES, is_gt=True)]
        titles = ["Ground Truth"]

        for label, model in model_objs.items():
            pred_boxes = predict_boxes(model, img_path, imgsz=IMGSZ, conf=PRED_CONF, iou=IOU, device=DEVICE)
            panels.append(draw_boxes(img, pred_boxes, CLASS_NAMES, is_gt=False))
            titles.append(label)

        row_canvas = compose_row_canvas(panels, titles, PANEL_SIZE, PANELS_PER_ROW)
        row_canvases.append(row_canvas)
        row_names.append(img_path.name)

        row_name = f"canvas_{idx:02d}_{img_path.stem}.jpg"
        row_path = canvases_dir / row_name
        cv2.imwrite(str(row_path), row_canvas)

        class_hist = {name: 0 for name in CLASS_NAMES}
        for gt in gt_boxes:
            cls_id = int(gt["cls"])
            if 0 <= cls_id < len(CLASS_NAMES):
                class_hist[CLASS_NAMES[cls_id]] += 1

        row = {
            "index": idx,
            "image_path": str(img_path),
            "canvas_path": str(row_path),
            "gt_boxes": len(gt_boxes),
        }
        for cname in CLASS_NAMES:
            row[f"gt_{cname}"] = class_hist[cname]
        canvas_manifest_rows.append(row)

    manifest_csv = outdir / "canvas_manifest.csv"
    write_csv(
        manifest_csv,
        canvas_manifest_rows,
        ["index", "image_path", "canvas_path", "gt_boxes", *[f"gt_{c}" for c in CLASS_NAMES]],
    )

    master_canvas = compose_master_canvas(row_canvases, row_names)
    master_canvas_path = outdir / "master_canvas.jpg"
    cv2.imwrite(str(master_canvas_path), master_canvas)

    # Quick summary markdown
    md = []
    md.append("# Same-Test Comparison Summary")
    md.append("")
    md.append(f"- Dataset test root: `{dataset_root}`")
    md.append(f"- Models compared: `{len(valid_models)}`")
    md.append("")
    md.append("## Files")
    md.append(f"- Global: `{global_csv}`")
    md.append(f"- Per-class: `{per_class_csv}`")
    md.append(f"- Manifest: `{manifest_csv}`")
    md.append(f"- Master canvas: `{master_canvas_path}`")
    md.append(f"- Row canvases: `{canvases_dir}`")
    md.append("")
    md.append("## Notes")
    md.append("- Gunakan `per_class_metrics.csv` untuk analisis per jenis pohon (B1-B4).")
    md.append("- Gunakan `master_canvas.jpg` untuk slide perbandingan visual 1 canvas.")
    (outdir / "README_results.md").write_text("\n".join(md), encoding="utf-8")

    print("\nDone.")
    print(f"Global metrics  : {global_csv}")
    print(f"Per-class       : {per_class_csv}")
    print(f"Manifest        : {manifest_csv}")
    print(f"Master canvas   : {master_canvas_path}")
    print(f"Row canvases    : {canvases_dir}")


if __name__ == "__main__":
    main()
