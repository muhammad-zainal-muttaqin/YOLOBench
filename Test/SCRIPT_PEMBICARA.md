# Script Pembicara — Presentasi Hasil Testing Model Deteksi Kematangan TBS

> Panduan ini mengikuti urutan slide di `PRESENTASI_HASIL_TEST.md`.
> Teks dalam **[kurung]** = instruksi untuk pembicara, bukan dibacakan.

---

## Slide 1 — Judul & Pendahuluan

**[Buka slide judul]**

> Assalamu'alaikum, selamat pagi/siang semuanya.
>
> Hari ini saya akan mempresentasikan hasil testing model deteksi kematangan Tandan Buah Segar — atau TBS — kelapa sawit. Kita sudah melatih total 14 model, dan semuanya sudah diuji pada dataset test yang sama agar perbandingannya fair.
>
> Sekilas konteksnya: model kita mendeteksi 4 kelas kematangan tandan. B1 itu tandan paling matang — tinggal sekitar 1 bulan lagi siap panen. Warnanya sudah oranye kemerahan, sangat khas. Sedangkan B4 itu tandan paling muda — masih sekitar 4 bulan lagi, warnanya masih hijau, dan secara visual sangat mirip dengan daun di sekitarnya.
>
> Jadi tantangannya: makin muda tandannya, makin sulit dideteksi.

---

## Slide 2 — Metodologi

**[Tunjukkan bagian metodologi]**

> Untuk testing ini, kita menggunakan dataset gabungan yang berisi 592 gambar dari dua lokasi kebun: DAMIMAS dan LONSUM. Semua 14 model dijalankan pada gambar yang persis sama.
>
> Metrik yang kita gunakan standar YOLO: Precision, Recall, mAP@50, dan mAP@50-95. Yang perlu diingat, mAP50 itu mengukur apakah model bisa mendeteksi objek, sedangkan mAP50-95 lebih ketat — mengukur seberapa presisi bounding box-nya.

---

## Slide 3 — Tabel Metrik Global & Ranking

**[Tunjukkan tabel ranking mAP50]**

> Langsung ke hasilnya. Ini ranking semua 14 model berdasarkan mAP50.
>
> **Dua model terbaik** ada di posisi teratas dengan skor identik — mAP50 sebesar 0.505:
> - `combined_yv9c_123`, yang dilatih dengan dataset gabungan
> - `damimas_yv9c_42`, yang dilatih hanya dengan data DAMIMAS
>
> Menariknya, keduanya sama-sama menggunakan arsitektur **YOLOv9c**.
>
> Di posisi ke-5, model legacy lama kita — `legacy_yv9c_640` — masih cukup kompetitif di mAP50 dengan skor 0.483. Tapi perhatikan mAP50-95-nya: hanya 0.161 dibanding 0.230 milik v2. Artinya, model lama memang bisa mendeteksi tandan, tapi bounding box-nya kurang presisi.
>
> Dan di bagian bawah, semua model LONSUM. Performanya jauh tertinggal — yang terbaik hanya 0.307. Ini akan kita bahas nanti kenapa.

---

## Slide 4 — Analisis Per Grup: Combined v2

**[Tunjukkan tabel Combined v2]**

> Kita bedah per grup. Pertama, **Combined v2** — model yang dilatih dengan data gabungan DAMIMAS + LONSUM.
>
> Di sini terlihat pola yang jelas: **YOLOv9c selalu mengungguli YOLO26L** sekitar 4–5 poin mAP50. Ini konsisten di semua seed.
>
> Perbedaan antar seed? Kecil saja, 1–2 persen. Jadi arsitektur jauh lebih berpengaruh daripada random seed.
>
> Recall tertinggi grup ini 0.611 — artinya model mampu menemukan sekitar 61% dari semua tandan yang ada.

---

## Slide 5 — Analisis Per Grup: DAMIMAS v2

**[Tunjukkan tabel DAMIMAS v2]**

> Ini yang menarik. Model DAMIMAS — yang **hanya dilatih dengan data dari satu kebun** — performanya ternyata **setara bahkan sedikit lebih baik** dari Combined.
>
> `damimas_yv9c_42` punya Precision tertinggi di antara semua 14 model: 0.502. Ini satu-satunya model yang menembus angka 50% precision.
>
> Apa artinya? Data DAMIMAS sangat representatif. Kualitas labelingnya bagus, dan distribusi kelasnya cukup balanced untuk generalisasi ke test set gabungan.

---

## Slide 6 — Analisis Per Grup: LONSUM v2

**[Tunjukkan tabel LONSUM v2]**

