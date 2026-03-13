# Analisis Dataset `dataset_640`

## 1. Sekilas Dataset

Dataset ini berisi foto-foto buah sawit dari dua kebun (**DAMIMAS** dan **LONSUM**), yang diberi label kematangan: **B1** (mentah), **B2** (mengkal), **B3** (matang), **B4** (lewat matang).

| Apa | Jumlah |
| --- | --- |
| Total foto | 3.992 |
| Total kotak label (bounding box) | 17.949 |
| Foto tanpa label | 83 |
| Total pohon yang difoto | 953 |
| Pohon bocor antar split | **0** (aman, tidak ada kebocoran) |
| Ukuran foto | 640 × 853 piksel |

---

## 2. Cek Kualitas Data

> **Catatan:** Jumlah foto di folder lokal (2772 / 608 / 612) sedikit berbeda dari catatan log repo (2780 / 620 / 592). Laporan ini menggunakan folder lokal sebagai acuan.

Hasil pengecekan:
- Setiap foto punya file label yang cocok — tidak ada yang hilang.
- Tidak ada pohon yang muncul di lebih dari satu split — **data aman dari kebocoran**.
- 83 foto tanpa label tetap dihitung, tidak dibuang.
- Ada dua cara foto: **4 sudut per pohon** (908 pohon) dan **8 sudut per pohon** (45 pohon, semua dari DAMIMAS).

### 2.1 Pembagian Data (Split)

Data dibagi jadi 3 bagian: **Train** (untuk melatih model), **Val** (untuk validasi saat training), dan **Test** (untuk evaluasi akhir).

| Split | Foto | Pohon | Kotak Label | Foto Kosong | Rata-rata Objek/Foto | Dari DAMIMAS | Dari LONSUM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Train | 2.772 | 667 | 12.426 | 57 | 4,48 | 2.492 | 280 |
| Val | 608 | 142 | 2.825 | 13 | 4,65 | 548 | 60 |
| Test | 612 | 144 | 2.698 | 13 | 4,41 | 556 | 56 |

![Komposisi split dan sumber data](figures/split_source_composition.png)

> **Cara baca grafik di atas:**
> - **Grafik kiri** — jumlah foto per split (train/val/test). Warna biru = DAMIMAS, oranye = LONSUM. Terlihat DAMIMAS jauh lebih banyak.
> - **Grafik kanan** — persentase DAMIMAS vs LONSUM di tiap split. Proporsinya hampir sama di semua split (~90% DAMIMAS, ~10% LONSUM), artinya pembagian split cukup konsisten.

### 2.2 Distribusi Kelas

Empat kelas kematangan tidak seimbang — **B3 (matang) mendominasi hampir setengah dari semua label**.

| Kelas | Jumlah Label | Persentase | Ada di Berapa Foto | Ukuran Rata-rata* | Posisi Rata-rata** |
| --- | --- | --- | --- | --- | --- |
| B1 (mentah) | 2.169 | 12,1% | 1.805 foto (45%) | 1,8% dari foto | 45% dari atas |
| B2 (mengkal) | 4.078 | 22,7% | 2.435 foto (61%) | 1,4% dari foto | 43% dari atas |
| B3 (matang) | 8.270 | 46,1% | 3.536 foto (89%) | 1,3% dari foto | 38% dari atas |
| B4 (lewat matang) | 3.432 | 19,1% | 2.186 foto (55%) | 0,9% dari foto | 34% dari atas |

> *\*Ukuran rata-rata: luas kotak label dibagi luas total foto. Misalnya 1,8% artinya kotak label B1 rata-rata mengisi 1,8% dari seluruh area foto — objeknya relatif kecil.*
>
> *\*\*Posisi rata-rata: 0% = paling atas foto, 100% = paling bawah. Jadi 45% artinya sedikit di bawah tengah foto.*

![Distribusi kelas](figures/class_distribution.png)

![Histogram jumlah label per foto](figures/label_count_histogram.png)

