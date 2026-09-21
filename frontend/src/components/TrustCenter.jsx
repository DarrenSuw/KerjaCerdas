// Employer trust page — replaces the old NPWP "verification" mock.
// Badges candidates see on every job, the admin-review request, strikes, and
// the posting guidelines AutoMod enforces.
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { AlertTriangle, BadgeCheck, Globe, ShieldCheck } from 'lucide-react'
import { BrutalCard, KC, topBtn } from './_design'
import { EmailVerifyCard } from './ProofUI'
import { fetchEmployerTrust, requestAdminReview } from '../services/api'

const GUIDELINES = [
    'Tidak meminta biaya apa pun dari pelamar (pelatihan, seragam, administrasi, medical).',
    'Tidak mensyaratkan usia, penampilan fisik, atau jenis kelamin tanpa alasan pekerjaan yang jelas.',
    'Kontak lewat tombol Lamar di KerjaCerdas, bukan Telegram / nomor pribadi saja.',
    'Gaji ditulis per bulan dan masuk akal.',
]

function Badge({ ok, label, hint }) {
    return (
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <BadgeCheck size={20} color={ok ? '#059669' : KC.borderMuted} />
            <div>
                <div style={{ fontWeight: 800 }}>{label} {ok ? '✓' : ''}</div>
                <div style={{ fontSize: 13, color: KC.mute }}>{hint}</div>
            </div>
        </div>
    )
}

export default function TrustCenter() {
    const [trust, setTrust] = useState(null)
    const [links, setLinks] = useState('')
    const [busy, setBusy] = useState(false)

    const load = () => fetchEmployerTrust().then(setTrust).catch(() => setTrust(null))
    useEffect(() => { load() }, [])

    const submitReview = async () => {
        setBusy(true)
        try {
            await requestAdminReview(links.split(/\s+/).filter(Boolean))
            toast.success('Permintaan tinjauan dikirim ke admin')
            load()
        } catch (e) {
            toast.error(e.message)
        } finally {
            setBusy(false)
        }
    }

    const b = trust?.badges || {}
    const strikes = trust?.strikes || { strikes: 0 }
    return (
        <div style={{ display: 'grid', gap: 18 }}>
            <div>
                <h1 style={{ fontSize: 28, fontWeight: 900, margin: 0 }}>Kepercayaan & Verifikasi</h1>
                <p style={{ color: KC.mute, margin: '6px 0 0' }}>
                    Pelamar melihat badge ini di setiap lowongan. Semua dicek oleh KerjaCerdas sendiri —
                    tanpa NPWP, tanpa pihak ketiga.
                </p>
            </div>

            <EmailVerifyCard onVerified={load} />

            <BrutalCard>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 900, marginBottom: 12 }}>
                    <ShieldCheck size={18} /> Badge perusahaan
                </div>
                <div style={{ display: 'grid', gap: 12 }}>
                    <Badge ok={b.email_verified} label="Email terverifikasi" hint="Akun membuktikan email lewat kode OTP." />
                    <Badge ok={b.company_email} label="Email perusahaan terverifikasi"
                        hint="Email terverifikasi memakai domain yang sama dengan website perusahaan (bukan gmail/yahoo). Isi website di Profil Perusahaan." />
                    <Badge ok={b.admin_reviewed} label="Ditinjau admin"
                        hint="Admin KerjaCerdas memeriksa bukti publik usaha kamu secara manual." />
                </div>
                <p style={{ fontSize: 13, color: KC.mute, marginTop: 12 }}>
                    Dengan badge email perusahaan atau &quot;Ditinjau admin&quot;, lowongan baru langsung tayang tanpa antre tinjauan.
                </p>
            </BrutalCard>

            {!b.admin_reviewed && (
                <BrutalCard color={KC.surface}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 900 }}>
                        <Globe size={18} /> Ajukan &quot;Ditinjau admin&quot;
                    </div>
                    <p style={{ fontSize: 13, color: KC.mute }}>
                        Tempel 1–5 tautan publik (pisahkan dengan spasi): Google Maps usaha, akun Instagram bisnis, website, atau marketplace.
                        {trust?.review_status === 'pending' && <b> Status: sedang ditinjau.</b>}
                    </p>
                    <textarea value={links} onChange={(e) => setLinks(e.target.value)} rows={3}
                        placeholder="https://maps.google.com/... https://instagram.com/usahaku"
                        style={{ width: '100%', padding: 10, border: `1.5px solid ${KC.ink}`, borderRadius: 9, fontFamily: 'inherit', boxSizing: 'border-box' }} />
                    <button style={{ ...topBtn(KC.ink, '#fff'), marginTop: 8 }} disabled={busy || !links.trim()} onClick={submitReview}>
                        Kirim untuk ditinjau
                    </button>
                </BrutalCard>
            )}

            <BrutalCard color={strikes.strikes ? KC.roseSoft : KC.paper}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 900 }}>
                    <AlertTriangle size={18} /> Pedoman lowongan & peringatan
                </div>
                <p style={{ fontSize: 13, margin: '6px 0' }}>
                    Peringatan aktif: <b>{strikes.strikes}</b>
                    {strikes.limited && ' — dibatasi 1 lowongan aktif selama 30 hari'}
                    {strikes.suspended && ' — akun ditangguhkan, ajukan banding ke admin'}
                    . Peringatan hangus setelah 90 hari tanpa pelanggaran baru.
                </p>
                <ul style={{ fontSize: 13, paddingLeft: 18, margin: 0, display: 'grid', gap: 4 }}>
                    {GUIDELINES.map((g) => <li key={g}>{g}</li>)}
                </ul>
            </BrutalCard>
        </div>
    )
}
