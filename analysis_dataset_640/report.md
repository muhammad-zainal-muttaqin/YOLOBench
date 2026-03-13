# Analisis Mendalam `dataset_640`

## Ringkasan Eksekutif

Analisis ini membedah `dataset_640` sebagai objek riset, bukan sekadar dataset training biasa. Fokusnya bukan hanya distribusi split dan jumlah label, tetapi juga pola tersembunyi: bias source, heterogenitas internal kelas, posisi vertikal, co-occurrence, perbedaan protokol view, dan kaitannya dengan performa model.

- Total image: 3.992
- Total instance: 17.949
- Empty label: 83
- Total tree: 953
- Tree leakage antar split: 0
- Resolusi unik: [['640', '853']]


## Audit Integritas

Folder lokal `dataset_640` berisi split 2772/608/612, berbeda dari log v2 repo yang menyebut 2780/620/592. Analisis ini memakai folder lokal sebagai sumber kebenaran dan mencatat mismatch tersebut sebagai temuan audit.

- Semua image dan label berpasangan dengan baik: `True`.
- Tidak ada tree yang muncul di lebih dari satu split.
- Label kosong diperlakukan sebagai bagian dari distribusi nyata, bukan dibuang dari analisis.
- Dataset menyimpan dua mode akuisisi sekaligus: view `1-4` dominan dan view `5-8` pada subset tree tertentu.

### Snapshot Split

| split | images | trees | instances | empty_images | avg_objects_per_image | median_objects_per_image | DAMIMAS | LONSUM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test | 612 | 144 | 2698 | 13 | 4.41 | 4.00 | 556 | 56 |
| train | 2772 | 667 | 12426 | 57 | 4.48 | 5.00 | 2492 | 280 |
| val | 608 | 142 | 2825 | 13 | 4.65 | 5.00 | 548 | 60 |

### Snapshot Kelas

| class_name | instances | instance_share | images_with_class | image_prevalence | mean_bbox_area | mean_y_center | mean_image_density |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | 2169 | 0.121 | 1805 | 0.452 | 0.018 | 0.451 | 5.205 |
| B2 | 4078 | 0.227 | 2435 | 0.610 | 0.014 | 0.427 | 5.193 |
| B3 | 8270 | 0.461 | 3536 | 0.886 | 0.013 | 0.380 | 5.115 |
| B4 | 3432 | 0.191 | 2186 | 0.548 | 0.009 | 0.336 | 5.397 |

### Snapshot Source x Kelas

| source | class_name | instances | instance_share_within_source | images_with_class | image_prevalence_within_source | mean_bbox_area | mean_y_center |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DAMIMAS | B1 | 2152 | 0.127 | 1790 | 0.498 | 0.018 | 0.451 |
| DAMIMAS | B2 | 3924 | 0.232 | 2325 | 0.647 | 0.014 | 0.428 |
| DAMIMAS | B3 | 7593 | 0.449 | 3211 | 0.893 | 0.013 | 0.382 |
| DAMIMAS | B4 | 3254 | 0.192 | 2057 | 0.572 | 0.009 | 0.336 |
| LONSUM | B1 | 17 | 0.017 | 15 | 0.038 | 0.012 | 0.432 |
| LONSUM | B2 | 154 | 0.150 | 110 | 0.278 | 0.009 | 0.392 |
| LONSUM | B3 | 677 | 0.660 | 325 | 0.821 | 0.008 | 0.365 |
| LONSUM | B4 | 178 | 0.173 | 129 | 0.326 | 0.006 | 0.337 |

## Hidden Patterns