> Sekarang yang kurang bagus. Model LONSUM performanya **sangat jauh di bawah** yang lain.
>
> mAP50 terbaik cuma 0.307 — kurang dari setengah performa Combined atau DAMIMAS. Kenapa?
>
> Kemungkinan besar ada **domain gap** yang besar. Kondisi kebun LONSUM — pencahayaan, sudut pengambilan gambar, variasi tandan — sangat berbeda dari DAMIMAS. Akibatnya, model yang dilatih murni di LONSUM tidak bisa generalisasi ke gambar DAMIMAS yang mendominasi test set.
>
> Ini jadi catatan penting: kalau mau deploy di lokasi LONSUM, kita perlu data tambahan atau fine-tuning khusus.

---

## Slide 7 — Analisis Per Grup: Legacy

**[Tunjukkan tabel Legacy]**

> Untuk referensi, ini model legacy — generasi sebelumnya.
>
> `legacy_yv9c_640` masih lumayan: mAP50 = 0.483. Tapi sekali lagi, mAP50-95-nya rendah di 0.161. Model v2 terbaik kita di 0.230 — itu peningkatan **43 persen** pada presisi bounding box.
>
> Jadi upgrade ke v2 memberikan peningkatan nyata, terutama pada kualitas lokalisasi objek.

---

## Slide 8 — Performa Per Kelas: Tabel Recall

**[Tunjukkan tabel recall per kelas B1–B4]**

> Sekarang kita masuk ke bagian paling penting: **bagaimana performa tiap kelas tandan?**
>
> Lihat tabel ini. Kolom B1 sampai B4 menunjukkan recall — persentase tandan yang berhasil dideteksi.
>
> Polanya sangat jelas: **makin muda tandannya, makin rendah recall-nya.**
>
> - **B1** (tandan matang): recall 70–80%. Sangat bagus. Warna oranye-merah TBS matang memang sangat khas dan mudah dikenali model.
> - **B2** (2 bulan): recall turun drastis ke 21–38%. Banyak B2 yang tertukar dengan B3 karena tingkat kematangannya berdekatan.
> - **B3** (3 bulan): recall 33–48%. Tandan setengah matang ini warnanya transisi — kadang kehijauan, kadang sedikit oranye — jadi ambigu.
> - **B4** (tandan muda): recall hanya 2–28%. Yang terbaik pun cuma mengenali 1 dari 4 tandan. Warna hijaunya menyatu dengan kanopi dan daun.
>
> **[Jeda sebentar]**
>
> Jadi kalau ditanya "apa tantangan terbesar model kita?" — jawabannya jelas: **B4 dan B2**.

---

## Slide 9 — Pola Kesalahan dari Confusion Matrix

**[Tunjukkan grid confusion matrix 2 kolom]**

> Mari kita lihat confusion matrix-nya secara visual.
>
> Yang perlu diperhatikan itu dua hal:
>
> **Pertama, diagonal** — makin gelap warnanya, makin bagus recall-nya. Lihat, B1 selalu paling gelap di diagonal. Bagus.
>
> **Kedua, baris "background" di paling bawah.** Ini menunjukkan berapa banyak tandan yang terlewat — diprediksi sebagai background alias tidak terdeteksi.
>
> Untuk model Combined dan DAMIMAS, B4 yang terlewat ke background itu 47–68%. Untuk LONSUM, bahkan sampai 85–87%. Hampir semua tandan muda tidak terdeteksi.
>
> Ada juga pola **B2 sering tertukar dengan B3** — ini terlihat dari sel di luar diagonal yang cukup terang antara kedua kelas itu.

---

## Slide 10 — Legacy vs v2: Head-to-Head

**[Tunjukkan tabel perbandingan Legacy vs v2]**

> Sekarang perbandingan langsung Legacy vs v2.
>
> Kalau kita bandingkan legacy terbaik — `legacy_yv9c_640` — dengan v2 terbaik — `combined_yv9c_123`:
>
> - mAP50: naik dari 0.483 ke 0.505. Peningkatan moderat.
> - mAP50-95: naik dari 0.161 ke 0.230. **Ini lonjakan 43 persen.** Bounding box v2 jauh lebih presisi.
> - B2 recall: naik 32% — dari 0.28 ke 0.37.
> - B4 recall: naik 50% — dari 0.16 ke 0.24.
>
> Tapi B1 recall sedikit turun dari 0.80 ke 0.78. Trade-off yang sangat kecil.
>
> **Kesimpulan: v2 menang di hampir semua aspek**, terutama pada presisi bounding box dan deteksi tandan yang lebih muda.

---

## Slide 11 — Kurva F1

**[Tunjukkan grid F1 curve 2 kolom]**

