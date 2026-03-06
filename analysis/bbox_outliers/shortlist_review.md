# Shortlist Review Anotasi BBox

Tanggal: 2026-03-06
Sumber: audit `outliers.csv` + analisis manual

Aturan klasifikasi:
- **DROP** = hapus bbox dari label (anotasi invalid/rusak)
- **REVIEW** = perlu cek visual manual, kemungkinan besar perlu diperbaiki atau dihapus
- **KEEP** = boleh dipertahankan, tapi catat sebagai edge case

---

## Tier 1: DROP (pasti rusak, hapus bbox)

| File | Split | Class | bbox_index | Size | Alasan |
|---|---|---|---:|---|---|
| DAMIMAS_A21B_0007_2.jpg | train | B3 | 8 | 0x0 | Invalid: area nol |
| DAMIMAS_A21B_0011_3.jpg | train | B2 | 2 | 0x0 | Invalid: area nol |
| DAMIMAS_A21B_0087_2.jpg | train | B2 | 0 | 0x0 | Invalid: area nol |

**Total: 3 bbox**

---

## Tier 2: REVIEW prioritas tinggi (rel_area <= 0.0005)

Bbox sangat kecil yang sangat mencurigakan — terutama B1/B2 yang secara distribusi seharusnya besar.

| File | Split | Class | bbox_index | Size | rel_area | Catatan |
|---|---|---|---:|---|---:|---|
| DAMIMAS_A21B_0342_2.jpg | val | B1 | 1 | 16x20 | 0.0003 | B1 seharusnya besar; sangat mencurigakan |
| DAMIMAS_A21B_0222_4.jpg | test | B1 | 0 | 22x31 | 0.0005 | B1 seharusnya besar; juga pelanggaran ordinal B1 < B3 |
| DAMIMAS_A21B_0083_4.jpg | train | B2 | 4 | 61x8 | 0.0004 | Rasio aspek 7.25 — sangat tipis/aneh |
| DAMIMAS_A21B_0441_2.jpg | train | B2 | 7 | 24x22 | 0.0004 | B2 sangat kecil |
| DAMIMAS_A21B_0546_1.jpg | test | B3 | 7 | 17x24 | 0.0003 | Sangat kecil bahkan untuk B3 |
| DAMIMAS_A21B_0122_1.jpg | val | B3 | 2 | 23x26 | 0.0005 | Sangat kecil |
| LONSUM_A21A_0091_1.jpg | val | B3 | 2 | 22x28 | 0.0005 | Sangat kecil + domain LONSUM |
| DAMIMAS_A21B_0345_4.jpg | train | B4 | 3 | 21x28 | 0.0005 | Kecil tapi B4 bisa wajar — cek visual |
| DAMIMAS_A21B_0442_1.jpg | test | B4 | 6 | 18x35 | 0.0005 | Kecil tapi B4 bisa wajar — cek visual |

**Total: 9 bbox**

---

## Tier 3: REVIEW tambahan (width <= 24 ATAU height <= 24, rel_area > 0.0005)

Bbox kecil yang belum otomatis salah tapi bisa merusak training.

### B1/B2 (lebih ketat, karena distribusi normal lebih besar)

| File | Split | Class | bbox_index | Size | rel_area |
|---|---|---|---:|---|---:|
| DAMIMAS_A21B_0398_2.jpg | val | B1 | 5 | 36x44 | 0.0013 |
| DAMIMAS_A21B_0746_4.jpg | train | B1 | 1 | 24x132 | 0.0026 |
| DAMIMAS_A21B_0501_3.jpg | train | B2 | 2 | 28x30 | 0.0007 |
| DAMIMAS_A21B_0246_1.jpg | test | B2 | 3 | 22x42 | 0.0008 |
| DAMIMAS_A21B_0449_1.jpg | test | B2 | 6 | 25x40 | 0.0008 |
| DAMIMAS_A21B_0470_3.jpg | train | B2 | 2 | 23x45 | 0.0008 |
| DAMIMAS_A21B_0493_4.jpg | train | B2 | 4 | 25x46 | 0.0009 |
| DAMIMAS_A21B_0724_3.jpg | val | B2 | 3 | 37x32 | 0.0010 |
| DAMIMAS_A21B_0398_2.jpg | val | B2 | 6 | 25x51 | 0.0011 |

### B3/B4 (threshold lebih longgar — hanya yang width <= 24 DAN height <= 24)

| File | Split | Class | bbox_index | Size | rel_area |
|---|---|---|---:|---|---:|
| DAMIMAS_A21B_0433_3.jpg | train | B3 | 5 | 42x20 | 0.0007 |
| DAMIMAS_A21B_0696_2.jpg | train | B3 | 4 | 47x18 | 0.0007 |
| DAMIMAS_A21B_0757_3.jpg | train | B3 | 4 | 23x37 | 0.0007 |
| DAMIMAS_A21B_0676_2.jpg | train | B3 | 7 | 21x44 | 0.0007 |
| DAMIMAS_A21B_0762_3.jpg | val | B3 | 1 | 20x51 | 0.0008 |
| DAMIMAS_A21B_0470_3.jpg | train | B3 | 5 | 20x54 | 0.0009 |
| DAMIMAS_A21B_0198_3.jpg | train | B3 | 3 | 21x48 | 0.0008 |
| DAMIMAS_A21B_0342_1.jpg | val | B4 | 5 | 41x20 | 0.0007 |
| DAMIMAS_A21B_0498_3.jpg | train | B4 | 4 | 23x34 | 0.0006 |
| DAMIMAS_A21B_0222_4.jpg | test | B4 | 6 | 24x34 | 0.0007 |
| DAMIMAS_A21B_0660_1.jpg | train | B4 | 3 | 22x44 | 0.0008 |
| DAMIMAS_A21B_0126_4.jpg | test | B4 | 4 | 20x56 | 0.0009 |

---

## Ringkasan

| Tier | Jumlah bbox | Tindakan |
|---|---:|---|
| Tier 1: DROP | 3 | Hapus bbox dari label file |
| Tier 2: REVIEW tinggi | 9 | Cek visual → kemungkinan besar drop/perbaiki |
| Tier 3: REVIEW tambahan | 21 | Cek visual → pertahankan jika objek terbaca |
| **Total perlu aksi** | **33** | |

### Distribusi per kelas (Tier 1+2+3)

| Class | DROP | REVIEW tinggi | REVIEW tambahan | Total |
|---|---:|---:|---:|---:|
| B1 | 0 | 2 | 2 | 4 |
| B2 | 2 | 2 | 7 | 11 |
| B3 | 1 | 3 | 7 | 11 |
| B4 | 0 | 2 | 5 | 7 |
| **Total** | **3** | **9** | **21** | **33** |

### Catatan

- B1/B2 kecil lebih mencurigakan karena secara distribusi normal median width B1=125px, B2=109px.
- B3/B4 kecil belum otomatis salah (median B4=94px, tapi P10=~50px), perlu konfirmasi visual.
- Bbox 61x8 (DAMIMAS_A21B_0083_4.jpg B2) sangat aneh — kemungkinan salah drag saat anotasi.
- DAMIMAS_A21B_0222_4.jpg muncul di 2 tier (B1 Tier 2 + B4 Tier 3) — gambar ini perlu review menyeluruh.