1. **Dataset nyaris sepenuhnya dikendalikan DAMIMAS**. DAMIMAS menyumbang 90.1% image dan 94.3% instance. Model combined lebih banyak belajar prior DAMIMAS daripada prior gabungan dua kebun.
1. **B1 hampir eksklusif milik DAMIMAS**. LONSUM hanya punya 17 instance B1 dan prevalensinya di source itu cuma 3.8%. Transfer domain untuk B1 hampir tidak bisa diukur secara adil.
1. **LONSUM lebih jarang objek per image, bukan hanya lebih sedikit image**. Rata-rata objek per image di DAMIMAS = 4.71, sedangkan LONSUM = 2.59. Combined dataset mencampur dua rezim kepadatan objek yang berbeda, sehingga domain shift menyentuh struktur scene, bukan sekadar tampilan visual.
1. **Ada stratifikasi vertikal yang konsisten antar kelas**. Rerata y-center bergerak dari B1 (0.451) ke B4 (0.336). Posisi objek berperan besar dalam separasi kelas, bukan hanya tekstur lokal.
1. **Ukuran objek lebih menentukan difficulty daripada jumlah sampel mentah**. B1 punya mean area terbesar (0.0179), sementara B4 terkecil (0.0091). Kelas kecil cenderung lebih sulit walau tidak selalu paling jarang.
1. **Kelas tersulit hidup di image paling padat**. B4 muncul pada image dengan rata-rata 5.40 objek, tertinggi di dataset. Kelas sulit tidak selalu kalah karena jumlah data; ia bisa kalah karena selalu muncul di konteks yang paling padat dan paling ambigu.
1. **Relasi antar kelas tidak independen**. Lift tertinggi ada pada B1-B2 (1.04), terendah pada B2-B4 (0.94). Ketergantungan ini tidak ekstrem, tetapi cukup sistematis untuk menunjukkan struktur komposisi objek yang berulang.
1. **Domain shift terbesar datang dari prior kelas**. JS distance campuran kelas DAMIMAS vs LONSUM = 0.237. Gap lintas-source tidak hanya soal appearance, tetapi juga perubahan komposisi label.
1. **Ada dua protokol akuisisi: 4-view dan 8-view**. Terdapat 45 tree dengan 8 view dan 908 tree dengan 4 view; seluruh tree 8-view berada di DAMIMAS. Coverage per tree tidak homogen dan ikut terikat ke source, sehingga protokol akuisisi berpotensi menjadi confounder terselubung.
1. **Sub-populasi internal kelas kadang lebih dekat ke source daripada label global**. Cluster paling source-specific ada pada B3 cluster 0 dengan 98.9% sampel dari DAMIMAS. Satu label menyatukan beberapa mode visual berbeda yang tidak sepenuhnya ekuivalen.
1. **Ranking difficulty model mengikuti struktur dataset**. Di log model, B1 punya mean mAP50 tertinggi (0.700), sedangkan B4 terendah (0.229). Properti dataset cukup konsisten untuk menjelaskan pola performa model.

### Co-occurrence Tersering

| class_combo | images | support |
| --- | --- | --- |
| B2+B3+B4 | 645 | 0.165 |
| B1+B2+B3+B4 | 568 | 0.145 |
| B2+B3 | 515 | 0.132 |
| B1+B2+B3 | 450 | 0.115 |
| B3+B4 | 434 | 0.111 |
| B1+B3+B4 | 374 | 0.096 |
| B3 | 351 | 0.090 |
| B1+B3 | 199 | 0.051 |
| B1+B2 | 125 | 0.032 |
| B2 | 61 | 0.016 |

### Pairwise Association Terkuat

| class_a | class_b | images_with_both | support_both | confidence_a_to_b | confidence_b_to_a | lift |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | B2 | 1174 | 0.300 | 0.650 | 0.482 | 1.044 |
| B3 | B4 | 2021 | 0.517 | 0.572 | 0.925 | 1.022 |
| B1 | B4 | 1009 | 0.258 | 0.559 | 0.462 | 1.000 |
| B2 | B3 | 2178 | 0.557 | 0.894 | 0.616 | 0.989 |
| B1 | B3 | 1591 | 0.407 | 0.881 | 0.450 | 0.974 |
| B2 | B4 | 1284 | 0.328 | 0.527 | 0.587 | 0.943 |

### Drift DAMIMAS vs LONSUM

