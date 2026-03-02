# YOLO Benchmarking Dashboard

An interactive, single-file web dashboard for analyzing and comparing the performance of YOLO (You Only Look Once) models across multiple datasets.

![Dashboard Preview Placeholder](https://via.placeholder.com/800x450.png?text=YOLO+Benchmarking+Dashboard+Interface)

## 📊 Overview

This project provides a comprehensive visualization of benchmarking results for object detection models. It enables quick performance analysis between different YOLO versions, helping researchers and developers identify the most effective model for specific dataset configurations.

### Key Features

*   **Interactive Leaderboard**: Real-time ranking of models based on selected metrics.
*   **Dual-Model Comparison**: Head-to-head comparison with automated winner detection and radar chart visualization for key performance indicators.
*   **Class Matrix Heatmap**: Detailed breakdown of performance across specific object classes (B1, B2, B3, B4).
*   **Split Filtering**: Support for analyzing performance across **TRAIN**, **VAL**, and **TEST** sets.

## 🛠️ Models & Datasets

### Models
*   **YOLO26l**: A specialized YOLO configuration.
*   **YOLOv9m**: Medium variant of the YOLOv9 architecture.
*   **YOLOv9c**: Compact variant of the YOLOv9 architecture.

### Datasets
*   **Stratified**: A custom stratified data split.
*   **Original**: Baseline dataset configuration.
*   **Damimas Full**: The full version of the Damimas object detection dataset.

## 📈 Metrics Analyzed

| Metric | Description |
| :--- | :--- |
| **mAP@50** | Mean Average Precision at 0.50 Intersection over Union (IoU). |
| **mAP@50-95** | Mean Average Precision across IoU thresholds from 0.50 to 0.95. |
| **Precision (P)** | Ratio of correct positive predictions to total positive predictions. |
| **Recall (R)** | Ratio of correct positive predictions to all actual positive instances. |

## 🚀 Usage

Since the dashboard is self-contained, no installation is required:

1.  Download or clone the repository.
2.  Open `yolo-comparison.html` in any modern web browser (Chrome, Firefox, Safari, Edge).
3.  Use the interactive controls to filter data and compare models.

---
*Created as part of the Assistive Teaching project.*
