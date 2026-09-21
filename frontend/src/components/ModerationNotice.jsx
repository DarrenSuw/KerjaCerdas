// AutoMod notice to the poster: which rule, the flagged sentence, how to fix,
// and an appeal. Shown on held / rejected jobs.
import { useState } from 'react'
import toast from 'react-hot-toast'
import { KC, topBtn } from './_design'
import { appealJob } from '../services/api'

export default function ModerationNotice({ job, onChanged }) {
    const [appeal, setAppeal] = useState('')
    const [open, setOpen] = useState(false)
    const status = job.moderation_status
    if (!status || status === 'published') return null

    const send = async () => {
        try {
            await appealJob(job.id, appeal)
            toast.success('Banding dikirim ke admin')
            setOpen(false)
            onChanged?.()
        } catch (e) {
            toast.error(e.message)
        }
    }

    return (
        <div style={{ background: status === 'rejected' ? KC.roseSoft : KC.yellowSoft, border: `1px solid ${status === 'rejected' ? '#FCA5A5' : KC.yellow}`, borderRadius: 10, padding: 12, fontSize: 13, margin: '10px 0' }}>
            <b>{status === 'rejected' ? 'Ditolak AutoMod' : 'Ditahan untuk ditinjau admin'}</b>
            <ul style={{ margin: '6px 0', paddingLeft: 18 }}>
                {(job.moderation_reasons || []).map((r, i) => (
                    <li key={i}>{r.fix}{r.excerpt ? <i> — “{r.excerpt}”</i> : null}</li>
                ))}
            </ul>
            <div>Perbaiki isi lowongan lalu simpan ulang, atau ajukan banding.</div>
            {!open
                ? <button style={{ ...topBtn(), marginTop: 8, padding: '6px 11px', fontSize: 12 }} onClick={() => setOpen(true)}>Ajukan banding</button>
                : (
                    <div style={{ marginTop: 8 }}>
                        <textarea rows={3} value={appeal} onChange={(e) => setAppeal(e.target.value)} placeholder="Jelaskan alasannya (min. 10 karakter)"
                            style={{ width: '100%', padding: 8, border: `1.5px solid ${KC.ink}`, borderRadius: 8, fontFamily: 'inherit', boxSizing: 'border-box' }} />
                        <button style={{ ...topBtn(KC.ink, '#fff'), marginTop: 6, padding: '6px 11px', fontSize: 12 }} disabled={appeal.trim().length < 10} onClick={send}>Kirim banding</button>
                    </div>
                )}
        </div>
    )
}
