# Model Bisnis & Keuangan KerjaCerdas (v2 — "Bukti, bukan klaim")

> **Aturan dokumen ini:** setiap harga infrastruktur/AI punya sumber (lihat §9). Angka tanpa sumber ditandai **(asumsi)** atau **(perlu penawaran)**. Tidak ada angka hasil rekaan.
> **Kurs:** US$1 = **Rp17.600** (JISDOR Bank Indonesia berkisar Rp17.536–17.727 pada September 2026 [S7]).
> Versi sebelumnya memakai model *Pay-to-Unlock* (Rp50.000/kontak). **Model itu dihapus** — alasannya di §1.

---

## 1. Kenapa Pay-to-Unlock dihapus

| Masalah | Penjelasan |
|---|---|
| Menagih rasa sakit yang salah | Juri mencatat kebutuhan perusahaan terkonfirmasi kuat pada **penyaringan** pelamar, bukan pada *sourcing* kandidat baru. Unlock menagih sourcing. |
| Butuh likuiditas yang belum ada | Membuka kontak baru bernilai hanya jika kolam kandidat besar. Di awal, kolam itu kosong. |
| Bocor | Teaser "Someone at X" + wilayah + pengalaman cukup untuk menemukan orangnya di LinkedIn tanpa membayar. |
| Risiko UU PDP | Menjual akses kontak pencari kerja tanpa persetujuan eksplisit. |
| Tidak bisa ditagih | Belum ada payment gateway; endpoint unlock menerima token apa pun (mode demo). |

**Gantinya:** employer membayar untuk **memeringkat & mewawancarai pelamar yang layak**; kontak pelamar yang melamar sendiri selalu gratis; kandidat yang belum melamar tampil **anonim**.

---

## 2. Aliran pendapatan (yang benar-benar ada di kode)

| Paket | Harga | Untuk siapa | Isi | Status |
|---|---|---|---|---|
| **Spark** | Rp0 | Semua employer | 1 lowongan aktif, link + poster QR, **semua pelamar diperingkat (tanpa batas)**, badge skill terbukti, konfirmasi "skill terbukti" | `[BUILT + TESTED]` |
| **Beacon** | **Rp49.000 / lowongan / 30 hari** | UKM yang sesekali merekrut | Pertanyaan wawancara AI, ekspor CSV, 30x cari kandidat yang belum melamar | `[BUILT + TESTED]`, pembayaran manual |
| **Lighthouse** | **Rp149.000 / 30 hari** | Yang merekrut tiap bulan | Semua fitur Beacon + hingga 5 lowongan aktif | `[BUILT + TESTED]`, pembayaran manual |
| **Prism** (pencari kerja) | **Rp15.000 / 30 hari** | Pencari kerja aktif | Peringkat persis tiap lamaran + rincian skor per komponen, advisor 20 pesan/hari (gratis: 10/hari) | `[BUILT + TESTED]`, pembayaran manual |
| Afiliasi Ed-Tech | komisi | — | Klik kursus sudah dilacak lewat event | `[PLANNED]` — **tidak** dihitung dalam BEP |

**Pencari kerja tidak pernah membayar untuk skor.** Prism hanya menambah kuota dan membuka *rincian hasilnya sendiri*; bobot bukti dan urutan identik di semua paket. Prism **tidak lagi** mempercepat ulang kuis — itu uang yang mempersingkat jalan menuju badge, dan badge menggerakkan skor.

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
| Pembuatan soal kuis (sekali per skill baru) | 3.1 Flash Lite | 3k / 2k | ~Rp85 |
| Pertanyaan wawancara / kandidat | 3.5 Flash-Lite | 3k / 1k | ~Rp60 |
| Analisis skill gap | 2.5 Flash-Lite (tier gratis) | 4k / 1,5k | ~Rp23 |
| 1 pesan advisor | 2.5 Flash-Lite / 3.5 Flash-Lite | 3k / 0,5k | ~Rp9 / ~Rp38 |
| 1 email (OTP verifikasi) | Resend — **gratis sampai 3.000/bln**, lalu Pro $20/50.000 [S4] | — | **Rp0** di tier gratis; ~Rp7 setelahnya |

