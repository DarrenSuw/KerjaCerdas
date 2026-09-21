# Pitch Canvas — KerjaCerdas (1 halaman)

**Cara pakai:** salin **seluruh isi antara dua garis `═══`** ke Claude design. Bagian setelahnya
(§Bekal Presenter) **tidak ikut disalin** — itu amunisi tanya-jawab untuk tim.

**Aturan yang dipegang dokumen ini:** tiap angka di slide bisa ditunjukkan sumbernya — dari kode,
dari `/admin → Metrik`, atau dari sumber publik. Yang belum ada buktinya **ditulis apa adanya di
slide**, tidak disembunyikan. Juri Digdaya menjatuhkan nilai kami justru pada klaim tanpa bukti.

**Catatan revisi:** versi sebelumnya mengunci desainer ke 11 kotak identik dan menaruh argumen
terkuat kami sebagai paragraf. Brief ini membalik itu: **angka jadi grafik, hierarki jadi nyata,
dan desainer diberi ruang** — yang tetap dikunci hanya fakta, bukan estetika.

---

═══════════════════ SALIN MULAI DARI SINI ═══════════════════

# BRIEF: One-page Pitch Canvas — KerjaCerdas

Design a **single-page pitch canvas** for an Indonesian AI job-matching startup, projected at an
innovation-festival booth and printed as a standing poster.

**Read this first — it is the brief's one real instruction:**

> This page must argue, not list. Its job is to prove one counter-intuitive claim — *a candidate
> who proves a skill outranks a candidate who merely writes it, even when the liar's CV matches
> the job posting better* — and every other element exists to support that. A reader standing 2 m
> away for 5 seconds should get that claim from **the charts alone**, before reading a word.
>
> The failure mode to avoid: a uniform grid of equal cards where every box is the same size,
> weight and colour, and all the evidence is bullet points. That page is skimmed and forgotten.

## How to treat this brief

- **Locked (never change):** every number, label and Indonesian sentence in §CONTENT, the honesty
  markers, and the source footnotes. Do not invent figures, logos, customers or testimonials.
- **Yours to decide:** composition, proportion, chart styling, rhythm, ornament, which blocks earn
  more space, and how to make the page feel alive. You are the designer. Use that.

If a locked sentence genuinely will not fit, **shrink the type, not the truth** — and keep the
honesty markers at full legibility even if a boast has to get smaller.

## Canvas

- **Artboard:** 1920 × 1080 px (16:9), also readable printed at A2 — nothing below 13 px.
- **Outer margin:** 48–64 px, your call. Background **`#FAF9F5`** (warm bone).

**Hierarchy is mandatory; the exact layout is not.** Compose in three tiers of clearly unequal
weight:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  TIER 1 — HERO. Full-bleed, dark (Ink) band. ~32–38% of page height.     │
│  The headline claim + V1 (the head-to-head chart). This block must       │
│  read first and look unlike anything else on the page.                   │
├──────────────────────────────────────────────────────────────────────────┤
│  TIER 2 — MECHANISM. How the claim is enforced.                          │
│  MASALAH · PRODUK (formula) · CARA KERJA (proof ladder, steps, AutoMod)  │
│  · KENAPA SULIT DITIRU. Cards here are the "normal" weight.              │
├──────────────────────────────────────────────────────────────────────────┤
│  TIER 3 — BUSINESS & HONESTY. Lower visual weight, denser.               │
│  BUKTI APA ADANYA · MODEL BISNIS · PENDANAAN · TIM · AJAKAN              │
└──────────────────────────────────────────────────────────────────────────┘
```

Within a tier, **vary the card sizes** by importance. PRODUK should be visibly larger than TIM.
A 12-column grid underneath is a good idea; a page where every cell is the same size is not.

## Palette

| Token | Hex | Use |
|---|---|---|
| Ink | `#090A0F` | borders, shadows, headings, the hero band |
| Bone | `#FAF9F5` | page background |
| Paper | `#FFFFFF` | card fill |
| Orange | `#FF4800` | the brand accent — the claim, the 40% weight, the CTA |
| Lime | `#10B981` | proven / verified |
| Cyan | `#0284C7` | neutral data series |
| Yellow | `#F59E0B` | honest-gap markers |
| Violet | `#7C3AED` | a fourth data series when a chart needs one |
| Mute | `#64748B` | captions, secondary text |
| Ash | `#E2E8F0` | bar tracks, dividers, dot grids |

