# Panduan Live Demo: KerjaCerdas (v2 — "Bukti, bukan klaim")

Panduan operasional untuk presenter. Inti cerita yang harus terlihat dalam 3 menit:
**kata kunci di CV tidak lagi menang — skill yang dibuktikan yang naik peringkat.**

Akun demo lengkap ada di [Demo Accounts](DEMO_ACCOUNTS.md); semua memakai `SEED_DEFAULT_PASSWORD`.

**Sebelum mulai:** jalankan `python -m scripts.seed_all`, set `ADMIN_ROUTES_ENABLED=true` +
`ADMIN_EMAILS` berisi email admin, lalu **pasang satu lowongan peraga** dari akun employer mana pun dan
catat kode publiknya dari **Lowongan Saya → Bagikan**. Siapkan dua akun pelamar: satu yang CV-nya penuh
kata kunci, satu yang sudah lulus kuis — inilah perbandingan yang jadi inti demo. Siapkan juga
**video rekaman 90 detik + tangkapan layar** di laptop sebagai cadangan bila koneksi bermasalah.

---

## 🎬 Sesi 1 (90 detik): Kata kunci vs bukti — inti demo

### 1.1 — Pelamar datang lewat QR
- **Aksi:** tunjukkan poster QR lowongan peraga (**Lowongan Saya → Bagikan → Cetak poster**), lalu
  pindai sendiri dengan ponsel dan tampilkan layarnya.
- **Yang ditunjukkan:** tanpa install aplikasi, pelamar mendaftar dengan email, mengisi profil singkat
  (atau unggah CV), lalu melihat skill apa saja yang diminta lowongan.

### 1.2 — Kuis skill (±3 menit, boleh dipercepat di demo)
- **Aksi:** klik **Ikut kuis** pada skill *Excel* (atau skill apapun). 5 soal skenario, timer berjalan.
- **Yang ditunjukkan:** jika skill belum ada di bank soal, AI membuatkannya secara *real-time* (ditebus 1x biaya AI). Soal dan urutan pilihan diacak per percobaan; jawaban dinilai di server dengan kunci jawaban (penilaian tanpa panggilan AI, jadi Rp0 per percobaan). Lulus 4/5 → badge **✓ Terbukti** berlaku 6 bulan dan berlaku di semua lowongan, bukan hanya lowongan ini.

### 1.3 — Peringkat berubah di sisi HR
- **Aksi:** pindah ke akun employer → **Kandidat → Pelamar**. Pelamar yang baru lulus kuis berada di
  atas pelamar yang CV-nya penuh kata kunci. Skor dihitung ulang setiap daftar dibuka, jadi kenaikannya
  terlihat langsung.
- **Kalimat kunci:** *"Dua pelamar sama-sama menulis Excel di CV. Yang satu membuktikannya. Skill klaim
  dihitung 30%, yang terbukti 85% — itu sebabnya peringkatnya berbeda."*

---

## 🎬 Sesi 2 (60 detik): Sisi HR

### 2.1 — Pasang lowongan & bagikan
- **Aksi:** login akun employer mana pun → **Pasang Lowongan** (gratis) → setelah tayang buka
  **Lowongan Saya** → **Bagikan** → *Cetak poster*.
- **Yang ditunjukkan:** HR menaruh link di bio Instagram / grup WhatsApp / poster di toko. Pelamar masuk
  ke satu daftar terperingkat, bukan membanjiri WhatsApp.

### 2.2 — Daftar pelamar & alat wawancara
- **Aksi:** buka **Kandidat → Pelamar**.
- **Yang ditunjukkan:** pelamar diurutkan skor yang dihitung ulang setiap dibuka, dengan badge per skill
  (Klaim / ✓ Terbukti / Dikonfirmasi HR). Klik **Wawancara & konfirmasi skill** → pertanyaan wawancara
  fokus ke skill yang masih klaim ("jelaskan contoh nyatanya").
