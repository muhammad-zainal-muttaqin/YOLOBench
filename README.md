# YOLO Benchmarking Dashboard

An interactive web dashboard for analyzing and comparing the performance of object detection models across different datasets.

## 📊 Overview

This project provides a visualization platform for benchmarking results. It allows users to compare different model versions and configurations to identify the most effective setup for specific tasks.

### Key Features

*   **Interactive Leaderboard**: View and sort model performance based on various metrics.
*   **Performance Comparison**: Head-to-head analysis with radar charts and automated winner detection.
*   **Class-Level Analysis**: Detailed breakdown of performance across specific object classes.
*   **Data Split Filtering**: Switch between **TRAIN**, **VAL**, and **TEST** results.

## 📈 Metrics Analyzed

| Metric | Description |
| :--- | :--- |
| **mAP@50** | Mean Average Precision at 0.50 IoU. |
| **mAP@50-95** | Mean Average Precision across IoU thresholds (0.50 to 0.95). |
| **Precision (P)** | Accuracy of positive predictions. |
| **Recall (R)** | Ability to find all positive instances. |

## 🚀 Usage

The dashboard is self-contained and requires no installation:

1.  Download or clone the repository.
2.  Open `yolo-comparison.html` in any web browser.
3.  Use the dropdowns and tabs to explore the benchmarking data.

---
*Created as part of the Assistive Teaching project.*