> **Cara baca histogram:** Sumbu horizontal = berapa objek dalam satu foto. Sumbu vertikal = berapa banyak foto yang punya jumlah objek sebanyak itu. Kebanyakan foto berisi 3–6 objek.

---

## 3. Temuan Utama

### 3.1 DAMIMAS Mendominasi, LONSUM Sangat Sedikit

DAMIMAS menyumbang **90% foto** dan **94% label**. Artinya model yang dilatih pakai "gabungan dua kebun" sebenarnya hampir hanya belajar pola DAMIMAS.

| Kebun | Kelas | Jumlah Label | % di Kebun Ini | Ada di Berapa Foto | Ukuran Rata-rata | Posisi Rata-rata |
| --- | --- | --- | --- | --- | --- | --- |
| DAMIMAS | B1 | 2.152 | 12,7% | 1.790 (50%) | 1,8% | 45% |
| DAMIMAS | B2 | 3.924 | 23,2% | 2.325 (65%) | 1,4% | 43% |
| DAMIMAS | B3 | 7.593 | 44,9% | 3.211 (89%) | 1,3% | 38% |
| DAMIMAS | B4 | 3.254 | 19,2% | 2.057 (57%) | 0,9% | 34% |
| LONSUM | B1 | **17** | 1,7% | 15 (4%) | 1,2% | 43% |
| LONSUM | B2 | 154 | 15,0% | 110 (28%) | 0,9% | 39% |
| LONSUM | B3 | 677 | 66,0% | 325 (82%) | 0,8% | 37% |
| LONSUM | B4 | 178 | 17,3% | 129 (33%) | 0,6% | 34% |

Hal penting:
- **B1 hampir tidak ada di LONSUM** — cuma 17 label. Kalau mau menilai apakah model bisa generalisasi antar kebun untuk B1, datanya tidak cukup.
- **Foto LONSUM lebih "sepi"** — rata-rata 2,6 objek/foto vs 4,7 di DAMIMAS. Bukan cuma beda tampilan, tapi beda kepadatan objek.
- **Buah di LONSUM umumnya lebih kecil** daripada di DAMIMAS untuk semua kelas.

![Perbedaan antar kebun per kelas](figures/source_class_drift.png)

> **Cara baca grafik di atas:** Grafik ini menunjukkan seberapa berbeda distribusi ukuran dan posisi buah antara DAMIMAS dan LONSUM. Semakin tinggi nilainya (Jensen-Shannon distance, skala 0–1), semakin berbeda. B1 paling berbeda antar kebun.

#### Seberapa Beda Kedua Kebun? (Jensen-Shannon Distance)

*Skala 0–1: 0 = identik, 1 = sangat berbeda*

| Yang Dibandingkan | B1 | B2 | B3 | B4 |
| --- | --- | --- | --- | --- |
| Ukuran kotak label | **0,44** | 0,26 | 0,28 | 0,22 |
| Posisi vertikal | **0,31** | 0,26 | 0,21 | 0,26 |

B1 paling berbeda di kedua metrik — ukuran dan posisi buah B1 di DAMIMAS vs LONSUM cukup jauh.

### 3.2 Ukuran dan Posisi Buah Menentukan Kesulitan Deteksi

Ada pola konsisten: **semakin matang buah, semakin kecil ukurannya di foto dan semakin tinggi posisinya** (lebih dekat ke atas frame).

| Kelas | Ukuran Rata-rata | Posisi Rata-rata | Kepadatan Foto |
| --- | --- | --- | --- |
| B1 (mentah) | 1,8% (terbesar) | 45% (terbawah) | 5,2 objek/foto |
| B2 (mengkal) | 1,4% | 43% | 5,2 objek/foto |
| B3 (matang) | 1,3% | 38% | 5,1 objek/foto |
| B4 (lewat matang) | 0,9% (terkecil) | 34% (teratas) | 5,4 objek/foto (terpadat) |

