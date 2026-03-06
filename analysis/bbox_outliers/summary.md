# BBox Outlier Audit

Dataset: `C:\Users\MyBook Z Series\OneDrive\Documents\YOLOBench\dataset_combined`
Output: `C:\Users\MyBook Z Series\OneDrive\Documents\YOLOBench\analysis\bbox_outliers`

## Distribusi per kelas

| Class | Count | P10 rel_area | Median rel_area | P90 rel_area | Median width px | Median height px |
|---|---:|---:|---:|---:|---:|---:|
| B1 | 2177 | 0.0061 | 0.0140 | 0.0339 | 125 | 137 |
| B2 | 4075 | 0.0045 | 0.0107 | 0.0268 | 109 | 121 |
| B3 | 8296 | 0.0034 | 0.0096 | 0.0261 | 105 | 114 |
| B4 | 3442 | 0.0026 | 0.0072 | 0.0171 | 94 | 96 |

## Overlap antarkelas (P10-P90)

| Pair | Overlap | LHS range | RHS range |
|---|---|---|---|
| B1 vs B2 | YES | 0.0061 - 0.0339 | 0.0045 - 0.0268 |
| B1 vs B3 | YES | 0.0061 - 0.0339 | 0.0034 - 0.0261 |
| B1 vs B4 | YES | 0.0061 - 0.0339 | 0.0026 - 0.0171 |
| B2 vs B3 | YES | 0.0045 - 0.0268 | 0.0034 - 0.0261 |
| B2 vs B4 | YES | 0.0045 - 0.0268 | 0.0026 - 0.0171 |
| B3 vs B4 | YES | 0.0034 - 0.0261 | 0.0026 - 0.0171 |

## Kandidat review utama

1. B4 right | DAMIMAS_A21B_0642_3.jpg | split=test | rel_area=0.0869 | reason=B4 terlalu besar dibanding distribusi kelasnya
2. B4 right | DAMIMAS_A21B_0641_3.jpg | split=train | rel_area=0.0725 | reason=B4 terlalu besar dibanding distribusi kelasnya
3. B3 right | DAMIMAS_A21B_0597_3.jpg | split=train | rel_area=0.0933 | reason=B3 terlalu besar dibanding distribusi kelasnya
4. B4 right | DAMIMAS_A21B_0708_4.jpg | split=val | rel_area=0.0690 | reason=B4 terlalu besar dibanding distribusi kelasnya
5. B1 right | DAMIMAS_A21B_0678_4.jpg | split=test | rel_area=0.1312 | reason=B1 terlalu besar dibanding distribusi kelasnya
6. B3 right | DAMIMAS_A21B_0692_3.jpg | split=train | rel_area=0.0869 | reason=B3 terlalu besar dibanding distribusi kelasnya
7. B3 right | DAMIMAS_A21B_0708_2.jpg | split=val | rel_area=0.0867 | reason=B3 terlalu besar dibanding distribusi kelasnya
8. B3 right | DAMIMAS_A21B_0707_4.jpg | split=train | rel_area=0.0854 | reason=B3 terlalu besar dibanding distribusi kelasnya
9. B3 right | DAMIMAS_A21B_0597_2.jpg | split=train | rel_area=0.0840 | reason=B3 terlalu besar dibanding distribusi kelasnya
10. B2 right | DAMIMAS_A21B_0716_3.jpg | split=test | rel_area=0.0917 | reason=B2 terlalu besar dibanding distribusi kelasnya
11. B3 right | DAMIMAS_A21B_0707_3.jpg | split=train | rel_area=0.0801 | reason=B3 terlalu besar dibanding distribusi kelasnya
12. B2 right | DAMIMAS_A21B_0678_2.jpg | split=test | rel_area=0.0876 | reason=B2 terlalu besar dibanding distribusi kelasnya

## Pelanggaran ordinal teratas

1. DAMIMAS_A21B_0222_4.jpg | B1 < B3 by size | ratio=29.550 | split=test
2. DAMIMAS_A21B_0724_3.jpg | B2 < B3 by size | ratio=24.247 | split=val
3. DAMIMAS_A21B_0676_2.jpg | B3 < B4 by size | ratio=20.165 | split=train
4. DAMIMAS_A21B_0698_3.jpg | B1 < B3 by size | ratio=19.587 | split=train
5. DAMIMAS_A21B_0616_3.jpg | B3 < B4 by size | ratio=19.186 | split=test
6. DAMIMAS_A21B_0342_2.jpg | B1 < B3 by size | ratio=19.127 | split=val
7. DAMIMAS_A21B_0616_3.jpg | B3 < B4 by size | ratio=16.056 | split=test
8. DAMIMAS_A21B_0684_4.jpg | B2 < B3 by size | ratio=15.037 | split=val
9. DAMIMAS_A21B_0684_4.jpg | B2 < B3 by size | ratio=14.768 | split=val
10. DAMIMAS_A21B_0589_3.jpg | B3 < B4 by size | ratio=13.317 | split=train
11. DAMIMAS_A21B_0222_4.jpg | B1 < B3 by size | ratio=13.150 | split=test
12. DAMIMAS_A21B_0398_2.jpg | B2 < B3 by size | ratio=13.040 | split=val

## Gambar padat

1. DAMIMAS_A21B_0007_2.jpg | split=train | boxes=10 | B1:2, B2:0, B3:6, B4:2
2. DAMIMAS_A21B_0360_2.jpg | split=train | boxes=10 | B1:4, B2:2, B3:0, B4:4
3. DAMIMAS_A21B_0429_3.jpg | split=train | boxes=10 | B1:1, B2:1, B3:5, B4:3
4. DAMIMAS_A21B_0632_4.jpg | split=train | boxes=10 | B1:1, B2:1, B3:5, B4:3
5. DAMIMAS_A21B_0723_2.jpg | split=train | boxes=10 | B1:1, B2:2, B3:4, B4:3
6. DAMIMAS_A21B_0075_4.jpg | split=train | boxes=9 | B1:2, B2:4, B3:2, B4:1
7. DAMIMAS_A21B_0103_4.jpg | split=val | boxes=9 | B1:1, B2:5, B3:3, B4:0
8. DAMIMAS_A21B_0163_3.jpg | split=train | boxes=9 | B1:1, B2:6, B3:1, B4:1
9. DAMIMAS_A21B_0285_1.jpg | split=train | boxes=9 | B1:3, B2:1, B3:4, B4:1
10. DAMIMAS_A21B_0285_4.jpg | split=train | boxes=9 | B1:1, B2:2, B3:4, B4:2
11. DAMIMAS_A21B_0291_4.jpg | split=train | boxes=9 | B1:1, B2:4, B3:2, B4:2
12. DAMIMAS_A21B_0354_1.jpg | split=train | boxes=9 | B1:0, B2:2, B3:6, B4:1

## Canvas

- `canvases/class_left_*.jpg`: outlier kecil per kelas
- `canvases/class_right_*.jpg`: outlier besar per kelas
- `canvases/dense_*.jpg`: satu gambar multi-bbox, semua object crop dijajarkan urut kelas
