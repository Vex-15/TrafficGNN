import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import ProjectHome from './components/ProjectHome'
import TemplateStep from './components/TemplateStep'
import EvidenceStep from './components/EvidenceStep'
import ReviewStep from './components/ReviewStep'
import ExportStep from './components/ExportStep'
import { Chip, Spinner } from './components/ui'

const steps = [
  { key: 'template', label: 'Template audit', hint: 'Structure, quality, mapping' },
  { key: 'evidence', label: 'Evidence ingest', hint: 'Documents, sheets, images' },
  { key: 'review', label: 'Validation', hint: 'Approve, fix, reconcile' },
  { key: 'export', label: 'Generate & export', hint: 'DOCX + PDF output' },
]

const stepForStage = (stage) => {
  if (stage === 'generated') return 3
  if (stage === 'review') return 2
  if (stage === 'sources') return 1
  return 0
}

export default function App() {
  const [projects, setProjects] = useState([])
  const [categories, setCategories] = useState([])
  const [project, setProject] = useState(null)
  const [step, setStep] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [uploadErrors, setUploadErrors] = useState([])
  const [booting, setBooting] = useState(true)

  const refreshProjects = useCallback(async () => {
    const list = await api.listProjects()
    setProjects(list)
    return list
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [, schema] = await Promise.all([refreshProjects(), api.schema()])
        if (!cancelled) setCategories(schema.categories)
      } catch (err) {
        if (!cancelled) setError(`Cannot reach the backend: ${err.message}`)
      } finally {
        if (!cancelled) setBooting(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [refreshProjects])

  const run = async (action, { keepStep = false } = {}) => {
    setBusy(true)
    setError('')
    try {
      const result = await action()
      if (result?.project) {
        setProject(result.project)
        if (!keepStep) setStep(stepForStage(result.project.stage))
      } else if (result?.id) {
        setProject(result)
        if (!keepStep) setStep(stepForStage(result.stage))
      }
      await refreshProjects()
      return result
    } catch (err) {
      setError(err.message)
      return null
    } finally {
      setBusy(false)
    }
  }

  const openProject = async (id) => {
    setBusy(true)
    setError('')
    try {
      const loaded = await api.getProject(id)
      setProject(loaded)
      setStep(stepForStage(loaded.stage))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const createProject = (payload) =>
    run(() => api.createProject(payload), { keepStep: true }).then((created) => {
      if (created) setStep(0)
    })

  const createDemo = () =>
    run(() => api.createDemo(), { keepStep: true }).then((created) => {
      if (created) setStep(0)
    })

  const deleteProject = async (id) => {
    if (!window.confirm('Delete this project and all of its extracted data?')) return
    setBusy(true)
    try {
      await api.deleteProject(id)
      if (project?.id === id) setProject(null)
      await refreshProjects()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const goHome = () => {
    setProject(null)
    setError('')
    setStep(0)
  }

  if (booting) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-3 text-sm text-ink-500">
        <Spinner className="h-5 w-5" /> Starting EduTemplateFitAI…
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-paper/85 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl items-center gap-4 px-6 py-3.5">
          <button type="button" onClick={goHome} className="flex items-center gap-2.5 text-left">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink-950 text-sm font-semibold text-white">
              EF
            </span>
            <span>
              <span className="font-display block text-sm leading-tight font-semibold text-ink-900">
                EduTemplateFitAI
              </span>
              <span className="block text-[10px] tracking-[0.14em] text-ink-500 uppercase">
                Evidence → template-faithful report
              </span>
            </span>
          </button>

          <div className="flex-1" />

          {project ? (
            <div className="hidden items-center gap-3 md:flex">
              <span className="max-w-72 truncate text-sm font-medium text-ink-700">{project.name}</span>
              <Chip tone={project.stage === 'generated' ? 'emerald' : 'brand'}>{project.stage}</Chip>
            </div>
          ) : (
            <span className="hidden text-xs text-ink-500 sm:block">
              {projects.length} project{projects.length === 1 ? '' : 's'} · local prototype
            </span>
          )}

          <button type="button" className="btn-ghost px-3 py-2 text-xs" onClick={goHome}>
            All projects
          </button>
        </div>
      </header>

      {project ? (
        <div className="mx-auto grid w-full max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[220px_1fr]">
          <aside className="lg:sticky lg:top-20 lg:self-start">
            <ol className="space-y-1">
              {steps.map((item, index) => {
                const state = index === step ? 'current' : index < step ? 'done' : 'todo'
                const unlocked = index === 0 || Boolean(project.template)
                return (
                  <li key={item.key}>
                    <button
                      type="button"
                      disabled={!unlocked}
                      onClick={() => setStep(index)}
                      className={`flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition ${
                        state === 'current'
                          ? 'bg-white shadow-sm ring-1 ring-slate-200'
                          : unlocked
                            ? 'hover:bg-white/70'
                            : 'cursor-not-allowed opacity-50'
                      }`}
                    >
                      <span
                        className={`font-display mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
                          state === 'done'
                            ? 'bg-emerald-100 text-emerald-700'
                            : state === 'current'
                              ? 'bg-brand-600 text-white'
                              : 'bg-slate-200 text-ink-500'
                        }`}
                      >
                        {state === 'done' ? '✓' : index + 1}
                      </span>
                      <span className="min-w-0">
                        <span
                          className={`block text-sm font-medium ${
                            state === 'current' ? 'text-ink-900' : 'text-ink-700'
                          }`}
                        >
                          {item.label}
                        </span>
                        <span className="block truncate text-[11px] text-ink-500">{item.hint}</span>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ol>

            <div className="mt-5 rounded-xl bg-white/70 px-3.5 py-3 text-[11px] leading-relaxed text-ink-500 ring-1 ring-slate-200">
              <p className="mb-1 font-semibold tracking-[0.08em] text-ink-700 uppercase">Project</p>
              <p className="truncate">{project.meta.institution || 'No institution set'}</p>
              <p className="truncate">{project.meta.department || 'No department set'}</p>
              <p className="truncate">{project.meta.academic_year || 'No academic year'}</p>
            </div>
          </aside>

          <main className="min-w-0 pb-16">
            {step === 0 ? (
              <TemplateStep
                project={project}
                categories={categories}
                busy={busy}
                error={error}
                onUpload={(file) => run(() => api.uploadTemplate(project.id, file))}
                onSaveMapping={(sections) =>
                  run(() => api.updateSections(project.id, sections), { keepStep: true })
                }
                onConfirm={() =>
                  run(() => api.confirmTemplate(project.id)).then((result) => {
                    if (result) setStep(1)
                  })
                }
              />
            ) : null}

            {step === 1 ? (
              <EvidenceStep
                project={project}
                busy={busy}
                error={error}
                uploadErrors={uploadErrors}
                onUpload={(files) =>
                  run(() => api.uploadSources(project.id, files), { keepStep: true }).then((result) => {
                    if (result) setUploadErrors(result.errors ?? [])
                  })
                }
                onDeleteSource={(sourceId) =>
                  run(() => api.deleteSource(project.id, sourceId), { keepStep: true })
                }
                onContinue={() => setStep(2)}
              />
            ) : null}

            {step === 2 ? (
              <ReviewStep
                project={project}
                categories={categories}
                busy={busy}
                error={error}
                onPatch={(recordId, payload) =>
                  run(() => api.patchRecord(project.id, recordId, payload), { keepStep: true })
                }
                onApproveSafe={() =>
                  run(() => api.approveSafe(project.id), { keepStep: true })
                }
                onResolveDuplicate={(duplicateId, action) =>
                  run(() => api.resolveDuplicate(project.id, duplicateId, action), { keepStep: true })
                }
                onResolveConflict={(conflictId, recordId) =>
                  run(() => api.resolveConflict(project.id, conflictId, recordId), { keepStep: true })
                }
                onContinue={() => setStep(3)}
              />
            ) : null}

            {step === 3 ? (
              <ExportStep
                project={project}
                busy={busy}
                error={error}
                onGenerate={(payload) =>
                  run(() => api.generate(project.id, payload), { keepStep: true })
                }
                onBack={() => setStep(2)}
              />
            ) : null}
          </main>
        </div>
      ) : (
        <ProjectHome
          projects={projects}
          onCreate={createProject}
          onDemo={createDemo}
          onOpen={openProject}
          onDelete={deleteProject}
          busy={busy}
          error={error}
        />
      )}
    </div>
  )
}