Kesimpulan:
- **Ukuran objek lebih penting daripada jumlah data.** B4 bukan kelas paling jarang, tapi paling sulit dideteksi karena ukurannya paling kecil.
- **B4 selalu muncul di foto yang paling ramai** (rata-rata 5,4 objek/foto) — makin banyak objek, makin sulit model membedakan.
- **Posisi vertikal konsisten per kelas** — buah mentah cenderung di bawah, buah matang/lewat matang di atas.

![Ukuran dan posisi kotak label per kelas](figures/bbox_geometry.png)

> **Cara baca grafik di atas:** Menunjukkan distribusi luas dan posisi kotak label. Sumbu menunjukkan ukuran (% dari luas foto) dan posisi Y (0% = atas foto, 100% = bawah foto). Terlihat B4 paling kecil dan paling di atas.

![Heatmap posisi buah per kelas](figures/spatial_heatmaps.png)

> **Cara baca heatmap:** Setiap panel menunjukkan satu kelas (B1/B2/B3/B4). Sumbu horizontal = posisi kiri-kanan di foto, sumbu vertikal = posisi atas-bawah di foto. Warna makin terang = makin banyak buah ditemukan di posisi itu. Terlihat B1 tersebar di tengah-bawah, sedangkan B4 terkumpul di atas.

### 3.3 Kelas Sering Muncul Bersama dalam Satu Foto

Kebanyakan foto berisi **campuran 3–4 kelas sekaligus**, bukan satu kelas saja.

| Kombinasi Kelas | Jumlah Foto | Persentase |
| --- | --- | --- |
| B2 + B3 + B4 | 645 | 16,5% |
| B1 + B2 + B3 + B4 (lengkap) | 568 | 14,5% |
| B2 + B3 | 515 | 13,2% |
| B1 + B2 + B3 | 450 | 11,5% |
| B3 + B4 | 434 | 11,1% |

![Heatmap kemunculan bersama antar kelas](figures/class_cooccurrence_lift.png)

> **Cara baca heatmap "Lift":**
> - Angka di setiap sel menunjukkan **lift** — ukuran apakah dua kelas muncul bersama lebih sering dari yang diharapkan secara kebetulan.
> - **Lift = 1,00** → muncul bersama sesuai ekspektasi acak (tidak ada hubungan khusus)
> - **Lift > 1,00** (misal 1,04) → muncul bersama **lebih sering** dari kebetulan. Contoh: B1 dan B2 sering muncul bareng.
> - **Lift < 1,00** (misal 0,94) → muncul bersama **lebih jarang** dari kebetulan. Contoh: B2 dan B4 cenderung tidak muncul bareng.
> - Warna makin gelap = lift makin tinggi (makin sering muncul bersama).

#### Pasangan Kelas yang Menarik

| Pasangan | Foto Bersama | Lift | Artinya |
| --- | --- | --- | --- |
| B1 ↔ B2 | 1.174 | **1,04** | Sering muncul bersama (di atas kebetulan) |
| B3 ↔ B4 | 2.021 | 1,02 | Sering berdampingan |
| B2 ↔ B4 | 1.284 | **0,94** | Cenderung *tidak* muncul bersama |

### 3.4 Dua Cara Foto: 4-Sudut vs 8-Sudut

| Cara Foto | Jumlah Pohon | Kebun |
| --- | --- | --- |
| 4 sudut per pohon | 908 | DAMIMAS + LONSUM |
| 8 sudut per pohon | 45 | DAMIMAS saja |

Semua pohon 8-sudut hanya dari DAMIMAS. Ini berpotensi jadi **bias tersembunyi** — model mungkin belajar mengenali "gaya foto", bukan kematangan buah.

![Konsistensi label antar sudut foto](figures/view_consistency.png)

> **Cara baca:** Grafik ini menunjukkan seberapa konsisten label yang diberikan pada satu pohon ketika difoto dari sudut berbeda. Variasi tinggi berarti label bisa berubah tergantung sudut pandang.

---

## 4. Analisis Kemiripan Visual (Embedding)

