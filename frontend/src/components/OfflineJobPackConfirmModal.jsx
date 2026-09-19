/**
 * OfflineJobPackConfirmModal — shown when uploadJobPack falls back to offline/demo
 * data (parsed_offline: true). The user must explicitly confirm before the
 * result is surfaced to the review table.
 */
import { KC, DesignStyles } from './_design'
import { AlertTriangle, WifiOff } from 'lucide-react'

export default function OfflineJobPackConfirmModal({ preview, onConfirm, onCancel }) {
    if (!preview) return null

    return (
        <div
            onClick={onCancel}
            style={{
                position: 'fixed',
                inset: 0,
                zIndex: 2000,
                background: 'rgba(9, 10, 15, 0.72)',
                backdropFilter: 'blur(4px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px',
            }}
        >
            <DesignStyles />

            <div
                onClick={e => e.stopPropagation()}
                style={{
                    background: KC.bone,
                    border: `2px solid ${KC.ink}`,
                    borderRadius: 16,
                    boxShadow: `5px 5px 0 ${KC.ink}`,
                    padding: '28px 28px 24px',
                    maxWidth: 460,
                    width: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 18,
                    animation: 'kcSlideUp .25s both',
                }}
            >
                {/* Warning header */}
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                    <div style={{
                        flexShrink: 0,
                        width: 44, height: 44,
                        borderRadius: 10,
                        background: KC.yellowSoft,
                        border: `1.5px solid ${KC.yellow}`,
                        display: 'grid', placeItems: 'center',
                    }}>
                        <WifiOff size={20} color={KC.yellow} />
                    </div>
                    <div>
                        <h2 style={{
                            font: '900 17px/1.2 "Plus Jakarta Sans", sans-serif',
                            color: KC.ink,
                            margin: '0 0 5px',
                            letterSpacing: '-0.4px',
                        }}>
                            Hasil Parsing Tidak Lengkap
                        </h2>
                        <p style={{
                            font: '400 13px/1.5 "Plus Jakarta Sans", sans-serif',
                            color: KC.mute,
                            margin: 0,
                        }}>
                            Gemini API tidak tersedia saat ini. Data lowongan di bawah berasal dari mode fallback (data demo) dan bukan hasil dari dokumen PDF Anda.
                        </p>
                    </div>
                </div>

                {/* Alert banner */}
                <div style={{
                    background: KC.yellowSoft,
                    border: `1.5px solid ${KC.yellow}`,
                    borderRadius: 9,
                    padding: '10px 13px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                }}>
                    <AlertTriangle size={15} color="#B45309" style={{ flexShrink: 0 }} />
                    <span style={{
                        font: '600 12.5px/1.4 "Plus Jakarta Sans", sans-serif',
                        color: '#92400E',
                    }}>
                        Meneruskan akan menampilkan lowongan demo ke draft Anda.
                    </span>
                </div>

                {/* Parsed preview */}
                <div style={{
                    background: '#fff',
                    border: `1.5px solid ${KC.ink}`,
                    borderRadius: 11,
                    boxShadow: `2.5px 2.5px 0 ${KC.ink}`,
                    padding: '16px 18px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10,
                }}>
                    <p style={{ margin: 0, font: '700 11px/1 "Plus Jakarta Sans", sans-serif', color: KC.mute, textTransform: 'uppercase', letterSpacing: 0.8 }}>
                        Preview Data Offline
                    </p>

                    <PreviewRow label="Lowongan" value={`${preview.jobs_count} posisi terdeteksi`} />
                    <PreviewRow label="Posisi 1" value={preview.sample_title || '—'} />
                </div>

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: 10 }}>
                    <button
                        onClick={onCancel}
                        className="kc-btn"
                        style={{
                            flex: 1,
                            padding: '12px 16px',
                            background: '#fff',
                            border: `1.5px solid ${KC.ink}`,
                            borderRadius: 10,
                            boxShadow: `2.5px 2.5px 0 ${KC.ink}`,
                            font: '700 13px/1 "Plus Jakarta Sans", sans-serif',
                            color: KC.ink,
                            cursor: 'pointer',
                        }}
                    >
                        Batalkan
                    </button>
                    <button
                        onClick={onConfirm}
                        className="kc-btn"
                        style={{
                            flex: 1,
                            padding: '12px 16px',
                            background: KC.yellow,
                            border: `1.5px solid ${KC.ink}`,
                            borderRadius: 10,
                            boxShadow: `2.5px 2.5px 0 ${KC.ink}`,
                            font: '700 13px/1 "Plus Jakarta Sans", sans-serif',
                            color: KC.ink,
                            cursor: 'pointer',
                        }}
                    >
                        Lanjutkan
                    </button>
                </div>
            </div>
        </div>
    )
}

function PreviewRow({ label, value }) {
    return (
        <div style={{ display: 'flex', gap: 10, alignItems: 'baseline' }}>
            <span style={{ font: '600 11.5px/1 "Plus Jakarta Sans", sans-serif', color: KC.mute, minWidth: 100 }}>{label}</span>
            <span style={{ font: '700 13px/1.3 "Plus Jakarta Sans", sans-serif', color: KC.ink }}>{value}</span>
        </div>
    )
}