**Colour rule — this replaces the old "max 5 orange elements" cap, which drained the page:**

- Orange means *"this is the argument"*. Roughly **6–10 orange moments**, and they should all be
  on the same idea: the claim, the 40% proof weight, the winning bar, the CTA.
- Lime is reserved for **proven** states — never decorative. Yellow only marks **gaps we admit**.
- Cyan and Violet are free for chart series; charts may be as colourful as the data needs.
- Inside the Ink hero band, invert: Paper text on Ink, with Orange and Lime doing the work.

## Texture & depth — allowed, and wanted

The old brief banned everything and got a flat grey page. Instead:

- ✅ Hard offset shadows `4px 4px 0 #090A0F` on Tier 2 cards. Keep it, it is the house style.
- ✅ **Ash dot-grid or hairline-rule texture** behind the hero band or under a chart.
- ✅ Oversized, cropped, low-opacity numerals or glyphs bleeding off a card edge as ornament.
- ✅ Thin-line icons (2 px, Lucide style), and one or two **large** line illustrations if they earn
  their space — a QR-to-phone-to-ranked-list motif, for instance.
- ✅ Diagonal ink hatching to mark "not yet measured" areas of a chart.
- ❌ Still no: gradients as fills, blur, glassmorphism, 3D renders, stock photos, emoji.

## Typography

- **Headings & body:** `Plus Jakarta Sans` — 900 headings, 700 sub-heads, 400–500 body.
- **Numbers, axes, micro-labels:** `JetBrains Mono` — 700, uppercase, letter-spacing 0.4 px.

Suggested scale (adjust for balance): hero claim 52–60 / 900, leading 1.05, tracking −1.5 px ·
box title 22 / 900 · micro-label 11 / 700 mono · body 15–16 / 400, leading 1.45 · big stat
40–48 / 900 mono · axis & caption 11–12 / 500 Mute.

**Set the hero claim as large as it can go without crowding V1.** It is the page's thesis.

---

# THE ELEVEN VISUALS — this is the heart of the brief

Data goes in charts. Prose is the fallback, not the default. Every figure below is real and
sourced; use them exactly.

### V1 — Head-to-head score bars · HERO · the most important graphic on the page

Two horizontal stacked bars on a shared 0 → 1.0 axis, comparing two candidates for the same job.
Both have identical experience and education; only cosine and proof differ.

| Candidate | cosine | proof | **total** |
|---|---|---|---|
| **"CV disalin dari iklan lowongan"** — keyword stuffer, claimed skills only | 0.90 | 0.30 | **0.685** |
| **"Skill dibuktikan lewat kuis"** — modest CV match, quiz-proven | 0.50 | 0.85 | **0.765** |

Segment the bars by the four weights so the reader sees *where* the win comes from: the loser's
bar is long on the cosine segment, the winner's is long on the proof segment. **Proof segment in
Orange; winner's total called out in Orange; loser's bar in Ash/Mute.** Do not draw the loser as
a villain — draw it as a bar that simply ends sooner.

**Kicker callout beside the chart** (this is the line that wins the argument):

> Bahkan pada kemiripan teks **sempurna 1.00**, CV yang hanya mengklaim skill berhenti di
> **0.720** — masih di bawah **0.765** milik kandidat terbukti yang kemiripan teksnya cuma 0.50.
> Menyalin kalimat iklan tidak bisa lagi mengejar bukti.

### V2 — Weight strip (in PRODUK)

