# Pitch Canvas — KerjaCerdas · booth Jakarta (1 halaman)

**Cara pakai:** salin **seluruh isi antara dua garis `═══`** ke Claude design. Bagian setelahnya
(§Bekal Presenter) **tidak ikut disalin** — itu amunisi tanya-jawab untuk tim.

**Aturan yang dipegang dokumen ini:** tiap angka di slide bisa ditunjukkan sumbernya — dari kode,
dari `/admin → Metrik`, atau dari sumber publik. Yang belum ada buktinya **ditulis apa adanya di
slide**, tidak disembunyikan. Juri Digdaya menjatuhkan nilai kami justru pada klaim tanpa bukti.

---

═══════════════════ SALIN MULAI DARI SINI ═══════════════════

# BRIEF: One-page Pitch Canvas — KerjaCerdas

Build a **single-page pitch canvas** for an Indonesian AI job-matching startup, to be projected at
a 3-day innovation-festival booth **and** printed as a standing poster. Follow the layout, palette
and typography below exactly — they are the product's real design system, so the canvas must look
like it came from the same hand as the app.

## Canvas & grid

- **Artboard:** 1920 × 1080 px (16:9). Must also hold up printed at A2 — nothing below 14 px.
- **Outer margin:** 56 px. **Gutter between boxes:** 20 px.
- **Structure:** a full-width banner, then a **12-column grid** in four rows:

```
┌──────────────────────────────────────────────────────────────────────┐
│  BANNER · Simple Statement                              (12 cols)    │
├───────────────────────────┬──────────────────────────────────────────┤
│  PAIN + GAIN      (5)     │  PRODUCT                        (7)      │
├───────────────────────────┼──────────────────────────────────────────┤
│  HOW IT WORKS     (7)     │  WHAT'S UNIQUE                  (5)      │
├───────────┬───────────────┼──────────────────┬───────────────────────┤
│ TRACTION  │ BUSINESS      │  INVESTMENT      │  TEAM                 │
│   (3)     │  MODEL  (3)   │      (3)         │    (3)                │
├───────────┴───────────────┴──────────────────┴───────────────────────┤
│  CALL TO ACTION + WHY US                                (12 cols)    │
└──────────────────────────────────────────────────────────────────────┘
```

- Every box is a card: **fill `#FFFFFF`**, **border `1.5px solid #090A0F`**, **radius 12 px**,
  **hard offset shadow `4px 4px 0 #090A0F`** — no blur, no gradient.
- Page background: **`#FAF9F5`** (warm bone, not white). Card padding: 24 px.

## Palette — use only these

| Token | Hex | Use |
|---|---|---|
| Ink | `#090A0F` | borders, shadows, headings, body |
| Bone | `#FAF9F5` | page background |
| Paper | `#FFFFFF` | card fill |
| **Orange** | `#FF4800` | **the one accent** — banner, key numbers, CTA |
| Lime | `#10B981` | "proven / verified" states only |
| Cyan | `#0284C7` | neutral data accent |
| Yellow | `#F59E0B` | honest-gap markers |
| Mute | `#64748B` | captions, secondary text |
| Ash | `#E2E8F0` | bar tracks, dividers |

Orange is load-bearing: **at most 5 orange elements on the whole page**. If everything is orange,
nothing is.

## Typography

- **Headings & body:** `Plus Jakarta Sans` — 900 headings, 700 sub-heads, 400–500 body.
- **Numbers, code, micro-labels:** `JetBrains Mono` — 700, uppercase, letter-spacing 0.4 px.

| Role | Size / weight |
|---|---|
| Banner statement | 46 px / 900, leading 1.1, letter-spacing −1 px |
| Box title | 22 px / 900 |
| Micro-label above box title | 11 px / 700 mono, uppercase, Mute |
| Body & bullets | 16 px / 400, leading 1.45 |
| Big stat number | 40 px / 900 (mono) |
| Stat caption | 12 px / 500, Mute |
| Footnote / source | 12 px / 400 italic, Mute |

## Visual elements to include

1. **Formula strip** in PRODUCT — a 100% stacked horizontal bar split `35 / 40 / 15 / 10`, each
   segment labelled. Segment 2 (40, skill) filled **Orange**; the rest **Ash** with ink outlines.
   This is the most important graphic on the page.
2. **Proof ladder** in HOW IT WORKS — three chips with arrows:
   `Klaim 0.30` (Ash) → `✓ Kuis 0.85` (Lime) → `✓✓ HR 1.00` (Ink fill, white text).
