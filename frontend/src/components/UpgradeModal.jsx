/**
 * Plans modal — Spark / Beacon / Lighthouse for employers, Free / Prism for
 * job seekers. Prices come from GET /billing/plans (backend settings).
 *
 * Payment is manual until a payment gateway is live: choosing a plan creates
 * a "pending" order with a code; the user pays by QRIS / bank transfer and an
 * admin activates it for 30 days. Paying never changes a match score.
 */
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Check, X } from 'lucide-react'
import useStore from '../store/useStore'
import { KC, topBtn } from './_design'
import { createPlanOrder, fetchPlans } from '../services/api'

const NAMES = { spark: 'Spark', beacon: 'Beacon', lighthouse: 'Lighthouse', free: 'Gratis', prism: 'Prism' }
const TAGLINE = {
    spark: 'Coba dulu, gratis',
    beacon: 'Per lowongan, 30 hari',
    lighthouse: 'Untuk yang rutin merekrut',
    free: 'Untuk semua pencari kerja',
    prism: 'Latihan & kuis lebih sering',
}

export default function UpgradeModal() {
    const { upgradeModalOpen, closeUpgradeModal, upgradeContext, userRole, employerJobs } = useStore()
    const [catalogue, setCatalogue] = useState(null)
    const [order, setOrder] = useState(null)
    const [jobId, setJobId] = useState('')

    // eslint-disable-next-line react-hooks/set-state-in-effect
    useEffect(() => {
        if (!upgradeModalOpen) return
        setOrder(null)
        setJobId(upgradeContext?.jobId || '')
        fetchPlans().then(setCatalogue).catch(() => setCatalogue(null))
    }, [upgradeModalOpen, upgradeContext])

    if (!upgradeModalOpen) return null
    const tiers = catalogue ? (userRole === 'employer' ? catalogue.employer : catalogue.seeker) : []

    const buy = async (plan) => {
        if (plan === 'beacon' && !jobId) {
            toast.error('Pilih lowongan untuk Beacon')
            return
        }
        try {
            setOrder(await createPlanOrder(plan, plan === 'beacon' ? jobId : null))
        } catch (e) {
            toast.error(e.message)
        }
    }

    return (
        <div onClick={closeUpgradeModal} style={{ position: 'fixed', inset: 0, background: 'rgba(9,10,15,0.55)', zIndex: 70, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
            <div role="dialog" aria-label="Paket KerjaCerdas" onClick={(e) => e.stopPropagation()}
                style={{ background: KC.bone, border: `1.5px solid ${KC.ink}`, borderRadius: 16, boxShadow: `6px 6px 0 ${KC.ink}`, width: '100%', maxWidth: 920, maxHeight: '92vh', overflowY: 'auto', padding: 22 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontWeight: 900, fontSize: 22 }}>Paket KerjaCerdas</div>
                    <button aria-label="Tutup" onClick={closeUpgradeModal} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X /></button>
                </div>
                <p style={{ color: KC.mute, fontSize: 13, margin: '4px 0 16px' }}>{catalogue?.note}</p>

                {order ? (
                    <div style={{ background: KC.paper, border: `1.5px solid ${KC.ink}`, borderRadius: 12, padding: 18 }}>
                        <div style={{ fontWeight: 900, fontSize: 18 }}>Pesanan {NAMES[order.plan]} dibuat</div>
                        <p>Kode pesanan: <b style={{ fontFamily: 'monospace', fontSize: 18 }}>{order.order_code}</b> · Total <b>Rp{order.amount_idr.toLocaleString('id-ID')}</b></p>
                        <p style={{ fontSize: 14 }}>{order.payment_instructions}</p>
                        <p style={{ fontSize: 13, color: KC.mute }}>Status: menunggu pembayaran. Paket aktif 30 hari setelah admin mengonfirmasi.</p>
                        <button style={topBtn(KC.ink, '#fff')} onClick={closeUpgradeModal}>Mengerti</button>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14 }}>
                        {tiers.map((t) => {
                            const paid = t.price_idr > 0
                            const highlight = t.plan === (upgradeContext?.plan || (userRole === 'employer' ? 'beacon' : 'prism'))
                            return (
                                <div key={t.plan} style={{ background: highlight ? KC.orangeSoft : KC.paper, border: `1.5px solid ${KC.ink}`, borderRadius: 12, padding: 18, boxShadow: `3px 3px 0 ${KC.ink}`, display: 'flex', flexDirection: 'column' }}>
                                    <div style={{ fontWeight: 900, fontSize: 20 }}>{NAMES[t.plan]}</div>
                                    <div style={{ fontSize: 13, color: KC.mute }}>{TAGLINE[t.plan]}</div>
                                    <div style={{ fontSize: 26, fontWeight: 900, margin: '10px 0 2px' }}>{paid ? `Rp${t.price_idr.toLocaleString('id-ID')}` : 'Rp0'}</div>
                                    <div style={{ fontSize: 12, color: KC.mute }}>{t.period}</div>
                                    <ul style={{ listStyle: 'none', padding: 0, margin: '12px 0', display: 'grid', gap: 6, fontSize: 13, flex: 1 }}>
                                        {t.features.map((f) => <li key={f} style={{ display: 'flex', gap: 6 }}><Check size={14} color="#059669" style={{ flexShrink: 0, marginTop: 2 }} />{f}</li>)}
                                    </ul>
                                    {t.plan === 'beacon' && (
                                        <select value={jobId} onChange={(e) => setJobId(e.target.value)}
                                            style={{ padding: 8, border: `1.5px solid ${KC.ink}`, borderRadius: 8, marginBottom: 8, fontFamily: 'inherit' }}>
                                            <option value="">Pilih lowongan…</option>
                                            {(employerJobs || []).map((j) => <option key={j.id || j.job_id} value={j.id || j.job_id}>{j.title}</option>)}
                                        </select>
                                    )}
                                    {paid
                                        ? <button style={topBtn(KC.orange, '#fff')} onClick={() => buy(t.plan)}>Pilih {NAMES[t.plan]}</button>
                                        : <div style={{ fontSize: 13, fontWeight: 700, color: KC.mute }}>Paket dasar semua akun</div>}
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>
        </div>
    )
}