100% stacked horizontal bar, `35 / 40 / 15 / 10`, each segment labelled with its percentage and
name. **Segment 2 (40%, skill terbukti) Orange and visually raised** — a taller segment, a notch,
or an outlined lift. Others Ash with ink outlines. This is V1's explanation, so place it where the
eye travels after the hero.

### V3 — Proof staircase (in CARA KERJA)

Three ascending bars whose **heights are proportional to the real weights** — not three equal
chips. `Klaim CV 0.30` (Ash) → `✓ Lulus kuis 0.85` (Lime) → `✓✓ Dikonfirmasi HR 1.00` (Ink fill,
Paper text). Print the weight inside or under each step.

### V4 — Band ruler (small, under V1 or V2)

A 0 → 1.0 axis with the two live thresholds marked: `possible ≥ 0.45`, `strong ≥ 0.65`. Plot both
V1 candidates on it. Honest and worth showing: **the stuffer still lands in "strong"** — the
system does not ban him, it simply ranks him below someone with proof. Label that plainly; a judge
who spots it unaided will trust the rest of the page less.

### V5 — Market scale (in MASALAH)

`89.141` UMKM terdaftar (*SIDT-UMKM, Des 2025*) and `7,24 jt` penganggur terbuka (*BPS, Feb 2026*)
as two icon-array / dot-grid figures. **Do not draw them as a ratio or a single shared scale** —
they are different units (businesses vs people) and implying a ratio would be a fabricated claim.
Two separate visuals, side by side.

### V6 — Journey flow (in PRODUK or CARA KERJA)

A left-to-right flow with a QR code as the entry point:

`Employer pasang lowongan` → `link + poster QR` → `ditempel di IG / grup WA yang sudah dipakai` →
`pelamar scan → daftar via email → kuis 5 soal` → `satu daftar terperingkat`

Numbered nodes, thin-line connectors. The QR may be a stylised glyph — **do not encode a real URL.**

### V7 — Margin curve (in MODEL BISNIS) · currently our best unused chart

A two-line chart, x = applicants per job (30 / 100 / 200), y = gross margin %.

| Applicants | Kolam kandidat masih baru | Kolam kandidat matang |
|---|---|---|
| 30 | 88% | — |
| 100 | 70% | — |
| 200 | **42%** | **86%** |

Cold-pool line in Yellow (it is the admitted weakness), mature-pool line in Cyan. Annotate the
crossing: *"biaya baca CV dibayar sekali per kandidat seumur akun — bukan per lamaran."* This
chart turns our scariest question into our best answer, so give it real space.

### V8 — Readiness meter (in BUKTI — APA ADANYA)

Five rows, each a filled or unfilled state marker — not a tick-mark table:

| Row | Marker |
|---|---|
| Prototipe jalan & teruji otomatis | penuh, Lime |
| Alignment PS-2 (penilaian juri) | penuh, Lime — *Sangat Kuat* |
| Kualitas prototipe (penilaian juri) | penuh, Lime — *Sangat Kuat* |
| Perusahaan membayar | kosong, Yellow — `BELUM ADA` |
| Validitas prediktif skor | kosong, Yellow — `BELUM DIUJI` |

Yellow gap markers are **a deliberate feature**. Legible, unapologetic, same size as the wins.

### V9 — Investment allocation (in PENDANAAN)

100% stacked bar or donut: Pendirian & legal **22%** · Menutup rugi sampai impas **29%** ·
Akuisisi employer & pencari kerja **20%** · Keamanan + gateway **6%** · Bantalan skenario buruk
**23%**. Label every slice with its percentage; no legend-only charts.

### V10 — Runway timeline (in PENDANAAN)

A thin horizontal timeline: `Bulan 0` funding → `Bulan 6` tahap kedua → `Bulan 15` **impas**
(Orange marker) → `Tahun 2` `Rp360 jt` pendapatan. Mark the cash trough `Rp101 jt` as a dip.

### V11 — AutoMod decision flow (in CARA KERJA, small)