3. **Three numbered steps** in HOW IT WORKS — circles `1 2 3`, ink outline, orange numerals.
4. **QR glyph** — a small stylised QR square in PRODUCT. Decorative; do **not** encode a real URL.
5. **Honesty pills** — small yellow-bordered pills reading `BELUM ADA` / `RENCANA`. These are a
   deliberate feature, not an error. Legible, not apologetic.
6. **Icons:** thin-line, 2 px stroke, ink only (Lucide style). No filled or coloured icons.

## Do / Don't

- ✅ Flat, high-contrast, confident. Generous white space. Left-align everything. One idea per bullet.
- ❌ No gradients, no shadow blur, no glassmorphism, no stock photos, no 3D, no emoji.
- ❌ Do not invent numbers, logos, or customer names. Use only what is written below.

---

# CONTENT — place verbatim

## ▸ BANNER · Simple Statement

**CV bisa ditulis siapa saja.
Kami membuat skill harus dibuktikan — lalu mengurutkan pelamar berdasarkan bukti itu.**

Sub-line (18 px, Mute):
*Pencocokan kerja berbasis AI untuk UMKM Indonesia dan pencari kerja 18–25 tahun.*

## ▸ PAIN + GAIN

**Micro-label:** MASALAH

**Bagi UMKM yang merekrut hari ini**
- Pasang "kirim CV ke WA" → puluhan PDF masuk, tidak terurut.
- Banyak CV mengklaim skill yang tidak dikuasai. CV buatan AI memperparah.
- Akibatnya: **jam kerja pemilik usaha habis mewawancarai orang yang salah.**

**Bagi pencari kerja**
- Melamar puluhan kali, tidak dapat kabar, tidak tahu apa yang kurang.

**Dua stat berdampingan:**
- `89.141` — usaha kecil & menengah terdaftar · *SIDT-UMKM, Des 2025*
- `7,24 jt` — penganggur terbuka · *BPS, Feb 2026*

## ▸ PRODUCT

**Micro-label:** PRODUK

**Satu daftar pelamar yang sudah diurutkan — dan skill-nya sudah diuji.**

- **Employer:** pasang lowongan → dapat **link + poster QR** → tempel di Instagram / grup WA yang
  sudah dipakai → pelamar masuk ke satu daftar terperingkat.
- **Pencari kerja:** scan QR → daftar via email → isi profil atau unggah CV → **ikut kuis skill
  5 soal** → lamar. Badge berlaku **180 hari di semua lowongan.**

**Formula strip** (stacked bar 35 / 40 / 15 / 10):

```
35% kemiripan CV–lowongan │ 40% SKILL YANG DIBUKTIKAN │ 15% pengalaman │ 10% pendidikan
```

Caption (12 px, Mute):
*Bobot bukti sengaja lebih besar dari kemiripan teks — karena kemiripan teks justru naik kalau CV
menyalin kalimat iklan.*

## ▸ HOW IT WORKS

**Micro-label:** CARA KERJA

**Proof ladder:**
`Klaim CV 0.30` → `✓ Lulus kuis 0.85` → `✓✓ Dikonfirmasi HR 1.00`

**Tiga langkah bernomor:**
1. **Kuis 5 soal skenario**, ±3 menit. Dinilai server pakai kunci jawaban — **tanpa panggilan AI,
   Rp0 per percobaan.** Lulus 4/5 → badge ✓ Terbukti.
2. **HR wawancara**, lalu mencentang *skill terbukti* → bukti terkuat, bobot 1.00.
3. **Skor dihitung ulang** tiap daftar dibuka — pelamar yang baru lulus kuis langsung naik.

**Penjaga lowongan (AutoMod):** iklan yang menarik biaya dari pelamar **ditolak otomatis**; syarat
diskriminatif ditahan untuk tinjauan. Pemasang dapat notifikasi berisi kalimat mana yang bermasalah
dan cara memperbaikinya. Pelanggaran berulang → peringatan → dibatasi → ditangguhkan.

**Data pribadi:** kami **tidak mengumpulkan NIK, KTP, ijazah, atau NPWP.** Verifikasi hanya email.
Nomor dan email di CV disamarkan otomatis sebelum teks dikirim ke AI.

## ▸ WHAT'S UNIQUE

**Micro-label:** KENAPA SULIT DITIRU

1. **Profil terbukti hanya ada di sini.** Peniru mulai dari nol kandidat terbukti. Fitur bisa
   disalin sebulan; kumpulan bukti tidak.
2. **QR tiap employer membawa pelamar baru** yang ikut dicocokkan ke lowongan lain — tumbuh dari
   pemakaian, bukan iklan.