Semua perhitungan di bawah memakai **buffer ×1,5** untuk retry dan model cadangan.

### Kontribusi per penjualan (asumsi pemakaian tipikal: 30 pelamar, 5 dishortlist)

> **Dua hal yang menentukan biaya, dan keduanya dibayar SEKALI PER KANDIDAT — bukan per lamaran:**
>
> 1. **Baca CV + embedding (~Rp99)** — dilakukan saat kandidat mengunggah CV. Kandidat yang sama
>    melamar ke 10 lowongan tidak menambah biaya apa pun di 9 lowongan berikutnya.
> 2. **Email OTP (~Rp7, atau Rp0 di tier gratis Resend)** — dikirim saat kandidat memverifikasi
>    email akunnya, sekali seumur akun. Bukan per lamaran, dan bukan per lowongan.
>
> Karena itu biaya marginal per lowongan **turun** seiring kolam kandidat matang. Tabel di bawah
> memakai asumsi konservatif "separuh pelamar adalah kandidat baru" (kondisi awal). Margin Beacon
> pada 200 pelamar: **42%** bila separuh kandidat baru (bulan-bulan awal), **86%** bila hanya 10%
> yang baru (kolam matang). Beacon tidak membatasi jumlah pelamar — risiko ini nyata di awal dan
> mengecil dengan sendirinya, dan biaya sungguhannya terpantau di `/admin → Metrik`.

| Item | Harga | COGS | **Kontribusi** | Margin |
|---|---|---|---|---|
| Beacon (1 lowongan) | Rp49.000 | ~Rp3.400 | **Rp45.600** | **93%** |
| Lighthouse (1 bulan, ~3 lowongan) | Rp149.000 | ~Rp10.250 | **Rp138.750** | **93%** |
| Prism (30 hari, pemakaian tipikal) | Rp15.000 | ~Rp2.500 | **Rp12.500** | **83%** |
| Prism (30 hari, **plafon** 600 pesan) | Rp15.000 | ~Rp8.100 | **Rp6.900** | **46%** |
| Spark (lowongan gratis) | Rp0 | ~Rp1.900 | −Rp1.900 | biaya akuisisi |
| Pencari kerja gratis (per pengguna aktif/bulan) | Rp0 | ~Rp310 | −Rp310 | biaya akuisisi |

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

> **Belum disesuaikan dengan harga baru.** Tabel di bawah masih dihitung dari Beacon Rp29.000 / Lighthouse Rp99.000 / Prism Rp25.000. Harga baru menaikkan kontribusi employer (+78% Beacon, +56% Lighthouse) dan menurunkan Prism (−28% harga, tapi margin naik 69%→83%), sehingga bulan impas kemungkinan **lebih awal** dari M15 — tapi konversi pada titik harga baru **belum diuji**, jadi kami tidak mengarang angkanya. Jangan kutip baris di bawah sebagai proyeksi terkini.

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
- Konteks: angkatan kerja 154,91 juta; TPT 4,68%; rata-rata upah Rp3,29 juta (BPS Feb 2026) [S15].

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
- [S15] BPS, Ketenagakerjaan Februari 2026: https://www.bps.go.id/id/pressrelease/2026/05/05/2574/tingkat-pengangguran-terbuka--tpt--sebesar-4-68-persen--rata-rata-upah-buruh-sebesar-3-29-juta-rupiah-.html
- [S16] Sektor alih daya (ABADI/FAADI): https://abadi.id/

> **Sebelum dipakai di pitch:** cek ulang tarif Xendit lewat kalkulator resminya, kurs pada hari-H, dan perbarui semua angka **(asumsi)** dengan data nyata dari `GET /api/v1/admin/metrics` setelah pilot.
