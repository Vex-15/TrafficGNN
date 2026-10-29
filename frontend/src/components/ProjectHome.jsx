import { useState } from 'react'
import { Alert, Chip, Spinner } from './ui'

const stageLabel = {
  template: 'Template audit',
  sources: 'Evidence ingest',
  review: 'Validation',
  generated: 'Generated',
}

const stageTone = {
  template: 'brand',
  sources: 'amber',
  review: 'amber',
  generated: 'emerald',
}

export default function ProjectHome({ projects, onCreate, onDemo, onOpen, onDelete, busy, error }) {
  const [form, setForm] = useState({
    name: 'Department Annual Report 2025-26',
    department: 'Computer Science & Engineering',
    academic_year: '2025-26',
    institution: 'Example Institute of Technology',
  })

  const update = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="animate-rise grid gap-8 lg:grid-cols-[1.15fr_0.85fr]">
        <div>
          <Chip tone="brand">Template-preserving reporting</Chip>
          <h1 className="font-display mt-4 text-4xl leading-[1.1] font-semibold tracking-tight text-ink-900">
            Turn scattered department evidence into a finished, on-template report.
          </h1>
          <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-ink-500">
            Upload the institutional DOCX template, drop in the messy evidence — meeting notes, Excel
            registers, PDFs, scanned certificates — and EduTemplateFitAI maps, extracts, validates and
            renders the report without breaking the original layout.
          </p>

          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {[
              ['01', 'Template audit', 'Structure, placeholders and quality scored before you commit.'],
              ['02', 'Evidence ingest', 'DOCX, XLSX, CSV, PDF, TXT and images normalised into one schema.'],
              ['03', 'Validation', 'Duplicate groups, conflicting values and evidence gaps surfaced.'],
              ['04', 'Template-faithful export', 'Human-approved records rendered back into the original layout.'],
            ].map(([step, title, copy]) => (
              <div key={step} className="card p-4">
                <span className="font-display text-xs font-semibold text-brand-600">{step}</span>
                <h3 className="font-display mt-1 text-sm font-semibold text-ink-900">{title}</h3>
                <p className="mt-1 text-xs leading-relaxed text-ink-500">{copy}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="card animate-rise p-6">
          <h2 className="font-display text-lg font-semibold text-ink-900">Start a reporting project</h2>
          <p className="mt-1 text-sm text-ink-500">Metadata feeds the placeholders in the template.</p>

          <form
            className="mt-5 space-y-3"
            onSubmit={(event) => {
              event.preventDefault()
              onCreate(form)
            }}
          >
            <div>
              <label className="label" htmlFor="name">
                Project name
              </label>
              <input id="name" className="input" value={form.name} onChange={update('name')} required />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="department">
                  Department
                </label>
                <input id="department" className="input" value={form.department} onChange={update('department')} />
              </div>
              <div>
                <label className="label" htmlFor="year">
                  Academic year
                </label>
                <input id="year" className="input" value={form.academic_year} onChange={update('academic_year')} />
              </div>
            </div>
            <div>
              <label className="label" htmlFor="institution">
                Institution
              </label>
              <input
                id="institution"
                className="input"
                value={form.institution}
                onChange={update('institution')}
              />
            </div>

            <Alert tone="rose">{error}</Alert>

            <button type="submit" className="btn-primary w-full" disabled={busy}>
              {busy ? <Spinner /> : null}
              Create project
            </button>
          </form>

          <div className="my-5 flex items-center gap-3 text-[11px] font-semibold tracking-[0.12em] text-ink-300 uppercase">
            <span className="h-px flex-1 bg-slate-200" />
            or
            <span className="h-px flex-1 bg-slate-200" />
          </div>

          <button type="button" className="btn-ghost w-full" onClick={onDemo} disabled={busy}>
            Load the demo dataset
          </button>
          <p className="mt-2 text-center text-xs text-ink-500">
            Generates a sample template plus DOCX, XLSX, PDF and image evidence — including a duplicate, a
            conflicting value and a gap.
          </p>
        </div>
      </div>

      <section className="mt-12">
        <div className="mb-4 flex items-end justify-between">
          <div>
            <h2 className="font-display text-lg font-semibold text-ink-900">Your projects</h2>
            <p className="text-sm text-ink-500">Everything is stored locally in the backend data folder.</p>
          </div>
          <span className="text-xs font-semibold text-ink-500">{projects.length} total</span>
        </div>

        {projects.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 px-6 py-10 text-center text-sm text-ink-500">
            No projects yet — create one above or load the demo dataset.
          </div>
        ) : (
          <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {projects.map((project) => (
              <li key={project.id} className="card group p-5 transition hover:-translate-y-0.5 hover:shadow-lg">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="font-display truncate text-sm font-semibold text-ink-900">{project.name}</h3>
                    <p className="mt-0.5 truncate text-xs text-ink-500">
                      {project.meta.department || 'No department'} · {project.meta.academic_year || '—'}
                    </p>
                  </div>
                  <Chip tone={stageTone[project.stage] ?? 'slate'}>{stageLabel[project.stage] ?? project.stage}</Chip>
                </div>
                <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
                  {[
                    ['Records', project.records],
                    ['Sources', project.sources],
                    ['Report', project.has_output ? 'ready' : '—'],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-lg bg-slate-50 py-2">
                      <dt className="text-[10px] font-semibold tracking-[0.08em] text-ink-500 uppercase">{label}</dt>
                      <dd className="font-display text-sm font-semibold text-ink-900">{value}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-4 flex items-center gap-2">
                  <button type="button" className="btn-primary flex-1" onClick={() => onOpen(project.id)}>
                    Open
                  </button>
                  <button
                    type="button"
                    className="btn-quiet px-3"
                    title="Delete project"
                    onClick={() => onDelete(project.id)}
                  >
                    ✕
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer className="mt-14 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 pt-5 text-xs text-ink-500">
        <span>EduTemplateFitAI · prototype</span>
        <span>
          {projects.reduce((sum, p) => sum + (p.records || 0), 0)} extracted records across{' '}
          {projects.reduce((sum, p) => sum + (p.sources || 0), 0)} sources
        </span>
      </footer>
    </div>
  )
}