3. **Model kami bertentangan dengan job board.** Mereka untung dari *banyak* lamaran; kami menang
   dengan mengirim *lebih sedikit tapi tepat*.

Kutipan penutup (italic, 15 px):
*"Fiturnya bisa ditiru. Profil yang sudah terbukti dan kepercayaan HR tidak bisa disalin."*

## ▸ TRACTION

**Micro-label:** BUKTI — APA ADANYA

| | |
|---|---|
| Prototipe jalan & teruji otomatis | ✅ |
| Alignment PS-2 (penilaian juri) | ✅ **Sangat Kuat** |
| Kualitas prototipe (penilaian juri) | ✅ **Sangat Kuat** |
| Perusahaan membayar | `BELUM ADA` |
| Validitas prediktif skor | `BELUM DIUJI` |

Catatan (12 px, Mute):
*Mesin pengukurnya sudah jalan: skor + bukti disimpan saat melamar, tiap perubahan status dicatat,
dan dashboard admin menghitung tingkat wawancara per band skor. Datanya yang belum ada — dan layar
kami menulis "belum ada data", bukan 0%.*

## ▸ BUSINESS MODEL

**Micro-label:** MODEL BISNIS

**Employer bayar untuk menyaring, bukan untuk mencari.**

| Paket | Harga |
|---|---|
| **Spark** | **Rp0** · 1 lowongan, 20 pelamar skor tertinggi |
| **Beacon** | **Rp29.000** / lowongan |
| **Lighthouse** | **Rp99.000** / bulan |
| **Prism** (pencari kerja) | **Rp25.000** / 30 hari |

**Stat besar:** `88%` — margin kotor per Beacon
*Caption:* biaya AI dihitung dari token asli. Kuis dan skor **tidak memanggil AI sama sekali.*

Garis tebal (15 px, Ink):
**Membayar tidak pernah menaikkan skor atau peringkat siapa pun.**

Footnote: *Pembayaran saat ini QRIS / transfer yang dikonfirmasi admin.* `RENCANA: payment gateway`

## ▸ INVESTMENT

**Micro-label:** PENDANAAN

**Stat besar:** `Rp200 jt` untuk **10%**
*Caption:* dua tahap — Rp100 jt saat tanda tangan, Rp100 jt di bulan ke-6 bila target tercapai.

**Dipakai untuk:**
- Pendirian & legal — 22%
- Menutup rugi sampai impas — 29%
- Akuisisi employer & pencari kerja — 20%
- Keamanan + gateway — 6%
- Bantalan skenario buruk — 23%

**Tiga angka berjajar:**
`Bulan 15` impas · `Rp101 jt` kas terdalam · `Rp360 jt` pendapatan Tahun 2

## ▸ TEAM

**Micro-label:** TIM

- **David** — AI / Backend · mesin pencocokan, bobot bukti, AutoMod
- **Darren** — Product / UX · alur seeker–employer, desain sistem
- **Vanessa** — Systems / Impact · data hasil, metrik dampak
- **Jason** — Business / Deployment · model bisnis, harga, pilot

Kalimat pembeda (italic, 14 px):
*Kami memperbaiki produk berdasarkan kritik, bukan membela slide: model Pay-to-Unlock, e-KYC NIK,
dan klaim "94% akurasi" semuanya kami hapus karena tidak bisa kami buktikan.*

## ▸ CALL TO ACTION + WHY US

**Micro-label:** LANGKAH BERIKUTNYA

**Tiga ajakan berdampingan, tiap satu dalam kotak sendiri:**

| Untuk UMKM / HR | Untuk pencari kerja | Untuk investor / offtaker |
|---|---|---|
| **Pasang 1 lowongan sekarang — gratis. Poster QR-nya kami cetakkan hari ini.** | **Scan, ikut 1 kuis 3 menit, bawa pulang badge ✓ Terbukti.** | **Beri kami 30 hari dan 10 UMKM pilot. Lalu kita baca bersama tingkat wawancara per band skor di dashboard yang sama.** |

**Target terukur 3 hari booth** (mono, 14 px):
`15` UMKM pasang lowongan · `100` pencari kerja selesai ≥1 kuis · `3` surat minat bayar Beacon

**Penutup — banner orange, teks putih, 30 px / 900:**
**"Pasar kerja Indonesia tidak kekurangan lamaran. Yang kurang adalah bukti.
Kami membangun tempat bukti itu disimpan."**

═══════════════════ SALIN SAMPAI SINI ═══════════════════

---

