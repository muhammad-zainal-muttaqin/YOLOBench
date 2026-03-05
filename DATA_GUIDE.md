# YOLOBench — Data Guide

> Panduan lengkap untuk menambah/mengupdate data di dashboard.
> Baca file ini **seluruhnya** sebelum mengubah data apapun.

---

## Instruksi untuk AI Assistant / Kontributor

Jika kamu adalah AI assistant (Claude, ChatGPT, Copilot, atau lainnya) atau kontributor baru:

1. **Baca seluruh file ini dulu** sebelum melakukan apapun.
2. **Baca `data/index.json`** — cek bulan yang sudah ada dan metadata saat ini.
3. **Baca `data/YYYY-MM.json` yang relevan** — cek event dan run terakhir, catat ID terakhir (`id` dan `run_id`).
4. **Ketika user memberikan data eksperimen baru**, analisis dulu:
   - Model apa? Dataset/scenario apa? Seed berapa? Generasi (legacy/v2)?
   - Apakah semua metrik lengkap (mAP50, mAP50-95, P, R per class, per split)?
   - Apakah ada split train, val, dan test?
   - Apakah scenario/model sudah ada di filter options HTML?
5. **Jika data tidak lengkap atau ada yang janggal — TANYA dulu, jangan asumsi:**
   - Metrik kurang? → Tanya nilainya.
   - Tidak jelas model/dataset/seed? → Minta klarifikasi.
   - Model atau dataset baru yang belum ada di filter? → Konfirmasi sebelum menambah.
   - Metrik terlihat aneh (misal mAP > 1.0 berarti dalam persen, perlu dibagi 100)? → Konfirmasi.
   - Data hanya untuk 1 split (misal cuma test)? → Tanya apakah train/val juga tersedia.
6. **Jika data sudah lengkap dan jelas**, lakukan update sesuai panduan "Cara Menambah Data" di bawah.
7. **Selalu jalankan `node scripts/update_inline.js`** setelah edit data.
8. **User berkomunikasi dalam Bahasa Indonesia** — respons dalam bahasa yang sama.

---

## Arsitektur Data

```
index.html                  ← Dashboard (all-in-one HTML+CSS+JS)
data/
├── index.json              ← Manifest: daftar bulan + metadata project
└── YYYY-MM.json            ← Data per bulan (events + runs + metrics)
scripts/
└── update_inline.js        ← Sync data JSON → inline fallback di index.html
```

Dashboard memuat data dengan 2 cara:
1. **Fetch** — `data/index.json` → lalu `data/YYYY-MM.json` per bulan (untuk deploy/server)
2. **Inline fallback** — `INLINE_MANIFEST` dan `window._INLINE_MONTHS` di dalam `index.html` (untuk buka via `file://`)

**Keduanya harus selalu sinkron.** Setelah edit file di `data/`, jalankan:
```bash
node scripts/update_inline.js
```

---

## File 1: `data/index.json` (Manifest)

```json
{
  "months": ["2026-03"],
  "meta": {
    "project_title": "YOLO Research Logbook",
    "subtitle": "Deskripsi singkat status project saat ini",
    "last_updated": "2026-03-04"
  },
  "rules": {
    "test_set": "shared test (v2)",
    "seeds": [42, 123]
  }
}
```

**Yang perlu diupdate saat ada data baru:**
- `meta.last_updated` → tanggal hari ini (ISO format)
- `meta.subtitle` → update jika progress berubah signifikan
- `months` → tambah entry baru jika bulan baru (e.g. `"2026-04"`)

---

## File 2: `data/YYYY-MM.json` (Data Bulanan)

Setiap file berisi array of events:

```json
{
  "events": [
    { /* event 1 */ },
    { /* event 2 */ }
  ]
}
```

---

## Schema: Event

Setiap event merepresentasikan **satu kegiatan/aktivitas** dalam satu hari.