Three-branch mini-diagram from `Iklan dipasang`:
`Minta biaya dari pelamar` → **DITOLAK + strike** (Orange/Ink) ·
`Syarat diskriminatif` → **DITAHAN, tinjauan admin** (Yellow) ·
`Bersih` → **TAYANG** (Lime).

---

# CONTENT — Indonesian text, place as written

## ▸ HERO

**CV bisa ditulis siapa saja.
Kami membuat skill harus dibuktikan — lalu mengurutkan pelamar berdasarkan bukti itu.**

Sub-line (18 px, Mute/Paper): *Pencocokan kerja berbasis AI untuk UMKM Indonesia dan pencari kerja
18–25 tahun.*

Plus **V1** and its kicker callout.

## ▸ MASALAH (PAIN + GAIN)

**Bagi UMKM yang merekrut hari ini**
- Pasang "kirim CV ke WA" → puluhan PDF masuk, tidak terurut.
- Banyak CV mengklaim skill yang tidak dikuasai. CV buatan AI memperparah.
- Akibatnya: **jam kerja pemilik usaha habis mewawancarai orang yang salah.**

**Bagi pencari kerja**
- Melamar puluhan kali, tidak dapat kabar, tidak tahu apa yang kurang.

Plus **V5**.

## ▸ PRODUK

**Satu daftar pelamar yang sudah diurutkan — dan skill-nya sudah diuji.**

- **Employer:** pasang lowongan → dapat **link + poster QR** → tempel di Instagram / grup WA yang
  sudah dipakai → pelamar masuk ke satu daftar terperingkat.
- **Pencari kerja:** scan QR → daftar via email → isi profil atau unggah CV → **ikut kuis skill
  5 soal** → lamar. Badge berlaku **180 hari di semua lowongan.**

Plus **V2** and **V6**. Caption under V2 (12 px, Mute): *Bobot bukti sengaja lebih besar dari
kemiripan teks — karena kemiripan teks justru naik kalau CV menyalin kalimat iklan.*

## ▸ CARA KERJA

Plus **V3**, **V11**.

**Tiga langkah bernomor:**
1. **Kuis 5 soal skenario**, ±3 menit. Dinilai server pakai kunci jawaban — **tanpa panggilan AI,
   Rp0 per percobaan.** Lulus 4/5 → badge ✓ Terbukti.
2. **HR wawancara**, lalu mencentang *skill terbukti* → bukti terkuat, bobot 1.00.
3. **Skor dihitung ulang** tiap daftar dibuka — pelamar yang baru lulus kuis langsung naik.

**Data pribadi:** kami **tidak mengumpulkan NIK, KTP, ijazah, atau NPWP.** Verifikasi hanya email.
Nomor, email, dan NIK **di dalam teks CV** disamarkan aturan regex tetap sebelum disimpan dan
sebelum dikirim ke AI — bukan lewat instruksi ke AI, jadi tidak bisa gagal karena prompt.

Caption (12 px, Mute): *CV hasil pindai atau foto tidak punya teks untuk disamarkan. Kami tidak
menolaknya — banyak pencari kerja Indonesia memang hanya punya foto CV — tapi kami **minta izin
dulu** sebelum gambarnya dikirim ke AI, dan hasil bacaannya tetap disamarkan sebelum disimpan.*

## ▸ KENAPA SULIT DITIRU

1. **Profil terbukti hanya ada di sini.** Peniru mulai dari nol kandidat terbukti. Fitur bisa
   disalin sebulan; kumpulan bukti tidak.
2. **QR tiap employer membawa pelamar baru** yang ikut dicocokkan ke lowongan lain — tumbuh dari
   pemakaian, bukan iklan.
3. **Model kami bertentangan dengan job board.** Mereka untung dari *banyak* lamaran; kami menang
   dengan mengirim *lebih sedikit tapi tepat*.

Kutipan penutup (italic, 15 px): *"Fiturnya bisa ditiru. Profil yang sudah terbukti dan kepercayaan
HR tidak bisa disalin."*

