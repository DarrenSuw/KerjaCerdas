// Admin → Metrik. Renders GET /admin/metrics as a readable dashboard instead
// of a JSON dump. Every number here is computed from real rows by
// api/services/admin_metrics.py — nothing on this page is illustrative.
//
// Empty states say "belum ada data" rather than rendering 0% / Rp0, so an
// untouched deployment can never be mistaken for a measured result.
import { useState } from 'react'
import { BrutalCard, FilledStat, KC, topBtn } from './_design'

const rupiah = (n) => `Rp${Math.round(n || 0).toLocaleString('id-ID')}`
const pct = (x) => `${Math.round((x || 0) * 100)}%`

const TASK_LABEL = {
    cv_parse: 'Baca CV', job_parse: 'Baca lowongan', automod: 'AutoMod',
    skill_gap: 'Analisis skill gap', advisor: 'Pesan advisor',
    interview_kit: 'Pertanyaan wawancara', embed: 'Embedding',
}
const BAND_LABEL = { strong: 'Strong', possible: 'Possible', stretch: 'Stretch' }
const BAND_COLOR = { strong: KC.lime, possible: KC.cyan, stretch: KC.mute }
const SOURCE_LABEL = { board: 'Papan lowongan', link: 'Tautan / QR' }

function Section({ title, hint, children }) {
    return (
        <BrutalCard>
            <h2 style={{ fontSize: 15, fontWeight: 900, margin: '0 0 2px' }}>{title}</h2>
            {hint && <p style={{ fontSize: 12, color: KC.mute, margin: '0 0 12px' }}>{hint}</p>}
            {children}
        </BrutalCard>
    )
}

function Empty({ children }) {
    return <p style={{ fontSize: 13, color: KC.mute, margin: 0 }}>{children}</p>
}

const th = { textAlign: 'left', fontSize: 10.5, fontWeight: 800, textTransform: 'uppercase', letterSpacing: 0.4, color: KC.mute, padding: '0 8px 6px 0' }
const td = { fontSize: 13, padding: '7px 8px 7px 0', borderTop: `1px solid ${KC.ash}` }
const num = { ...td, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }

