# Pitch Canvas — KerjaCerdas (booth, 1 slide)

> **Cara pakai:** tiap `##` di bawah = satu kotak di Pitch Canvas. Teks **tebal** masuk ke slide;
> teks biasa adalah catatan presenter (jangan dicetak di slide).
>
> **Aturan main dokumen ini:** setiap angka di sini bisa ditunjukkan sumbernya — dari kode, dari
> `/admin → Metrik`, atau dari sumber publik yang dikutip di [BUSINESS_MODEL.md](BUSINESS_MODEL.md).
> Yang belum ada buktinya ditulis `[RENCANA]` atau `[BELUM ADA]`, tidak disamarkan. Juri Digdaya
> menjatuhkan nilai kami justru pada klaim tanpa bukti — lihat [§Tanggapan Feedback](#lampiran--tanggapan-langsung-ke-feedback-juri).

---

## Simple Statement

> **"CV bisa ditulis siapa saja. Kami membuat skill harus dibuktikan — lalu mengurutkan pelamar
> berdasarkan bukti itu, bukan kata kunci."**

Satu kalimat cadangan kalau yang di atas terlalu abstrak untuk pengunjung booth:
*"Warung dan UMKM pasang lowongan lewat QR, pelamar ikut kuis skill 3 menit, HR dapat daftar
pelamar yang sudah diurutkan — gratis untuk mulai."*

---

## Pain (+ Gain)

**Sisi UMKM/HR — masalah yang terasa hari ini:**
- Pasang "Dicari Admin, kirim CV ke WA" → **puluhan PDF masuk WhatsApp, tidak terurut**.
- Dibaca satu per satu. Banyak CV mengklaim skill yang tidak dikuasai — **AI penulis CV memperparah**.
- Hasilnya: **wawancara untuk orang yang salah**. Itu jam kerja pemilik usaha yang hilang.

**Sisi pencari kerja:**
- Melamar banyak, **tidak pernah dapat kabar**, tidak tahu apa yang kurang.

**Gain:** HR membuka satu daftar yang sudah diperingkat lengkap dengan **skill mana yang sudah
terbukti**; pelamar melihat skor, celah skill, dan rekomendasi belajar — sekali buktikan, berlaku
di semua lamaran.

**Ukuran pasar (lantai, dihitung konservatif):** 89.141 usaha kecil+menengah terdaftar (SIDT-UMKM
Des 2025) × 4 lowongan/tahun × Rp29.000 ≈ **Rp10,3 M/tahun**; 7,24 juta penganggur (BPS Feb 2026)
× 2% × Rp25.000 × 3 bulan ≈ **Rp10,9 M/tahun**. **Total lantai ≈ Rp21 M/tahun.**

**Validasi kesediaan membayar: [BELUM ADA].** Nol perusahaan membayar. Ini kelemahan #2 di feedback
juri dan kami tidak menutupinya — target booth ada di [Call To Action](#call-to-action--end-statement).

---

## Product

**Alur employer (3 langkah):**
1. **Pasang lowongan** — ketik, tempel, atau unggah PDF; AI menarik judul, skill, pengalaman, pendidikan.
2. **Dapat link + poster QR** (`kerjacerdas.tech/j/ABC2345`) → ditempel di bio Instagram, grup WA,
   atau dicetak di toko. **Employer tidak perlu pindah kanal — hanya lamarannya yang pindah tempat.**
3. **Buka dashboard** → pelamar sudah diperingkat, tiap skill berlabel *Klaim / ✓ Terbukti / Dikonfirmasi HR*.

**Alur pencari kerja (±5 menit, tanpa install):**
Scan QR → daftar pakai email (OTP) → unggah CV atau isi profil singkat → **ikut kuis skill 5 soal**
→ lamar. Badge ✓ Terbukti berlaku **180 hari di semua lowongan**, bukan cuma yang ini.

**Rumus skor (ditampilkan apa adanya ke kandidat):**

```
skor = 0.35 × kemiripan CV–lowongan
     + 0.40 × skill DITIMBANG BUKTI      ← klaim 0.30 · lulus kuis 0.85 · dikonfirmasi HR 1.00
     + 0.15 × pengalaman
     + 0.10 × pendidikan vs syarat lowongan
```

**Bobot bukti sengaja lebih besar dari kemiripan teks.** Kemiripan teks justru naik kalau CV
menyalin kalimat iklan — itu persis yang dilakukan penumpuk kata kunci. Dengan 0.35/0.40, penumpuk
kata kunci butuh keunggulan kemiripan **0,63** untuk mengalahkan kandidat yang membuktikan semua
skill — di luar rentang yang bisa dicapai kemiripan pada pasangan CV–lowongan nyata.

**Sudah dibangun & diuji:** 540 tes backend + 39 tes frontend lolos, lint bersih.

---

## Product Demo

**Yang dijalankan langsung di booth (semua siap sebelum booth buka — bukan eksperimen):**

| # | Aksi | Yang terlihat | Waktu |
|---|---|---|---|
| 1 | Pengunjung scan QR dari poster | Halaman lowongan publik, tanpa login | 10 dtk |
| 2 | Daftar email → profil singkat | Skor awal muncul, skill masih *Klaim* | 60 dtk |
| 3 | **Ikut kuis Excel** (5 soal skenario, timer) | Lulus 4/5 → badge **✓ Terbukti** | 90 dtk |
| 4 | Buka sisi HR | **Peringkatnya naik melewati CV penuh kata kunci** | 15 dtk |
| 5 | Pasang iklan "wajib bayar biaya seragam Rp250.000" | **AutoMod menolak** + notifikasi berisi kalimat mana yang salah & cara memperbaiki | 20 dtk |
| 6 | Buka `/admin → Metrik` | **Biaya AI per aksi dalam Rupiah, dari token asli** | 15 dtk |

**Cadangan wajib:** rekaman 90 detik + tangkapan layar di laptop. Pada sesi final, demo kami gagal
tayang karena koneksi dan pertanyaan juri soal bukti tidak pernah terjawab. **Itu tidak boleh terulang.**

---

## What's Unique

**1. Profil terbukti hanya ada di KerjaCerdas.** Tiap kuis lulus dan tiap konfirmasi HR menempel di
profil kandidat **di sini**. Peniru mulai dari **nol kandidat terbukti**. Fitur bisa disalin dalam
sebulan; kumpulan profil terbukti tidak bisa.

**2. QR tiap employer membawa pelamar baru.** Pelamar yang masuk lewat link satu employer ikut
dicocokkan ke lowongan lain. Pertumbuhan datang dari pelanggan yang memakai produk, bukan dari iklan.

**3. Model bisnis kami bertentangan dengan job board.** Papan lowongan untung dari **banyak**
lamaran. Kami menang dengan mengirim **lebih sedikit, tapi lebih tepat**. Menyalin "bukti dulu"
melawan sumber pendapatan mereka sendiri.

**4. Bank soal berbahasa Indonesia untuk skill non-teknis** (kasir, administrasi, melayani pelanggan)
— kerja lokal yang lambat, dan makin akurat tiap ada konfirmasi HR.

**Kalimat jujur untuk juri:**
> *"Fiturnya bisa ditiru. Profil yang sudah terbukti dan kepercayaan HR tidak bisa disalin."*

---

## Customer Traction

**Jujur di depan — ini sisi terlemah kami, dan juri sudah menandainya.**

| Klaim | Status |
|---|---|
| Prototipe berjalan, teruji otomatis | ✅ 540 tes backend + 39 frontend, lint bersih |
| Alignment PS-2 | ✅ Dinilai **"Sangat Kuat"** oleh juri |
| Kualitas prototipe | ✅ Dinilai **"Sangat Kuat — Menonjol"** oleh juri |
| Validasi pencari kerja | ⚠️ <10 orang, lingkaran pertemanan, **belum terdokumentasi rapi** |
| Perusahaan membayar | ❌ **Nol** |
| Validitas prediktif skor | ⚠️ **Belum diuji** — mekanismenya sudah jalan, datanya belum ada |

**Yang sudah kami bangun untuk menjawabnya:** skor + cuplikan bukti skill **disimpan saat melamar**,
tiap perubahan status dicatat, dan `/admin → Metrik` sudah menghitung **tingkat wawancara per band
skor**. Begitu pilot jalan, pertanyaan juri *"apakah skor tinggi benar-benar lolos wawancara?"*
terjawab angka, bukan opini. **Hari ini angkanya masih kosong — dan layarnya menulis "belum ada data",
bukan 0%.**

---

## Business Model

**Employer bayar untuk menyaring, bukan untuk mencari.** *(Pay-to-Unlock kontak Rp50.000 dihapus —
menagih sourcing, bocor lewat teaser, berisiko UU PDP; alasan lengkap di BUSINESS_MODEL.md.)*

| | Spark | Beacon | Lighthouse | Prism (pencari kerja) |
|---|---|---|---|---|
| Harga | **Rp0** | **Rp29.000**/lowongan | **Rp99.000**/bulan | **Rp25.000**/30 hari |
| Lowongan aktif | 1 | 1 per pembelian | 5 | — |
| Pelamar diperingkat | **20 skor teratas** | Semua | Semua | — |
| Pertanyaan wawancara AI | — | ✓ | ✓ | — |
| Ekspor CSV | — | ✓ | ✓ | — |

**Margin per penjualan (biaya AI dihitung dari token asli × harga Gemini × kurs Rp17.600):**

| Produk | Harga | Biaya langsung | Kontribusi | Margin |
|---|---|---|---|---|
| Beacon (1 lowongan, ~30 pelamar) | Rp29.000 | ~Rp3.400 | **Rp25.600** | **88%** |
| Lighthouse (bulanan, ~3 lowongan) | Rp99.000 | ~Rp10.250 | **Rp88.750** | **90%** |
| Prism (30 hari) | Rp25.000 | ~Rp7.715 | **Rp17.300** | **69%** |

**Kenapa marginnya tinggi:** **kuis dan skor tidak memanggil AI sama sekali — Rp0 per percobaan.**
AI mahal hanya dipakai sekali (baca CV ~Rp99, baca lowongan + AutoMod ~Rp130) lalu dipakai ulang.

**Aturan yang tidak kami langgar:** **membayar tidak pernah menaikkan skor atau peringkat siapa pun.**
Hanya kuis dan konfirmasi HR yang menggerakkan skor. Ini yang menjaga kepercayaan HR — dan itu aset
kami.

**Pembayaran:** QRIS/transfer manual → admin aktifkan `[MANUAL]`. Gateway Midtrans/Xendit (QRIS 0,7%)
`[RENCANA]` setelah PT berdiri — biaya setup Rp0, jadi bukan penghalang.

---

## Investment

**Rp200.000.000 untuk 10%** (pra-uang Rp1,8 M · pasca-uang Rp2,0 M), **dua tahap**:
- **Rp100 jt saat tanda tangan.**
- **Rp100 jt di bulan ke-6, bila:** ≥30 employer membayar · ≥60% pelamar ikut ≥1 kuis ·
  ≥50 pembeli Prism · biaya terukur per Beacon ≤ Rp5.000.

| Penggunaan | Jumlah | % |
|---|---|---|
| Biaya pendirian sekali jalan (PT, merek, dokumen privasi, tinjauan bank soal) | Rp45 jt | 22,5% |
| Menutup rugi sampai titik impas | Rp57 jt | 28,5% |
| Tinjauan keamanan + go-live payment gateway | Rp12 jt | 6% |
| Akuisisi employer & pencari kerja (job fair kampus, konten, poster) | Rp40 jt | 20% |
| Bantalan skenario buruk | Rp46 jt | 23% |

**Angka kunci (skenario dasar):** pendapatan Tahun 1 ≈ Rp60 jt · Tahun 2 ≈ Rp360 jt ·
**titik impas bulan ke-15** · **kas terdalam ≈ −Rp101 jt** · gaji pendiri baru mulai bulan ke-20,
dan hanya dari laba.

**Jujur:** harga yang terjangkau bagi UMKM membuat titik impas lebih lambat. Itu pilihan sadar,
bukan kelalaian hitungan.

---

## Team

Empat orang, peran lengkap dari AI sampai go-to-market — komposisi ini dinilai juri sebagai
kekuatan tim.

| Nama | Peran | Kontribusi konkret |
|---|---|---|
| **David** | AI / Backend | Mesin pencocokan, bobot bukti, AutoMod, migrasi & keamanan |
| **Darren** | Product / UX | Alur seeker–employer, halaman lamaran publik, desain sistem UI |
| **Vanessa** | Systems / Impact | Model data hasil, metrik admin, pengukuran dampak |
| **Jason** | Business / Deployment | Model bisnis, harga, biaya infrastruktur, rencana pilot |

Yang membedakan: **kami memperbaiki produk berdasarkan kritik, bukan membela slide.** Pay-to-Unlock
dihapus, e-KYC NIK dihapus, klaim "94% akurasi" dan "100% e-KYC" dihapus — semuanya karena tidak
bisa kami buktikan.

---

## Call To Action & End Statement

**Untuk pemilik usaha / HR di booth:**
> **"Pasang satu lowongan sekarang, gratis. Kami cetakkan poster QR-nya hari ini juga."**

**Untuk pencari kerja:**
> **"Scan, ikut satu kuis 3 menit, dan bawa pulang badge ✓ Terbukti yang berlaku di semua lamaran."**

**Untuk investor / offtaker:**
> **"Kami tidak minta Anda percaya angka proyeksi. Kami minta 30 hari: 10 UMKM pilot, lalu kita
> lihat bersama tingkat wawancara per band skor di dashboard yang sama."**

**Target terukur 3 hari booth:** 15 UMKM memasang lowongan gratis · 100 pencari kerja menyelesaikan
≥1 kuis · **3 UMKM menyatakan bersedia membayar Beacon** (tanda tangan surat minat, bukan lisan).

**Kalimat penutup:**
> **"Pasar kerja Indonesia tidak kekurangan lamaran. Yang kurang adalah bukti. Kami membangun
> tempat bukti itu disimpan."**

---

## Why You?

Kami membangun ini karena kami **adalah** penggunanya: empat mahasiswa yang mengirim CV dan tidak
pernah dapat balasan, dengan keluarga yang menjalankan usaha kecil dan merekrut lewat grup WhatsApp.

Yang membuat kami layak dipercaya bukan pitch ini, tapi **jejak revisinya**: saat juri bilang model
pendapatan kami tidak masuk akal, kami **menghapus** model itu. Saat panelis bertanya bagaimana CV
rekayasa diverifikasi, kami **mengubah rumus skornya** sampai kata kunci benar-benar kalah — lalu
menuliskannya sebagai tes supaya klaim itu tidak bisa diam-diam jadi salah lagi.

> **"Kami tidak akan mengklaim angka yang tidak bisa kami tunjukkan sumbernya."**

---

## Lampiran — Tanggapan langsung ke feedback juri

| Catatan juri | Tindakan |
|---|---|
| "Pesaing bisa dengan mudah copy" | Pertahanan diganti: profil terbukti + kepercayaan HR (bukan closed loop / fine-tuning). Lihat [What's Unique](#whats-unique) |
| "Ada mekanisme ban / turun peringkat?" (tak terjawab) | **AutoMod + notifikasi pemasang + banding + strike 1/2/3 + laporan kandidat** — sudah dibangun & diuji |
| "Redaksional berbasis prompt bisa gagal?" (tak terjawab) | Penyamaran PII pakai **aturan regex tetap sebelum tiap panggilan AI**, bukan instruksi ke AI. NIK tidak dikumpulkan sama sekali |
| "Skor tinggi benar lolos interview?" (tak terjawab) | Skor + bukti disimpan saat melamar; status dicatat; `/admin → Metrik` menghitung tingkat wawancara per band |
| "Biaya per pengguna & margin" | Dihitung dari token asli di `ai_logs`, tampil di dashboard admin. Lihat [Business Model](#business-model) |
| "Dari mana lowongan pertama?" | Pasang gratis + QR di kanal yang sudah dipakai employer. Lihat [Product](#product) |
| Mentor: "bobot per skill, bukan per job" | **Persis yang dibangun** — bobot bukti dihitung per skill |
| Validasi tipis, nol perusahaan membayar | **Belum selesai.** Target booth di [Call To Action](#call-to-action--end-statement) |

**Yang masih `[RENCANA]` dan harus dikatakan apa adanya kalau ditanya:** gateway pembayaran,
kalibrasi skor terhadap hasil rekrutmen nyata, kemitraan afiliasi ed-tech, dan **tinjauan manusia
atas bank soal** (48 soal awal masih draf AI, 6 soal per skill — sedang diperluas).