## ▸ BUKTI — APA ADANYA

**V8**, plus catatan (12 px, Mute): *Mesin pengukurnya sudah jalan: skor + bukti disimpan saat
melamar, tiap perubahan status dicatat, dan dashboard admin menghitung tingkat wawancara per band
skor. Datanya yang belum ada — dan layar kami menulis "belum ada data", bukan 0%.*

## ▸ MODEL BISNIS

**Employer bayar untuk menyaring, bukan untuk mencari.**

| Paket | Harga |
|---|---|
| **Spark** | **Rp0** · 1 lowongan, 20 pelamar skor tertinggi |
| **Beacon** | **Rp29.000** / lowongan |
| **Lighthouse** | **Rp99.000** / bulan |
| **Prism** (pencari kerja) | **Rp25.000** / 30 hari |

Plus **V7**. Caption: *asumsi pemakaian tipikal 30 pelamar / 5 dishortlist, buffer ×1,5, sudah
termasuk biaya QRIS. Kuis dan skor **tidak memanggil AI sama sekali**.*

Garis tebal (15 px, Ink): **Membayar tidak pernah menaikkan skor atau peringkat siapa pun.**

Footnote: *Pembayaran saat ini QRIS / transfer yang dikonfirmasi admin.* `RENCANA: payment gateway`

## ▸ PENDANAAN

**Stat besar:** `Rp200 jt` untuk **10%** — *dua tahap: Rp100 jt saat tanda tangan, Rp100 jt di
bulan ke-6 bila target tercapai.* Plus **V9** and **V10**.

## ▸ TIM

- **David** — AI / Backend · mesin pencocokan, bobot bukti, AutoMod
- **Darren** — Product / UX · alur seeker–employer, desain sistem
- **Vanessa** — Systems / Impact · data hasil, metrik dampak
- **Jason** — Business / Deployment · model bisnis, harga, pilot

Kalimat pembeda (italic, 14 px): *Kami memperbaiki produk berdasarkan kritik, bukan membela slide:
model Pay-to-Unlock, e-KYC NIK, dan klaim "94% akurasi" semuanya kami hapus karena tidak bisa kami
buktikan.*

## ▸ AJAKAN

**Tiga ajakan berdampingan, tiap satu dalam kotak sendiri:**

| Untuk UMKM / HR | Untuk pencari kerja | Untuk investor / offtaker |
|---|---|---|
| **Pasang 1 lowongan sekarang — gratis. Poster QR-nya kami cetakkan hari ini.** | **Scan, ikut 1 kuis 3 menit, bawa pulang badge ✓ Terbukti.** | **Beri kami 30 hari dan 10 UMKM pilot. Lalu kita baca bersama tingkat wawancara per band skor di dashboard yang sama.** |

**Target terukur 3 hari** (mono, 14 px): `15` UMKM pasang lowongan · `100` pencari kerja selesai
≥1 kuis · `3` surat minat bayar Beacon

**Penutup — banner Orange, teks Paper, 30–34 px / 900:**
**"Pasar kerja Indonesia tidak kekurangan lamaran. Yang kurang adalah bukti.
Kami membangun tempat bukti itu disimpan."**

---

## Final check before you hand this over

1. Can someone 2 m away name the main claim in 5 seconds, from the charts alone?
2. Is there one obvious place the eye lands first, and does it lead somewhere second?
3. Are the yellow gap markers as legible as the wins? (If they shrank, put them back.)
4. Is every number on the page traceable to §CONTENT above? Nothing invented?
5. Are there at least 8 real data visuals, and is no chart doing work a sentence already did?

═══════════════════ SALIN SAMPAI SINI ═══════════════════

---

# Bekal Presenter — JANGAN ditaruh di slide

Setiap jawaban di bawah **sudah benar terhadap kode hari ini**. Jangan improvisasi angka baru.

### Pertanyaan yang dulu tidak terjawab

