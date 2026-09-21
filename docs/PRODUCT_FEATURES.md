# Product Features: KerjaCerdas (v2 — "Bukti, bukan klaim")

Status setiap fitur ditandai jujur: `[BUILT + TESTED]`, `[BUILT, MANUAL PAYMENT]`, `[BUILT, BANK SOAL DRAF]`, atau `[PLANNED]`.

---

## 1. AI Job Matching berbobot bukti `[BUILT + TESTED]`

CV PDF diekstraksi Gemini menjadi skill/pengalaman/pendidikan, lalu jadi vektor 768 dimensi yang dicocokkan dengan lowongan aktif lewat pgvector (index HNSW).

```python
final_score = (
    cosine_similarity  * 0.35 +   # kemiripan makna CV vs lowongan
    proven_skill_score * 0.40 +   # skill, DITIMBANG BUKTI (lihat bawah)
    experience_fit     * 0.15 +   # masa kerja vs syarat minimum
    education_fit      * 0.10     # jenjang vs education_min lowongan
)
```

**Bagian skill ditimbang bukti** (`backend/app/services/matching/evidence.py`):

| Tingkat bukti | Cara diperoleh | Bobot |
|---|---|---|
| **Klaim** | hanya tertulis di CV/profil | 0,30 |
| **Terbukti (kuis)** | lulus kuis skill, berlaku 180 hari | 0,85 |
| **Dikonfirmasi HR** | employer mencentang "terbukti" setelah wawancara | 1,00 |

Contoh (lowongan butuh Excel, Customer Service, Administrasi):
- Kandidat A mengklaim ketiganya → (0,3+0,3+0,3)/3 = **0,30**
- Kandidat B lulus kuis Excel & CS, klaim Administrasi → (0,85+0,85+0,3)/3 = **0,67**

Skill wajib berbobot 80% dan *nice-to-have* 20% dari bagian skill. Filter lokasi/gaji tetap eliminasi langsung (bukan bagian skor). Bonus "recency" 0,05 yang dulu diberikan rata ke semua kandidat **dihapus** karena tidak membawa sinyal apa pun.

**Perubahan lain:** pendidikan kini dibandingkan dengan `education_min` lowongan (dulu hanya "punya pendidikan atau tidak").

**API:** `POST /api/v1/uploads/cv`, `POST /api/v1/agent/invoke`, `GET /api/v1/jobs`
**Komponen:** `CVUploader`, `SeekerMatchResults`, `JobDetailModal`, `ProofUI`

---

## 2. Kuis skill → badge ✓ Terbukti `[BUILT, BANK SOAL DRAF]`

- 5 soal skenario per skill, diambil acak dari bank soal; urutan pilihan diacak per percobaan.
- Batas waktu 45 detik per soal dijaga server; jawaban **tidak pernah** dikirim ke browser sebelum dikumpulkan.
- Dinilai dengan kunci jawaban — penilaian per percobaan **tanpa panggilan AI** (biaya Rp0).
- Lulus = 4/5 → skill menjadi **✓ Terbukti** selama 180 hari. Gagal → boleh mengulang setelah 7 hari (Prism: 2 hari).
- **Skill baru → antrean tinjauan, bukan kuis instan `[BUILT, DRAFT CONTENT]`:** jika pelamar mencoba kuis untuk skill yang belum ada di bank soal, AI (Gemini) menyusun 6 draf soal + kunci jawaban **satu kali** (dedup atas seluruh baris, termasuk yang belum ditinjau, jadi tidak pernah menagih ulang) dan menyimpannya sebagai `reviewed=false`. Soal draf **tidak diujikan**: pelamar menerima "kuis sedang disiapkan" dan skill itu tetap dihitung sebagai klaim (30%). Setelah admin menyetujui, bank itu aktif untuk semua pemegang skill tersebut sekaligus.
- **Mengapa tidak langsung diujikan:** kunci jawaban yang salah akan menilai jawaban benar sebagai salah tanpa cara mendeteksinya; dua kandidat tidak lagi mengerjakan kuis yang sebanding (padahal bobot 85% mensyaratkan itu); dan pelamar bisa mengarang nama skill untuk memanggil kuis baru yang belum ditinjau. Permintaan skill tanpa kuis dicatat sebagai event `quiz_unavailable` agar antrean ditinjau sesuai kebutuhan nyata.
- Anti-curang jujur: soal acak + timer + rotasi bank + pertanyaan wawancara "jelaskan jawabanmu". Kuis menyaring, wawancara memastikan.

