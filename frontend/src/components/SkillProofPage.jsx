// "Bukti Skill" — replaces the old e-KYC page. Seekers prove skills with
// short quizzes (✓ Terbukti, valid 6 months) and verify their email.
import { useCallback, useEffect, useState } from 'react'
import { Award, PlayCircle } from 'lucide-react'
import useStore from '../store/useStore'
import { BrutalCard, KC, topBtn } from './_design'
import { EmailVerifyCard, ProofChip, ProofLegend } from './ProofUI'
import QuizModal from './QuizModal'
import { fetchQuizSkills } from '../services/api'

export default function SkillProofPage() {
    const { loadSeekerProfile } = useStore()
    const [data, setData] = useState({ items: [], bank: [] })
    const [quizSkill, setQuizSkill] = useState(null)
    const [loading, setLoading] = useState(true)

    const load = useCallback(() => {
        setLoading(true)
        fetchQuizSkills()
            .then(setData)
            .catch(() => setData({ items: [], bank: [] }))
            .finally(() => setLoading(false))
    }, [])

    // eslint-disable-next-line react-hooks/set-state-in-effect
    useEffect(() => { load() }, [load])

    const mine = data.items.filter((i) => i.proof !== 'missing')
    const proven = mine.filter((i) => i.proof === 'quiz' || i.proof === 'hr_confirmed').length

    return (
        <div style={{ display: 'grid', gap: 18 }}>
            <div>
                <h1 style={{ fontSize: 28, fontWeight: 900, margin: 0 }}>Bukti Skill</h1>
                <p style={{ color: KC.mute, margin: '6px 0 0' }}>
                    Skill yang hanya ditulis di CV dihitung sebagai <b>klaim</b>. Lulus kuis singkat
                    (5 soal, ±3 menit) menjadikannya <b>✓ Terbukti</b> dan menaikkan skor kecocokanmu
                    di semua lowongan. Membayar tidak pernah menaikkan skor.
                </p>
                <ProofLegend />
            </div>

            <EmailVerifyCard />

            <BrutalCard>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 900, marginBottom: 12 }}>
                    <Award size={18} /> Skill di profilmu · {proven} terbukti
                </div>
                {loading && <p>Memuat…</p>}
                {!loading && mine.length === 0 && (
                    <p style={{ color: KC.mute }}>Belum ada skill. Upload CV atau isi profil dulu.</p>
                )}
                <div style={{ display: 'grid', gap: 10 }}>
                    {mine.map((item) => (
                        <div key={item.key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap', borderBottom: `1px solid ${KC.ash}`, paddingBottom: 10 }}>
                            <div style={{ display: 'grid', gap: 4 }}>
                                <ProofChip name={item.skill} status={item.proof} />
                                {item.proof === 'quiz' && item.proof_date && (
                                    <span style={{ fontSize: 12, color: KC.mute }}>Lulus {item.proof_date} · berlaku 6 bulan</span>
                                )}
                            </div>
                            {(() => {
                                const isClaimed = item.proof === 'claimed'
                                const capped = item.daily_attempts_used >= item.daily_attempts_cap
                                if (!isClaimed) return null
                                if (!item.quiz_available) {
                                    return <span style={{ fontSize: 12, color: KC.mute }}>Kuis belum tersedia · dibuktikan saat wawancara</span>
                                }
                                if (capped) {
                                    const resetDate = item.cap_resets_at
                                        ? new Date(item.cap_resets_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'long' })
                                        : 'besok'
                                    const statusText = item.last_attempt_status === 'abandoned'
                                        ? 'Kuis dibatalkan — tidak dihitung sebagai lulus'
                                        : 'Sudah dicoba hari ini'
                                    return (
                                        <span style={{ fontSize: 12, color: KC.mute, textAlign: 'right' }}>
                                            {statusText}<br />
                                            <b style={{ color: KC.ink }}>Coba lagi {resetDate}</b>
                                        </span>
                                    )
                                }
                                return (
                                    <button style={topBtn(KC.orange, '#fff')} onClick={() => setQuizSkill(item.skill)}>
                                        <PlayCircle size={15} /> Buktikan
                                    </button>
                                )
                            })()}

                        </div>
                    ))}
                </div>
            </BrutalCard>

            {quizSkill && (
                <QuizModal
                    key={quizSkill}
                    skill={quizSkill}
                    onClose={() => setQuizSkill(null)}
                    onDone={() => { load(); loadSeekerProfile() }}
                />
            )}
        </div>
    )
}