# Bekal Presenter — JANGAN ditaruh di slide

Setiap jawaban di bawah **sudah benar terhadap kode hari ini**. Jangan improvisasi angka baru.

### Pertanyaan yang dulu tidak terjawab

| Pertanyaan | Jawaban yang benar |
|---|---|
| *"CV bisa direkayasa, bagaimana verifikasinya?"* | Skill yang hanya ditulis di CV bernilai **0.30**; lulus kuis **0.85**; dikonfirmasi HR **1.00**. Karena bobot bukti (0.40) **lebih besar** dari kemiripan teks (0.35), menyalin kalimat iklan tidak lagi cukup untuk menang. |
| *"Ada mekanisme ban / turun peringkat?"* | Ada dan sudah jalan: AutoMod menolak/menahan sebelum tayang, pemasang dapat notifikasi + bisa banding, kandidat bisa melapor, dan strike 1→2→3 membatasi lalu menangguhkan akun. |
| *"Redaksional berbasis prompt bisa gagal?"* | Karena itu penyamaran data pribadi **tidak** memakai instruksi ke AI — memakai aturan regex tetap sebelum tiap panggilan AI. NIK bahkan tidak dikumpulkan sama sekali. |
| *"Skor tinggi benar lolos interview?"* | Mekanismenya sudah dibangun — skor + bukti disimpan saat melamar, status dicatat, dashboard menghitung tingkat wawancara per band. **Datanya belum ada, dan kami tidak akan mengarang.** Itu yang kami minta 30 hari pilot untuk dapatkan. |
| *"Kenapa tidak mudah ditiru?"* | Bukan closed loop dan bukan fine-tuning — keduanya bisa ditiru. Yang tidak bisa disalin adalah kumpulan profil yang sudah terbukti di platform kami. |
| *"Dari mana lowongan pertama?"* | Pasang gratis, dan employer membagikan QR di kanal yang **sudah** mereka pakai. Kami tidak meminta mereka pindah kanal — hanya lamarannya yang pindah tempat. |

### Lubang yang kami akui — jawab persis begini

| Kalau ditanya | Jawab |
|---|---|
| Sudah ada yang bayar? | **Belum satu pun.** Target booth ini: 3 surat minat. |
| Bank soalnya berapa? | **8 skill × 6 soal, masih draf AI**, sedang diperluas ke ~20 per skill dengan tinjauan praktisi HR. Kuis menyaring; wawancara memastikan. |
| Kuis bisa dicontek? | Bisa. Karena itu ada timer per soal, soal acak, dan **HR tetap penentu akhir** lewat centang "skill terbukti". Kami tidak mengklaim kuis anti-curang. |
| Payment gateway? | Belum. Sekarang QRIS/transfer dikonfirmasi admin. Midtrans/Xendit biaya setup Rp0, jadi bukan penghalang — menunggu PT. |
| Validasi penggunanya berapa? | Di bawah 10 orang dan belum terdokumentasi rapi. Itu kelemahan yang sedang kami tutup dengan paket bukti loop dampak. |
| Kualitas kode? | Unit test, lint backend, dan build frontend **menggugurkan** build kalau merah. Integration test (migrasi ke PostgreSQL asli) berjalan tapi **non-gating** — dan justru itu yang menemukan dua tabel yang tidak pernah dibuat migrasi mana pun. ESLint frontend **belum** dikonfigurasi. |

### Angka yang boleh disebut, dan sumbernya

| Angka | Sumber |
|---|---|
| 35 / 40 / 15 / 10 | `matcher.py` — `_W_COSINE` / `_W_SKILL` / `_W_EXPERIENCE` / `_W_EDUCATION` |
| 0.30 / 0.85 / 1.00 | `evidence.py` — `PROOF_WEIGHTS` |
| Rp0 per percobaan kuis | dinilai dengan kunci jawaban, tanpa panggilan AI |
| Margin 88% / 90% / 69% | `BUSINESS_MODEL.md` — biaya AI dari token asli × harga Gemini × kurs Rp17.600 |
| Bulan 15 · Rp101 jt · Rp360 jt | proyeksi skenario dasar, `BUSINESS_MODEL.md` |
| 89.141 · 7,24 jt | SIDT-UMKM Des 2025 · BPS Feb 2026 |
| Spark 20 pelamar | **skor tertinggi**, bukan yang pertama melamar |

> **Aturan tunggal di booth:** kalau sebuah angka tidak ada di tabel ini, **jangan sebut**.
> Katakan "belum kami ukur" — itu jawaban yang menang, bukan yang kalah.