| split_scope | metric | class_name | value |
| --- | --- | --- | --- |
| all | bbox_area_js | B1 | 0.437 |
| all | bbox_area_js | B3 | 0.280 |
| all | bbox_area_js | B2 | 0.264 |
| all | bbox_area_js | B4 | 0.221 |
| all | y_center_js | B1 | 0.311 |
| all | y_center_js | B4 | 0.263 |
| all | y_center_js | B2 | 0.258 |
| all | y_center_js | B3 | 0.207 |

### Struktur Tree dan View

| split | source | tree_id | views | total_objects | mean_objects_per_view | cv_objects_per_view | distinct_combos |
| --- | --- | --- | --- | --- | --- | --- | --- |
| train | LONSUM | LONSUM_A21A_0073 | 4 | 2 | 0.500 | 2.000 | 2 |
| test | DAMIMAS | DAMIMAS_A21B_0074 | 4 | 2 | 0.500 | 2.000 | 2 |
| train | LONSUM | LONSUM_A21A_0030 | 4 | 1 | 0.250 | 2.000 | 2 |
| train | LONSUM | LONSUM_A21A_0072 | 4 | 1 | 0.250 | 2.000 | 2 |
| train | LONSUM | LONSUM_A21A_0057 | 4 | 3 | 0.750 | 1.277 | 3 |
| val | DAMIMAS | DAMIMAS_A21B_0528 | 4 | 2 | 0.500 | 1.155 | 2 |
| train | LONSUM | LONSUM_A21A_0046 | 4 | 2 | 0.500 | 1.155 | 2 |
| train | LONSUM | LONSUM_A21A_0032 | 4 | 2 | 0.500 | 1.155 | 2 |
| test | DAMIMAS | DAMIMAS_A21B_0763 | 4 | 2 | 0.500 | 1.155 | 2 |
| val | LONSUM | LONSUM_A21A_0085 | 4 | 2 | 0.500 | 1.155 | 3 |
| val | DAMIMAS | DAMIMAS_A21B_0232 | 4 | 8 | 2.000 | 0.913 | 3 |
| train | LONSUM | LONSUM_A21A_0022 | 4 | 8 | 2.000 | 0.913 | 3 |

## Separabilitas Visual

Embedding crop berbasis `ResNet50` menunjukkan bahwa separasi kelas tidak merata. Kelas dengan sinyal ukuran dan posisi yang kuat cenderung lebih mudah dipisahkan, sementara kelas tengah lebih banyak saling tumpang tindih.

### Ringkasan Probe

| class_name | precision | recall | overall_accuracy |
| --- | --- | --- | --- |
| B1 | 0.770 | 0.713 | 0.528 |
| B2 | 0.394 | 0.463 | 0.528 |
| B3 | 0.420 | 0.362 | 0.528 |
| B4 | 0.554 | 0.575 | 0.528 |

### Cluster Internal Kelas

| class_name | cluster_id | samples | dominant_source | dominant_source_share | dominant_view | dominant_view_share | mean_bbox_area | mean_y_center |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | 0 | 101 | DAMIMAS | 0.871 | 1 | 0.327 | 0.011 | 0.444 |
| B1 | 1 | 112 | DAMIMAS | 0.982 | 1 | 0.277 | 0.016 | 0.457 |
| B1 | 2 | 107 | DAMIMAS | 0.981 | 1 | 0.299 | 0.026 | 0.445 |
| B2 | 0 | 107 | DAMIMAS | 0.626 | 3 | 0.318 | 0.008 | 0.414 |
| B2 | 1 | 88 | DAMIMAS | 0.989 | 3 | 0.261 | 0.009 | 0.449 |
| B2 | 2 | 125 | DAMIMAS | 0.936 | 3 | 0.296 | 0.022 | 0.425 |
| B3 | 0 | 94 | DAMIMAS | 0.989 | 2 | 0.277 | 0.020 | 0.384 |
| B3 | 1 | 113 | DAMIMAS | 0.602 | 2 | 0.292 | 0.006 | 0.367 |
| B3 | 2 | 113 | DAMIMAS | 0.973 | 2 | 0.292 | 0.010 | 0.396 |
| B4 | 0 | 106 | DAMIMAS | 0.943 | 3 | 0.274 | 0.011 | 0.324 |
| B4 | 1 | 103 | DAMIMAS | 0.641 | 4 | 0.359 | 0.004 | 0.346 |
| B4 | 2 | 111 | DAMIMAS | 0.946 | 3 | 0.297 | 0.009 | 0.345 |

