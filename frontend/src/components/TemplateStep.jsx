import { useMemo, useState } from 'react'
import { Alert, Chip, Dropzone, EmptyState, Meter, ScoreRing, SectionHeader, Spinner } from './ui'

const scoreMeta = [
  ['structure', 'Structure detection', 'Headings, numbering and hierarchy'],
  ['reproducibility', 'Layout reproducibility', 'Tables, merges and spacing fidelity'],
  ['placeholder_identification', 'Placeholder detection', 'Merge fields and blanks'],
  ['mapping_readiness', 'Mapping readiness', 'Sections matched to the schema'],
]

export default function TemplateStep({ project, categories, onUpload, onSaveMapping, onConfirm, busy, error }) {
  const analysis = project?.template?.analysis
  const confirmed = project?.template?.confirmed

  const seed = (source) =>
    Object.fromEntries((source?.sections ?? []).map((section) => [section.id, section.category || '']))

  const [mapping, setMapping] = useState(() => seed(analysis))
  const [dirty, setDirty] = useState(false)
  const [syncedAnalysis, setSyncedAnalysis] = useState(analysis)

  // Re-seed the selects whenever a different template analysis arrives (React's
  // documented "adjust state during render" pattern, no effect needed).
  if (analysis !== syncedAnalysis) {
    setSyncedAnalysis(analysis)
    setDirty(false)
    if (analysis) setMapping(seed(analysis))
  }

  const mappedCount = useMemo(
    () => Object.values(mapping).filter(Boolean).length,
    [mapping],
  )

  if (!analysis) {
    return (
      <div className="animate-rise">
        <SectionHeader
          eyebrow="Step 1"
          title="Audit the institutional template"
          description="Upload the DOCX template that the department must keep using. The analyser reads its structure, placeholders and tables before any content is generated."
        />
        <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <div className="card p-6">
            <Dropzone
              accept=".docx"
              busy={busy}
              onFiles={onUpload}
              title="Drop the template .docx here"
              hint="or click to browse · DOCX only · nothing leaves this machine"
            />
            <Alert tone="rose">{error}</Alert>
            <ul className="mt-5 space-y-2 text-sm text-ink-500">
              {[
                'Heading and numbering structure is detected to segment the report.',
                'Tables, merged cells, headers and footers are profiled for fidelity risk.',
                'Merge fields ({{…}}, <<…>>, [[…]]) and blank underscores are catalogued.',
                'Each section gets a proposed schema category you can override.',
              ].map((line) => (
                <li key={line} className="flex gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
                  {line}
                </li>
              ))}
            </ul>
          </div>
          <div className="card bg-gradient-to-br from-ink-950 to-ink-900 p-6 text-white">
            <h3 className="font-display text-base font-semibold">Why audit first?</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-300">
              Reports usually fail at the template boundary, not at the data. Scoring the template up front
              tells you whether automated rendering is safe — and which sections will need a human.
            </p>
            <div className="mt-5 space-y-3">
              {[
                ['Quality', 'Weighted score across 4 dimensions'],
                ['Mapping', 'Section → schema category proposals'],
                ['Fidelity', 'Render path keeps fonts, spacing, tables'],
              ].map(([title, copy]) => (
                <div key={title} className="rounded-xl bg-white/5 px-3.5 py-3 ring-1 ring-white/10">
                  <p className="text-xs font-semibold tracking-[0.1em] text-brand-300 uppercase">{title}</p>
                  <p className="mt-1 text-sm text-slate-200">{copy}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  const quality = analysis.quality

  return (
    <div className="animate-rise space-y-5">
      <SectionHeader
        eyebrow="Step 1"
        title="Template audit & mapping"
        description={`${project.template.filename} · ${analysis.sections.length} sections · ${analysis.tables.length} tables detected`}
        actions={
          <Chip tone={confirmed ? 'emerald' : 'amber'}>{confirmed ? 'Mapping confirmed' : 'Mapping not confirmed'}</Chip>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_1.25fr]">
        <div className="card p-6">
          <div className="flex items-center gap-6">
            <ScoreRing value={quality.overall} />
            <div>
              <p className="text-[11px] font-semibold tracking-[0.12em] text-ink-500 uppercase">Template quality</p>
              <p className="font-display mt-1 text-sm leading-relaxed font-semibold text-ink-900">
                {quality.recommendation}
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <Chip tone="brand">{analysis.sections.length} sections</Chip>
                <Chip tone="slate">{analysis.tables.length} tables</Chip>
                <Chip tone="slate">{analysis.placeholders.count} placeholders</Chip>
                {quality.ambiguous_fields > 0 ? <Chip tone="amber">{quality.ambiguous_fields} ambiguous</Chip> : null}
              </div>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {scoreMeta.map(([key, label, hint]) => (
              <div key={key}>
                <div className="flex items-baseline justify-between">
                  <span className="text-sm font-medium text-ink-900">{label}</span>
                  <span className="font-display text-sm font-semibold text-ink-700">{quality[key]}</span>
                </div>
                <Meter
                  className="mt-1.5"
                  value={quality[key]}
                  tone={quality[key] >= 90 ? 'emerald' : quality[key] >= 78 ? 'brand' : 'amber'}
                />
                <p className="mt-1 text-[11px] text-ink-500">{hint}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 grid grid-cols-2 gap-2 text-xs">
            {[
              ['Header/footer', analysis.has_header_footer ? 'detected' : 'none'],
              ['Inline images', analysis.image_count],
              ['Table detection', `${quality.table_detection}%`],
              ['Template title', analysis.title || '—'],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 px-3 py-2">
                <p className="text-[10px] font-semibold tracking-[0.08em] text-ink-500 uppercase">{label}</p>
                <p className="mt-0.5 truncate font-medium text-ink-900">{value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="card overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
            <div>
              <h3 className="font-display text-sm font-semibold text-ink-900">Section mapping</h3>
              <p className="text-xs text-ink-500">
                {mappedCount} of {analysis.sections.length} sections mapped to a schema category
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                className="btn-ghost"
                disabled={!dirty || busy}
                onClick={async () => {
                  await onSaveMapping(
                    Object.entries(mapping).map(([id, category]) => ({ id, category: category || null })),
                  )
                  setDirty(false)
                }}
              >
                {busy ? <Spinner /> : null}
                Save mapping
              </button>
              <button type="button" className="btn-primary" disabled={busy} onClick={onConfirm}>
                Confirm & continue
              </button>
            </div>
          </div>

          {analysis.sections.length === 0 ? (
            <div className="p-5">
              <EmptyState
                title="No headings detected"
                description="The analyser could not find headings or numbered sections. The template may need manual structuring before generation."
              />
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {analysis.sections.map((section) => (
                <li key={section.id} className="flex flex-wrap items-center gap-3 px-5 py-3">
                  <span
                    className="font-display w-7 shrink-0 text-center text-[11px] font-semibold text-ink-300"
                    aria-hidden
                  >
                    H{section.level}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink-900" title={section.title}>
                      {section.title}
                    </p>
                    <p className="text-[11px] text-ink-500">
                      {section.category
                        ? section.confidence >= 0.9
                          ? `High confidence match · ${Math.round(section.confidence * 100)}%`
                          : `Proposed match · ${Math.round(section.confidence * 100)}%`
                        : 'No category proposed'}
                      {section.table_index ? ' · linked table' : ''}
                    </p>
                  </div>
                  <select
                    className="input w-56 shrink-0 py-1.5 text-xs"
                    value={mapping[section.id] || ''}
                    onChange={(event) => {
                      setMapping((prev) => ({ ...prev, [section.id]: event.target.value }))
                      setDirty(true)
                    }}
                  >
                    <option value="">Unmapped</option>
                    {categories.map((category) => (
                      <option key={category.key} value={category.key}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                </li>
              ))}
            </ul>
          )}

          <Alert tone="rose">{error}</Alert>
        </div>
      </div>
    </div>
  )
}