- **Setelah wawancara:** HR mencentang *Terbukti* → menjadi bukti terkuat (bobot 1,0) di profil kandidat.
- **Paket:** Spark gratis memeringkat 20 pelamar pertama; Beacon Rp29.000/lowongan membuka semuanya +
  pertanyaan wawancara AI + ekspor CSV.

### 2.3 — AutoMod (tunjukkan yang ditolak)
- **Aksi:** pasang lowongan uji berisi *"Wajib bayar biaya seragam Rp250.000. Usia maksimal 23 tahun."*
- **Yang ditunjukkan:** ditolak otomatis + pemberitahuan berisi **kalimat mana** yang bermasalah, cara
  memperbaikinya, tombol edit & kirim ulang, dan banding. Pelanggaran berulang → peringatan → dibatasi
  → ditangguhkan.

---

## 🎬 Sesi 3 (30 detik): Admin & angka

- **Aksi:** login akun admin → `/admin`.
- **Moderasi:** antrean lowongan yang ditahan + banding, tombol Tayangkan/Tolak.
- **Metrik:** biaya AI **per aksi** dihitung dari token asli di `ai_logs` × harga Gemini × kurs;
  funnel lamaran per sumber (papan/link); **tingkat wawancara per band skor** — inilah yang nanti
  menjawab pertanyaan juri *"apakah skor tinggi benar-benar lolos wawancara?"* begitu data pilot masuk.
- **Bank soal:** semua soal awal berstatus **draf** sampai ditinjau praktisi HR — ditandai jujur di UI.

---

## 💡 Pertanyaan yang sering muncul

**T:** *Pelamar bisa merekayasa CV agar skornya naik — bagaimana Anda memverifikasinya?*
**J:** Skill yang hanya tertulis di CV dihitung 30%. Yang lulus kuis 85%, yang dikonfirmasi HR setelah
wawancara 100%. Jadi menumpuk kata kunci hampir tidak menggerakkan skor. Kami juga menyimpan cuplikan
tingkat bukti saat melamar, sehingga bisa diaudit.

**T:** *Kuis kan bisa dibantu orang lain atau AI?*
**J:** Bisa — kami tidak mengklaim anti-curang. Yang kami lakukan: soal acak, urutan pilihan acak,
timer, jeda mengulang, lalu **pertanyaan wawancara yang meminta kandidat menjelaskan jawabannya
sendiri**. Kuis menyaring, wawancara memastikan, dan konfirmasi HR yang menjadi bukti final.

**T:** *Bagaimana data pribadi dilindungi?*
**J:** Kami **tidak mengumpulkan NIK, KTP, ijazah, atau NPWP** — kolomnya sudah dihapus dari basis data.
Yang diverifikasi hanya email (OTP). Email, nomor telepon, dan NIK yang tertulis di CV disamarkan dengan
aturan tetap **sebelum** teks dikirim ke Gemini. Kandidat yang belum melamar tampil anonim di talent
pool. Keputusan akhir tetap pada manusia, dan pelamar bisa meminta peninjauan manusia (UU PDP).

**T:** *Bagaimana cara Anda menghasilkan uang?*
**J:** Employer: gratis memasang lowongan, Rp29.000/lowongan (Beacon) atau Rp99.000/bulan (Lighthouse).
Pencari kerja: gratis, dengan Prism Rp25.000/30 hari yang hanya menambah kuota — **membayar tidak
pernah menaikkan skor**. Pembayaran saat ini QRIS/transfer yang dikonfirmasi admin; gateway menyusul.
Model Pay-to-Unlock lama sudah dihapus (alasannya di [BUSINESS_MODEL.md](BUSINESS_MODEL.md)).

**T:** *Berapa biaya AI per pengguna?*
**J:** Terukur, bukan perkiraan: `GET /api/v1/admin/metrics` menghitung dari token yang benar-benar
terpakai. Kuis dan skor tidak memanggil AI sama sekali.