### Outlier Audit

| class_name | source | split | view_id | bbox_area | y_center | label_count | centroid_distance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | DAMIMAS | train | 6 | 0.033 | 0.534 | 3 | 17.046 |
| B1 | LONSUM | train | 1 | 0.002 | 0.330 | 4 | 14.655 |
| B1 | DAMIMAS | val | 4 | 0.012 | 0.508 | 5 | 13.888 |
| B1 | DAMIMAS | train | 2 | 0.008 | 0.360 | 3 | 13.827 |
| B1 | LONSUM | train | 4 | 0.011 | 0.410 | 3 | 13.650 |
| B1 | DAMIMAS | train | 1 | 0.002 | 0.463 | 7 | 13.161 |
| B1 | DAMIMAS | val | 1 | 0.046 | 0.282 | 3 | 13.003 |
| B1 | DAMIMAS | test | 3 | 0.004 | 0.319 | 3 | 12.756 |
| B2 | LONSUM | train | 1 | 0.001 | 0.170 | 4 | 15.332 |
| B2 | LONSUM | train | 1 | 0.001 | 0.254 | 4 | 14.062 |
| B2 | LONSUM | train | 3 | 0.004 | 0.330 | 5 | 14.002 |
| B2 | LONSUM | train | 2 | 0.007 | 0.191 | 3 | 13.622 |

## Kaitan dengan Hasil Model

| scenario | model | runs | mean_mAP50 | mean_mAP5095 | mean_precision | mean_recall |
| --- | --- | --- | --- | --- | --- | --- |
| all_data | YOLOv9c | 2 | 0.504 | 0.228 | 0.484 | 0.599 |
| damimas_only | YOLOv9c | 2 | 0.502 | 0.227 | 0.492 | 0.601 |
| damimas_only | YOLO26l | 2 | 0.467 | 0.212 | 0.450 | 0.543 |
| all_data | YOLO26l | 2 | 0.459 | 0.209 | 0.449 | 0.537 |
| lonsum_only | YOLOv9c | 2 | 0.282 | 0.105 | 0.328 | 0.335 |
| lonsum_only | YOLO26l | 2 | 0.222 | 0.086 | 0.297 | 0.280 |

| class_name | mean_mAP50 | mean_mAP5095 | mean_precision | mean_recall | mean_f1 |
| --- | --- | --- | --- | --- | --- |
| B1 | 0.700 | 0.330 | 0.598 | 0.738 | 0.656 |
| B3 | 0.410 | 0.170 | 0.422 | 0.533 | 0.468 |
| B2 | 0.285 | 0.126 | 0.329 | 0.396 | 0.341 |
| B4 | 0.229 | 0.085 | 0.318 | 0.264 | 0.285 |

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

1. Prioritaskan enrichment untuk B4: kelas ini paling kecil secara geometri, jadi butuh close-up, quality control anotasi, dan augmentasi skala.
1. Lengkapi coverage LONSUM untuk B1; saat ini kelas itu hampir tidak ada di source tersebut sehingga benchmark combined belum seimbang.
1. Gunakan relasi konteks untuk pasangan B1-B2 karena keduanya muncul bersama jauh di atas ekspektasi acak.
1. Jangan menjadikan jumlah sampel sebagai satu-satunya prioritas. B1 sudah relatif mudah, sementara B4 butuh intervensi data-centric yang lebih spesifik.
1. Pertahankan split per-tree karena integritasnya sudah baik; fokus perbaikan berikutnya seharusnya pada coverage source, protokol view campur, dan image kosong.
    