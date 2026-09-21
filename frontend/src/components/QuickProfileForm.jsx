// Minimal 5-field profile for visitors applying from a job link (no CV needed).
import { useState } from 'react'
import toast from 'react-hot-toast'
import useStore from '../store/useStore'
import { BrutalCard, KC, topBtn } from './_design'
import { updateSeekerProfile } from '../services/api'

const inputStyle = { width: '100%', padding: '9px 12px', border: `1.5px solid ${KC.ink}`, borderRadius: 9, fontFamily: 'inherit', boxSizing: 'border-box' }

export default function QuickProfileForm({ suggestedSkills = [], onSaved }) {
    const { user, navigate } = useStore()
    const [name, setName] = useState(user?.name || '')
    const [headline, setHeadline] = useState('')
    const [degree, setDegree] = useState('SMA')
    const [picked, setPicked] = useState([])
    const [extra, setExtra] = useState('')
    const [busy, setBusy] = useState(false)

    const toggle = (s) => setPicked((p) => (p.includes(s) ? p.filter((x) => x !== s) : [...p, s]))

    const save = async () => {
        const skills = [...picked, ...extra.split(',').map((s) => s.trim()).filter(Boolean)]
        if (!name.trim() || skills.length === 0) {
            toast.error('Isi nama dan minimal satu skill')
            return
        }
        setBusy(true)
        try {
            await updateSeekerProfile({
                full_name: name.trim(),
                headline: headline.trim(),
                region_code: '3171',
                skills,
                education: [{ institution: '', degree, major: '', graduation_year: new Date().getFullYear() }],
            })
            toast.success('Profil tersimpan')
            onSaved?.()
        } catch (e) {
            toast.error(e.message)
        } finally {
            setBusy(false)
        }
    }

    return (
        <BrutalCard>
            <div style={{ fontWeight: 900, marginBottom: 4 }}>Profil singkat (1 menit)</div>
            <p style={{ fontSize: 13, color: KC.mute, marginTop: 0 }}>
                Atau <button onClick={() => navigate('seeker-profile')} style={{ background: 'none', border: 'none', color: KC.orange, fontWeight: 700, cursor: 'pointer', padding: 0 }}>upload CV</button> untuk profil lengkap.
                Skill yang kamu centang dihitung sebagai <b>klaim</b> sampai dibuktikan lewat kuis.
            </p>
            <div style={{ display: 'grid', gap: 10 }}>
                <input style={inputStyle} value={name} onChange={(e) => setName(e.target.value)} placeholder="Nama lengkap" />
                <input style={inputStyle} value={headline} onChange={(e) => setHeadline(e.target.value)} placeholder="Contoh: Lulusan SMK Akuntansi" />
                <select style={inputStyle} value={degree} onChange={(e) => setDegree(e.target.value)}>
                    {['SMA', 'D3', 'D4', 'S1', 'S2'].map((d) => <option key={d} value={d}>Pendidikan terakhir: {d === 'SMA' ? 'SMA/SMK' : d}</option>)}
                </select>
                {suggestedSkills.length > 0 && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {suggestedSkills.map((s) => (
                            <button key={s} onClick={() => toggle(s)} style={{
                                padding: '5px 11px', borderRadius: 999, cursor: 'pointer', fontFamily: 'inherit', fontSize: 13,
                                border: `1.5px solid ${picked.includes(s) ? KC.orange : KC.borderMuted}`,
                                background: picked.includes(s) ? KC.orangeSoft : KC.paper,
                            }}>{picked.includes(s) ? '✓ ' : ''}{s}</button>
                        ))}
                    </div>
                )}
                <input style={inputStyle} value={extra} onChange={(e) => setExtra(e.target.value)} placeholder="Skill lain, pisahkan dengan koma" />
                <button style={topBtn(KC.ink, '#fff')} disabled={busy} onClick={save}>Simpan profil</button>
            </div>
        </BrutalCard>
    )
}