**API:** `GET /api/v1/quiz/skills`, `POST /api/v1/quiz/start`, `POST /api/v1/quiz/submit`
**Komponen:** `SkillProofPage`, `QuizModal`

---

## 3. Link + poster QR lowongan `[BUILT + TESTED]`

Setiap lowongan punya kode publik → `/j/<kode>`. Employer membagikannya di bio Instagram, grup WhatsApp, atau mencetak poster QR (QR dirender server dengan `segno`, tanpa layanan pihak ketiga). Pelamar membuka halaman publik tanpa login, mendaftar, mengisi profil singkat (atau upload CV), boleh ikut kuis, lalu melamar — semuanya masuk ke satu daftar pelamar terperingkat.

**API:** `GET /api/v1/public/jobs/{code}`, `GET /api/v1/public/jobs/{code}/qr.svg`
**Komponen:** `PublicJobPage`, `QuickProfileForm`, `JobShareModal`

---

## 4. Skill Gap Analyzer & Career Advisor `[BUILT + TESTED]`

Peta skill gap terhadap lowongan target, estimasi jam belajar, rekomendasi kursus (Gemini → katalog internal sebagai cadangan), dan advisor percakapan berbasis LangGraph. Kuota advisor: gratis 10 pesan/hari, Prism 20 pesan/hari — satuan yang sama, dan yang berbayar selalu lebih besar.

**API:** `POST /api/v1/seeker/skill-gap`, `GET /api/v1/seeker/skill-gap/latest`, `POST /api/v1/agent/invoke`

---

## 5. Sisi employer: pelamar terperingkat, bukan kontak terkunci `[BUILT + TESTED]`

