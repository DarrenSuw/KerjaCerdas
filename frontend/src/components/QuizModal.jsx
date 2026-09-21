// Skill quiz runner: 5 scenario questions, 45 s each, pass = 4/5.
// Answers are graded on the server; the browser never receives the key.
import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { Clock, X } from 'lucide-react'
import { KC, topBtn } from './_design'
import { startQuiz, submitQuiz } from '../services/api'

function FormattedText({ text }) {
    if (!text) return null
    // Unescape basic characters that Gemini might escape, like \$ or \*
    const unescaped = text.replace(/\\([$*`_])/g, '$1')
    
    // Parse inline code with backticks
    const parts = unescaped.split(/`([^`]+)`/g)
    return (
        <>
            {parts.map((part, i) => {
                if (i % 2 === 1) {
                    return (
                        <code key={i} style={{ 
                            background: 'rgba(0,0,0,0.06)', 
                            padding: '2px 5px', 
                            borderRadius: 4, 
                            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                            fontSize: '0.9em',
                            color: KC.ink
                        }}>
                            {part}
                        </code>
                    )
                }
                
                // Parse bold
                const boldParts = part.split(/\*\*([^*]+)\*\*/g)
                return (
                    <span key={i}>
                        {boldParts.map((bPart, j) => {
                            if (j % 2 === 1) return <strong key={j}>{bPart}</strong>
                            
                            // Parse italics
                            const italicParts = bPart.split(/\*([^*]+)\*/g)
                            return (
                                <span key={j}>
                                    {italicParts.map((iPart, k) => {
                                        if (k % 2 === 1) return <em key={k}>{iPart}</em>
                                        return iPart
                                    })}
                                </span>
                            )
                        })}
                    </span>
                )
            })}
        </>
    )
}

export default function QuizModal({ skill, onClose, onDone }) {
    const [attempt, setAttempt] = useState(null)
    const [index, setIndex] = useState(0)
    const [answers, setAnswers] = useState([])
    const [result, setResult] = useState(null)
    const [error, setError] = useState('')
    const [secondsLeft, setSecondsLeft] = useState(0)
    const submitted = useRef(false)

    useEffect(() => {
        startQuiz(skill)
            .then((a) => {
                setAttempt(a)
                setAnswers(Array(a.questions.length).fill(-1))
                setSecondsLeft(Math.max(0, Math.round((new Date(a.deadline_at) - Date.now()) / 1000)))
            })
            .catch((e) => setError(e.message))
    }, [skill])

    const submit = async (final) => {
        if (submitted.current || !attempt) return
        submitted.current = true
        try {
            const r = await submitQuiz(attempt.attempt_id, final)
            setResult(r)
            // `passed` is the score; `proof_granted` is whether it earned the
            // badge. They differ when the question bank was too thin to avoid
            // repeating the previous attempt — the server withholds the badge,
            // and announcing one here would tell the candidate they hold proof
            // they do not have.
            if (r.proof_granted) toast.success(`Lulus! ${skill} sekarang ✓ Terbukti`)
            else if (r.passed) toast(`Nilaimu lulus, tapi badge belum diberikan — soalnya masih terbatas`)
            onDone?.(r)
        } catch (e) {
            setError(e.message)
        }
    }

    useEffect(() => {
        if (!attempt || result) return undefined
        const t = setInterval(() => {
            setSecondsLeft((s) => {
                if (s <= 1) {
                    clearInterval(t)
                    submit(answers)
                    return 0
                }
                return s - 1
            })
        }, 1000)
        return () => clearInterval(t)
    }, [attempt, result, answers])  // eslint-disable-line react-hooks/exhaustive-deps

    const choose = (i) => {
        const next = [...answers]
        next[index] = i
        setAnswers(next)
    }

    const q = attempt?.questions?.[index]
    const last = attempt && index === attempt.questions.length - 1

    return (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(9,10,15,0.55)', zIndex: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
            <div role="dialog" aria-label={`Kuis ${skill}`} style={{ background: KC.paper, border: `1.5px solid ${KC.ink}`, borderRadius: 14, boxShadow: `5px 5px 0 ${KC.ink}`, width: '100%', maxWidth: 560, padding: 22, maxHeight: '90vh', overflowY: 'auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <div style={{ fontWeight: 900, fontSize: 18 }}>Kuis skill: {attempt?.skill_label || skill}</div>
                    <button aria-label="Tutup" onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X /></button>
                </div>

                {error && <p style={{ color: KC.rose, fontWeight: 700 }}>{error}</p>}
                {!attempt && !error && <p>Menyiapkan soal…</p>}

                {attempt && !result && q && (
                    <>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: KC.mute, marginBottom: 8 }}>
                            <span>Soal {index + 1} dari {attempt.questions.length} · lulus jika benar {attempt.pass_mark}</span>
                            <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center', fontWeight: 800, color: secondsLeft < 30 ? KC.rose : KC.ink }}>
                                <Clock size={14} /> {Math.floor(secondsLeft / 60)}:{String(secondsLeft % 60).padStart(2, '0')}
                            </span>
                        </div>
                        {attempt.draft_bank && (
                            <p style={{ fontSize: 12, background: KC.yellowSoft, border: `1px solid ${KC.yellow}`, borderRadius: 8, padding: '6px 10px' }}>
                                Bank soal versi awal — sedang ditinjau praktisi HR.
                            </p>
                        )}
                        <p style={{ fontWeight: 700, fontSize: 15, lineHeight: 1.5 }}>
                            <FormattedText text={q.question} />
                        </p>
                        <div style={{ display: 'grid', gap: 8 }}>
                            {q.options.map((opt, i) => (
                                <button key={i} onClick={() => choose(i)} style={{
                                    textAlign: 'left', padding: '10px 12px', borderRadius: 9, cursor: 'pointer', fontFamily: 'inherit', fontSize: 14,
                                    border: `1.5px solid ${answers[index] === i ? KC.orange : KC.borderMuted}`,
                                    background: answers[index] === i ? KC.orangeSoft : KC.paper,
                                }}>
                                    {String.fromCharCode(65 + i)}. <FormattedText text={opt} />
                                </button>
                            ))}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
                            <button style={topBtn()} disabled={index === 0} onClick={() => setIndex(index - 1)}>Sebelumnya</button>
                            {last
                                ? <button style={topBtn(KC.orange, '#fff')} disabled={answers.includes(-1)} onClick={() => submit(answers)}>Kumpulkan</button>
                                : <button style={topBtn(KC.ink, '#fff')} disabled={answers[index] === -1} onClick={() => setIndex(index + 1)}>Berikutnya</button>}
                        </div>
                    </>
                )}

                {result && (
                    <div style={{ textAlign: 'center', padding: '10px 0' }}>
                        <div style={{ fontSize: 40, fontWeight: 900 }}>{result.score}/{result.total}</div>
                        <p style={{ fontWeight: 800, color: result.proof_granted ? '#059669' : (result.passed ? KC.amber || '#B45309' : KC.rose) }}>
                            {result.proof_granted
                                ? '✓ Lulus — skill ini sekarang Terbukti (berlaku 6 bulan)'
                                : result.passed
                                    ? 'Nilaimu lulus, tapi badge belum bisa diberikan'
                                    : 'Belum lulus'}
                        </p>
                        {result.passed && !result.proof_granted && (
                            <p style={{ fontSize: 13, color: KC.mute }}>
                                Bank soal untuk skill ini masih terbatas, jadi beberapa soal terpaksa
                                diulang dari percobaan sebelumnya. Lulus atas soal yang sudah kamu lihat
                                belum bisa kami hitung sebagai bukti. Kami sedang menambah soalnya —
                                coba lagi besok untuk kuis penuh.
                            </p>
                        )}
                        {!result.passed && (
                            <p style={{ fontSize: 13, color: KC.mute }}>
                                Pelajari materinya di rekomendasi kursus, lalu coba lagi setelah {result.retake_after_days} hari.
                                {result.late ? ' Waktu habis sebelum dikumpulkan.' : ''}
                            </p>
                        )}
                        <button style={topBtn(KC.ink, '#fff')} onClick={onClose}>Selesai</button>
                    </div>
                )}
            </div>
        </div>
    )
}