| Pertanyaan | Jawaban yang benar |
|---|---|
| *"CV bisa direkayasa, bagaimana verifikasinya?"* | Skill yang hanya ditulis di CV bernilai **0.30**; lulus kuis **0.85**; dikonfirmasi HR **1.00**. Karena bobot bukti (0.40) **lebih besar** dari kemiripan teks (0.35), menyalin kalimat iklan tidak lagi cukup untuk menang — lihat grafik utama di kanvas. |
| *"Tunjukkan bahwa keyword stuffing benar-benar kalah."* | Dua kandidat, pengalaman & pendidikan sama. Penyalin iklan: kemiripan 0.90, semua skill hanya klaim → **0.685**. Kandidat terbukti: kemiripan 0.50, semua skill lulus kuis → **0.765**. Bahkan pada kemiripan **sempurna 1.00**, penyalin berhenti di **0.720**. Selisih bobot yang harus dikejar setara **0.629 poin kemiripan** — di luar rentang nyata. |
| *"Berarti pembohong diblokir?"* | **Tidak, dan kami tidak mengklaim itu.** Skor 0.685 masih masuk band "strong" (ambang 0.65). Yang kami jamin cuma satu: dia **di bawah** kandidat terbukti dalam urutan yang dibaca HR. Menyaring, bukan menghakimi. |
| *"Ada mekanisme ban / turun peringkat?"* | Ada dan sudah jalan: AutoMod menolak/menahan sebelum tayang, pemasang dapat notifikasi + bisa banding, kandidat bisa melapor, dan strike 1→2→3 membatasi lalu menangguhkan akun. |
| *"Redaksional berbasis prompt bisa gagal?"* | Karena itu penyamaran data pribadi **tidak** memakai instruksi ke AI — memakai aturan regex tetap sebelum tiap panggilan AI. NIK bahkan tidak dikumpulkan sama sekali. |
| *"Skor tinggi benar lolos interview?"* | Mekanismenya sudah dibangun — skor + bukti disimpan saat melamar, status dicatat, dashboard menghitung tingkat wawancara per band. **Datanya belum ada, dan kami tidak akan mengarang.** Itu yang kami minta 30 hari pilot untuk dapatkan. |
| *"Kenapa tidak mudah ditiru?"* | Bukan closed loop dan bukan fine-tuning — keduanya bisa ditiru. Yang tidak bisa disalin adalah kumpulan profil yang sudah terbukti di platform kami. |
| *"Dari mana lowongan pertama?"* | Pasang gratis, dan employer membagikan QR di kanal yang **sudah** mereka pakai. Kami tidak meminta mereka pindah kanal — hanya lamarannya yang pindah tempat. |

### Lubang yang kami akui — jawab persis begini

