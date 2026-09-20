// "Laporkan lowongan" — enough distinct reports hide a job for admin review.
import { useState } from 'react'
import toast from 'react-hot-toast'
import { X } from 'lucide-react'
import { KC, topBtn } from './_design'
import { reportJob } from '../services/api'

export default function ReportJobModal({ code, reasons = {}, onClose }) {
    const [reason, setReason] = useState('')
    const [detail, setDetail] = useState('')
    const [busy, setBusy] = useState(false)

    const send = async () => {
        setBusy(true)
        try {
            const r = await reportJob(code, reason, detail)
            toast.success(r.status === 'already_reported' ? 'Kamu sudah melaporkan lowongan ini' : 'Terima kasih, laporan diterima')
            onClose()
        } catch (e) {
            toast.error(e.message)
        } finally {
            setBusy(false)
        }
    }

    return (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(9,10,15,0.55)', zIndex: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
            <div role="dialog" aria-label="Laporkan lowongan" style={{ background: KC.paper, border: `1.5px solid ${KC.ink}`, borderRadius: 14, boxShadow: `5px 5px 0 ${KC.ink}`, width: '100%', maxWidth: 440, padding: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 900, fontSize: 17 }}>
                    Laporkan lowongan
                    <button aria-label="Tutup" onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X /></button>
                </div>
                <div style={{ display: 'grid', gap: 6, margin: '12px 0' }}>
                    {Object.entries(reasons).map(([key, label]) => (
                        <label key={key} style={{ display: 'flex', gap: 8, fontSize: 14 }}>
                            <input type="radio" name="reason" checked={reason === key} onChange={() => setReason(key)} /> {label}
                        </label>
                    ))}
                </div>
                <textarea rows={3} value={detail} maxLength={1000} onChange={(e) => setDetail(e.target.value)} placeholder="Detail (opsional)"
                    style={{ width: '100%', padding: 10, border: `1.5px solid ${KC.ink}`, borderRadius: 9, fontFamily: 'inherit', boxSizing: 'border-box' }} />
                <button style={{ ...topBtn(KC.rose, '#fff', KC.ink), marginTop: 10 }} disabled={!reason || busy} onClick={send}>Kirim laporan</button>
            </div>
        </div>
    )
}
