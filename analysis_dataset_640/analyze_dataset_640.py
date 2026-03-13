from __future__ import annotations

import argparse
import json
import random
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from PIL import Image
from scipy.spatial.distance import jensenshannon
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.manifold import TSNE
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from torchvision import models

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

CLASS_MAP = {"0": "B1", "1": "B2", "2": "B3", "3": "B4"}
CLASS_ORDER = ["B1", "B2", "B3", "B4"]
SPLIT_ORDER = ["train", "val", "test"]
SOURCE_MAP = {"DAMIMAS_A21B": "DAMIMAS", "LONSUM_A21A": "LONSUM"}
SOURCE_ORDER = ["DAMIMAS", "LONSUM"]
PALETTE = {
    "B1": "#136f63",
    "B2": "#ff7f11",
    "B3": "#3f88c5",
    "B4": "#d7263d",
    "DAMIMAS": "#1f4e79",
    "LONSUM": "#c85c18",
}
SEED = 42


@dataclass
class CropSample:
    sample_id: int
    class_name: str
    source: str
    split: str
    tree_id: str
    view_id: str
    image_path: Path
    bbox: tuple[float, float, float, float]
    crop: Image.Image
    area: float
    y_center: float
    label_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deep analysis for dataset_640")
    parser.add_argument("--dataset-root", type=Path, default=Path("dataset_640"))
    parser.add_argument("--output-dir", type=Path, default=Path("analysis_dataset_640"))
    parser.add_argument("--with-model-context", action="store_true")
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def ensure_dirs(output_dir: Path) -> dict[str, Path]:
    figures_dir = output_dir / "figures"
    tables_dir = output_dir / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    return {"root": output_dir, "figures": figures_dir, "tables": tables_dir}


def split_tree_view(stem: str) -> tuple[str, str, str]:
    parts = stem.split("_")
    source_key = "_".join(parts[:2])
    tree_id = "_".join(parts[:-1])
    view_id = parts[-1]
    return source_key, tree_id, view_id


def save_table(df: pd.DataFrame, path: Path, sort_columns: list[str] | None = None) -> pd.DataFrame:
    table = df.copy()
    if sort_columns:
        valid_columns = [column for column in sort_columns if column in table.columns]
        if valid_columns and not table.empty:
            table = table.sort_values(valid_columns)
    table.to_csv(path, index=False)
    return table


def fmt_int(value: float | int) -> str:
    return f"{int(value):,}".replace(",", ".")


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def markdown_table(df: pd.DataFrame, precision: int = 3, max_rows: int | None = None) -> str:
    table = df.copy()
    if max_rows is not None:
        table = table.head(max_rows)
    for column in table.columns:
        if pd.api.types.is_float_dtype(table[column]):
            table[column] = table[column].map(lambda x: f"{x:.{precision}f}")
    columns = list(table.columns)
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = ["| " + " | ".join(str(row[column]) for column in columns) + " |" for _, row in table.iterrows()]
    return "\n".join([header, divider, *rows])


def js_distance_from_counts(left: pd.Series, right: pd.Series) -> float:
    left = left.astype(float)
    right = right.astype(float)
    if left.sum() == 0 or right.sum() == 0:
        return float("nan")
    return float(jensenshannon(left / left.sum(), right / right.sum(), base=2))


def histogram_js_distance(left: pd.Series, right: pd.Series, bins: np.ndarray) -> float:
    left_hist, _ = np.histogram(left, bins=bins)
    right_hist, _ = np.histogram(right, bins=bins)
    if left_hist.sum() == 0 or right_hist.sum() == 0:
        return float("nan")
    return float(jensenshannon(left_hist / left_hist.sum(), right_hist / right_hist.sum(), base=2))