Untuk memahami apakah kelas-kelas bisa dibedakan secara visual, setiap potongan buah (crop) diproses oleh ResNet50 (model pengenalan gambar) menjadi vektor angka (embedding), lalu divisualisasikan dalam grafik 2D menggunakan t-SNE.

**Cara baca t-SNE:** Setiap titik = satu potongan buah. Titik yang berdekatan artinya terlihat mirip menurut model. Jika satu kelas membentuk kelompok terpisah, berarti kelas itu mudah dibedakan.

### 4.1 Seberapa Mudah Kelas Dibedakan?

Tes sederhana: latih classifier linier di atas embedding, lalu lihat hasilnya.

| Kelas | Precision* | Recall** | Akurasi Total |
| --- | --- | --- | --- |
| B1 | **0,77** | **0,71** | 0,53 |
| B4 | 0,55 | 0,58 | 0,53 |
| B2 | 0,39 | 0,46 | 0,53 |
| B3 | 0,42 | 0,36 | 0,53 |

> *\*Precision: dari semua yang diprediksi sebagai kelas X, berapa persen yang benar.*
>
> *\*\*Recall: dari semua yang seharusnya kelas X, berapa persen yang berhasil ditemukan.*

B1 paling mudah dibedakan, B2 dan B3 paling sering tertukar.

![Visualisasi t-SNE per kelas](figures/embedding_tsne_class.png)

> **Cara baca:** Setiap warna = satu kelas. Jika warna membentuk kelompok terpisah, kelas itu mudah dibedakan. Terlihat B1 agak terpisah, sementara B2 dan B3 bercampur.

![Visualisasi t-SNE per kebun](figures/embedding_tsne_source.png)

> **Cara baca:** Warna menunjukkan kebun asal (DAMIMAS vs LONSUM). Jika warna terpisah, artinya foto dari kedua kebun terlihat berbeda secara visual.

![Confusion matrix](figures/probe_confusion_matrix.png)

> **Cara baca confusion matrix:** Baris = kelas sebenarnya, kolom = kelas yang diprediksi. Angka di diagonal (kiri atas ke kanan bawah) = prediksi benar. Angka di luar diagonal = salah prediksi. Makin besar angka di diagonal, makin bagus.

### 4.2 Sub-kelompok dalam Satu Kelas

Dalam satu kelas, ternyata ada sub-kelompok yang tampilannya berbeda. Kadang perbedaannya terkait ke kebun asal, bukan ke kematangan.

Contoh: **B3 kelompok 0** berisi 98,9% sampel dari DAMIMAS — artinya satu label bisa menyatukan tampilan visual yang sebenarnya berbeda.

| Kelas | Kelompok | Sampel | Kebun Dominan | % dari Kebun Itu | Ukuran | Posisi |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | 0 | 101 | DAMIMAS | 87% | 1,1% | 44% |
| B1 | 1 | 112 | DAMIMAS | 98% | 1,6% | 46% |
| B1 | 2 | 107 | DAMIMAS | 98% | 2,6% | 45% |
| B2 | 0 | 107 | DAMIMAS | 63% | 0,8% | 41% |
| B2 | 1 | 88 | DAMIMAS | 99% | 0,9% | 45% |
| B2 | 2 | 125 | DAMIMAS | 94% | 2,2% | 43% |
| B3 | 0 | 94 | DAMIMAS | **99%** | 2,0% | 38% |
| B3 | 1 | 113 | DAMIMAS | 60% | 0,6% | 37% |
| B3 | 2 | 113 | DAMIMAS | 97% | 1,0% | 40% |
| B4 | 0 | 106 | DAMIMAS | 94% | 1,1% | 32% |
| B4 | 1 | 103 | DAMIMAS | 64% | 0,4% | 35% |
| B4 | 2 | 111 | DAMIMAS | 95% | 0,9% | 35% |

![Contoh potongan buah per kelompok](figures/representative_crops.png)

### 4.3 Outlier (Label yang Perlu Dicek Ulang)

Buah-buah berikut paling "aneh" dibandingkan teman sekelasnya — kemungkinan salah label atau kondisi tidak biasa.