| Kalau ditanya | Jawab |
|---|---|
| Sudah ada yang bayar? | **Belum satu pun.** Target booth ini: 3 surat minat. |
| Bank soalnya berapa? | **8 skill × 6 soal, masih draf AI**, sedang diperluas ke ~20 per skill dengan tinjauan praktisi HR. Dengan 6 soal, satu kuis 5 soal hanya punya 6 kombinasi — jadi ujian ulang pasti mengulang soal. Kami tahu, dan itu antrean kerja berikutnya. |
| Kuis bisa dicontek? | Bisa. Karena itu ada timer per soal, soal acak, dan **HR tetap penentu akhir** lewat centang "skill terbukti". Kami tidak mengklaim kuis anti-curang. |
| Payment gateway? | Belum. Sekarang QRIS/transfer dikonfirmasi admin. Midtrans/Xendit biaya setup Rp0, jadi bukan penghalang — menunggu PT. |
| Validasi penggunanya berapa? | Di bawah 10 orang dan belum terdokumentasi rapi. Itu kelemahan yang sedang kami tutup dengan paket bukti loop dampak. |
| Margin 88% itu dari mana? | Dari **asumsi** pemakaian 30 pelamar / 5 dishortlist dengan buffer ×1,5, bukan dari pengukuran pelanggan nyata — kami belum punya pelanggan. Yang **terukur** adalah biaya per aksi di `/admin → Metrik`, dihitung dari token asli di `ai_logs`. |
| Kalau lowongannya viral, 200 pelamar? | Margin turun **di bulan-bulan awal**: 88% (30) → 70% (100) → **42% (200)** selama separuh pelamar masih kandidat baru. Tapi dua biaya utama — baca CV (~Rp99) dan email OTP — dibayar **sekali per kandidat seumur akun, bukan per lamaran**. Begitu kolam kandidat matang dan hanya ~10% yang baru, margin pada 200 pelamar kembali ke **86%**. Risiko cold-start yang mengecil sendiri, bukan kebocoran struktural. |
| Kuis/skor benar tidak pakai AI? | Benar. Kuis dinilai dengan kunci jawaban di server, skor dihitung dari vektor tersimpan. Rp0 per percobaan, dan itu sebabnya margin bertahan saat pemakaian naik. |
| Penyamaran data gagal untuk CV pindai? | CV pindai tidak punya teks untuk disamarkan, jadi hanya bisa dikirim sebagai gambar. Kami **tidak melakukannya diam-diam dan tidak memblokir**: pelamar diberi tahu persis apa yang akan dikirim, lalu memilih lanjut atau isi profil manual. Memblokir akan menyingkirkan justru pengguna yang paling kami tuju — banyak yang CV-nya foto HP. Persetujuan eksplisit juga dasar hukum yang benar menurut UU PDP. Teks yang **disimpan** selalu sudah disamarkan, di kedua jalur parsing. |
| Kualitas kode? | **Semua check menggugurkan build kalau merah**: unit test backend, lint backend (Ruff), ESLint + unit test + build frontend, dan integration test yang menjalankan **migrasi Alembic ke PostgreSQL asli beserta uji rollback**. Integration test itulah yang menemukan dua tabel yang tidak pernah dibuat migrasi mana pun — dulu non-gating, sekarang tidak lagi. ESLint baru lulus pada aturan *bug*; 55 peringatan gaya sengaja dibiarkan terlihat sebagai antrean kerja, bukan dimatikan. |

### Angka yang boleh disebut, dan sumbernya

| Angka | Sumber |
|---|---|
| 35 / 40 / 15 / 10 | `matcher.py` — `_W_COSINE` / `_W_SKILL` / `_W_EXPERIENCE` / `_W_EDUCATION` |
| 0.30 / 0.85 / 1.00 | `evidence.py` — `PROOF_WEIGHTS` |
| 0.685 / 0.720 / 0.765 | dihitung dari rumus di `matcher.py` (pengalaman & pendidikan disamakan). Guard test: `TestProofBeatsKeywordStuffing` di `test_v2_scoring.py` |
| Ambang band 0.45 / 0.65 | `settings.py` — `band_possible_threshold` / `band_strong_threshold` |
| Rp0 per percobaan kuis | dinilai dengan kunci jawaban, tanpa panggilan AI |
| Margin 88% / 70% / 42% / 86% | `BUSINESS_MODEL.md` — **jumlah token per aksi masih asumsi**, dikalikan harga Gemini × kurs Rp17.600, buffer ×1,5. Angka **sungguhan** ada di `/admin → Metrik` yang membaca tabel `ai_logs`. Jangan tukar keduanya. |
| Bulan 15 · Rp101 jt · Rp360 jt | proyeksi skenario dasar, `BUSINESS_MODEL.md` |
| 89.141 · 7,24 jt | SIDT-UMKM Des 2025 · BPS Feb 2026 |
| Spark 20 pelamar | **skor tertinggi**, bukan yang pertama melamar |

> **Aturan tunggal di booth:** kalau sebuah angka tidak ada di tabel ini, **jangan sebut**.
> Katakan "belum kami ukur" — itu jawaban yang menang, bukan yang kalah.
