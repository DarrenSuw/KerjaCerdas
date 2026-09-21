# Model Bisnis & Keuangan KerjaCerdas ("Bukti, bukan klaim")

> **Aturan dokumen ini:** setiap harga infrastruktur/AI punya sumber (lihat §9). Angka tanpa sumber ditandai **(asumsi)** atau **(perlu penawaran)**. Tidak ada angka hasil rekaan.
> **Kurs:** US$1 = **Rp17.600** (JISDOR Bank Indonesia berkisar Rp17.536–17.727 pada September 2026 [S7]).

---

## 1. Prinsip: yang berbiaya yang ditagih

Satu aturan menentukan setiap baris harga di dokumen ini:

> **Kami menagih pekerjaan yang menghemat waktu employer, bukan akses ke orang.**

Konsekuensinya, dan semuanya sudah berlaku di kode:

| Prinsip | Bentuk nyatanya |
|---|---|
| Menyaring itu gratis | Memeringkat pelamar berbiaya **Rp0** untuk kami hitung (tanpa panggilan AI), jadi tidak pernah dibatasi — termasuk di paket gratis. Membatasinya tidak menghemat apa pun dan hanya menyembunyikan kandidat dari employer yang justru meminta peringkat. |
| Kontak pelamar tidak dijual | Pelamar yang melamar sendiri sudah memberi kontaknya kepada employer itu — gratis, selamanya. Kandidat yang **belum** melamar tampil **anonim**, dan tidak ada cara membeli identitasnya. |
| Yang berbayar yang berbiaya atau menghemat waktu | Kit wawancara (dihitung AI, di-cache), ekspor, pencarian kandidat yang belum melamar, dan kuota lowongan aktif. |
| Membayar tidak pernah menggerakkan skor | Bobot bukti, urutan pelamar, dan jeda ulang kuis identik di semua paket. Tidak ada paket yang bisa membeli peringkat. |

Aturan ini juga yang menutup risiko UU PDP: kami tidak pernah berada dalam posisi menjual akses ke data pribadi pencari kerja.

---

## 2. Aliran pendapatan (yang benar-benar ada di kode)

| Paket | Harga | Untuk siapa | Isi | Status |
|---|---|---|---|---|
| **Spark** | Rp0 | Semua employer | 1 lowongan aktif, link + poster QR, **semua pelamar diperingkat (tanpa batas)**, badge skill terbukti, konfirmasi "skill terbukti" | `[BUILT + TESTED]` |
| **Beacon** | **Rp49.000 / lowongan / 30 hari** | UKM yang sesekali merekrut | Pertanyaan wawancara AI, ekspor CSV, 30x cari kandidat yang belum melamar | `[BUILT + TESTED]`, pembayaran manual |
| **Lighthouse** | **Rp149.000 / 30 hari** | Yang merekrut tiap bulan | Semua fitur Beacon + hingga 5 lowongan aktif | `[BUILT + TESTED]`, pembayaran manual |
| **Prism** (pencari kerja) | **Rp15.000 / 30 hari** | Pencari kerja yang ingin berlatih | Advisor 20 pesan/hari (gratis: 10/hari) `[BUILT + TESTED]`. Roadmap: simulasi wawancara AI + CV terformat `[PLANNED]` | pembayaran manual |
| Afiliasi Ed-Tech | komisi | — | Klik kursus sudah dilacak lewat event | `[PLANNED]` — **tidak** dihitung dalam BEP |

### 2a. Apa persisnya yang dibeli tiap paket — dan di mana itu ditegakkan

Tabel ini adalah **sumber kebenaran** untuk setiap klaim harga di deck, di UI, dan di jawaban
presenter. Kolom terakhir bukan hiasan: fitur berbayar yang tidak ditegakkan di kode adalah
pendapatan yang kami berikan gratis tanpa sadar.

