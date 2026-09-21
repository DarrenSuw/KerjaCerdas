// Edit an existing posting. Saving re-runs AutoMod, which is how a poster
// fixes a held / rejected ad ("edit & resubmit").
import { useState } from 'react'
import toast from 'react-hot-toast'
import { X } from 'lucide-react'
import { KC, topBtn } from './_design'
import { updateEmployerJob } from '../services/api'

const input = { width: '100%', padding: '9px 12px', border: `1.5px solid ${KC.ink}`, borderRadius: 9, fontFamily: 'inherit', fontSize: 14, boxSizing: 'border-box' }

export default function JobEditModal({ job, onClose, onSaved }) {
    const [title, setTitle] = useState(job.title || '')
    const [description, setDescription] = useState(job.description || '')
    const [skills, setSkills] = useState((job.required_skills || []).join(', '))
    const [salaryMin, setSalaryMin] = useState(job.salary_min || 0)
    const [salaryMax, setSalaryMax] = useState(job.salary_max || 0)
    const [busy, setBusy] = useState(false)

    const save = async () => {
        setBusy(true)
        try {
            const res = await updateEmployerJob(job.id, {
                title: title.trim(),
                description,
                required_skills: skills.split(',').map((s) => s.trim()).filter(Boolean),
                salary_min: Number(salaryMin) || 0,
                salary_max: Number(salaryMax) || 0,
            })
            if (res.moderation_status === 'published') toast.success('Tersimpan — lowongan lolos AutoMod')
            else toast(res.notice || 'Tersimpan, masih perlu ditinjau', { icon: '⏳', duration: 8000 })
            onSaved?.()
            onClose()
        } catch (e) {
            toast.error(e.message)
        } finally {
            setBusy(false)
        }
    }

    return (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(9,10,15,0.55)', zIndex: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
            <div role="dialog" aria-label="Edit lowongan" style={{ background: KC.paper, border: `1.5px solid ${KC.ink}`, borderRadius: 14, boxShadow: `5px 5px 0 ${KC.ink}`, width: '100%', maxWidth: 560, padding: 20, maxHeight: '90vh', overflowY: 'auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 900, fontSize: 17, marginBottom: 12 }}>
                    Edit lowongan
                    <button aria-label="Tutup" onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X /></button>
                </div>
                <div style={{ display: 'grid', gap: 10 }}>
                    <label style={{ fontSize: 13, fontWeight: 700 }}>Judul<input style={input} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
                    <label style={{ fontSize: 13, fontWeight: 700 }}>Deskripsi<textarea rows={6} style={input} value={description} onChange={(e) => setDescription(e.target.value)} /></label>
                    <label style={{ fontSize: 13, fontWeight: 700 }}>Skill wajib (pisahkan koma)<input style={input} value={skills} onChange={(e) => setSkills(e.target.value)} /></label>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                        <label style={{ fontSize: 13, fontWeight: 700 }}>Gaji min / bulan<input type="number" style={input} value={salaryMin} onChange={(e) => setSalaryMin(e.target.value)} /></label>
                        <label style={{ fontSize: 13, fontWeight: 700 }}>Gaji maks / bulan<input type="number" style={input} value={salaryMax} onChange={(e) => setSalaryMax(e.target.value)} /></label>
                    </div>
                    <p style={{ fontSize: 12, color: KC.mute, margin: 0 }}>Menyimpan akan memeriksa ulang lowongan dengan AutoMod.</p>
                    <button style={topBtn(KC.ink, '#fff')} disabled={busy || !title.trim()} onClick={save}>Simpan & periksa ulang</button>
                </div>
            </div>
        </div>
    )
}
