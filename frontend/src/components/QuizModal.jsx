// Skill quiz runner: 5 scenario questions, 45 s each, pass = 4/5.
// Answers are graded on the server; the browser never receives the key.
import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { AlertTriangle, ArrowRight, Clock, X } from 'lucide-react'
import { KC, topBtn } from './_design'
import { abandonQuiz, startQuiz, submitQuiz } from '../services/api'

function FormattedText({ text }) {
    if (!text) return null
    const unescaped = text.replace(/\\([$*`_])/g, '$1')
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
                const boldParts = part.split(/\*\*([^*]+)\*\*/g)
                return (
                    <span key={i}>
                        {boldParts.map((bPart, j) => {
                            if (j % 2 === 1) return <strong key={j}>{bPart}</strong>
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

// Question navigator — numbered tiles per question.
// Orange filled = answered, bold outline = current, muted = unanswered.
function QuestionNav({ total, index, answers, onGoto }) {
    return (
        <div style={{ marginBottom: 2 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                {Array.from({ length: total }, (_, i) => {
                    const answered = answers[i] !== -1
                    const current = i === index
                    const bg = answered ? KC.orange : KC.paper
                    const fg = answered ? '#fff' : current ? KC.ink : KC.mute
                    const borderColor = current ? KC.ink : answered ? KC.orange : KC.borderMuted
                    const shadow = current ? `2px 2px 0 ${KC.ink}` : answered ? `2px 2px 0 ${KC.orange}` : 'none'
                    return (
                        <button
                            key={i}
                            onClick={() => onGoto(i)}
                            title={answered ? `Soal ${i + 1} (sudah dijawab)` : `Soal ${i + 1} (belum dijawab)`}
                            style={{
                                width: 34,
                                height: 34,
                                borderRadius: 8,
                                border: `1.5px solid ${borderColor}`,
                                background: bg,
                                color: fg,
                                fontWeight: current ? 900 : answered ? 700 : 500,
                                fontSize: 13,
                                cursor: 'pointer',
                                fontFamily: 'inherit',
                                boxShadow: shadow,
                                transition: 'all 0.12s ease',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                outline: current ? `2.5px solid ${KC.ink}` : 'none',
                                outlineOffset: 1,
                            }}
                        >
                            {i + 1}
                        </button>
                    )
                })}
            </div>
            <div style={{ display: 'flex', gap: 14, marginTop: 8, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 11, color: KC.mute, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 3, background: KC.orange, display: 'inline-block', flexShrink: 0 }} />
                    Dijawab
                </span>
                <span style={{ fontSize: 11, color: KC.mute, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 3, border: `1.5px solid ${KC.ink}`, display: 'inline-block', flexShrink: 0 }} />
                    Sedang dikerjakan
                </span>
                <span style={{ fontSize: 11, color: KC.mute, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 3, border: `1.5px solid ${KC.borderMuted}`, display: 'inline-block', flexShrink: 0 }} />
                    Belum dijawab
                </span>
            </div>
        </div>
    )
}

// Confirmation overlay when submitting with unanswered questions.
function UnansweredConfirm({ unanswered, onGoto, onSubmit, onCancel }) {
    const firstUnanswered = unanswered[0]
    return (
        <div style={{
            position: 'absolute', inset: 0, borderRadius: 14,
            background: 'rgba(9,10,15,0.65)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 10, padding: 20,
        }}>
            <div style={{
                background: KC.paper,
                border: `1.5px solid ${KC.ink}`,
                borderRadius: 12,
                boxShadow: `4px 4px 0 ${KC.ink}`,
                padding: 24,
                width: '100%',
                maxWidth: 380,
            }}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 14 }}>
                    <AlertTriangle size={20} color={KC.yellow} style={{ flexShrink: 0, marginTop: 2 }} />
                    <div>
                        <div style={{ fontWeight: 900, fontSize: 15, marginBottom: 5 }}>
                            {unanswered.length === 1 ? '1 soal belum dijawab' : `${unanswered.length} soal belum dijawab`}
                        </div>
                        <p style={{ fontSize: 13, color: KC.mute, margin: 0, lineHeight: 1.6 }}>
                            Soal yang dilewati akan dihitung salah. Yakin ingin mengumpulkan sekarang?
                        </p>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 18 }}>
                    {unanswered.map((i) => (
                        <span key={i} style={{
                            width: 30, height: 30, borderRadius: 7,
                            border: `1.5px solid ${KC.rose}`,
                            background: KC.roseSoft,
                            color: KC.rose,
                            fontWeight: 800, fontSize: 13,
                            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                            {i + 1}
                        </span>
                    ))}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <button
                        style={topBtn(KC.ink, '#fff')}
                        onClick={() => { onCancel(); onGoto(firstUnanswered) }}
                    >
                        <ArrowRight size={14} />
                        Kerjakan soal nomor {firstUnanswered + 1}
                    </button>
                    <button
                        style={{ ...topBtn(), border: `1.5px solid ${KC.rose}`, color: KC.rose, boxShadow: `2.5px 2.5px 0 ${KC.rose}` }}
                        onClick={onSubmit}
                    >
                        Kumpulkan tetap saja
                    </button>
                    <button style={{ ...topBtn(), justifyContent: 'center' }} onClick={onCancel}>
                        Batal
                    </button>
                </div>
            </div>
        </div>
    )
}

export default function QuizModal({ skill, onClose, onDone }) {
    const [attempt, setAttempt] = useState(null)
    const [index, setIndex] = useState(0)
    const [answers, setAnswers] = useState([])
    const [result, setResult] = useState(null)
    const [error, setError] = useState('')
    const [secondsLeft, setSecondsLeft] = useState(0)
    const [showConfirm, setShowConfirm] = useState(false)
    const submitted = useRef(false)
    const abandonSent = useRef(false)
    const startedAtRef = useRef(Date.now())

    const recordAbandon = async (elapsedSeconds = null) => {
        if (!attempt || submitted.current || abandonSent.current) return
        abandonSent.current = true
        const seconds = elapsedSeconds ?? Math.max(0, Math.round((Date.now() - startedAtRef.current) / 1000))
        if (seconds < 30) return
        try {
            await abandonQuiz(attempt.attempt_id, seconds)
        } catch {
            // Best effort; if the browser is closing, the beacon path below is the
            // actual persisted signal, and the server will consider the attempt used.
        }
    }

    useEffect(() => {
        startQuiz(skill)
            .then((a) => {
                setAttempt(a)
                setAnswers(Array(a.questions.length).fill(-1))
                startedAtRef.current = Date.now()
                setSecondsLeft(Math.max(0, Math.round((new Date(a.deadline_at) - Date.now()) / 1000)))
            })
            .catch((e) => setError(e.message))
    }, [skill])

    const submit = async (final) => {
        if (submitted.current || !attempt) return
        submitted.current = true
        setShowConfirm(false)
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
            submitted.current = false
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

    useEffect(() => {
        if (!attempt || result || submitted.current) return undefined
        const token = (() => {
            try {
                const rawV4 = localStorage.getItem('kerjacerdas-v4')
                const tokenV4 = rawV4 ? JSON.parse(rawV4)?.state?.authToken : null
                if (tokenV4) return tokenV4
                const rawV3 = localStorage.getItem('kerjacerdas-v3')
                const tokenV3 = rawV3 ? JSON.parse(rawV3)?.state?.authToken : null
                return tokenV3 || null
            } catch {
                return null
            }
        })()

        const triggerAbandon = (elapsed) => {
            if (elapsed < 30 || !attempt?.attempt_id || abandonSent.current) return
            abandonSent.current = true
            const headers = { 'Content-Type': 'application/json' }
            if (token) headers.Authorization = `Bearer ${token}`
            fetch('/api/v1/quiz/abandon', {
                method: 'POST',
                headers,
                body: JSON.stringify({ attempt_id: attempt.attempt_id, elapsed_seconds: elapsed }),
                keepalive: true,
                credentials: 'same-origin',
            }).catch(() => {})
        }

        const handleVisibility = () => {
            if (document.visibilityState === 'hidden') {
                const elapsed = Math.max(0, Math.round((Date.now() - startedAtRef.current) / 1000))
                triggerAbandon(elapsed)
            }
        }
        const handleBeforeUnload = () => {
            const elapsed = Math.max(0, Math.round((Date.now() - startedAtRef.current) / 1000))
            triggerAbandon(elapsed)
        }
        document.addEventListener('visibilitychange', handleVisibility)
        window.addEventListener('beforeunload', handleBeforeUnload)
        return () => {
            document.removeEventListener('visibilitychange', handleVisibility)
            window.removeEventListener('beforeunload', handleBeforeUnload)
        }
    }, [attempt, result])

    const choose = (i) => {
        const next = [...answers]
        next[index] = i
        setAnswers(next)
    }

    const handleSubmitClick = () => {
        const unanswered = answers.reduce((acc, a, i) => { if (a === -1) acc.push(i); return acc }, [])
        if (unanswered.length > 0) {
            setShowConfirm(true)
        } else {
            submit(answers)
        }
    }

    const q = attempt?.questions?.[index]
    const last = attempt && index === attempt.questions.length - 1
    const unansweredList = answers.reduce((acc, a, i) => { if (a === -1) acc.push(i); return acc }, [])
    const answeredCount = answers.filter(a => a !== -1).length

    return (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(9,10,15,0.55)', zIndex: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
            <div role="dialog" aria-label={`Kuis ${skill}`} style={{ position: 'relative', background: KC.paper, border: `1.5px solid ${KC.ink}`, borderRadius: 14, boxShadow: `5px 5px 0 ${KC.ink}`, width: '100%', maxWidth: 560, padding: 22, maxHeight: '90vh', overflowY: 'auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <div style={{ fontWeight: 900, fontSize: 18 }}>Kuis skill: {attempt?.skill_label || skill}</div>
                    <button
                        aria-label="Tutup"
                        onClick={() => {
                            void recordAbandon()
                            onClose()
                        }}
                        style={{ background: 'none', border: 'none', cursor: 'pointer' }}
                    ><X /></button>
                </div>

                {error && <p style={{ color: KC.rose, fontWeight: 700 }}>{error}</p>}
                {!attempt && !error && <p>Menyiapkan soal…</p>}

                {attempt && !result && q && (
                    <>
                        {/* Timer row */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: KC.mute, marginBottom: 12 }}>
                            <span>Soal {index + 1} dari {attempt.questions.length} · lulus jika benar {attempt.pass_mark}</span>
                            <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center', fontWeight: 800, color: secondsLeft < 30 ? KC.rose : KC.ink }}>
                                <Clock size={14} /> {Math.floor(secondsLeft / 60)}:{String(secondsLeft % 60).padStart(2, '0')}
                            </span>
                        </div>

                        {/* Question navigator */}
                        <QuestionNav
                            total={attempt.questions.length}
                            index={index}
                            answers={answers}
                            onGoto={setIndex}
                        />

                        {/* Progress bar */}
                        <div style={{ height: 4, background: KC.ash, borderRadius: 99, margin: '12px 0 16px', overflow: 'hidden' }}>
                            <div style={{
                                height: '100%',
                                width: `${(answeredCount / attempt.questions.length) * 100}%`,
                                background: KC.orange,
                                borderRadius: 99,
                                transition: 'width 0.3s ease',
                            }} />
                        </div>

                        {attempt.draft_bank && (
                            <p style={{ fontSize: 12, background: KC.yellowSoft, border: `1px solid ${KC.yellow}`, borderRadius: 8, padding: '6px 10px', marginBottom: 10 }}>
                                Bank soal versi awal — sedang ditinjau praktisi HR.
                            </p>
                        )}
                        <p style={{ fontWeight: 700, fontSize: 15, lineHeight: 1.5, marginBottom: 10 }}>
                            <FormattedText text={q.question} />
                        </p>
                        <div style={{ display: 'grid', gap: 8 }}>
                            {q.options.map((opt, i) => (
                                <button key={i} onClick={() => choose(i)} style={{
                                    textAlign: 'left', padding: '10px 12px', borderRadius: 9, cursor: 'pointer', fontFamily: 'inherit', fontSize: 14,
                                    border: `1.5px solid ${answers[index] === i ? KC.orange : KC.borderMuted}`,
                                    background: answers[index] === i ? KC.orangeSoft : KC.paper,
                                    transition: 'all 0.12s ease',
                                }}>
                                    {String.fromCharCode(65 + i)}. <FormattedText text={opt} />
                                </button>
                            ))}
                        </div>

                        {/* Navigation row */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16 }}>
                            <button style={topBtn()} disabled={index === 0} onClick={() => setIndex(index - 1)}>Sebelumnya</button>
                            {last
                                ? (
                                    <button style={topBtn(KC.orange, '#fff')} onClick={handleSubmitClick}>
                                        {unansweredList.length > 0
                                            ? `Kumpulkan (${unansweredList.length} belum dijawab)`
                                            : 'Kumpulkan'}
                                    </button>
                                )
                                : <button style={topBtn(KC.ink, '#fff')} onClick={() => setIndex(index + 1)}>Berikutnya</button>
                            }
                        </div>

                        {/* Answered count summary */}
                        <div style={{ marginTop: 10, textAlign: 'center', fontSize: 12, color: KC.mute }}>
                            {answeredCount} dari {attempt.questions.length} soal terjawab
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

                {/* Unanswered confirmation overlay */}
                {showConfirm && (
                    <UnansweredConfirm
                        unanswered={unansweredList}
                        onGoto={setIndex}
                        onSubmit={() => submit(answers)}
                        onCancel={() => setShowConfirm(false)}
                    />
                )}
            </div>
        </div>
    )
}