| Kelas | Kebun | Split | Sudut | Ukuran | Posisi | Seberapa Aneh* |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | DAMIMAS | train | 6 | 3,3% | 53% | 17,1 |
| B1 | LONSUM | train | 1 | 0,2% | 33% | 14,7 |
| B1 | DAMIMAS | val | 4 | 1,2% | 51% | 13,9 |
| B2 | LONSUM | train | 1 | 0,1% | 17% | 15,3 |
| B2 | LONSUM | train | 1 | 0,1% | 25% | 14,1 |
| B2 | LONSUM | train | 3 | 0,4% | 33% | 14,0 |

> *\*Seberapa aneh: jarak dari pusat kelompok di ruang embedding. Makin besar, makin berbeda dari teman sekelasnya.*

![Galeri outlier](figures/outlier_gallery.png)

---

## 5. Hubungan dengan Performa Model

Apakah pola-pola di atas terlihat di hasil training? **Ya, sangat konsisten.**

### 5.1 Performa per Skenario Data

| Skenario | Model | Run | mAP50 | mAP50-95 | Precision | Recall |
| --- | --- | --- | --- | --- | --- | --- |
| Gabungan (all_data) | YOLOv9c | 2 | **0,504** | 0,228 | 0,484 | 0,599 |
| DAMIMAS saja | YOLOv9c | 2 | 0,502 | 0,227 | 0,492 | 0,601 |
| DAMIMAS saja | YOLO26l | 2 | 0,467 | 0,212 | 0,450 | 0,543 |
| Gabungan (all_data) | YOLO26l | 2 | 0,459 | 0,209 | 0,449 | 0,537 |
| LONSUM saja | YOLOv9c | 2 | 0,282 | 0,105 | 0,328 | 0,335 |
| LONSUM saja | YOLO26l | 2 | 0,222 | 0,086 | 0,297 | 0,280 |

Menambahkan LONSUM ke DAMIMAS **hampir tidak mengubah skor** (0,502 → 0,504). Karena LONSUM cuma 10% dari dataset, pengaruhnya tenggelam.

### 5.2 Performa per Kelas

| Kelas | mAP50 | mAP50-95 | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- |
| B1 (mentah) | **0,700** | 0,330 | 0,598 | 0,738 | 0,656 |
| B3 (matang) | 0,410 | 0,170 | 0,422 | 0,533 | 0,468 |
| B2 (mengkal) | 0,285 | 0,126 | 0,329 | 0,396 | 0,341 |
| B4 (lewat matang) | **0,229** | 0,085 | 0,318 | 0,264 | 0,285 |

Urutan kesulitan model **cocok dengan pola dataset**:
- **B1 paling mudah** — ukuran terbesar di foto, posisi paling jelas, secara visual paling berbeda dari kelas lain.
- **B4 paling sulit** — ukuran terkecil, selalu di foto yang ramai, bukan karena datanya sedikit tapi karena objeknya memang sulit.
- **B2 dan B3 di tengah** — secara visual sering mirip, sehingga model sering salah antara keduanya.

---

## 6. Rekomendasi

| Prioritas | Aksi | Kenapa |
| --- | --- | --- |
| 1 | **Perbaiki data B4**: foto lebih dekat, cek ulang label, tambah augmentasi ukuran | Kelas terkecil di foto dan paling sulit dideteksi |
| 2 | **Tambah foto LONSUM untuk B1** | Cuma 17 label — terlalu sedikit untuk evaluasi antar kebun |
| 3 | **Manfaatkan B1 + B2 yang sering bareng** | Kemunculan bersama bisa jadi petunjuk konteks buat model |
| 4 | **Jangan cuma nambah jumlah data** | B1 sudah mudah meski sedikit; B4 butuh perbaikan kualitas, bukan kuantitas |
| 5 | **Pertahankan pembagian split per-pohon** | Sudah aman dari kebocoran; fokus selanjutnya ke keseimbangan antar kebun |