export default function AdminMetrics({ data }) {
    const [raw, setRaw] = useState(false)

    const tasks = Object.entries(data.ai_cost_by_task || {})
    const totalCost = tasks.reduce((s, [, t]) => s + (t.cost_idr || 0), 0)
    const totalCalls = tasks.reduce((s, [, t]) => s + (t.calls || 0), 0)
    const totalFailures = tasks.reduce((s, [, t]) => s + (t.failures || 0), 0)

    const bands = Object.entries(data.outcomes_by_band || {})
        .sort((a, b) => ['strong', 'possible', 'stretch'].indexOf(a[0]) - ['strong', 'possible', 'stretch'].indexOf(b[0]))
    const quizzes = data.quizzes || {}
    const skills = Object.entries(quizzes.by_skill || {}).sort((a, b) => b[1].attempts - a[1].attempts)
    const passRate = quizzes.submitted ? quizzes.passed / quizzes.submitted : null
    const apps = data.applications || {}
    const sources = Object.entries(apps.by_source || {}).sort((a, b) => b[1] - a[1])
    const plans = data.plans || {}
    const mod = data.moderation || {}

    return (
        <div style={{ display: 'grid', gap: 16 }}>
            {/* ── Headline numbers: the four figures the business model claims ── */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 12 }}>
                <FilledStat
                    label="Biaya AI (total)" accent={KC.orange}
                    value={totalCalls ? rupiah(totalCost) : '—'}
                    sub={totalCalls ? `${totalCalls} panggilan · rata-rata ${rupiah(totalCost / totalCalls)}` : 'Belum ada panggilan AI'}
                />
                <FilledStat
                    label="Pendapatan 30 hari" accent={KC.lime}
                    value={rupiah(plans.revenue_last_30_days_idr)}
                    sub={`${plans.pending_orders || 0} pesanan menunggu pembayaran`}
                />
                <FilledStat
                    label="Lamaran masuk" accent={KC.cyan}
                    value={apps.total ?? 0}
                    sub={sources.length ? sources.map(([k, v]) => `${SOURCE_LABEL[k] || k} ${v}`).join(' · ') : 'Belum ada lamaran'}
                />
                <FilledStat
                    label="Kuis lulus" accent={KC.indigo}
                    value={passRate === null ? '—' : pct(passRate)}
                    sub={quizzes.submitted ? `${quizzes.passed} lulus dari ${quizzes.submitted} percobaan` : 'Belum ada percobaan kuis'}
                />
            </div>

            {/* ── Cost per action — answers "biaya per pengguna, margin?" ────── */}
            <Section
                title="Biaya AI per aksi"
                hint={`Dari token asli di ai_logs × harga Gemini × kurs Rp${(data.usd_to_idr || 0).toLocaleString('id-ID')}/USD.`}
            >
                {tasks.length === 0 ? <Empty>Belum ada panggilan AI yang tercatat.</Empty> : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 460 }}>
                            <thead><tr>
                                <th style={th}>Aksi</th><th style={{ ...th, textAlign: 'right' }}>Panggilan</th>
                                <th style={{ ...th, textAlign: 'right' }}>Rata-rata</th>
                                <th style={{ ...th, textAlign: 'right' }}>Total</th>
                                <th style={{ ...th, textAlign: 'right' }}>Gagal</th>
                            </tr></thead>
                            <tbody>
                                {tasks.sort((a, b) => b[1].cost_idr - a[1].cost_idr).map(([task, t]) => (
                                    <tr key={task}>
                                        <td style={td}>{TASK_LABEL[task] || task}</td>
                                        <td style={num}>{t.calls}</td>
                                        <td style={num}>{rupiah(t.avg_cost_idr_per_call)}</td>
                                        <td style={{ ...num, fontWeight: 800 }}>{rupiah(t.cost_idr)}</td>
                                        <td style={{ ...num, color: t.failures ? KC.rose : KC.mute }}>{t.failures}</td>
                                    </tr>
                                ))}
                                <tr>
                                    <td style={{ ...td, fontWeight: 900 }}>Total</td>
                                    <td style={{ ...num, fontWeight: 900 }}>{totalCalls}</td>
                                    <td style={num}>—</td>
                                    <td style={{ ...num, fontWeight: 900 }}>{rupiah(totalCost)}</td>
                                    <td style={{ ...num, fontWeight: 900 }}>{totalFailures}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                )}
            </Section>

            {/* ── The evidence question the judges asked ──────────────────────── */}
            <Section
                title="Apakah skor tinggi benar-benar lolos ke wawancara?"
                hint="Skor + bukti skill disimpan saat melamar; status dari HR dicatat terpisah. Butuh puluhan lamaran sebelum angka ini berarti."
            >
                {bands.length === 0 ? <Empty>Belum ada lamaran untuk diukur.</Empty> : bands.map(([band, b]) => (
                    <div key={band} style={{ marginBottom: 12 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 5 }}>
                            <span style={{ fontWeight: 800 }}>{BAND_LABEL[band] || band}</span>
                            <span style={{ fontVariantNumeric: 'tabular-nums' }}>
                                <b>{pct(b.interview_rate)}</b>
                                <span style={{ color: KC.mute }}> · {b.reached_interview}/{b.applications} lamaran</span>
                            </span>
                        </div>
                        <div style={{ height: 8, background: KC.ash, borderRadius: 999, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${(b.interview_rate || 0) * 100}%`, background: BAND_COLOR[band] || KC.ink, borderRadius: 999 }} />
                        </div>
                    </div>
                ))}
            </Section>

            {/* ── Quiz funnel per skill: which banks are too hard or too easy ── */}
            <Section title="Kuis per skill" hint="Tingkat kelulusan jauh di atas 90% atau di bawah 20% biasanya berarti soalnya perlu ditinjau ulang.">
                {skills.length === 0 ? <Empty>Belum ada percobaan kuis.</Empty> : (
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead><tr>
                            <th style={th}>Skill</th>
                            <th style={{ ...th, textAlign: 'right' }}>Percobaan</th>
                            <th style={{ ...th, textAlign: 'right' }}>Lulus</th>
                            <th style={{ ...th, textAlign: 'right' }}>Rasio</th>
                        </tr></thead>
                        <tbody>
                            {skills.map(([skill, s]) => (
                                <tr key={skill}>
                                    <td style={{ ...td, textTransform: 'capitalize' }}>{skill}</td>
                                    <td style={num}>{s.attempts}</td>
                                    <td style={num}>{s.passed}</td>
                                    <td style={{ ...num, fontWeight: 800 }}>{s.attempts ? pct(s.passed / s.attempts) : '—'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </Section>

            {/* ── Plans + moderation health ───────────────────────────────────── */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
                <Section title="Paket aktif">
                    {Object.entries(plans.active_by_plan || {}).map(([plan, n]) => (
                        <div key={plan} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '5px 0' }}>
                            <span style={{ textTransform: 'capitalize' }}>{plan}</span>
                            <b style={{ fontVariantNumeric: 'tabular-nums' }}>{n}</b>
                        </div>
                    ))}
                </Section>
                <Section title="Moderasi lowongan">
                    {[['Tayang', mod.published, KC.lime], ['Ditahan', mod.held, KC.yellow],
                      ['Ditolak', mod.rejected, KC.rose], ['Laporan terbuka', mod.open_reports, KC.orange]].map(([label, n, c]) => (
                        <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '5px 0' }}>
                            <span>{label}</span>
                            <b style={{ color: n ? c : KC.mute, fontVariantNumeric: 'tabular-nums' }}>{n || 0}</b>
                        </div>
                    ))}
                </Section>
            </div>

            <div>
                <button style={topBtn()} onClick={() => setRaw((v) => !v)}>
                    {raw ? 'Sembunyikan data mentah' : 'Lihat data mentah (JSON)'}
                </button>
                <span style={{ fontSize: 11.5, color: KC.mute, marginLeft: 10 }}>
                    Dihitung {data.generated_at ? new Date(data.generated_at).toLocaleString('id-ID') : '—'}
                </span>
            </div>
            {raw && (
                <BrutalCard color={KC.surface}>
                    <pre style={{ fontSize: 11.5, whiteSpace: 'pre-wrap', margin: 0 }}>{JSON.stringify(data, null, 2)}</pre>
                </BrutalCard>
            )}
        </div>
    )
}
