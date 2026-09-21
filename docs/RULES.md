# Aturan KerjaCerdas

Satu daftar, dipakai tiga pihak: **pemasang lowongan** sebelum menulis iklan,
**pelamar** saat melaporkan, dan **peninjau AI** saat memeriksa laporan. Tidak
ada yang dimoderasi dengan standar yang tidak bisa dia baca.

Sumber kebenarannya ada di kode: `backend/app/services/trust/rules.py`.
Daftar ini juga disajikan lewat `GET /api/v1/public/jobs/rules`.

---

## Aturan lowongan

| ID | Aturan | Tingkat |
|---|---|---|
| **R1** | Lowongan tidak boleh meminta biaya apa pun dari pelamar | **Keras** |
| **R2** | Lowongan harus mewakili pekerjaan dan perusahaan yang nyata | Lunak |
| **R3** | Syarat tidak boleh diskriminatif | Lunak |
| **R4** | Proses lamaran tidak boleh dipindahkan ke kanal pribadi | Lunak |
| **R5** | Gaji dan bentuk kerja harus ditulis jujur | Lunak |
| **R6** | Dilarang meminta dokumen identitas sensitif di tahap lamaran | Lunak |

**Keras** = ditolak otomatis sebelum tayang, dan pemasangnya dapat *strike*.
**Lunak** = ditahan untuk ditinjau manusia. AI tidak pernah menolak sendiri.

Rincian dan cara memperbaiki tiap aturan ada di `rules.py` dan ikut dikirim di
notifikasi penolakan, lengkap dengan kalimat mana yang bermasalah.

---

## Bagaimana sebuah laporan diproses

Ini menggantikan aturan lama "3 laporan → lowongan disembunyikan", yang
sekaligus **terlalu keras** (menghapus atas tuduhan, tanpa memeriksa apa pun)
dan **terlalu lemah** (penipuan nyata tetap tayang sampai orang ketiga
kebetulan melapor). Tiga akun baru cukup untuk menurunkan iklan pesaing.

```
Pelamar melapor + mengutip aturan (R1..R6)
        │
        ▼
Bobot pelapor dihitung — bukan dihitung jumlah akunnya
  email terverifikasi & akun ≥ 3 hari .... syarat minimum, di bawah ini bobot 0
  pernah melamar ke lowongan itu ......... +1
  punya laporan yang pernah terbukti ..... +1
  ≥ 3 laporan ditolak sebelumnya ......... bobot 0 (tetap dicatat untuk admin)
        │
        ▼
Total bobot ≥ 5 DAN pelapor ≥ 2 orang
        │
        ▼
Status "flagged" — LOWONGAN TETAP TERLIHAT, dengan catatan sedang ditinjau
        │
        ▼
Peninjau AI memeriksa lowongan HANYA terhadap aturan yang dikutip
        ├─ LANGGAR  → ditahan (disembunyikan), pemasang diberi tahu, bisa banding
        ├─ TIDAK    → tetap tayang, laporan masuk antrean admin
        └─ RAGU     → tetap tayang, antrean admin
```

**Tidak ada jalur yang menyembunyikan lowongan hanya karena dilaporkan.**
Penyembunyian butuh putusan terhadap aturan tertentu — dari AI atau admin — dan
admin selalu bisa membatalkannya.

AI sengaja tidak pernah ditanya "apakah ini penipuan". Ia diberi satu aturan,
beserta bunyi aturannya, dan hanya boleh menjawab LANGGAR / TIDAK / RAGU.
Pertanyaan terbuka adalah tempat model berhalusinasi, dan mode kegagalan
"model yang ragu menurunkan iklan perusahaan sungguhan" akan menghilangkan sisi
pasar yang paling sulit kami dapatkan kembali.

---

## Tangga sanksi pemasang lowongan

| Pelanggaran | Akibat |
|---|---|
| 1 | Peringatan |
| 2 | Dibatasi 1 lowongan aktif selama 30 hari |
| 3 | Akun ditangguhkan |

Strike kedaluwarsa 90 hari setelah yang terakhir. Semua dicatat di
`moderation_events`.

## Tangga sanksi pelamar

Sengaja lebih lambat daripada tangga pemasang: satu lowongan dilihat ratusan
orang, satu pelamar tidak, dan pelamar yang salah dibatasi kehilangan
penghasilan.

| Laporan terbukti | Akibat |
|---|---|
| 1 | Peringatan |
| 2 | Dibatasi 5 lamaran per hari |
| 3 | Akun ditangguhkan |

Juga kedaluwarsa setelah 90 hari.

---

## Apa yang kami verifikasi, dan apa yang tidak

Kami **tidak** mengumpulkan NIK, KTP, ijazah, atau NPWP. Bukan hanya karena UU
PDP — tapi karena mengumpulkannya tidak menyelesaikan masalah ini. Penipuan
lowongan di Indonesia rutin jalan memakai NIK asli, curian atau dibeli, dan
tanpa akses Dukcapil yang bisa kami periksa hanyalah formatnya: 16 digit. Itu
bukan verifikasi.

Yang kami periksa adalah hal yang mahal untuk dipalsukan:

**Pemasang lowongan** — domain email harus cocok dengan website perusahaan
(penyedia email gratis tidak memenuhi syarat), jejak publik dicek admin (Google
Maps, Instagram bisnis, website), dan lowongan pertama ditahan sampai
tepercaya.

**Pelamar** — kami tidak menanyakan siapa dia, kami menguji apa yang bisa dia
kerjakan. Ijazah membuktikan seseorang pernah kuliah; kuis membuktikan dia bisa
mengerjakan. Dokumen identitas tetap diperiksa HR saat wawancara, di titik yang
memang tepat, dan di situ tanggung jawabnya ada pada pemberi kerja.