```json
{
  "id": "e5",
  "date": "2026-03-05",
  "type": "training",
  "status": "Solved",
  "title": "Judul singkat kegiatan",
  "tags": ["v2", "YOLO26l", "all_data"],
  "notes_md": "Catatan dalam format markdown. Bisa multi-line.",
  "schedules": [
    { "text": "Deskripsi task", "done": true },
    { "text": "Task belum selesai", "done": false }
  ],
  "cross_test_summary": {
    "headline": "Ringkasan singkat hasil cross-test.",
    "highlights": ["Poin penting 1", "Poin penting 2"],
    "best_cases": [],
    "generalization_notes": [],
    "source_artifact": "cross_test_analysis.xlsx"
  },
  "runs": []
}
```

### Field Reference

| Field | Required | Nilai yang Valid | Keterangan |
|-------|----------|-----------------|------------|
| `id` | Ya | `"e1"`, `"e2"`, dst | Harus unik di seluruh file. Lanjutkan dari ID terakhir. |
| `date` | Ya | `"YYYY-MM-DD"` | Harus sesuai bulan file-nya. |
| `type` | Ya | `"training"`, `"evaluation"`, `"planning"`, `"discussion"`, `"dataset-prep"` | Harus cocok dengan opsi filter di HTML. |
| `status` | Ya | `"Plan"`, `"Progress"`, `"Solved"` | Case-sensitive (huruf pertama kapital). |
| `title` | Ya | String | Singkat, deskriptif. |
| `tags` | Ya | Array of string | Untuk filtering. Masukkan gen (`legacy`/`v2`), model, dataset. |
| `notes_md` | Ya | String (markdown) | Penjelasan detail. Gunakan `\n` untuk newline dalam JSON. **Dirender sebagai Markdown** (heading, tabel, bold, list, code block, gambar). Lihat [Panduan Markdown](#panduan-markdown-untuk-notes_md-dan-summary). |
| `schedules` | Opsional | Array of `{text, done}` | Checklist tasks. `done`: `true`/`false`. |
| `cross_test_summary` | Opsional | Object | Ringkasan analisis lintas-run/lintas-domain di level event. Cocok untuk workbook agregat seperti cross-test. |
| `runs` | Opsional | Array of Run objects | Bisa `[]` kosong untuk event tanpa eksperimen. |

### Contoh Event TANPA runs (meeting/planning):
```json
{
  "id": "e3",
  "date": "2026-03-03",
  "type": "discussion",
  "status": "Solved",
  "title": "Meeting: lock split strategy with lecturer",
  "tags": ["meeting", "policy", "split"],
  "notes_md": "Hasil meeting:\n- Tree-level split\n- 2 seeds (42, 123)\n- 2 models",
  "schedules": [
    { "text": "Lock split policy", "done": true },
    { "text": "Define scenarios", "done": true }
  ],
  "runs": []
}
```

### `cross_test_summary` dipakai kapan?

Gunakan field ini jika satu event punya **analisis agregat yang tidak cocok dimasukkan ke satu run**, misalnya:
- cross-test train-vs-test antar domain
- ranking model lintas beberapa run
- ringkasan dari workbook/Excel agregat

Struktur minimumnya:

```json
{
  "cross_test_summary": {
    "headline": "Kesimpulan 1 paragraf.",
    "highlights": [
      "Angka penting 1",
      "Angka penting 2"
    ],
    "best_cases": [
      {
        "label": "Best combined test",
        "model": "damimas_yv9c_42",
        "arch": "YOLOv9c",
        "train_set": "damimas",
        "test_set": "combined",
        "mAP50": 0.505,
        "mAP5095": 0.230
      }
    ],
    "generalization_notes": [
      "Catatan domain gap / stabilitas model"
    ],
    "source_artifact": "cross_test_analysis.xlsx"
  }
}
```

---

## Schema: Run

Setiap run merepresentasikan **satu eksperimen training/evaluation**.

```json
{
  "run_id": "exp10",
  "gen": "v2",
  "scenario": "all_data",
  "model": "YOLO26l",
  "seed": "42",
  "eval_set": "all_data/test (592 imgs)",
  "summary": "Deskripsi singkat hasil. Bisa mention highlights.",
  "splits": {
    "train": { /* split data */ },
    "val":   { /* split data */ },
    "test":  { /* split data */ }
  }
}
```

### Field Reference

| Field | Required | Nilai yang Valid | Keterangan |
|-------|----------|-----------------|------------|
| `run_id` | Ya | `"exp1"`, `"exp10"`, dst | Harus unik secara global. Lanjutkan dari terakhir. |
| `gen` | Ya | `"legacy"` atau `"v2"` | Generasi eksperimen. |
| `scenario` | Ya | `"stratifikasi"`, `"sawit-yolo"`, `"damimas-full"`, `"all_data"`, `"damimas_only"`, `"lonsum_only"` | Harus cocok dengan opsi filter Dataset di HTML. |
| `model` | Ya | `"YOLO26l"`, `"YOLOv9m"`, `"YOLOv9c"` | Harus cocok dengan opsi filter Model di HTML. |
| `seed` | Ya | `"42"`, `"123"`, atau `"-"` | String, bukan number. `"-"` jika tidak pakai seed. |
| `eval_set` | Ya | String | Deskripsi dataset yang dieval, misal `"all_data/test (592 imgs)"`. |
| `summary` | Ya | String | 1-2 kalimat ringkasan hasil. |
| `splits` | Ya | Object | Berisi `train`, `val`, `test`. Semua opsional tapi minimal `test` harus ada untuk tampil di leaderboard. |

### Dashboard menggunakan splits untuk:
- **Leaderboard & Detail panel** → mengambil dari `splits.test` (fallback ke `global_metrics` jika tidak ada)
- **Train–Val gap (overfit)** → ditampilkan jika `train` DAN `val` ada
- **Val–Test gap (leakage)** → ditampilkan jika `val` DAN `test` ada
- **Radar chart & overfit chart** → membandingkan train vs val vs test per class

---

## Schema: Split Data

Setiap split (`train`, `val`, `test`) punya struktur yang sama:

```json
{
  "images": 2504,
  "instances": 11200,
  "global": {
    "mAP50": 0.523,
    "mAP5095": 0.198,
    "P": 0.512,
    "R": 0.534
  },
  "classes": {
    "B1": {
      "images": 800,
      "instances": 1200,
      "P": 0.612,
      "R": 0.745,
      "mAP50": 0.721,
      "mAP5095": 0.301,
      "F1": 0.672
    },
    "B2": { /* sama */ },
    "B3": { /* sama */ },
    "B4": { /* sama */ }
  },
  "speed": {
    "preprocess": 0.5,
    "inference": 22.1,
    "postprocess": 0.8
  }
}
```

### Field Reference

| Field | Required | Tipe | Keterangan |
|-------|----------|------|------------|
| `images` | Ya | Integer | Jumlah gambar di split ini |
| `instances` | Ya | Integer | Jumlah total bounding box |
| `global` | Ya | Object | Metrik global (aggregated) |
| `global.mAP50` | Ya | Float 0-1 | Mean Average Precision @ IoU 0.50 |
| `global.mAP5095` | Ya | Float 0-1 | Mean Average Precision @ IoU 0.50:0.95 |
| `global.P` | Ya | Float 0-1 | Precision |
| `global.R` | Ya | Float 0-1 | Recall |
| `classes` | Ya | Object | Metrik per kelas (B1, B2, B3, B4) |
| `classes.XX.images` | Ya | Integer | Jumlah gambar yang mengandung kelas ini |
| `classes.XX.instances` | Ya | Integer | Jumlah instance kelas ini |
| `classes.XX.P` | Ya | Float 0-1 | Precision kelas |
| `classes.XX.R` | Ya | Float 0-1 | Recall kelas |
| `classes.XX.mAP50` | Ya | Float 0-1 | mAP@50 kelas |
| `classes.XX.mAP5095` | Ya | Float 0-1 | mAP@50-95 kelas |
| `classes.XX.F1` | Ya | Float 0-1 | F1-score kelas |
| `speed` | Opsional | Object | Kecepatan inferensi (ms) |
| `speed.preprocess` | Ya* | Float | Waktu preprocessing (ms) |
| `speed.inference` | Ya* | Float | Waktu inferensi (ms) |
| `speed.postprocess` | Ya* | Float | Waktu postprocessing (ms) |

> Semua metrik dalam skala 0-1 (bukan persen). Dashboard akan mengalikan ×100 saat ditampilkan.

---

## Cara: Menambah Eksperimen Baru ke Bulan yang Sudah Ada

**Skenario:** User memberikan hasil training baru, misal v2 experiments.

### Langkah-langkah:

1. **Tentukan event** — Apakah ini masuk event yang sudah ada, atau event baru?
   - Jika training di hari yang sama dengan tema sama → tambah run ke event yang ada
   - Jika kegiatan baru (hari baru/tema beda) → buat event baru

2. **Buka `data/YYYY-MM.json`**

3. **Tambah event/run** — Pastikan:
   - `id` event lanjutan dari terakhir (cek yang sudah ada, e.g. `e4` → next `e5`)
   - `run_id` lanjutan dari terakhir (cek yang sudah ada, e.g. `exp9` → next `exp10`)
   - Semua field wajib terisi
   - Nilai `scenario`, `model`, `type` harus cocok dengan opsi di HTML

4. **Update `data/index.json`**:
   - `meta.last_updated` → tanggal hari ini

5. **Sync inline data**:
   ```bash
   node scripts/update_inline.js
   ```

6. **Jika ada dataset/model/type BARU** yang belum ada di filter:
   - Edit `index.html` lines ~99-105, tambah `<option>` baru ke `<select>` yang sesuai

---

## Cara: Menambah Bulan Baru

1. **Buat file** `data/YYYY-MM.json`:
   ```json
   {
     "events": []
   }
   ```

2. **Update `data/index.json`**:
   - Tambah `"YYYY-MM"` ke array `months`
   - Update `meta.last_updated`

3. **Isi events dan runs** sesuai schema di atas

4. **Sync inline data**:
   ```bash
   node scripts/update_inline.js
   ```

---

## Cara: Mengubah Status Event

Jika eksperimen yang tadinya `"Progress"` sudah selesai:
1. Ubah `"status": "Solved"`
2. Update `schedules` → set semua `"done": true`
3. Tambahkan `runs` dengan hasil metriknya
4. Jalankan `node scripts/update_inline.js`

---

## Data yang Biasa Diberikan User

User biasanya memberikan data dalam bentuk:
- Screenshot hasil YOLO training (tabel metrics)
- Copy-paste dari terminal/console output
- File CSV/text hasil evaluasi

### Dari output YOLO, yang perlu diekstrak:
- **Global metrics**: mAP50, mAP50-95, Precision, Recall (baris `all`)
- **Per-class metrics**: sama, untuk setiap kelas (B1, B2, B3, B4)
- **Images & instances**: jumlah per split dan per class
- **Speed**: preprocess, inference, postprocess (ms)
- **Info run**: model apa, dataset apa, seed berapa, split apa (train/val/test)

### Contoh output YOLO yang umum:
```
                 Class     Images  Instances      P      R  mAP50  mAP50-95
                   all        592       2656  0.523  0.534  0.523    0.198
                    B1        200        338  0.612  0.745  0.721    0.301
                    B2        250        650  0.489  0.425  0.463    0.170
                    B3        350       1201  0.501  0.530  0.470    0.161
                    B4        180        467  0.322  0.267  0.206    0.062
Speed: 0.5ms preprocess, 22.1ms inference, 0.8ms postprocess
```

Map baris `all` → `global`, baris per-class → `classes.XX`. Hitung F1 = 2*P*R/(P+R).

---

## Analisis & Insight Wajib

Setiap kali data eksperimen baru ditambahkan, **wajib** menyertakan analisis mendalam:

### Event `notes_md` harus berisi:
1. **Ringkasan temuan utama** — apa yang dipelajari dari batch eksperimen ini
2. **Perbandingan dengan eksperimen sebelumnya** — bandingkan dengan run legacy/v2 yang sudah ada. Jika ada cross-evaluation (model ditest pada test set berbeda), buat tabel perbandingan
3. **Dekomposisi gap** — jika ada perbedaan performa yang signifikan, jelaskan faktor penyebabnya (leakage, domain shift, data size, dsb.) beserta kontribusi masing-masing
4. **Insight per-class** — kelas mana yang paling bagus/buruk dan kenapa
5. **Kesimpulan & rekomendasi** — apa langkah selanjutnya, apa yang perlu diperbaiki

### Run `summary` harus berisi:
1. **Info training** — trained on apa, berapa data
2. **Skor utama** — mAP50 dan mAP50-95 pada test set
3. **Cross-evaluation** — jika tersedia, skor pada test set lain (misal legacy vs v2) dan delta-nya
4. **Perbandingan langsung** — bandingkan dengan run serupa (seed lain, model lain, legacy equivalent)
5. **Highlight spesifik** — apa yang unik dari run ini (best/worst, anomali, temuan menarik)

### Contoh summary yang BAIK:
```
"YOLOv9c seed42 trained on damimas_only. BEST V2 MODEL: mAP50=0.505, mAP50-95=0.230.
Cross-eval: 0.599 on legacy damimas-only test. Beats legacy yv9c_640 on combined test
(0.505 vs 0.483). mAP50-95 jauh lebih baik (0.230 vs 0.161) — localization quality superior."
```

### Contoh summary yang BURUK (jangan seperti ini):
```
"YOLOv9c seed42 on damimas. mAP50=0.505."
```

---

## Panduan Markdown untuk `notes_md` dan `summary`

Dashboard merender `notes_md` (event) dan `summary` (run) sebagai **GitHub-Flavored Markdown** menggunakan [marked.js](https://github.com/markedjs/marked). Fitur yang didukung:

- **Heading**: `## Heading 2`, `### Heading 3`
- **Tabel**: sintaks GFM standar (`| col1 | col2 |`)
- **Bold/italic**: `**bold**`, `*italic*`
- **List**: `- item` atau `1. item`
- **Code block**: `` ``` `` fenced code blocks
- **Inline code**: `` `code` ``
- **Gambar**: `![alt](path/to/image.png)` — gambar di repo otomatis served oleh Cloudflare Pages
- **Blockquote**: `> quote`

### Catatan khusus:
- **Tilde `~` aman digunakan** — strikethrough (`~~text~~`) dinonaktifkan di dashboard karena kita sering pakai `~` untuk nilai perkiraan (e.g. `~50%`). Semua `~` ditampilkan apa adanya.
- Gunakan `\n` untuk newline di dalam string JSON.
- Untuk tabel di JSON, pastikan separator (`|---|---|`) ada di baris sendiri.

---

## Bahasa Dashboard

UI dashboard menggunakan **Bahasa Indonesia**. Ketika menulis `notes_md` dan `summary`:
- Boleh menggunakan Bahasa Indonesia atau Inggris (atau campuran)
- Istilah teknis, nama model, nama dataset tetap dalam bahasa asli (e.g. mAP50, YOLO26l, damimas_only, tree-level split, leakage)

---

## Catatan Penting

1. **ID harus unik dan sequential** — Cek ID terakhir sebelum menambah.
2. **Semua metrik skala 0-1** — Jika user memberikan dalam persen, bagi 100.
3. **F1 tidak ada di output YOLO** — Hitung manual: `F1 = 2 * P * R / (P + R)`.
4. **`seed` adalah string** — Tulis `"42"` bukan `42`.
5. **Selalu jalankan `update_inline.js`** setelah edit data — Agar offline mode tetap kerja.
6. **Jangan lupa update `last_updated`** di manifest.
7. **Validasi JSON** — Pastikan tidak ada trailing comma atau syntax error.
8. **Markdown dirender** — `notes_md` dan `summary` ditampilkan sebagai rendered Markdown, bukan raw text. Tulis dengan format yang rapi.