- **Tab Pelamar:** diurutkan skor proof-weighted yang dihitung ulang setiap kali dibuka (kandidat yang baru lulus kuis naik peringkat), lengkap dengan badge bukti per skill, status pipeline, catatan.
- **Pertanyaan wawancara AI** per kandidat, fokus ke skill yang masih klaim; ada cadangan template bila AI tidak tersedia.
- **Konfirmasi "skill terbukti"** setelah wawancara → bukti terkuat (bobot 1,0) yang menempel pada profil kandidat.
- **Ekspor CSV** pelamar.
- **Talent pool anonim:** kandidat yang belum melamar ditampilkan tanpa nama, tanpa nama perusahaan/sekolah, tanpa kontak (mencegah identifikasi ulang; UU PDP).
- **Pay-to-Unlock dihapus** — alasan lengkap di [BUSINESS_MODEL.md](BUSINESS_MODEL.md#1-kenapa-pay-to-unlock-dihapus).

**API:** `GET /api/v1/employer/applications`, `GET /api/v1/employer/applications/{id}/interview-kit`, `POST /api/v1/employer/applications/{id}/confirm-skills`, `GET /api/v1/employer/jobs/{id}/applicants.csv`

---

## 6. AutoMod lowongan & sistem kepercayaan `[BUILT + TESTED]`

- Setiap lowongan diperiksa sebelum tayang: aturan tetap (minta biaya dari pelamar = **ditolak**; batas usia, syarat penampilan, jenis kelamin tanpa alasan, kontak Telegram-only, gaji di luar batas wajar = **ditahan**) + pemeriksaan AI opsional yang hanya boleh *menahan*.
- Pemasang menerima **pemberitahuan** berisi aturan yang dilanggar, kalimat yang ditandai, cara memperbaiki, tombol edit & kirim ulang, dan **banding**.
- **Strike ladder:** 1 = peringatan, 2 = dibatasi 1 lowongan aktif selama 30 hari, 3 = akun ditangguhkan; hangus setelah 90 hari bersih.
- **Laporan pengguna:** cukup laporan berbeda → lowongan disembunyikan untuk ditinjau admin.
- **Badge kepercayaan:** email terverifikasi → email domain perusahaan → "Ditinjau admin" (admin memeriksa tautan publik seperti Google Maps/Instagram bisnis).
- **Lowongan pertama** ditahan untuk tinjauan admin kecuali employer sudah punya badge domain/admin.

**API:** `POST /api/v1/public/jobs/{code}/report`, `POST /api/v1/employer/jobs/{id}/appeal`, `GET/POST /api/v1/employer/trust*`, `GET/POST /api/v1/admin/moderation/*`

---

## 7. Verifikasi email — satu-satunya cek identitas `[BUILT + TESTED]`

Kode OTP 6 digit dikirim ke email akun (Resend bila `RESEND_API_KEY` diisi; tanpa itu kode hanya muncul di respons saat mode demo dan **tidak pernah** di produksi). **NIK, KTP, ijazah, dan NPWP tidak dikumpulkan sama sekali** — identitas diperiksa HR saat wawancara. Kolom `nik`, `nik_verified`, `ijazah_verified`, dan `npwp` sudah dihapus dari basis data.

**API:** `GET /api/v1/verify/status`, `POST /api/v1/verify/email/send`, `POST /api/v1/verify/email/verify`

---

## 8. Paket & pembayaran `[BUILT, MANUAL PAYMENT]`

Spark (gratis) · Beacon Rp49.000/lowongan · Lighthouse Rp149.000/bulan · Prism Rp15.000/30 hari. Pesanan dibuat di aplikasi → bayar QRIS/transfer → **admin mengaktifkan** 30 hari. Gateway pembayaran `[PLANNED]`. Membayar tidak pernah mengubah skor atau peringkat.

**API:** `GET /api/v1/billing/plans`, `GET /api/v1/billing/me`, `POST /api/v1/billing/orders`, `POST /api/v1/admin/orders/{id}/activate`

---

## 9. Data hasil & metrik admin `[BUILT + TESTED]`

- Skor kecocokan + snapshot bukti skill disimpan **saat melamar**; setiap perubahan status lamaran dicatat di `application_status_events`.
- `GET /api/v1/admin/metrics` menghitung: **biaya AI per aksi** (dari token `ai_logs` × harga Gemini × kurs), funnel lamaran per sumber (board/link), **tingkat wawancara per band skor** (menjawab "apakah skor tinggi benar-benar lolos wawancara?"), tingkat lulus kuis per skill, statistik moderasi, dan pesanan paket.

---

## 11. Privasi & guardrail AI `[BUILT + TESTED]`

- **Redaksi PII sebelum AI:** email, nomor telepon, dan NIK 16 digit dihapus dengan aturan tetap sebelum teks dikirim ke Gemini (bukan sekadar instruksi prompt). CV berbasis teks diekstrak lokal lalu dikirim sudah tersamar; hanya PDF hasil pindai yang dikirim utuh.
- Anti prompt-injection, rate limit per rute, token efficiency gate, hallucination guard, fallback 3 model + circuit breaker.
- **Bukti tidak bisa dipalsukan dari klien:** skema input skill tidak punya kolom bukti; profil inline di endpoint agent direset ke "klaim" lalu bukti asli disalin dari profil tersimpan; edit profil / unggah CV ulang tidak menghapus badge yang sudah diraih.

---

## 12. Yang dihapus di v2

| Fitur lama | Status | Alasan |
|---|---|---|
| Pay-to-Unlock kontak (Rp50.000) | **Dihapus** | Menagih sourcing, bukan penyaringan; bocor lewat teaser; risiko UU PDP; tanpa gateway |
| e-KYC KTP/NIK, ijazah, NPWP | **Dihapus** | Mock tanpa otoritas; minimisasi data UU PDP |
| OTP SMS/WhatsApp | **Diganti email OTP** | Tanpa biaya provider dan bisa jalan hari ini |
| Klaim "94% akurasi", "100% profil terverifikasi e-KYC", "<8 detik" | **Dihapus dari UI** | Tidak ada dasar pengukuran |
