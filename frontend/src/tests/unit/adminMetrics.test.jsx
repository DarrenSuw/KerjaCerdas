import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import AdminMetrics from '../../components/AdminMetrics'

const FULL = {
    generated_at: '2026-09-20T09:00:00+00:00',
    usd_to_idr: 17600,
    ai_cost_by_task: {
        cv_parse: { calls: 4, tokens_in: 8000, tokens_out: 2000, cost_idr: 396, failures: 1, avg_cost_idr_per_call: 99 },
        automod: { calls: 2, tokens_in: 4000, tokens_out: 800, cost_idr: 60, failures: 0, avg_cost_idr_per_call: 30 },
    },
    applications: { total: 12, by_source: { link: 7, board: 5 } },
    outcomes_by_band: {
        strong: { applications: 4, reached_interview: 3, interview_rate: 0.75 },
        stretch: { applications: 8, reached_interview: 1, interview_rate: 0.125 },
    },
    quizzes: { submitted: 10, passed: 6, by_skill: { excel: { attempts: 6, passed: 4 } } },
    plans: { active_by_plan: { beacon: 2, lighthouse: 1, prism: 0 }, revenue_last_30_days_idr: 157000, pending_orders: 3 },
    moderation: { published: 9, held: 2, rejected: 1, open_reports: 0 },
}

describe('AdminMetrics', () => {
    it('shows the four headline business numbers', () => {
        const html = renderToStaticMarkup(<AdminMetrics data={FULL} />)
        expect(html).toContain('Rp456')          // total AI cost, 396 + 60
        expect(html).toContain('Rp157.000')      // revenue last 30 days, id-ID separators
        expect(html).toContain('60%')            // quiz pass rate, 6 of 10
        expect(html).toContain('3 pesanan menunggu pembayaran')
    })

    it('reports interview rate per score band', () => {
        const html = renderToStaticMarkup(<AdminMetrics data={FULL} />)
        expect(html).toContain('Strong')
        expect(html).toContain('75%')
        expect(html).toContain('3/4 lamaran')
    })

    it('keeps the raw JSON hidden until it is asked for', () => {
        const html = renderToStaticMarkup(<AdminMetrics data={FULL} />)
        expect(html).toContain('Lihat data mentah')
        expect(html).not.toContain('"usd_to_idr"')
    })

    // The house rule: never render a metric the data cannot back. An untouched
    // deployment must read "belum ada data", not a confident 0%.
    it('says there is no data instead of showing zeroes', () => {
        const empty = {
            generated_at: '2026-09-20T09:00:00+00:00', usd_to_idr: 17600,
            ai_cost_by_task: {}, applications: { total: 0, by_source: {} },
            outcomes_by_band: {}, quizzes: { submitted: 0, passed: 0, by_skill: {} },
            plans: { active_by_plan: {}, revenue_last_30_days_idr: 0, pending_orders: 0 },
            moderation: { published: 0, held: 0, rejected: 0, open_reports: 0 },
        }
        const html = renderToStaticMarkup(<AdminMetrics data={empty} />)
        expect(html).toContain('Belum ada panggilan AI')
        expect(html).toContain('Belum ada lamaran untuk diukur')
        expect(html).toContain('Belum ada percobaan kuis')
        // A rate or a cost with no underlying events reads "—", never a
        // confident 0%. (Matched as a standalone element value so the
        // "di bawah 20%" guidance text in a hint can't satisfy or break it.)
        expect(html).not.toContain('>0%<')
        // Revenue is the exception and deliberately still shows Rp0: no orders
        // really does mean no income, which is a measurement, not a guess.
        expect(html).toContain('>Rp0<')
    })
})