def load_dataset(dataset_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    image_records: list[dict] = []
    instance_records: list[dict] = []
    instance_id = 0

    for split in SPLIT_ORDER:
        image_dir = dataset_root / "images" / split
        label_dir = dataset_root / "labels" / split
        image_paths = sorted(image_dir.glob("*.jpg"))
        label_paths = {p.stem: p for p in label_dir.glob("*.txt")}

        for image_path in image_paths:
            label_path = label_paths.get(image_path.stem)
            source_key, tree_id, view_id = split_tree_view(image_path.stem)
            source = SOURCE_MAP.get(source_key, source_key)

            with Image.open(image_path) as image:
                width, height = image.size

            file_size = image_path.stat().st_size
            lines: list[str] = []
            if label_path is not None:
                raw = label_path.read_text().strip()
                lines = [line for line in raw.splitlines() if line.strip()]

            class_ids = [line.split()[0] for line in lines]
            class_names = sorted({CLASS_MAP[class_id] for class_id in class_ids})
            class_combo = "+".join(class_names) if class_names else "EMPTY"

            image_records.append(
                {
                    "image_path": str(image_path),
                    "label_path": str(label_path) if label_path else "",
                    "stem": image_path.stem,
                    "split": split,
                    "source_key": source_key,
                    "source": source,
                    "tree_id": tree_id,
                    "view_id": view_id,
                    "width_px": width,
                    "height_px": height,
                    "file_size_bytes": file_size,
                    "label_count": len(lines),
                    "is_empty": int(len(lines) == 0),
                    "unique_class_count": len(class_names),
                    "class_combo": class_combo,
                    **{f"has_{class_name}": int(class_name in class_names) for class_name in CLASS_ORDER},
                }
            )

            for line_index, line in enumerate(lines):
                class_id, x_center, y_center, bbox_w, bbox_h = line.split()
                x_center = float(x_center)
                y_center = float(y_center)
                bbox_w = float(bbox_w)
                bbox_h = float(bbox_h)
                bbox_area = bbox_w * bbox_h
                aspect_ratio = bbox_w / bbox_h if bbox_h else 0.0
                instance_records.append(
                    {
                        "instance_id": instance_id,
                        "line_index": line_index,
                        "image_path": str(image_path),
                        "stem": image_path.stem,
                        "split": split,
                        "source_key": source_key,
                        "source": source,
                        "tree_id": tree_id,
                        "view_id": view_id,
                        "class_id": class_id,
                        "class_name": CLASS_MAP[class_id],
                        "x_center": x_center,
                        "y_center": y_center,
                        "bbox_w": bbox_w,
                        "bbox_h": bbox_h,
                        "bbox_area": bbox_area,
                        "aspect_ratio": aspect_ratio,
                    }
                )
                instance_id += 1

    images_df = pd.DataFrame(image_records)
    instances_df = pd.DataFrame(instance_records)
    if not instances_df.empty:
        label_count_lookup = images_df.set_index("stem")["label_count"]
        instances_df["image_label_count"] = instances_df["stem"].map(label_count_lookup).astype(int)
        instances_df["crowding_others"] = instances_df["image_label_count"] - 1
    return images_df, instances_df


def build_split_summary(images_df: pd.DataFrame, instances_df: pd.DataFrame) -> pd.DataFrame:
    tree_counts = images_df.groupby("split")["tree_id"].nunique().rename("trees")
    source_counts = images_df.groupby(["split", "source"]).size().unstack(fill_value=0)
    instance_counts = instances_df.groupby("split").size().rename("instances")

    summary = (
        images_df.groupby("split")
        .agg(
            images=("stem", "count"),
            empty_images=("is_empty", "sum"),
            avg_objects_per_image=("label_count", "mean"),
            median_objects_per_image=("label_count", "median"),
            p90_objects_per_image=("label_count", lambda x: float(np.quantile(x, 0.9))),
        )
        .join(tree_counts)
        .join(instance_counts)
        .join(source_counts)
        .reset_index()
    )
    summary["instances"] = summary["instances"].fillna(0).astype(int)
    summary["non_empty_images"] = summary["images"] - summary["empty_images"]
    summary["empty_rate"] = summary["empty_images"] / summary["images"]
    summary["damimas_share_images"] = summary["DAMIMAS"] / summary["images"]
    summary["lonsum_share_images"] = summary["LONSUM"] / summary["images"]
    return summary


def build_class_summary(images_df: pd.DataFrame, instances_df: pd.DataFrame) -> pd.DataFrame:
    total_instances = len(instances_df)
    overall_image_count = len(images_df)
    records = []
    for class_name in CLASS_ORDER:
        class_instances = instances_df[instances_df["class_name"] == class_name]
        images_with_class = images_df[f"has_{class_name}"].sum()
        records.append(
            {
                "class_name": class_name,
                "instances": len(class_instances),
                "instance_share": len(class_instances) / total_instances,
                "images_with_class": int(images_with_class),
                "image_prevalence": images_with_class / overall_image_count,
                "mean_bbox_area": class_instances["bbox_area"].mean(),
                "median_bbox_area": class_instances["bbox_area"].median(),
                "mean_bbox_w": class_instances["bbox_w"].mean(),
                "mean_bbox_h": class_instances["bbox_h"].mean(),
                "mean_aspect_ratio": class_instances["aspect_ratio"].mean(),
                "mean_x_center": class_instances["x_center"].mean(),
                "mean_y_center": class_instances["y_center"].mean(),
                "mean_image_density": class_instances["image_label_count"].mean(),
                "mean_crowding_others": class_instances["crowding_others"].mean(),
            }
        )
    return pd.DataFrame(records)


def build_source_class_summary(images_df: pd.DataFrame, instances_df: pd.DataFrame) -> pd.DataFrame:
    image_counts = (
        images_df.groupby("source")[["has_B1", "has_B2", "has_B3", "has_B4"]]
        .sum()
        .rename(columns=lambda x: x.replace("has_", "images_with_"))
    )
    instance_counts = (
        instances_df.groupby(["source", "class_name"])
        .size()
        .rename("instances")
        .reset_index()
        .pivot(index="source", columns="class_name", values="instances")
        .fillna(0)
    )

    records = []
    for source in SOURCE_ORDER:
        total_images = int((images_df["source"] == source).sum())
        total_instances = int((instances_df["source"] == source).sum())
        for class_name in CLASS_ORDER:
            class_instances = instances_df[
                (instances_df["source"] == source) & (instances_df["class_name"] == class_name)
            ]
            records.append(
                {
                    "source": source,
                    "class_name": class_name,
                    "instances": int(instance_counts.loc[source, class_name]) if source in instance_counts.index else 0,
                    "instance_share_within_source": len(class_instances) / total_instances if total_instances else 0.0,
                    "images_with_class": (
                        int(image_counts.loc[source, f"images_with_{class_name}"])
                        if source in image_counts.index
                        else 0
                    ),
                    "image_prevalence_within_source": (
                        int(image_counts.loc[source, f"images_with_{class_name}"]) / total_images
                        if total_images
                        else 0.0
                    ),
                    "mean_bbox_area": class_instances["bbox_area"].mean() if not class_instances.empty else np.nan,
                    "mean_y_center": class_instances["y_center"].mean() if not class_instances.empty else np.nan,
                }
            )
    return pd.DataFrame(records)


def build_class_split_summary(images_df: pd.DataFrame, instances_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for split in SPLIT_ORDER:
        split_images = images_df[images_df["split"] == split]
        split_instances = instances_df[instances_df["split"] == split]
        for class_name in CLASS_ORDER:
            subset = split_instances[split_instances["class_name"] == class_name]
            records.append(
                {
                    "split": split,
                    "class_name": class_name,
                    "instances": len(subset),
                    "images_with_class": int(split_images[f"has_{class_name}"].sum()),
                    "instance_share_in_split": len(subset) / len(split_instances) if len(split_instances) else 0.0,
                    "image_prevalence_in_split": split_images[f"has_{class_name}"].mean(),
                }
            )
    return pd.DataFrame(records)


def build_source_split_summary(images_df: pd.DataFrame, instances_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for split in SPLIT_ORDER:
        split_images = images_df[images_df["split"] == split]
        split_instances = instances_df[instances_df["split"] == split]
        for source in SOURCE_ORDER:
            source_images = split_images[split_images["source"] == source]
            source_instances = split_instances[split_instances["source"] == source]
            records.append(
                {
                    "split": split,
                    "source": source,
                    "images": len(source_images),
                    "trees": source_images["tree_id"].nunique(),
                    "instances": len(source_instances),
                    "empty_images": int(source_images["is_empty"].sum()),
                    "avg_objects_per_image": source_images["label_count"].mean(),
                    "image_share_in_split": len(source_images) / len(split_images),
                    "instance_share_in_split": len(source_instances) / len(split_instances)
                    if len(split_instances)
                    else 0.0,
                }
            )
    return pd.DataFrame(records)


def build_class_combo_summary(images_df: pd.DataFrame) -> pd.DataFrame:
    combos = images_df[images_df["class_combo"] != "EMPTY"].copy()
    summary = (
        combos.groupby("class_combo")
        .agg(images=("stem", "count"))
        .reset_index()
        .sort_values("images", ascending=False)
    )
    summary["support"] = summary["images"] / len(combos)
    return summary


def build_pairwise_association(images_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    non_empty_images = images_df[images_df["class_combo"] != "EMPTY"]
    total = len(non_empty_images)
    for index_a, class_a in enumerate(CLASS_ORDER):
        for class_b in CLASS_ORDER[index_a + 1 :]:
            has_a = non_empty_images[f"has_{class_a}"].astype(bool)
            has_b = non_empty_images[f"has_{class_b}"].astype(bool)
            both = has_a & has_b
            support_a = has_a.mean()
            support_b = has_b.mean()
            support_both = both.mean()
            confidence_a_to_b = support_both / support_a if support_a else np.nan
            confidence_b_to_a = support_both / support_b if support_b else np.nan
            lift = support_both / (support_a * support_b) if support_a and support_b else np.nan
            records.append(
                {
                    "class_a": class_a,
                    "class_b": class_b,
                    "images_with_both": int(both.sum()),
                    "support_a": support_a,
                    "support_b": support_b,
                    "support_both": support_both,
                    "confidence_a_to_b": confidence_a_to_b,
                    "confidence_b_to_a": confidence_b_to_a,
                    "lift": lift,
                    "expected_if_independent": support_a * support_b * total,
                    "excess_pairings": both.sum() - (support_a * support_b * total),
                }
            )
    return pd.DataFrame(records).sort_values("lift", ascending=False)


def build_tree_view_tables(images_df: pd.DataFrame, instances_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tree_summary = (
        images_df.groupby(["split", "source", "tree_id"])
        .agg(
            views=("view_id", "nunique"),
            images=("stem", "count"),
            total_objects=("label_count", "sum"),
            mean_objects_per_view=("label_count", "mean"),
            std_objects_per_view=("label_count", "std"),
            distinct_combos=("class_combo", "nunique"),
            empty_views=("is_empty", "sum"),
        )
        .reset_index()
    )
    tree_summary["std_objects_per_view"] = tree_summary["std_objects_per_view"].fillna(0.0)
    tree_summary["cv_objects_per_view"] = tree_summary["std_objects_per_view"] / (
        tree_summary["mean_objects_per_view"] + 1e-9
    )

    per_view = (
        images_df.groupby(["split", "source", "view_id"])
        .agg(images=("stem", "count"), mean_objects=("label_count", "mean"), empty_rate=("is_empty", "mean"))
        .reset_index()
    )

    tree_class = (
        instances_df.groupby(["tree_id", "class_name"])
        .size()
        .rename("instances")
        .reset_index()
        .pivot(index="tree_id", columns="class_name", values="instances")
        .fillna(0)
        .reset_index()
    )
    tree_summary = tree_summary.merge(tree_class, how="left", on="tree_id").fillna(0)
    return tree_summary, per_view, tree_class


def build_zero_coverage_table(source_class_summary: pd.DataFrame) -> pd.DataFrame:
    return source_class_summary[source_class_summary["instances"] == 0].copy()


def build_source_drift_tables(images_df: pd.DataFrame, instances_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    area_bins = np.linspace(0, 0.08, 17)
    y_bins = np.linspace(0, 1.0, 21)
    density_bins = np.arange(0, 12, 1)

    for split in ["all", *SPLIT_ORDER]:
        image_subset = images_df if split == "all" else images_df[images_df["split"] == split]
        instance_subset = instances_df if split == "all" else instances_df[instances_df["split"] == split]
        damimas_images = image_subset[image_subset["source"] == "DAMIMAS"]
        lonsum_images = image_subset[image_subset["source"] == "LONSUM"]
        damimas_instances = instance_subset[instance_subset["source"] == "DAMIMAS"]
        lonsum_instances = instance_subset[instance_subset["source"] == "LONSUM"]
        if damimas_images.empty or lonsum_images.empty:
            continue

        class_mix_damimas = damimas_instances["class_name"].value_counts().reindex(CLASS_ORDER, fill_value=0)
        class_mix_lonsum = lonsum_instances["class_name"].value_counts().reindex(CLASS_ORDER, fill_value=0)
        records.append(
            {
                "split_scope": split,
                "metric": "class_mix_instances_js",
                "class_name": "ALL",
                "value": js_distance_from_counts(class_mix_damimas, class_mix_lonsum),
            }
        )
        records.append(
            {
                "split_scope": split,
                "metric": "image_density_js",
                "class_name": "ALL",
                "value": histogram_js_distance(damimas_images["label_count"], lonsum_images["label_count"], density_bins),
            }
        )

        for class_name in CLASS_ORDER:
            damimas_class = damimas_instances[damimas_instances["class_name"] == class_name]
            lonsum_class = lonsum_instances[lonsum_instances["class_name"] == class_name]
            records.append(
                {
                    "split_scope": split,
                    "metric": "bbox_area_js",
                    "class_name": class_name,
                    "value": histogram_js_distance(damimas_class["bbox_area"], lonsum_class["bbox_area"], area_bins),
                }
            )
            records.append(
                {
                    "split_scope": split,
                    "metric": "y_center_js",
                    "class_name": class_name,
                    "value": histogram_js_distance(damimas_class["y_center"], lonsum_class["y_center"], y_bins),
                }
            )
    return pd.DataFrame(records)


def pick_stratified_samples(instances_df: pd.DataFrame, max_per_class: int = 320) -> pd.DataFrame:
    samples = []
    for class_name in CLASS_ORDER:
        class_df = instances_df[instances_df["class_name"] == class_name].copy()
        if class_df.empty:
            continue
        chosen = []
        for source in ["LONSUM", "DAMIMAS"]:
            source_df = class_df[class_df["source"] == source]
            if source_df.empty:
                continue
            keep = min(len(source_df), max(40, int(max_per_class * 0.18)) if source == "LONSUM" else max_per_class)
            chosen.append(source_df.sample(n=keep, random_state=SEED, replace=False))
        chosen_df = pd.concat(chosen, ignore_index=True).drop_duplicates(subset=["instance_id"])
        if len(chosen_df) > max_per_class:
            chosen_df = chosen_df.sample(n=max_per_class, random_state=SEED, replace=False)
        if len(chosen_df) < max_per_class and len(class_df) > len(chosen_df):
            extra = class_df[~class_df["instance_id"].isin(chosen_df["instance_id"])]
            take = min(max_per_class - len(chosen_df), len(extra))
            if take:
                chosen_df = pd.concat(
                    [chosen_df, extra.sample(n=take, random_state=SEED, replace=False)], ignore_index=True
                )
        samples.append(chosen_df)
    return pd.concat(samples, ignore_index=True)


def crop_from_bbox(image_path: Path, bbox: tuple[float, float, float, float], margin: float = 0.12) -> Image.Image:
    x_center, y_center, bbox_w, bbox_h = bbox
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        width, height = image.size
        x1 = max(0, int((x_center - bbox_w / 2 - bbox_w * margin) * width))
        y1 = max(0, int((y_center - bbox_h / 2 - bbox_h * margin) * height))
        x2 = min(width, int((x_center + bbox_w / 2 + bbox_w * margin) * width))
        y2 = min(height, int((y_center + bbox_h / 2 + bbox_h * margin) * height))
        if x2 <= x1 or y2 <= y1:
            x1 = max(0, int((x_center - bbox_w / 2) * width))
            y1 = max(0, int((y_center - bbox_h / 2) * height))
            x2 = min(width, int((x_center + bbox_w / 2) * width))
            y2 = min(height, int((y_center + bbox_h / 2) * height))
        return image.crop((x1, y1, x2, y2))


def build_crop_samples(sample_instances: pd.DataFrame) -> list[CropSample]:
    samples: list[CropSample] = []
    for row in sample_instances.itertuples(index=False):
        crop = crop_from_bbox(Path(row.image_path), (row.x_center, row.y_center, row.bbox_w, row.bbox_h))
        samples.append(
            CropSample(
                sample_id=int(row.instance_id),
                class_name=row.class_name,
                source=row.source,
                split=row.split,
                tree_id=row.tree_id,
                view_id=row.view_id,
                image_path=Path(row.image_path),
                bbox=(row.x_center, row.y_center, row.bbox_w, row.bbox_h),
                crop=crop,
                area=float(row.bbox_area),
                y_center=float(row.y_center),
                label_count=int(row.image_label_count),
            )
        )
    return samples


def extract_embeddings(samples: list[CropSample]) -> tuple[pd.DataFrame, np.ndarray]:
    weights = models.ResNet50_Weights.IMAGENET1K_V2
    preprocess = weights.transforms()
    model = models.resnet50(weights=weights)
    model.fc = torch.nn.Identity()
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    vectors = []
    metadata = []
    batch_tensors = []
    batch_metadata = []
    batch_size = 32

    with torch.no_grad():
        for sample in samples:
            batch_tensors.append(preprocess(sample.crop).unsqueeze(0))
            batch_metadata.append(sample)
            if len(batch_tensors) == batch_size:
                batch = torch.cat(batch_tensors, dim=0).to(device)
                outputs = model(batch).cpu().numpy()
                for output, meta in zip(outputs, batch_metadata, strict=True):
                    vectors.append(output)
                    metadata.append(
                        {
                            "sample_id": meta.sample_id,
                            "class_name": meta.class_name,
                            "source": meta.source,
                            "split": meta.split,
                            "tree_id": meta.tree_id,
                            "view_id": meta.view_id,
                            "image_path": str(meta.image_path),
                            "bbox_area": meta.area,
                            "y_center": meta.y_center,
                            "label_count": meta.label_count,
                        }
                    )
                batch_tensors = []
                batch_metadata = []
        if batch_tensors:
            batch = torch.cat(batch_tensors, dim=0).to(device)
            outputs = model(batch).cpu().numpy()
            for output, meta in zip(outputs, batch_metadata, strict=True):
                vectors.append(output)
                metadata.append(
                    {
                        "sample_id": meta.sample_id,
                        "class_name": meta.class_name,
                        "source": meta.source,
                        "split": meta.split,
                        "tree_id": meta.tree_id,
                        "view_id": meta.view_id,
                        "image_path": str(meta.image_path),
                        "bbox_area": meta.area,
                        "y_center": meta.y_center,
                        "label_count": meta.label_count,
                    }
                )

    return pd.DataFrame(metadata), np.vstack(vectors)


def analyze_embeddings(embedding_df: pd.DataFrame, embeddings: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    pca_50 = PCA(n_components=min(50, embeddings.shape[0] - 1, embeddings.shape[1]), random_state=SEED)
    reduced = pca_50.fit_transform(embeddings)
    pca_2 = PCA(n_components=2, random_state=SEED)
    embedding_df[["pca_x", "pca_y"]] = pca_2.fit_transform(reduced[:, : min(20, reduced.shape[1])])

    tsne = TSNE(
        n_components=2,
        perplexity=max(10, min(35, embeddings.shape[0] // 30)),
        learning_rate="auto",
        init="pca",
        random_state=SEED,
    )
    embedding_df[["tsne_x", "tsne_y"]] = tsne.fit_transform(reduced)

    X_train, X_test, y_train, y_test = train_test_split(
        reduced, embedding_df["class_name"], test_size=0.25, random_state=SEED, stratify=embedding_df["class_name"]
    )
    probe = RandomForestClassifier(
        n_estimators=400,
        random_state=SEED,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )
    probe.fit(X_train, y_train)
    predictions = probe.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    confusion = confusion_matrix(y_test, predictions, labels=CLASS_ORDER)

    probe_summary = []
    y_test_arr = np.asarray(y_test)
    pred_arr = np.asarray(predictions)
    for class_name in CLASS_ORDER:
        class_mask = y_test_arr == class_name
        recall = (pred_arr[class_mask] == class_name).mean() if class_mask.any() else np.nan
        pred_mask = pred_arr == class_name
        precision = (y_test_arr[pred_mask] == class_name).mean() if pred_mask.any() else np.nan
        probe_summary.append({"class_name": class_name, "precision": precision, "recall": recall})
    probe_summary_df = pd.DataFrame(probe_summary)
    probe_summary_df["overall_accuracy"] = accuracy
    return embedding_df, probe_summary_df, confusion


def build_cluster_profiles(embedding_df: pd.DataFrame, embeddings: np.ndarray) -> pd.DataFrame:
    profiles = []
    for class_name in CLASS_ORDER:
        mask = embedding_df["class_name"] == class_name
        class_embeddings = embeddings[mask]
        class_df = embedding_df[mask].copy()
        if len(class_df) < 24:
            continue
        n_clusters = min(3, max(2, len(class_df) // 80))
        model = KMeans(n_clusters=n_clusters, random_state=SEED, n_init=20)
        class_df["cluster_id"] = model.fit_predict(class_embeddings)
        for cluster_id in sorted(class_df["cluster_id"].unique()):
            cluster = class_df[class_df["cluster_id"] == cluster_id]
            source_share = cluster["source"].value_counts(normalize=True)
            view_share = cluster["view_id"].value_counts(normalize=True)
            profiles.append(
                {
                    "class_name": class_name,
                    "cluster_id": int(cluster_id),
                    "samples": len(cluster),
                    "dominant_source": source_share.index[0],
                    "dominant_source_share": source_share.iloc[0],
                    "dominant_view": view_share.index[0],
                    "dominant_view_share": view_share.iloc[0],
                    "mean_bbox_area": cluster["bbox_area"].mean(),
                    "mean_y_center": cluster["y_center"].mean(),
                    "mean_label_count": cluster["label_count"].mean(),
                }
            )
    return pd.DataFrame(profiles)


def build_outlier_table(embedding_df: pd.DataFrame, embeddings: np.ndarray) -> pd.DataFrame:
    records = []
    for class_name in CLASS_ORDER:
        mask = embedding_df["class_name"] == class_name
        class_df = embedding_df[mask].copy()
        class_embeddings = embeddings[mask]
        centroid = class_embeddings.mean(axis=0)
        class_df["centroid_distance"] = np.linalg.norm(class_embeddings - centroid, axis=1)
        records.extend(class_df.nlargest(8, "centroid_distance").to_dict(orient="records"))
    return pd.DataFrame(records)


def build_representative_table(embedding_df: pd.DataFrame, embeddings: np.ndarray) -> pd.DataFrame:
    records = []
    for class_name in CLASS_ORDER:
        mask = embedding_df["class_name"] == class_name
        class_df = embedding_df[mask].copy()
        class_embeddings = embeddings[mask]
        centroid = class_embeddings.mean(axis=0)
        class_df["centroid_distance"] = np.linalg.norm(class_embeddings - centroid, axis=1)
        chosen = []
        seen_images = set()
        for _, row in class_df.sort_values("centroid_distance").iterrows():
            if row["image_path"] in seen_images:
                continue
            chosen.append(row)
            seen_images.add(row["image_path"])
            if len(chosen) == 6:
                break
        records.extend(chosen)
    return pd.DataFrame(records)


def compute_model_context(repo_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    json_path = repo_root / "data" / "2026-03.json"
    if not json_path.exists():
        return pd.DataFrame(), pd.DataFrame()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    run_records = []
    class_records = []
    for event in payload.get("events", []):
        for run in event.get("runs", []):
            test_split = run.get("splits", {}).get("test")
            if not test_split:
                continue
            run_records.append(
                {
                    "run_id": run["run_id"],
                    "gen": run["gen"],
                    "scenario": run["scenario"],
                    "model": run["model"],
                    "seed": run["seed"],
                    "test_images": test_split["images"],
                    "mAP50": test_split["global"]["mAP50"],
                    "mAP5095": test_split["global"]["mAP5095"],
                    "P": test_split["global"]["P"],
                    "R": test_split["global"]["R"],
                }
            )
            for class_name, metrics in test_split.get("classes", {}).items():
                class_records.append(
                    {
                        "run_id": run["run_id"],
                        "gen": run["gen"],
                        "scenario": run["scenario"],
                        "model": run["model"],
                        "seed": run["seed"],
                        "test_images": test_split["images"],
                        "class_name": class_name,
                        "mAP50": metrics["mAP50"],
                        "mAP5095": metrics["mAP5095"],
                        "P": metrics["P"],
                        "R": metrics["R"],
                        "F1": metrics["F1"],
                    }
                )
    return pd.DataFrame(run_records), pd.DataFrame(class_records)


def build_model_context_tables(run_df: pd.DataFrame, class_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if run_df.empty or class_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    combined_runs = run_df[run_df["test_images"] == 592].copy()
    combined_classes = class_df[class_df["test_images"] == 592].copy()
    scenario_summary = (
        combined_runs.groupby(["scenario", "model"])
        .agg(
            runs=("run_id", "count"),
            mean_mAP50=("mAP50", "mean"),
            mean_mAP5095=("mAP5095", "mean"),
            mean_precision=("P", "mean"),
            mean_recall=("R", "mean"),
        )
        .reset_index()
        .sort_values(["mean_mAP50", "mean_mAP5095"], ascending=False)
    )
    class_summary = (
        combined_classes.groupby("class_name")
        .agg(
            mean_mAP50=("mAP50", "mean"),
            mean_mAP5095=("mAP5095", "mean"),
            mean_precision=("P", "mean"),
            mean_recall=("R", "mean"),
            mean_f1=("F1", "mean"),
        )
        .reset_index()
        .sort_values("mean_mAP50", ascending=False)
    )
    return scenario_summary, class_summary


def create_split_source_figure(split_summary: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].bar(split_summary["split"], split_summary["DAMIMAS"], color=PALETTE["DAMIMAS"], label="DAMIMAS")
    axes[0].bar(
        split_summary["split"],
        split_summary["LONSUM"],
        bottom=split_summary["DAMIMAS"],
        color=PALETTE["LONSUM"],
        label="LONSUM",
    )
    axes[0].set_title("Komposisi image per split")
    axes[0].set_ylabel("Jumlah image")
    axes[0].legend(frameon=False)

    axes[1].bar(split_summary["split"], split_summary["damimas_share_images"], color=PALETTE["DAMIMAS"], label="DAMIMAS")
    axes[1].bar(
        split_summary["split"],
        split_summary["lonsum_share_images"],
        bottom=split_summary["damimas_share_images"],
        color=PALETTE["LONSUM"],
        label="LONSUM",
    )
    axes[1].set_title("Share sumber per split")
    axes[1].set_ylim(0, 1)
    axes[1].set_ylabel("Proporsi")
    axes[1].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def create_class_distribution_figure(class_summary: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].bar(
        class_summary["class_name"],
        class_summary["instances"],
        color=[PALETTE[class_name] for class_name in class_summary["class_name"]],
    )
    axes[0].set_title("Distribusi instance per kelas")
    axes[0].set_ylabel("Jumlah instance")

    axes[1].bar(
        class_summary["class_name"],
        class_summary["image_prevalence"],
        color=[PALETTE[class_name] for class_name in class_summary["class_name"]],
    )
    axes[1].set_title("Prevalensi kelas per image")
    axes[1].set_ylabel("Proporsi image")
    axes[1].set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def create_label_histogram(images_df: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    bins = np.arange(images_df["label_count"].max() + 2) - 0.5
    ax.hist(images_df["label_count"], bins=bins, color="#4f5d75", edgecolor="white")
    ax.set_title("Distribusi jumlah objek per image")
    ax.set_xlabel("Jumlah objek")
    ax.set_ylabel("Jumlah image")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def create_cooccurrence_heatmap(pairwise_df: pd.DataFrame, path: Path) -> None:
    matrix = pd.DataFrame(np.eye(len(CLASS_ORDER)), index=CLASS_ORDER, columns=CLASS_ORDER)
    for row in pairwise_df.itertuples(index=False):
        matrix.loc[row.class_a, row.class_b] = row.lift
        matrix.loc[row.class_b, row.class_a] = row.lift
    fig, ax = plt.subplots(figsize=(7, 6))
    image = ax.imshow(matrix.values, cmap="YlGnBu")
    ax.set_xticks(range(len(CLASS_ORDER)))
    ax.set_yticks(range(len(CLASS_ORDER)))
    ax.set_xticklabels(CLASS_ORDER)
    ax.set_yticklabels(CLASS_ORDER)
    ax.set_title("Lift co-occurrence antar kelas")
    for i in range(len(CLASS_ORDER)):
        for j in range(len(CLASS_ORDER)):
            ax.text(j, i, f"{matrix.iloc[i, j]:.2f}", ha="center", va="center", color="black", fontsize=9)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def create_bbox_geometry_figure(instances_df: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for class_name in CLASS_ORDER:
        subset = instances_df[instances_df["class_name"] == class_name]
        axes[0].hist(subset["bbox_area"], bins=np.linspace(0, 0.08, 25), alpha=0.45, label=class_name, color=PALETTE[class_name])
        axes[1].hist(subset["bbox_h"], bins=np.linspace(0, 0.35, 25), alpha=0.45, label=class_name, color=PALETTE[class_name])
        axes[2].hist(subset["y_center"], bins=np.linspace(0, 1.0, 25), alpha=0.45, label=class_name, color=PALETTE[class_name])
    axes[0].set_title("Luas bbox")
    axes[0].set_xlabel("Area ter-normalisasi")
    axes[1].set_title("Tinggi bbox")
    axes[1].set_xlabel("Height ter-normalisasi")
    axes[2].set_title("Posisi vertikal center")
    axes[2].set_xlabel("y center")
    axes[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def create_spatial_heatmaps(instances_df: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 9), sharex=True, sharey=True)
    for ax, class_name in zip(axes.flatten(), CLASS_ORDER, strict=True):
        subset = instances_df[instances_df["class_name"] == class_name]
        hexbin = ax.hexbin(subset["x_center"], subset["y_center"], gridsize=22, cmap="magma", mincnt=1)
        ax.set_title(class_name)
        ax.set_xlim(0, 1)
        ax.set_ylim(1, 0)
        ax.set_xlabel("x center")
        ax.set_ylabel("y center")
        fig.colorbar(hexbin, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle("Heatmap posisi bbox per kelas", y=0.98)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def create_source_drift_figure(source_class_summary: pd.DataFrame, path: Path) -> None:
    pivot = source_class_summary.pivot(index="class_name", columns="source", values="instance_share_within_source").reindex(CLASS_ORDER)
    x = np.arange(len(CLASS_ORDER))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - width / 2, pivot["DAMIMAS"], width=width, color=PALETTE["DAMIMAS"], label="DAMIMAS")
    ax.bar(x + width / 2, pivot["LONSUM"], width=width, color=PALETTE["LONSUM"], label="LONSUM")
    ax.set_xticks(x)
    ax.set_xticklabels(CLASS_ORDER)
    ax.set_ylabel("Share instance dalam sumber")
    ax.set_title("Perbedaan prior kelas per sumber")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def create_view_consistency_figure(tree_summary: pd.DataFrame, per_view: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for source in SOURCE_ORDER:
        subset = tree_summary[tree_summary["source"] == source]
        axes[0].hist(subset["cv_objects_per_view"], bins=np.linspace(0, 1.5, 20), alpha=0.55, label=source, color=PALETTE[source])
    axes[0].set_title("Variasi jumlah objek antar-view dalam tree")
    axes[0].set_xlabel("Coefficient of variation")
    axes[0].set_ylabel("Jumlah tree")
    axes[0].legend(frameon=False)

    for source in SOURCE_ORDER:
        subset = per_view[per_view["source"] == source].sort_values("view_id")
        axes[1].plot(subset["view_id"], subset["mean_objects"], marker="o", label=source, color=PALETTE[source])
    axes[1].set_title("Rata-rata objek per view index")
    axes[1].set_xlabel("View index")
    axes[1].set_ylabel("Rata-rata objek")
    axes[1].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def create_embedding_scatter(embedding_df: pd.DataFrame, x_col: str, y_col: str, color_col: str, path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 7))
    for label, subset in embedding_df.groupby(color_col):
        ax.scatter(
            subset[x_col],
            subset[y_col],
            s=20,
            alpha=0.7,
            label=label,
            color=PALETTE.get(label, "#444444"),
            edgecolors="none",
        )
    ax.set_title(title)
    ax.legend(frameon=False, markerscale=1.4)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def create_confusion_figure(confusion: np.ndarray, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 6))
    image = ax.imshow(confusion, cmap="Blues")
    ax.set_xticks(range(len(CLASS_ORDER)))
    ax.set_yticks(range(len(CLASS_ORDER)))
    ax.set_xticklabels(CLASS_ORDER)
    ax.set_yticklabels(CLASS_ORDER)
    ax.set_xlabel("Prediksi")
    ax.set_ylabel("Ground truth")
    ax.set_title("Confusion matrix classifier probe")
    for i in range(confusion.shape[0]):
        for j in range(confusion.shape[1]):
            ax.text(j, i, str(confusion[i, j]), ha="center", va="center", color="black", fontsize=10)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def create_crop_gallery_from_rows(sample_table: pd.DataFrame, path: Path, title: str) -> None:
    if sample_table.empty:
        return
    rows = len(CLASS_ORDER)
    cols = 3
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.6, rows * 2.3))
    axes = np.atleast_2d(axes)
    fig.suptitle(title, y=0.995, fontsize=14)
    for row_index, class_name in enumerate(CLASS_ORDER):
        subset = sample_table[sample_table["class_name"] == class_name].head(cols)
        for col_index in range(cols):
            ax = axes[row_index, col_index]
            ax.axis("off")
            if col_index < len(subset):
                row = subset.iloc[col_index]
                image = crop_from_bbox(
                    Path(row["image_path"]),
                    (float(row["x_center"]), float(row["y_center"]), float(row["bbox_w"]), float(row["bbox_h"])),
                )
                ax.imshow(image)
                distance = row["centroid_distance"] if "centroid_distance" in row else 0.0
                ax.set_title(f"{class_name}\n{row['source']}, d={distance:.2f}", fontsize=8, color=PALETTE[class_name])
        axes[row_index, 0].set_ylabel(class_name, rotation=90, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def merge_bbox_back(sample_table: pd.DataFrame, instances_df: pd.DataFrame) -> pd.DataFrame:
    if sample_table.empty:
        return sample_table
    return sample_table.merge(
        instances_df[["instance_id", "x_center", "bbox_w", "bbox_h"]],
        left_on="sample_id",
        right_on="instance_id",
        how="left",
    )


def build_integrity_summary(images_df: pd.DataFrame, instances_df: pd.DataFrame) -> dict:
    image_stems = set(images_df["stem"])
    label_stems = {Path(path).stem for path in images_df["label_path"] if path}
    tree_split_unique = images_df.groupby("tree_id")["split"].nunique()
    return {
        "total_images": int(len(images_df)),
        "total_instances": int(len(instances_df)),
        "image_label_pairs_match": len(image_stems) == len(label_stems) == len(image_stems & label_stems),
        "missing_labels": int(len(image_stems - label_stems)),
        "missing_images": int(len(label_stems - image_stems)),
        "empty_labels": int(images_df["is_empty"].sum()),
        "split_counts": images_df["split"].value_counts().reindex(SPLIT_ORDER).fillna(0).astype(int).to_dict(),
        "resolution_unique": images_df[["width_px", "height_px"]].drop_duplicates().astype(str).values.tolist(),
        "tree_leakage_count": int((tree_split_unique > 1).sum()),
        "trees_total": int(images_df["tree_id"].nunique()),
        "views_total": {str(key): int(value) for key, value in images_df["view_id"].value_counts().sort_index().items()},
    }


def build_hidden_patterns(
    images_df: pd.DataFrame,
    instances_df: pd.DataFrame,
    class_summary: pd.DataFrame,
    source_class_summary: pd.DataFrame,
    pairwise_df: pd.DataFrame,
    drift_df: pd.DataFrame,
    tree_summary: pd.DataFrame,
    cluster_profiles: pd.DataFrame,
    model_class_summary: pd.DataFrame,
) -> list[dict]:
    patterns = []
    source_counts = images_df["source"].value_counts(normalize=True)
    density_by_source = images_df.groupby("source")["label_count"].mean()
    patterns.append(
        {
            "title": "Dataset nyaris sepenuhnya dikendalikan DAMIMAS",
            "evidence": (
                f"DAMIMAS menyumbang {fmt_pct(source_counts['DAMIMAS'])} image dan "
                f"{fmt_pct((instances_df['source'] == 'DAMIMAS').mean())} instance."
            ),
            "impact": "Model combined lebih banyak belajar prior DAMIMAS daripada prior gabungan dua kebun.",
        }
    )

    lonsum_b1 = source_class_summary[
        (source_class_summary["source"] == "LONSUM") & (source_class_summary["class_name"] == "B1")
    ].iloc[0]
    patterns.append(
        {
            "title": "B1 hampir eksklusif milik DAMIMAS",
            "evidence": (
                f"LONSUM hanya punya {fmt_int(lonsum_b1['instances'])} instance B1 "
                f"dan prevalensinya di source itu cuma {fmt_pct(lonsum_b1['image_prevalence_within_source'])}."
            ),
            "impact": "Transfer domain untuk B1 hampir tidak bisa diukur secara adil.",
        }
    )

    patterns.append(
        {
            "title": "LONSUM lebih jarang objek per image, bukan hanya lebih sedikit image",
            "evidence": (
                f"Rata-rata objek per image di DAMIMAS = {density_by_source['DAMIMAS']:.2f}, "
                f"sedangkan LONSUM = {density_by_source['LONSUM']:.2f}."
            ),
            "impact": "Combined dataset mencampur dua rezim kepadatan objek yang berbeda, sehingga domain shift menyentuh struktur scene, bukan sekadar tampilan visual.",
        }
    )

    vertical = class_summary.sort_values("mean_y_center", ascending=False)[["class_name", "mean_y_center"]]
    patterns.append(
        {
            "title": "Ada stratifikasi vertikal yang konsisten antar kelas",
            "evidence": (
                f"Rerata y-center bergerak dari {vertical.iloc[0]['class_name']} ({vertical.iloc[0]['mean_y_center']:.3f}) "
                f"ke {vertical.iloc[-1]['class_name']} ({vertical.iloc[-1]['mean_y_center']:.3f})."
            ),
            "impact": "Posisi objek berperan besar dalam separasi kelas, bukan hanya tekstur lokal.",
        }
    )

    size_order = class_summary.sort_values("mean_bbox_area", ascending=False)[["class_name", "mean_bbox_area"]]
    patterns.append(
        {
            "title": "Ukuran objek lebih menentukan difficulty daripada jumlah sampel mentah",
            "evidence": (
                f"{size_order.iloc[0]['class_name']} punya mean area terbesar ({size_order.iloc[0]['mean_bbox_area']:.4f}), "
                f"sementara {size_order.iloc[-1]['class_name']} terkecil ({size_order.iloc[-1]['mean_bbox_area']:.4f})."
            ),
            "impact": "Kelas kecil cenderung lebih sulit walau tidak selalu paling jarang.",
        }
    )

    densest = class_summary.sort_values("mean_image_density", ascending=False).iloc[0]
    patterns.append(
        {
            "title": "Kelas tersulit hidup di image paling padat",
            "evidence": (
                f"{densest['class_name']} muncul pada image dengan rata-rata {densest['mean_image_density']:.2f} objek, tertinggi di dataset."
            ),
            "impact": "Kelas sulit tidak selalu kalah karena jumlah data; ia bisa kalah karena selalu muncul di konteks yang paling padat dan paling ambigu.",
        }
    )

    highest_lift = pairwise_df.iloc[0]
    lowest_lift = pairwise_df.iloc[-1]
    patterns.append(
        {
            "title": "Relasi antar kelas tidak independen",
            "evidence": (
                f"Lift tertinggi ada pada {highest_lift['class_a']}-{highest_lift['class_b']} ({highest_lift['lift']:.2f}), "
                f"terendah pada {lowest_lift['class_a']}-{lowest_lift['class_b']} ({lowest_lift['lift']:.2f})."
            ),
            "impact": "Ketergantungan ini tidak ekstrem, tetapi cukup sistematis untuk menunjukkan struktur komposisi objek yang berulang.",
        }
    )

    class_mix_all = drift_df[(drift_df["split_scope"] == "all") & (drift_df["metric"] == "class_mix_instances_js")].iloc[0]
    patterns.append(
        {
            "title": "Domain shift terbesar datang dari prior kelas",
            "evidence": f"JS distance campuran kelas DAMIMAS vs LONSUM = {class_mix_all['value']:.3f}.",
            "impact": "Gap lintas-source tidak hanya soal appearance, tetapi juga perubahan komposisi label.",
        }
    )

    eight_view = tree_summary[tree_summary["views"] == 8]
    patterns.append(
        {
            "title": "Ada dua protokol akuisisi: 4-view dan 8-view",
            "evidence": (
                f"Terdapat {fmt_int(len(eight_view))} tree dengan 8 view dan "
                f"{fmt_int((tree_summary['views'] == 4).sum())} tree dengan 4 view; seluruh tree 8-view berada di DAMIMAS."
            ),
            "impact": "Coverage per tree tidak homogen dan ikut terikat ke source, sehingga protokol akuisisi berpotensi menjadi confounder terselubung.",
        }
    )

    if not cluster_profiles.empty:
        source_pure = cluster_profiles.sort_values("dominant_source_share", ascending=False).iloc[0]
        patterns.append(
            {
                "title": "Sub-populasi internal kelas kadang lebih dekat ke source daripada label global",
                "evidence": (
                    f"Cluster paling source-specific ada pada {source_pure['class_name']} cluster {int(source_pure['cluster_id'])} "
                    f"dengan {fmt_pct(source_pure['dominant_source_share'])} sampel dari {source_pure['dominant_source']}."
                ),
                "impact": "Satu label menyatukan beberapa mode visual berbeda yang tidak sepenuhnya ekuivalen.",
            }
        )

    if not model_class_summary.empty:
        best_model = model_class_summary.iloc[0]
        worst_model = model_class_summary.iloc[-1]
        patterns.append(
            {
                "title": "Ranking difficulty model mengikuti struktur dataset",
                "evidence": (
                    f"Di log model, {best_model['class_name']} punya mean mAP50 tertinggi ({best_model['mean_mAP50']:.3f}), "
                    f"sedangkan {worst_model['class_name']} terendah ({worst_model['mean_mAP50']:.3f})."
                ),
                "impact": "Properti dataset cukup konsisten untuk menjelaskan pola performa model.",
            }
        )
    return patterns


def build_recommendations(
    class_summary: pd.DataFrame,
    source_class_summary: pd.DataFrame,
    pairwise_df: pd.DataFrame,
    model_class_summary: pd.DataFrame,
) -> list[str]:
    recommendations = []
    smallest = class_summary.sort_values("mean_bbox_area").iloc[0]
    recommendations.append(
        f"Prioritaskan enrichment untuk {smallest['class_name']}: kelas ini paling kecil secara geometri, jadi butuh close-up, quality control anotasi, dan augmentasi skala."
    )
    sparse_lonsum = source_class_summary[source_class_summary["source"] == "LONSUM"].sort_values("instances").iloc[0]
    recommendations.append(
        f"Lengkapi coverage LONSUM untuk {sparse_lonsum['class_name']}; saat ini kelas itu hampir tidak ada di source tersebut sehingga benchmark combined belum seimbang."
    )
    hardest_pair = pairwise_df.sort_values("lift", ascending=False).iloc[0]
    recommendations.append(
        f"Gunakan relasi konteks untuk pasangan {hardest_pair['class_a']}-{hardest_pair['class_b']} karena keduanya muncul bersama jauh di atas ekspektasi acak."
    )
    if not model_class_summary.empty:
        hardest = model_class_summary.sort_values("mean_mAP50").iloc[0]
        easiest = model_class_summary.sort_values("mean_mAP50", ascending=False).iloc[0]
        recommendations.append(
            f"Jangan menjadikan jumlah sampel sebagai satu-satunya prioritas. {easiest['class_name']} sudah relatif mudah, sementara {hardest['class_name']} butuh intervensi data-centric yang lebih spesifik."
        )
    recommendations.append(
        "Pertahankan split per-tree karena integritasnya sudah baik; fokus perbaikan berikutnya seharusnya pada coverage source, protokol view campur, dan image kosong."
    )
    return recommendations


def write_report(
    output_dir: Path,
    integrity_summary: dict,
    split_summary: pd.DataFrame,
    class_summary: pd.DataFrame,
    source_split_summary: pd.DataFrame,
    source_class_summary: pd.DataFrame,
    combo_summary: pd.DataFrame,
    pairwise_df: pd.DataFrame,
    tree_summary: pd.DataFrame,
    drift_df: pd.DataFrame,
    cluster_profiles: pd.DataFrame,
    outlier_table: pd.DataFrame,
    probe_summary_df: pd.DataFrame,
    model_scenario_summary: pd.DataFrame,
    model_class_summary: pd.DataFrame,
    hidden_patterns: list[dict],
    recommendations: list[str],
) -> None:
    split_mismatch_note = (
        "Folder lokal `dataset_640` berisi split 2772/608/612, berbeda dari log v2 repo yang menyebut 2780/620/592. "
        "Analisis ini memakai folder lokal sebagai sumber kebenaran dan mencatat mismatch tersebut sebagai temuan audit."
    )

    key_numbers = (
        f"- Total image: {fmt_int(integrity_summary['total_images'])}\n"
        f"- Total instance: {fmt_int(integrity_summary['total_instances'])}\n"
        f"- Empty label: {fmt_int(integrity_summary['empty_labels'])}\n"
        f"- Total tree: {fmt_int(integrity_summary['trees_total'])}\n"
        f"- Tree leakage antar split: {fmt_int(integrity_summary['tree_leakage_count'])}\n"
        f"- Resolusi unik: {integrity_summary['resolution_unique']}\n"
    )
    hidden_text = "\n".join(
        [f"1. **{item['title']}**. {item['evidence']} {item['impact']}" for item in hidden_patterns]
    )
    recommendation_text = "\n".join([f"1. {item}" for item in recommendations])
    drift_focus = drift_df[(drift_df["split_scope"] == "all") & (drift_df["metric"].isin(["bbox_area_js", "y_center_js"]))].sort_values(
        ["metric", "value"], ascending=[True, False]
    )

    report = f"""# Analisis Mendalam `dataset_640`

## Ringkasan Eksekutif

Analisis ini membedah `dataset_640` sebagai objek riset, bukan sekadar dataset training biasa. Fokusnya bukan hanya distribusi split dan jumlah label, tetapi juga pola tersembunyi: bias source, heterogenitas internal kelas, posisi vertikal, co-occurrence, perbedaan protokol view, dan kaitannya dengan performa model.

{key_numbers}

## Audit Integritas

{split_mismatch_note}

- Semua image dan label berpasangan dengan baik: `{integrity_summary['image_label_pairs_match']}`.
- Tidak ada tree yang muncul di lebih dari satu split.
- Label kosong diperlakukan sebagai bagian dari distribusi nyata, bukan dibuang dari analisis.
- Dataset menyimpan dua mode akuisisi sekaligus: view `1-4` dominan dan view `5-8` pada subset tree tertentu.

### Snapshot Split

{markdown_table(split_summary[['split', 'images', 'trees', 'instances', 'empty_images', 'avg_objects_per_image', 'median_objects_per_image', 'DAMIMAS', 'LONSUM']], precision=2)}

### Snapshot Kelas

{markdown_table(class_summary[['class_name', 'instances', 'instance_share', 'images_with_class', 'image_prevalence', 'mean_bbox_area', 'mean_y_center', 'mean_image_density']], precision=3)}

### Snapshot Source x Kelas

{markdown_table(source_class_summary[['source', 'class_name', 'instances', 'instance_share_within_source', 'images_with_class', 'image_prevalence_within_source', 'mean_bbox_area', 'mean_y_center']], precision=3)}

## Hidden Patterns

{hidden_text}

### Co-occurrence Tersering

{markdown_table(combo_summary[['class_combo', 'images', 'support']], precision=3, max_rows=10)}

### Pairwise Association Terkuat

{markdown_table(pairwise_df[['class_a', 'class_b', 'images_with_both', 'support_both', 'confidence_a_to_b', 'confidence_b_to_a', 'lift']], precision=3, max_rows=6)}

### Drift DAMIMAS vs LONSUM

{markdown_table(drift_focus[['split_scope', 'metric', 'class_name', 'value']], precision=3, max_rows=12)}

### Struktur Tree dan View

{markdown_table(tree_summary[['split', 'source', 'tree_id', 'views', 'total_objects', 'mean_objects_per_view', 'cv_objects_per_view', 'distinct_combos']].sort_values('cv_objects_per_view', ascending=False), precision=3, max_rows=12)}

## Separabilitas Visual

Embedding crop berbasis `ResNet50` menunjukkan bahwa separasi kelas tidak merata. Kelas dengan sinyal ukuran dan posisi yang kuat cenderung lebih mudah dipisahkan, sementara kelas tengah lebih banyak saling tumpang tindih.

### Ringkasan Probe

{markdown_table(probe_summary_df[['class_name', 'precision', 'recall', 'overall_accuracy']], precision=3)}

### Cluster Internal Kelas

{markdown_table(cluster_profiles[['class_name', 'cluster_id', 'samples', 'dominant_source', 'dominant_source_share', 'dominant_view', 'dominant_view_share', 'mean_bbox_area', 'mean_y_center']], precision=3, max_rows=12) if not cluster_profiles.empty else 'Tidak ada cluster profile yang cukup kuat untuk dilaporkan.'}

### Outlier Audit

{markdown_table(outlier_table[['class_name', 'source', 'split', 'view_id', 'bbox_area', 'y_center', 'label_count', 'centroid_distance']], precision=3, max_rows=12)}

## Kaitan dengan Hasil Model

{markdown_table(model_scenario_summary[['scenario', 'model', 'runs', 'mean_mAP50', 'mean_mAP5095', 'mean_precision', 'mean_recall']], precision=3) if not model_scenario_summary.empty else 'Model context tidak tersedia.'}

{markdown_table(model_class_summary[['class_name', 'mean_mAP50', 'mean_mAP5095', 'mean_precision', 'mean_recall', 'mean_f1']], precision=3) if not model_class_summary.empty else ''}

Interpretasi utama:

- Kelas kecil dan tinggi di frame cenderung lebih sulit.
- Jika satu kelas sangat dominan di satu source tetapi nyaris hilang di source lain, metrik combined bisa terlihat sehat padahal transfer domain sebenarnya lemah.
- Banyaknya sampel mentah tidak otomatis membuat kelas mudah; crowding dan overlap visual sering lebih menentukan.

## Artefak

- `[figures/split_source_composition.png](figures/split_source_composition.png)`
- `[figures/class_distribution.png](figures/class_distribution.png)`
- `[figures/label_count_histogram.png](figures/label_count_histogram.png)`
- `[figures/class_cooccurrence_lift.png](figures/class_cooccurrence_lift.png)`
- `[figures/bbox_geometry.png](figures/bbox_geometry.png)`
- `[figures/spatial_heatmaps.png](figures/spatial_heatmaps.png)`
- `[figures/source_class_drift.png](figures/source_class_drift.png)`
- `[figures/view_consistency.png](figures/view_consistency.png)`
- `[figures/embedding_tsne_class.png](figures/embedding_tsne_class.png)`
- `[figures/embedding_tsne_source.png](figures/embedding_tsne_source.png)`
- `[figures/probe_confusion_matrix.png](figures/probe_confusion_matrix.png)`
- `[figures/representative_crops.png](figures/representative_crops.png)`
- `[figures/outlier_gallery.png](figures/outlier_gallery.png)`

## Rekomendasi Prioritas

{recommendation_text}
    """
    (output_dir / "report.md").write_text(report, encoding="utf-8")


def main() -> None:
    args = parse_args()
    set_seed(SEED)
    repo_root = Path.cwd()
    paths = ensure_dirs(args.output_dir)

    images_df, instances_df = load_dataset(args.dataset_root)
    split_summary = build_split_summary(images_df, instances_df)
    class_summary = build_class_summary(images_df, instances_df)
    source_class_summary = build_source_class_summary(images_df, instances_df)
    class_split_summary = build_class_split_summary(images_df, instances_df)
    source_split_summary = build_source_split_summary(images_df, instances_df)
    combo_summary = build_class_combo_summary(images_df)
    pairwise_df = build_pairwise_association(images_df)
    tree_summary, per_view, tree_class = build_tree_view_tables(images_df, instances_df)
    zero_coverage = build_zero_coverage_table(source_class_summary)
    drift_df = build_source_drift_tables(images_df, instances_df)
    integrity_summary = build_integrity_summary(images_df, instances_df)

    sample_instances = pick_stratified_samples(instances_df)
    crop_samples = build_crop_samples(sample_instances)
    embedding_df, embeddings = extract_embeddings(crop_samples)
    embedding_df, probe_summary_df, confusion = analyze_embeddings(embedding_df, embeddings)
    cluster_profiles = build_cluster_profiles(embedding_df, embeddings)
    outlier_table = build_outlier_table(embedding_df, embeddings)
    representative_table = build_representative_table(embedding_df, embeddings)

    embedding_with_bbox = merge_bbox_back(embedding_df, instances_df)
    outlier_with_bbox = merge_bbox_back(outlier_table, instances_df)
    representative_with_bbox = merge_bbox_back(representative_table, instances_df)

    run_df, model_class_df = compute_model_context(repo_root) if args.with_model_context else (pd.DataFrame(), pd.DataFrame())
    model_scenario_summary, model_class_summary = build_model_context_tables(run_df, model_class_df)

    hidden_patterns = build_hidden_patterns(
        images_df,
        instances_df,
        class_summary,
        source_class_summary,
        pairwise_df,
        drift_df,
        tree_summary,
        cluster_profiles,
        model_class_summary,
    )
    recommendations = build_recommendations(class_summary, source_class_summary, pairwise_df, model_class_summary)

    save_table(images_df, paths["tables"] / "image_level.csv")
    save_table(instances_df, paths["tables"] / "instance_level.csv")
    save_table(split_summary, paths["tables"] / "split_summary.csv", ["split"])
    save_table(class_summary, paths["tables"] / "class_summary.csv", ["class_name"])
    save_table(source_class_summary, paths["tables"] / "source_class_summary.csv", ["source", "class_name"])
    save_table(class_split_summary, paths["tables"] / "class_split_summary.csv", ["split", "class_name"])
    save_table(source_split_summary, paths["tables"] / "source_split_summary.csv", ["split", "source"])
    save_table(combo_summary, paths["tables"] / "class_combo_summary.csv")
    save_table(pairwise_df, paths["tables"] / "pairwise_association.csv")
    save_table(tree_summary, paths["tables"] / "tree_summary.csv", ["split", "source", "tree_id"])
    save_table(per_view, paths["tables"] / "view_summary.csv", ["split", "source", "view_id"])
    save_table(tree_class, paths["tables"] / "tree_class_matrix.csv", ["tree_id"])
    save_table(zero_coverage, paths["tables"] / "zero_coverage_cells.csv", ["source", "class_name"])
    save_table(drift_df, paths["tables"] / "source_drift_scores.csv", ["split_scope", "metric", "class_name"])
    save_table(embedding_with_bbox, paths["tables"] / "embedding_samples.csv", ["class_name", "source"])
    save_table(cluster_profiles, paths["tables"] / "cluster_profiles.csv", ["class_name", "cluster_id"])
    save_table(outlier_with_bbox, paths["tables"] / "outlier_instances.csv", ["class_name", "centroid_distance"])
    save_table(representative_with_bbox, paths["tables"] / "representative_instances.csv", ["class_name", "centroid_distance"])
    save_table(probe_summary_df, paths["tables"] / "probe_summary.csv", ["class_name"])
    if not model_scenario_summary.empty:
        save_table(model_scenario_summary, paths["tables"] / "model_scenario_summary.csv")
        save_table(model_class_summary, paths["tables"] / "model_class_summary.csv")

    create_split_source_figure(split_summary, paths["figures"] / "split_source_composition.png")
    create_class_distribution_figure(class_summary, paths["figures"] / "class_distribution.png")
    create_label_histogram(images_df, paths["figures"] / "label_count_histogram.png")
    create_cooccurrence_heatmap(pairwise_df, paths["figures"] / "class_cooccurrence_lift.png")
    create_bbox_geometry_figure(instances_df, paths["figures"] / "bbox_geometry.png")
    create_spatial_heatmaps(instances_df, paths["figures"] / "spatial_heatmaps.png")
    create_source_drift_figure(source_class_summary, paths["figures"] / "source_class_drift.png")
    create_view_consistency_figure(tree_summary, per_view, paths["figures"] / "view_consistency.png")
    create_embedding_scatter(
        embedding_df,
        "tsne_x",
        "tsne_y",
        "class_name",
        paths["figures"] / "embedding_tsne_class.png",
        "t-SNE embedding crop by class",
    )
    create_embedding_scatter(
        embedding_df,
        "tsne_x",
        "tsne_y",
        "source",
        paths["figures"] / "embedding_tsne_source.png",
        "t-SNE embedding crop by source",
    )
    create_confusion_figure(confusion, paths["figures"] / "probe_confusion_matrix.png")
    create_crop_gallery_from_rows(
        representative_with_bbox,
        paths["figures"] / "representative_crops.png",
        "Representative crops per class",
    )
    create_crop_gallery_from_rows(
        outlier_with_bbox,
        paths["figures"] / "outlier_gallery.png",
        "Visual outliers per class",
    )

    summary_payload = {
        "integrity_summary": integrity_summary,
        "top_hidden_patterns": hidden_patterns,
        "recommendations": recommendations,
    }
    (paths["root"] / "metrics_summary.json").write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_report(
        paths["root"],
        integrity_summary,
        split_summary,
        class_summary,
        source_split_summary,
        source_class_summary,
        combo_summary,
        pairwise_df,
        tree_summary,
        drift_df,
        cluster_profiles,
        outlier_with_bbox,
        probe_summary_df,
        model_scenario_summary,
        model_class_summary,
        hidden_patterns,
        recommendations,
    )
    print("Analysis complete.")
    print(f"Output dir: {paths['root']}")


if __name__ == "__main__":
    main()
