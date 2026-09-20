// Admin panel (accounts listed in ADMIN_EMAILS): moderation queue, "Ditinjau
// admin" reviews, manual-payment plan activation, question bank, metrics.
import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import AdminMetrics from './AdminMetrics'
import { BrutalCard, KC, topBtn } from './_design'
import { adminFetch, adminPost } from '../services/api'

const TABS = [['queue', 'Moderasi'], ['reviews', 'Tinjauan usaha'], ['orders', 'Pesanan paket'], ['questions', 'Bank soal'], ['metrics', 'Metrik']]
const PATHS = { queue: '/moderation/queue', reviews: '/employer-reviews', orders: '/orders?status_filter=pending', questions: '/questions', metrics: '/metrics' }

export default function AdminPanel() {
    const [tab, setTab] = useState('queue')
    const [data, setData] = useState(null)
    const [error, setError] = useState('')

    const load = useCallback(() => {
        setData(null)
        adminFetch(PATHS[tab]).then((d) => { setData(d); setError('') }).catch((e) => setError(e.message))
    }, [tab])
    useEffect(() => { load() }, [load])

    const act = async (path, body, msg) => {
        try { await adminPost(path, body); toast.success(msg); load() } catch (e) { toast.error(e.message) }
    }

    return (
        <div style={{ display: 'grid', gap: 16 }}>
            <h1 style={{ fontSize: 28, fontWeight: 900, margin: 0 }}>Admin</h1>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {TABS.map(([k, label]) => (
                    <button key={k} style={topBtn(tab === k ? KC.ink : '#fff', tab === k ? '#fff' : KC.ink)} onClick={() => setTab(k)}>{label}</button>
                ))}
            </div>
            {error && <BrutalCard color={KC.roseSoft}>{error} — hanya email di ADMIN_EMAILS dengan ADMIN_ROUTES_ENABLED=true.</BrutalCard>}
            {!error && !data && <p>Memuat…</p>}

            {data && tab === 'queue' && (data.items.length ? data.items.map((j) => (
                <BrutalCard key={j.job_id}>
                    <div style={{ fontWeight: 900 }}>{j.title} · {j.company_name}</div>
                    <p style={{ fontSize: 13, whiteSpace: 'pre-line' }}>{j.description}</p>
                    <ul style={{ fontSize: 13 }}>{j.reasons.map((r, i) => <li key={i}><b>{r.rule}</b>: {r.fix} {r.excerpt && <i>“{r.excerpt}”</i>}</li>)}</ul>
                    {j.reports.length > 0 && <p style={{ fontSize: 13 }}>Laporan: {j.reports.map((r) => r.reason).join(', ')}</p>}
                    {j.events.filter((e) => e.action === 'appealed').map((e) => <p key={e.id} style={{ fontSize: 13 }}>Banding: {e.note}</p>)}
                    <button style={topBtn(KC.lime, '#fff')} onClick={() => act(`/moderation/jobs/${j.job_id}`, { decision: 'publish' }, 'Ditayangkan')}>Tayangkan</button>
                    <button style={{ ...topBtn(KC.rose, '#fff'), marginLeft: 8 }} onClick={() => act(`/moderation/jobs/${j.job_id}`, { decision: 'reject', note: window.prompt('Alasan penolakan (dikirim ke pemasang):') || '' }, 'Ditolak + peringatan')}>Tolak</button>
                </BrutalCard>
            )) : <p>Tidak ada lowongan yang ditahan.</p>)}

            {data && tab === 'reviews' && (data.items.length ? data.items.map((e) => (
                <BrutalCard key={e.employer_id}>
                    <div style={{ fontWeight: 900 }}>{e.company_name}</div>
                    <ul>{e.links.map((l) => <li key={l}><a href={l} target="_blank" rel="noreferrer noopener">{l}</a></li>)}</ul>
                    <button style={topBtn(KC.lime, '#fff')} onClick={() => act(`/employer-reviews/${e.employer_id}`, { approve: true }, 'Badge diberikan')}>Setujui</button>
                    <button style={{ ...topBtn(), marginLeft: 8 }} onClick={() => act(`/employer-reviews/${e.employer_id}`, { approve: false }, 'Ditolak')}>Tolak</button>
                </BrutalCard>
            )) : <p>Tidak ada permintaan.</p>)}

            {data && tab === 'orders' && (data.items.length ? data.items.map((o) => (
                <BrutalCard key={o.id}>
                    <div style={{ fontWeight: 900 }}>{o.plan.toUpperCase()} · Rp{o.amount_idr.toLocaleString('id-ID')} · kode {o.id.slice(0, 8).toUpperCase()}</div>
                    <p style={{ fontSize: 13 }}>User {o.user_id}{o.job_id ? ` · lowongan ${o.job_id}` : ''} · {o.created_at}</p>
                    <button style={topBtn(KC.lime, '#fff')} onClick={() => act(`/orders/${o.id}/activate`, {}, 'Paket aktif 30 hari')}>Pembayaran diterima → aktifkan</button>
                    <button style={{ ...topBtn(), marginLeft: 8 }} onClick={() => act(`/orders/${o.id}/cancel`, {}, 'Dibatalkan')}>Batalkan</button>
                </BrutalCard>
            )) : <p>Tidak ada pesanan menunggu.</p>)}

            {data && tab === 'questions' && data.items.map((q) => (
                <BrutalCard key={q.id} color={q.reviewed ? KC.paper : KC.yellowSoft}>
                    <div style={{ fontSize: 12, fontWeight: 800 }}>{q.skill_label} · {q.reviewed ? 'sudah ditinjau' : 'DRAF'} · {q.active ? 'aktif' : 'nonaktif'}</div>
                    <p style={{ fontWeight: 700 }}>{q.question}</p>
                    <ol type="A" style={{ fontSize: 13 }}>{q.options.map((o, i) => <li key={i} style={{ fontWeight: i === q.correct_index ? 800 : 400 }}>{o}</li>)}</ol>
                    <button style={topBtn()} onClick={() => act(`/questions/${q.id}`, { reviewed: !q.reviewed }, 'Disimpan')}>{q.reviewed ? 'Tandai draf' : 'Tandai sudah ditinjau'}</button>
                    <button style={{ ...topBtn(), marginLeft: 8 }} onClick={() => act(`/questions/${q.id}`, { active: !q.active }, 'Disimpan')}>{q.active ? 'Nonaktifkan' : 'Aktifkan'}</button>
                </BrutalCard>
            ))}

            {data && tab === 'metrics' && <AdminMetrics data={data} />}
        </div>
    )
}
