import { useState } from 'react'
import { Alert, Chip, Meter, ScoreRing, SectionHeader, Spinner, StatTile } from './ui'
import { formatBytes } from '../api'

const metricMeta = [
  ['template_fidelity', 'Template fidelity', 'Layout and styling preserved'],
  ['content_completeness', 'Content completeness', 'Required fields filled'],
  ['section_coverage', 'Section coverage', 'Mapped sections with approved data'],
  ['average_confidence', 'Average confidence', 'Across approved records'],
]

export default function ExportStep({ project, onGenerate, onBack, busy, error }) {
  const [includeAudit, setIncludeAudit] = useState(true)
  const [faculty, setFaculty] = useState('')

  const generated = project?.generated
  const summary = project?.summary ?? {}
  const pending = summary.pending_review ?? 0
  const approved = (project?.records ?? []).filter((record) => record.approved && !record.duplicate_of).length

  return (
    <div className="animate-rise space-y-5">
      <SectionHeader
        eyebrow="Step 4"
        title="Generate the report"
        description="Approved records are rendered into a copy of your template. Downloads are produced as DOCX (layout intact) and PDF."
        actions={
          <button type="button" className="btn-ghost" onClick={onBack} disabled={busy}>
            Back to review
          </button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Approved records" value={approved} hint="ready" tone="emerald" />
        <StatTile label="Pending" value={pending} hint="not rendered" tone="amber" />
        <StatTile label="Sections" value={summary.mapped_sections ?? 0} hint="mapped" />
        <StatTile label="Sources" value={summary.sources ?? 0} hint="cited" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr]">
        <div className="card p-6">
          <h3 className="font-display text-sm font-semibold text-ink-900">Generation settings</h3>
          <p className="mt-1 text-xs text-ink-500">
            Placeholders are filled from project metadata and the fields below.
          </p>

          <div className="mt-5 space-y-3">
            {[
              ['Institution', project?.meta?.institution || '—'],
              ['Department', project?.meta?.department || '—'],
              ['Academic year', project?.meta?.academic_year || '—'],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between rounded-lg bg-slate-50 px-3.5 py-2.5">
                <span className="text-xs font-medium text-ink-500">{label}</span>
                <span className="truncate text-sm font-medium text-ink-900">{value}</span>
              </div>
            ))}
            <div>
              <label className="label" htmlFor="faculty">
                Prepared by (FACULTY_NAME placeholder)
              </label>
              <input
                id="faculty"
                className="input"
                placeholder="e.g. Dr. A. Sharma, HOD"
                value={faculty}
                onChange={(event) => setFaculty(event.target.value)}
              />
            </div>

            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 px-3.5 py-3">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 accent-indigo-600"
                checked={includeAudit}
                onChange={(event) => setIncludeAudit(event.target.checked)}
              />
              <span>
                <span className="block text-sm font-medium text-ink-900">Append traceability annexure</span>
                <span className="block text-xs text-ink-500">
                  Lists every rendered record with its source file and confidence.
                </span>
              </span>
            </label>
          </div>

          <Alert tone="rose">{error}</Alert>
          {pending > 0 ? (
            <p className="mt-3 rounded-xl bg-amber-50 px-3.5 py-2.5 text-xs text-amber-800 ring-1 ring-amber-200/70">
              {pending} record{pending === 1 ? '' : 's'} still pending — they will not appear in the report.
            </p>
          ) : null}

          <button
            type="button"
            className="btn-primary mt-4 w-full"
            disabled={busy || approved === 0}
            onClick={() =>
              onGenerate({
                include_audit: includeAudit,
                placeholders: faculty.trim() ? { FACULTY_NAME: faculty.trim() } : {},
              })
            }
          >
            {busy ? <Spinner /> : null}
            {generated ? 'Regenerate report' : 'Generate report'}
          </button>
          {approved === 0 ? (
            <p className="mt-2 text-center text-xs text-ink-500">Approve at least one record first.</p>
          ) : null}
        </div>

        <div className="space-y-4">
          {generated ? (
            <>
              <div className="card p-6">
                <div className="flex items-center gap-5">
                  <ScoreRing value={generated.metrics.template_fidelity} label="Fidelity" size={112} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-display text-sm font-semibold text-ink-900">Report generated</h3>
                      <Chip tone="emerald">ready</Chip>
                    </div>
                    <p className="mt-1 text-xs text-ink-500">
                      {generated.metrics.approved_records} approved records ·{' '}
                      {generated.metrics.sections_filled} sections filled
                    </p>
                    <div className="mt-3 grid grid-cols-2 gap-2">
                      <a className="btn-primary text-xs" href={generated.docx.url} download>
                        ↓ DOCX · {formatBytes(generated.docx.size)}
                      </a>
                      <a className="btn-ghost text-xs" href={generated.pdf.url} download>
                        ↓ PDF · {formatBytes(generated.pdf.size)}
                      </a>
                    </div>
                  </div>
                </div>

                <div className="mt-6 space-y-3">
                  {metricMeta.map(([key, label, hint]) => (
                    <div key={key}>
                      <div className="flex items-baseline justify-between">
                        <span className="text-xs font-medium text-ink-900">{label}</span>
                        <span className="font-display text-xs font-semibold text-ink-700">
                          {generated.metrics[key]}%
                        </span>
                      </div>
                      <Meter
                        className="mt-1"
                        value={generated.metrics[key]}
                        tone={generated.metrics[key] >= 90 ? 'emerald' : generated.metrics[key] >= 75 ? 'brand' : 'amber'}
                      />
                      <p className="mt-0.5 text-[10px] text-ink-500">{hint}</p>
                    </div>
                  ))}
                </div>
              </div>

              {generated.metrics.sections_empty?.length > 0 ? (
                <div className="card p-5">
                  <h4 className="font-display text-sm font-semibold text-ink-900">Sections rendered empty</h4>
                  <p className="mt-1 text-xs text-ink-500">
                    No approved evidence reached these sections; the template headings were preserved.
                  </p>
                  <ul className="mt-2 flex flex-wrap gap-1.5">
                    {generated.metrics.sections_empty.map((section) => (
                      <li key={section}>
                        <Chip tone="amber">{section}</Chip>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="card overflow-hidden">
                <div className="border-b border-slate-100 px-5 py-3.5">
                  <h4 className="font-display text-sm font-semibold text-ink-900">Render details</h4>
                </div>
                <dl className="divide-y divide-slate-100 text-sm">
                  {[
                    ['Filename', generated.docx.filename],
                    ['Records rendered', `${generated.metrics.approved_records} of ${generated.metrics.total_records}`],
                    ['Annexure', generated.include_audit ? 'included' : 'not included'],
                    ['Rendered at', new Date(generated.generated_at).toLocaleString()],
                  ].map(([label, value]) => (
                    <div key={label} className="flex items-center justify-between gap-4 px-5 py-2.5">
                      <dt className="text-xs text-ink-500">{label}</dt>
                      <dd className="truncate text-xs font-medium text-ink-900">{value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </>
          ) : (
            <div className="card flex h-full flex-col items-center justify-center gap-3 p-10 text-center">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-xl text-brand-600">
                ⎙
              </span>
              <h3 className="font-display text-base font-semibold text-ink-900">Nothing generated yet</h3>
              <p className="max-w-sm text-sm text-ink-500">
                The renderer edits a copy of your uploaded template, so fonts, tables, headers and footers
                survive the merge. Generate to see fidelity and completeness metrics.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
