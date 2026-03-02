# YOLO Benchmarking Dashboard

An interactive, research-driven web dashboard for analyzing and comparing state-of-the-art object detection models across diverse dataset configurations.

## 📊 Overview

This project provides a comprehensive visualization platform for benchmarking results, specifically focused on the latest YOLO architectures. It enables researchers to perform deep-dive comparisons between traditional scaled models and next-generation NMS-free architectures.

### Key Features

*   **Next-Gen Analysis**: Specialized benchmarking for **YOLO26l**, featuring native End-to-End (NMS-free) architecture analysis.
*   **Architectural Comparison**: Head-to-head performance tracking between **YOLOv9-c** (Compact) and **YOLOv9-m** (Medium), reflecting their unique parameter hierarchies.
*   **Interactive Leaderboard**: Dynamic ranking based on mAP, Precision, and Recall across various data splits.
*   **Class-Level Heatmaps**: Detailed performance matrix for specific object classes (B1-B4) to identify model-specific strengths and weaknesses.
*   **Split Filtering**: Full support for **TRAIN**, **VAL**, and **TEST** set performance visualization.

## 🛠️ Models & Datasets

### Models Analyzed
*   **YOLO26l (Large)**: A cutting-edge variant utilizing a native **End-to-End** architecture. By eliminating Non-Maximum Suppression (NMS), it achieves superior inference speed on CPU/Edge devices while maintaining high accuracy.
*   **YOLOv9-c (Compact)**: The standard base model of YOLOv9. Despite the "Compact" label, it features a larger parameter count (~25.5M) and higher accuracy than the medium variant.
*   **YOLOv9-m (Medium)**: A scaled variant (~20.1M parameters) optimized for a balanced speed-to-accuracy trade-off.

### Datasets
*   **Stratified**: A custom split maintaining proportional class distributions.
*   **Original**: The baseline dataset configuration.
*   **Damimas Full**: A comprehensive object detection dataset used as the primary benchmarking target.

## 📈 Metrics Analyzed

| Metric | Description | Technical Detail |
| :--- | :--- | :--- |
| **mAP@50** | Mean Average Precision | Calculated at 0.50 IoU threshold. |
| **mAP@50-95** | mAP (COCO) | Averaged across IoU thresholds from 0.50 to 0.95. |
| **Precision (P)** | Prediction Accuracy | Ratio of correct positive predictions to total predictions. |
| **Recall (R)** | Detection Coverage | Ability of the model to identify all actual positive instances. |

## 🚀 Usage

The dashboard is a self-contained analytics tool:

1.  Clone the repository: `git clone https://github.com/muhammad-zainal-muttaqin/YOLOBench.git`
2.  Open `yolo-comparison.html` in any modern web browser.
3.  Filter by metric, dataset, or model to explore the benchmarking data.

---
*Created for the Assistive Teaching project. Research-backed model specifications included.*