> Ini kurva F1 untuk semua model. Kurva F1 menunjukkan keseimbangan antara precision dan recall pada berbagai threshold confidence.
>
> Yang kita inginkan: puncak kurva yang tinggi dan lebar. Artinya model robust di berbagai threshold.
>
> Perhatikan model Combined dan DAMIMAS — puncaknya konsisten lebih tinggi. Sedangkan LONSUM, kurvanya rendah dan sempit. Model-model itu hanya bekerja di range confidence yang sangat terbatas.

---

## Slide 12 — Kurva PR

**[Tunjukkan grid PR curve 2 kolom]**

> Precision-Recall curve. Area di bawah kurva ini sama dengan mAP50.
>
> Tiap garis warna merepresentasikan satu kelas. Biasanya garis paling atas itu B1 — recall tinggi, precision juga lumayan. Garis paling bawah itu B4 — sangat rendah di kedua metrik.
>
> Untuk LONSUM, semua garis sangat dangkal. Ini konfirmasi lagi bahwa model LONSUM memang tidak mampu bekerja di dataset gabungan ini.

---

## Slide 13 — Visualisasi Prediksi

**[Tunjukkan grid prediksi batch & canvas per gambar]**

> Terakhir, visualisasi langsung. Ini gambar test yang diprediksi oleh semua model.
>
> **[Scroll ke canvas individual — sekarang 2 kolom HD]**
>
> Di canvas ini bisa dilihat side-by-side: Ground Truth di kiri atas, lalu prediksi tiap model. Sekarang sudah dalam format 2 kolom dan resolusi HD, jadi bisa dilihat dengan jelas detail bounding box dan label confidence-nya.
>
> Perhatikan:
>
> - Model Combined dan DAMIMAS v2: bounding box rapi, kebanyakan tandan B1 dan B3 terdeteksi
> - Model LONSUM: sangat sedikit box yang muncul — banyak tandan yang terlewat
> - Legacy: deteksinya ada, tapi box-nya kadang kurang pas ukurannya — sesuai dengan mAP50-95 yang rendah

---

## Slide 14 — Kesimpulan

**[Tunjukkan bagian kesimpulan]**

> Saya rangkum temuan utama:
>
> **Satu** — Model terbaik kita: `combined_yv9c_123` dan `damimas_yv9c_42`, keduanya mAP50 = 0.505. Rekomendasi untuk deployment.
>
> **Dua** — YOLOv9c secara konsisten lebih baik dari YOLO26L. Selisihnya 4–5 poin mAP50.
>
> **Tiga** — v2 signifikan lebih baik dari Legacy, terutama di presisi bounding box. Peningkatan 43% di mAP50-95.
>
> **Empat** — Data DAMIMAS sangat representatif. Model DAMIMAS-only setara dengan Combined. Sementara LONSUM punya domain gap yang besar.
>
> **Lima** — Hierarki kesulitan kelas: B1 paling mudah, B4 paling sulit. Tandan muda menjadi bottleneck utama. Recall B4 terbaik hanya 28%.

---

## Slide 15 — Rekomendasi & Penutup

**[Tunjukkan tabel rekomendasi]**

> Rekomendasi ke depan:
>
> **Prioritas tinggi:**
> - Pakai `combined_yv9c_123` atau `damimas_yv9c_42` untuk deployment
> - Fokus riset untuk meningkatkan deteksi B4 — tandan muda
>
> **Prioritas sedang:**
> - Perbaiki kemampuan membedakan B2 dan B3 yang sering tertukar
> - Coba augmentasi tambahan: mosaic, copy-paste, dan color jittering khusus untuk tandan muda
>
> **Prioritas rendah:**
> - Investigasi kenapa LONSUM gagal — apakah masalah kualitas data, jumlah data, atau memang beda domain
>
> **[Jeda]**
>
> Demikian presentasi saya. Terima kasih atas perhatiannya. Apakah ada pertanyaan?

---

## Tips Presentasi

- **Durasi estimasi:** 15–20 menit + 5–10 menit Q&A
- **Highlight utama:** Tekankan peningkatan v2 vs legacy (+43% mAP50-95) dan tantangan B4
- **Kalau ditanya "kenapa LONSUM jelek?"** — Jelaskan domain gap: beda lokasi, beda kondisi cahaya, beda angle kamera, distribusi data training tidak representatif untuk test set gabungan
- **Kalau ditanya "kenapa B4 sulit?"** — Warna hijau tandan muda menyatu dengan kanopi daun, kontras rendah, dan secara visual sangat mirip bagian vegetasi non-tandan
- **Kalau ditanya "next step?"** — Augmentasi targeted untuk B4, eksplorasi resolusi lebih tinggi, dan kemungkinan two-stage approach (deteksi dulu semua tandan, baru klasifikasi kematangan)