| Paket | Yang didapat | Ditegakkan di | Biaya kami / pemakaian |
|---|---|---|---|
| **Spark** (Gratis) | 1 lowongan aktif | `plans.active_job_limit` → `employer.py` | baca lowongan ~Rp130, sekali |
| | **Semua pelamar diperingkat, tanpa batas** | tidak dibatasi — disengaja | **Rp0** (tanpa panggilan AI) |
| | Link + poster QR lowongan | `services/hiring/links.py` | Rp0 |
| | Badge ✓ Terbukti terlihat + centang "skill terbukti" | `quiz/`, `hiring.py` | Rp0 per percobaan kuis |
| **Beacon** (Rp49.000 / lowongan / 30 hari) | Pertanyaan wawancara AI per kandidat | `hiring.py::_require_premium` | ~Rp60, **di-cache** per (kandidat, lowongan) |
| | Ekspor pelamar CSV | `hiring.py::_require_premium` | Rp0 |
| | **Cari kandidat yang belum melamar — 30x / 30 hari, PER LOWONGAN** | `employer.py::_check_talent_search_quota` (kuota dihitung per `job_id`) | Rp0 (pgvector, tanpa AI) |
| **Lighthouse** (Rp149.000 / 30 hari) | Hingga 5 lowongan aktif | `plans.active_job_limit` | ~Rp130 per lowongan |
| | Semua fitur Beacon di semua lowongan | `Entitlements.job_tier` | — |
| | Cari kandidat **150x / 30 hari**, berlaku se-akun | `employer.py::_check_talent_search_quota` | Rp0 |
| **Gratis** (pencari kerja) | Skor, band, skill gap, rekomendasi kursus | `seeker.py` | baca CV ~Rp99 sekali seumur akun |
| | Kuis tanpa batas (ulang besoknya) | `quiz/service.RETAKE_DAYS` | **Rp0 per percobaan** |
| | **Peringkat persis tiap lamaran** (mis. #14 dari 62) + rincian bukti per skill | `seeker.py::application_rank` | **Rp0** — dibaca dari baris yang ditulis saat melamar |
| | Advisor 10 pesan / hari | `agent.py::_check_advisor_quota` | ~Rp9 / pesan |
| **Prism** (Rp15.000 / 30 hari) | Advisor 20 pesan / hari | `agent.py::_check_advisor_quota` | ~Rp9 / pesan, plafon Rp8.100 / 30 hari |
| | *Roadmap:* simulasi wawancara AI + umpan balik `[PLANNED]` | — | ~Rp150 / sesi (perkiraan) |
| | *Roadmap:* CV terformat dari profil terverifikasi `[PLANNED]` | — | ~Rp50 (perkiraan) |

**Tiga aturan yang tidak boleh dilanggar paket mana pun:**

1. **ATURAN PENCARI KERJA — pencari kerja boleh membayar untuk LATIHAN dan PRESENTASI, tidak pernah
   untuk POSISI maupun untuk INFORMASI TENTANG POSISINYA.** Peringkat persis sempat dijual di Prism.
   Skor dan urutannya identik bagi yang bayar maupun tidak, jadi kelihatannya adil — tapi kandidat
   yang tahu dia peringkat 14 dari 62, dan tahu skill klaim mana yang menahannya, bisa bertindak;
   yang tidak tahu, tidak bisa. Itu keunggulan yang dibeli dengan uang, ditagihkan ke sisi pasar yang
   paling sedikit punya uang. **Sekarang gratis untuk semua**, dan ada test yang gagal kalau
   gerbangnya kembali. Semua yang menyentuh peringkat — skor, band, peringkat persis, rincian bukti,
   kuis, badge, jeda ulang 1 hari — gratis selamanya di semua paket.
2. **Paywall ada di *sourcing*, tidak pernah di *screening*.** Memeringkat orang yang sudah melamar
   berbiaya Rp0 untuk dihitung; membatasinya tidak menghemat sepeser pun dan hanya menyembunyikan
   kandidat peringkat 21 dari employer yang justru meminta peringkat. Mencari orang yang **belum**
   melamar adalah sourcing — itu yang dijual, dan itu yang punya kuota.
3. **Setiap fitur berbayar harus DITEGAKKAN di kode.** Fitur yang diiklankan di katalog tapi tidak
   punya gerbang adalah pendapatan yang kami berikan gratis tanpa sadar — persis yang terjadi pada
   kuota pencarian kandidat: `talent_search_limit()` ada dan diuji, tapi tidak satu pun router
   memanggilnya, jadi kuota Spark "0" sebenarnya tak terbatas. Kolom "Ditegakkan di" pada tabel di
   atas wajib terisi sebelum sebuah fitur boleh dijual.

**Kenapa margin bertahan saat pemakaian naik.** Tiga dari empat hal yang dibeli berbiaya **Rp0**
untuk dilayani: pemeringkatan pelamar, pencarian kandidat (pgvector), dan peringkat persis pencari
kerja (pembacaan baris — **gratis**, bukan fitur berbayar). Yang benar-benar memanggil AI hanyalah
kit wawancara (di-cache) dan pesan advisor (berkuota). Karena itu jumlah pelamar tidak menggerakkan
COGS employer sama sekali.

---

**Pencari kerja tidak pernah membayar untuk skor — dan tidak pernah membayar untuk *mengetahui* skornya.** Peringkat persis, rincian bukti per skill, band, dan skill yang kurang: gratis di semua paket. Prism hanya menambah kuota advisor; bobot bukti dan urutan identik di semua paket. Prism juga **tidak** mempercepat ulang kuis — itu uang yang mempersingkat jalan menuju badge, dan badge menggerakkan skor.

**Kenapa paywall-nya bukan di jumlah pelamar.** Menghitung peringkat berbiaya **Rp0**, jadi membatasinya tidak pernah menghemat apa pun — yang terjadi hanya kandidat peringkat 21 tidak terlihat oleh employer yang justru meminta peringkat. Kuota dipindah ke *reverse matching* (mencari kandidat yang belum melamar), yaitu sourcing, plus kit wawancara dan ekspor yang memang berbiaya.

**Pembayaran hari ini:** QRIS / transfer bank → admin mengaktifkan pesanan 30 hari (`[BUILT, MANUAL PAYMENT]`). Gateway (Midtrans/Xendit) `[PLANNED]`: QRIS 0,7%, VA Rp4.000, kartu 2,9% + Rp2.000, tanpa biaya setup [S1]. Stripe belum bisa dipakai — di Indonesia statusnya undangan dan tanpa transaksi lintas negara [S2].

---

## 3. Biaya per aksi AI (dasar COGS)

Harga Gemini API [S3]; `gemini-3.1-flash-lite` tidak ada di daftar harga publik sehingga dipakai tarif **3.5 Flash-Lite** sebagai proksi konservatif. Jumlah token per aksi = **(asumsi)**, diverifikasi lewat `GET /api/v1/admin/metrics` yang menghitung dari tabel `ai_logs` sungguhan.

| Aksi | Model | Token (in/out) | Biaya |
|---|---|---|---|
| Baca 1 lowongan + AutoMod | 3.5 Flash-Lite | 4k / 1,5k | ~Rp130 |
| Baca 1 CV + embedding (sekali per kandidat) | 3.5 Flash-Lite + Embedding 2 | 5k / 1,5k + 2k | ~Rp99 |
| Skor kecocokan | tanpa panggilan AI | — | **Rp0** |
| **Kuis skill (percobaan)** | tanpa panggilan AI (kunci jawaban) | — | **Rp0** |
| Pembuatan soal kuis — **per batch 10 soal** | 3.1 Flash Lite | 3k / 3,3k | ~Rp110 |
| Mengisi 1 skill baru sampai bank 30 soal (3 batch) | 3.1 Flash Lite | — | **~Rp330** |
| Pertanyaan wawancara / kandidat — **di-cache, sekali per (kandidat, lowongan)** | 3.5 Flash-Lite | 3k / 1k | ~Rp60 |
| Peringkat pelamar · reverse matching | pgvector, tanpa panggilan AI | — | **Rp0** |
| Analisis skill gap | 2.5 Flash-Lite (tier gratis) | 4k / 1,5k | ~Rp23 |
| 1 pesan advisor (tier flash-lite) | 3.1 / 3.5 Flash-Lite | 3k / 0,5k | ~Rp9 |
| 1 pesan advisor **saat fallback** ke `gemini-3.6-flash` | 3.6 Flash | 3k / 0,5k | **~Rp38** |
| 1 email (OTP verifikasi) | Resend — **gratis sampai 3.000/bln**, lalu Pro $20/50.000 [S4] | — | **Rp0** di tier gratis; ~Rp7 setelahnya |

Semua perhitungan di bawah memakai **buffer ×1,5** untuk retry dan model cadangan.

**Dua perubahan biaya dari revisi v3, keduanya searah berlawanan:**

- **Bank soal naik dari 6 ke 30 per skill**, jadi menyiapkan satu skill baru kini ~Rp330, bukan ~Rp85. Ini biaya sekali per skill yang diamortisasi ke seluruh percobaan selamanya, dan ia yang membeli jaminan "ujian ulang tidak mengulang soal".
- **Baca CV tidak lagi dibebankan ke paket employer.** Pelamar mengunggah CV-nya sendiri sekali seumur akun; biaya itu pindah ke baris *pencari kerja gratis* di bawah. Biayanya tidak hilang — ia berpindah dari pendapatan ke akuisisi. Konsekuensinya: **jumlah pelamar tidak lagi menggerakkan COGS employer sama sekali**, dan kurva margin lama (88% → 70% → 42% seiring pelamar bertambah) **tidak berlaku lagi**.

### Kontribusi per penjualan (asumsi pemakaian tipikal: 30 pelamar, 5 dishortlist)

> **Dua hal yang menentukan biaya, dan keduanya dibayar SEKALI PER KANDIDAT — bukan per lamaran:**
>
> 1. **Baca CV + embedding (~Rp99)** — dilakukan saat kandidat mengunggah CV. Kandidat yang sama
>    melamar ke 10 lowongan tidak menambah biaya apa pun di 9 lowongan berikutnya.
> 2. **Email OTP (~Rp7, atau Rp0 di tier gratis Resend)** — dikirim saat kandidat memverifikasi
>    email akunnya, sekali seumur akun. Bukan per lamaran, dan bukan per lowongan.
>
> **Sejak v3 ini tidak lagi berlaku.** Baca CV dibebankan ke akun pencari kerja, bukan ke paket
> employer, jadi jumlah pelamar tidak menggerakkan COGS employer sama sekali. Kurva 88% → 70% →
> 42% yang dulu kami tampilkan **sudah tidak ada** — bukan karena membaik, tapi karena bebannya
> pindah ke baris akuisisi. Biaya sungguhannya tetap terpantau di `/admin → Metrik`.

| Item | Harga | COGS | **Kontribusi** | Margin |
|---|---|---|---|---|
| Beacon (1 lowongan, 5 dishortlist) | Rp49.000 | ~Rp645 | **Rp48.355** | **99%** |
| Lighthouse (1 bulan, ~3 lowongan) | Rp149.000 | ~Rp1.935 | **Rp147.065** | **99%** |
| Prism (30 hari, pemakaian tipikal) | Rp15.000 | ~Rp2.500 | **Rp12.500** | **83%** |
| Prism (30 hari, **plafon** 600 pesan, flash-lite) | Rp15.000 | ~Rp8.100 | **Rp6.900** | **46%** |
| Spark (lowongan gratis) | Rp0 | ~Rp195 | −Rp195 | biaya akuisisi |
| Pencari kerja — **onboarding sekali** (baca CV + embedding) | Rp0 | ~Rp150 | −Rp150 | biaya akuisisi |
| Pencari kerja gratis (per pengguna aktif/bulan) | Rp0 | ~Rp310 | −Rp310 | biaya akuisisi |

Beacon kini ~Rp645 (baca lowongan Rp195 + 5 kit wawancara Rp450) — bukan ~Rp3.400 seperti model lama, yang membebankan baca CV pelamar ke paket employer. **Angka 99% itu jujur tapi menyesatkan kalau dibaca sendirian:** biaya baca CV tidak hilang, ia pindah ke baris akuisisi pencari kerja. Yang berubah secara struktural adalah *siapa* yang menanggungnya dan *apa* yang menggerakkannya — bukan totalnya.

Margin tinggi karena **kuis, skor, peringkat, dan reverse matching tidak memanggil AI sama sekali**; biaya AI hanya untuk membaca CV/lowongan sekali, pertanyaan wawancara (kini di-cache, jadi klik ulang gratis), dan pesan advisor.

**Plafon Prism dihitung, bukan ditebak.** Pada 20 pesan/hari seorang pelanggan bisa memakai 600 pesan per 30 hari: ~Rp8.100 pada tier flash-lite, jadi lantai marginnya 46%. Sempat disetel 30/hari, yang menyisakan 19%. Titik impas Rp15.000 adalah **1.111 pesan** di flash-lite tapi hanya **263 pesan** bila `llm_factory` jatuh ke `gemini-3.6-flash` — yaitu 37/hari lawan 8,8/hari. **Risiko terbuka:** fallback yang berkepanjangan membuat 20/hari pun rugi di plafon. Perbaikan strukturalnya adalah metering berbasis *biaya*, bukan jumlah pesan; sampai itu ada, ini eksposur yang dipantau, bukan yang sudah selesai.

---

## 4. Biaya tetap bulanan (harga bersumber)

| Komponen | Sumber harga | Bulan 1–6 | Bulan 7+ |
|---|---|---|---|
| Server aplikasi | DigitalOcean Basic 2 vCPU/4GB **$24**; 4 vCPU/8GB **$48** [S5] | Rp422k | Rp845k |
| Database (Postgres + pgvector) | Supabase Pro **$25** (disk 8GB, kredit compute $10); compute Medium **$60** [S6] | Rp440k | Rp1,32jt |
| Penyimpanan CV/PDF | Cloudflare R2: 10GB gratis, lalu $0,015/GB, tanpa biaya egress [S8] | Rp0 | ~Rp11k |
| Email transaksional | Resend: gratis 3.000/bln; Pro **$20** untuk 50.000 [S4] | Rp0 → Rp352k | Rp352k |
| Domain `.id` | Rp120k–250k/tahun di registrar [S9] | Rp21k | Rp21k |
| Backup & monitoring | **(perkiraan, perlu verifikasi)** | Rp85k | Rp170k |
| **Subtotal infrastruktur** | | **≈Rp1,32jt** | **≈Rp2,72jt** |
| Pemasaran (konten, poster QR, kunjungan UKM) | **(pilihan anggaran)** | Rp2,5jt | Rp4jt |
| Transport kunjungan employer Jabodetabek | **(pilihan anggaran)** | Rp1jt | Rp1jt |
| Tools, akuntansi, admin | **(perkiraan)** | Rp0,7jt | Rp1jt |
| **Total biaya operasional** | | **≈Rp5,5jt/bln** | **≈Rp8,7jt/bln** |
| Uang saku 4 founder (4 × Rp2,5jt) | **dibayar hanya dari surplus** (kontribusi ≥ opex + Rp10jt) | Rp0 | Rp10jt saat syarat terpenuhi |

### Biaya sekali jalan (Rp45jt)

| Item | Sumber | Anggaran |
|---|---|---|
| Pendirian PT (akta notaris, SK AHU, NIB, NPWP perusahaan) | Rp4,9jt–15jt (2026) [S10] | Rp10jt |
| Merek dagang 2 kelas | DJKI: Rp2,8jt/kelas umum (PP 30/2026); **UMK Rp500rb/kelas** [S11] | Rp1jt (tarif UMK) |
| Dokumen UU PDP (kebijakan privasi, DPA, retensi) | **(perlu penawaran)** | Rp8jt |
| Tinjauan bank soal: 25–40 skill × honor praktisi HR | **(pilihan anggaran)** | Rp25jt |
| Materi booth & demo | **(perkiraan)** | Rp3jt |
| Cadangan setup | | Rp3jt |

Di luar model dasar (didanai investasi): audit keamanan sebelum gateway live ~Rp12jt **(perlu penawaran)**. Setup gateway sendiri gratis [S1].

---

## 5. Asumsi pertumbuhan (berpatokan benchmark)

| Pendorong | Asumsi | Benchmark |
|---|---|---|
| Employer mendaftar (uji coba Spark) | 40 di bulan 1, **+15%/bulan**, batas 400/bln | Target startup SaaS awal **10–20%/bulan** [S12] |
| Uji coba → berbayar | **18%** | Median trial-to-paid B2B tanpa kartu **18,2–18,5%** [S13] |
| Pencari kerja beli Prism | **2%** dari pengguna aktif | Freemium → berbayar **2,6%** organik [S13]; dipangkas karena daya beli |
| Pelamar per lowongan | 15 pengguna aktif per lowongan aktif | **(asumsi)** |

---

## 6. Proyeksi 24 bulan (skenario dasar, Rp juta)

> **⚠️ Tabel ini superseded — jangan dipakai sebagai proyeksi terkini.**
> Ia dihitung pada harga lama, dan angkanya **tidak bisa direkonsiliasi** dengan revisi harga di §2:
> memakai perubahan yang tercatat (+78% Beacon, +56% Lighthouse, −28% Prism) pada unit M24 di bawah
> menghasilkan pendapatan ≈Rp37jt, bukan Rp49,8jt yang tertulis. Artinya harga yang dipakai membangun
> tabel ini tidak sama dengan yang tercatat di mana pun, jadi ia tidak boleh dipakai sebagai dasar
> keputusan. **Kami membiarkannya terlihat, bukan menghapusnya diam-diam**, supaya jelas apa yang
> belum dikerjakan.
>
> Proyeksi bulan-per-bulan yang benar butuh dua angka yang **belum kami ukur**: churn Lighthouse dan
> campuran Beacon/Lighthouse dari waktu ke waktu. Keduanya menentukan bulan impas sepenuhnya (lihat
> §6a), dan kami tidak mengarangnya. Yang bisa dihitung hari ini ada di §6a.

### 6a. Yang bisa dihitung sekarang — syarat impas

Tanpa asumsi churn, ini tetap terhitung persis dari kontribusi per penjualan (§3) dan opex (§4):

| Untuk menutup opex **Rp8,7jt/bulan** | Butuh per bulan |
|---|---|
| Kalau semuanya Beacon (kontribusi Rp48.355) | **180** lowongan berbayar |
| Kalau semuanya Lighthouse (kontribusi Rp147.065) | **59** langganan aktif |
| Kalau semuanya Prism (kontribusi Rp12.500) | **696** pelanggan |

**Inilah sebabnya campuran menentukan segalanya.** Asumsi pertumbuhan §5 memberi maksimum 400
pendaftar/bulan pada batas atas; pada konversi 18% itu **72 pelanggan berbayar baru per bulan**.
Angka itu **tidak cukup** kalau semuanya Beacon (butuh 180), tapi **lebih dari cukup** kalau cukup
banyak yang Lighthouse (butuh 59) — dan Lighthouse berulang, jadi langganannya menumpuk sementara
lowongan Beacon tidak. Impas karena itu ditentukan oleh seberapa cepat basis Lighthouse tumbuh, bukan
oleh jumlah pendaftar.

**Konsekuensi yang harus disebut jujur ke investor:** angka impas kami bergantung pada retensi
Lighthouse yang belum pernah kami ukur, karena belum ada pelanggan. Itu justru salah satu hal yang
pilot 30 hari dirancang untuk menghasilkan.

---

#### Tabel lama (superseded — hanya untuk jejak, jangan dikutip)

| Bulan | Lowongan Beacon | Lighthouse | Pengguna aktif | Prism | **Pendapatan** | **Kontribusi** | Opex | Uang saku | **Laba/rugi** | **Kumulatif** |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 | 6 | 1 | 686 | 14 | 0,7 | 0,4 | 5,5 | 0 | −5,1 | −50,1 |
| M3 | 13 | 4 | 1.884 | 38 | 1,9 | 1,0 | 5,5 | 0 | −4,6 | −59,6 |
| M6 | 24 | 9 | 3.876 | 78 | 4,0 | 2,0 | 5,5 | 0 | −3,5 | −71,1 |
| M9 | 40 | 16 | 6.497 | 130 | 6,9 | 3,6 | 8,7 | 0 | −5,1 | −88,2 |
| M12 | 64 | 26 | 10.260 | 205 | 11,0 | 5,9 | 8,7 | 0 | −2,9 | −99,3 |
| M15 | 99 | 41 | 15.857 | 317 | 17,2 | 9,2 | 8,7 | 0 | **+0,5** | −101,4 *(titik terendah)* |
| M18 | 152 | 65 | 24.294 | 486 | 26,6 | 14,3 | 8,7 | 0 | +5,6 | −90,2 |
| M21 | 211 | 96 | 36.142 | 723 | 39,7 | 21,4 | 8,7 | 10 | +2,7 | −79,4 |
| M24 | 247 | 123 | 44.399 | 888 | 49,8 | 27,3 | 8,7 | 10 | +8,6 | −59,3 |

- **Pendapatan tahun 1 ≈ Rp60jt; tahun 2 ≈ Rp360jt.**
- **Titik impas operasional: bulan 15.** Uang saku founder mulai bulan ~20.
- **Kebutuhan kas terbesar: ≈Rp101jt.**
- Komposisi pendapatan M24: employer ≈55%, pencari kerja (Prism) ≈45% — **dua sisi ikut membayar**.

### Rumus titik impas

```
Pelanggan berbayar yang dibutuhkan = (biaya tetap + biaya pengguna gratis) ÷ kontribusi per penjualan
Contoh M15: Rp8,7jt ÷ (campuran Beacon Rp25,6rb / Lighthouse Rp88,75rb / Prism Rp17,3rb)
```

### Skenario

| Skenario | Pertumbuhan / konversi employer / konversi Prism | Kas terbesar | Impas operasional | Posisi M24 |
|---|---|---|---|---|
| Baik | 20% / 25% / 2,6% | ≈Rp74jt | M10 | kumulatif positif |
| **Dasar** | 15% / 18% / 2% | **≈Rp101jt** | **M15** | −Rp59jt (menuju positif) |
| Buruk | 8% / 9% / 1% + pemangkasan biaya di gerbang M9 | ≈Rp164jt | belum di M24 | perlu penyempitan fokus |

---

## 7. Kebutuhan pendanaan

**Rp200.000.000 untuk 10% saham** (pra-uang Rp1,8 M; pasca-uang Rp2,0 M) — **(usulan, bukan valuasi hasil audit)**.

| Penggunaan dana | Jumlah |
|---|---|
| Biaya sekali jalan (§4) | Rp45jt |
| Menutup rugi sampai impas (dasar Rp57jt; skenario buruk lebih besar) | Rp57jt |
| Audit keamanan + go-live payment gateway | Rp12jt |
| Akselerasi akuisisi (konten, job fair kampus, poster) | Rp40jt |
| Cadangan skenario buruk | Rp46jt |
| **Total** | **Rp200jt** |

**Pencairan bertahap:** Rp100jt saat penandatanganan; Rp100jt setelah milestone bulan 6 — ≥30 employer berbayar, ≥60% pelamar mengikuti minimal satu kuis, ≥50 pembeli Prism, COGS terukur per lowongan Beacon ≤ Rp5.000.

**Struktur kepemilikan (ilustrasi):** founder 4 orang 90% (vesting 4 tahun, cliff 1 tahun) + ESOP 10% → setelah investasi: founder 81%, ESOP 9%, investor 10%.

---

## 8. Ukuran pasar (metode jelas, angka bersumber)

- **Employer:** 73.828 usaha kecil + 15.313 usaha menengah = **89.141 unit** (SIDT-UMKM, 31 Des 2025) [S14] × 4 lowongan/tahun **(asumsi)** × Rp49.000 ≈ **Rp17,5 miliar/tahun**.
- **Pencari kerja:** 7,28 juta penganggur (BPS, **Mei 2026**, rilis 5 Agustus 2026) [S15] × 2% membeli Prism **(asumsi)** × Rp15.000 × 3 bulan/tahun **(asumsi)** ≈ **Rp6,6 miliar/tahun**.
- **Total lantai pasar ≈ Rp21 miliar/tahun.** Pendapatan tahun 2 pada skenario dasar ≈ 1,7% dari angka itu.
- Belum dihitung (potensi tambahan, perlu sumber): usaha mikro yang tetap mempekerjakan staf, perusahaan besar untuk posisi entry-level, agen penyalur kerja (>3.000 perusahaan alih daya di asosiasi FAADI [S16]), dan pekerja yang ingin pindah kerja.
- Konteks: TPT **4,65%**, rata-rata upah buruh **Rp3,39 juta** (BPS Mei 2026, rilis 5 Agustus 2026) [S15]. Ini rilis terbaru; angka Februari 2026 (TPT 4,68%, upah Rp3,29 juta) sudah digantikan dan tidak boleh dikutip lagi.

---

## 9. Sumber

- [S1] Midtrans, biaya transaksi: https://midtrans.com/pricing
- [S2] Stripe Indonesia (undangan, tanpa lintas negara): https://support.stripe.com/questions/requirements-to-open-a-stripe-account-in-indonesia
- [S3] Harga Gemini API: https://ai.google.dev/gemini-api/docs/pricing
- [S4] Resend: https://resend.com/pricing
- [S5] DigitalOcean Droplets: https://www.digitalocean.com/pricing/droplets
- [S6] Supabase: https://supabase.com/pricing
- [S7] Kurs JISDOR Bank Indonesia: https://www.bi.go.id/id/statistik/informasi-kurs/jisdor/default.aspx
- [S8] Cloudflare R2: https://developers.cloudflare.com/r2/pricing/
- [S9] Harga domain `.id`: https://www.hostingekspres.com/blog/harga-domain-id
- [S10] Biaya pendirian PT 2026: https://izin.co.id/blog/berapa-biaya-pendirian-pt-di-indonesia/
- [S11] Tarif merek DJKI (PP 30/2026): https://www.dgip.go.id/artikel/detail-artikel-berita/djki-sesuaikan-tarif-merek-umk-tetap-dapat-keringanan?kategori=liputan-humas
- [S12] Benchmark pertumbuhan SaaS awal: https://www.lightercapital.com/blog/2025-b2b-saas-startup-benchmarks
- [S13] Benchmark konversi trial & freemium: https://firstpagesage.com/seo-blog/saas-free-trial-conversion-rate-benchmarks/
- [S14] Data SIDT-UMKM (Des 2025): https://ukmindonesia.id/baca-deskripsi-posts/data-umkm-jumlah-dan-pertumbuhan-usaha-mikro-kecil-dan-menengah-di-indonesia
- [S15] BPS, Ketenagakerjaan Mei 2026 (rilis 5 Agustus 2026): https://www.bps.go.id/id/pressrelease/2026/08/05/2606/tingkat-pengangguran-terbuka--tpt--sebesar-4-65-persen---rata-rata-upah-buruh-sebesar-3-39-juta-rupiah-.html
- [S16] Sektor alih daya (ABADI/FAADI): https://abadi.id/

> **Sebelum dipakai di pitch:** cek ulang tarif Xendit lewat kalkulator resminya, kurs pada hari-H, dan perbarui semua angka **(asumsi)** dengan data nyata dari `GET /api/v1/admin/metrics` setelah pilot.
