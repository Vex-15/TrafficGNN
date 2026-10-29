import { useMemo, useState } from 'react'
import { statusMeta, toneClasses } from '../api'
import { Alert, Chip, EmptyState, Meter, SectionHeader, Spinner, StatTile } from './ui'

const tabs = [
  ['records', 'Records'],
  ['duplicates', 'Duplicates'],
  ['conflicts', 'Conflicts'],
  ['gaps', 'Evidence gaps'],
]

const filters = [
  ['all', 'All'],
  ['pending', 'Pending'],
  ['approved', 'Approved'],
  ['auto', 'Auto'],
  ['review', 'Review'],
  ['manual', 'Manual'],
  ['conflict', 'Conflict'],
]

export default function ReviewStep({
  project,
  categories,
  onPatch,
  onApproveSafe,
  onResolveDuplicate,
  onResolveConflict,
  onContinue,
  busy,
  error,
}) {
  const [tab, setTab] = useState('records')
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [openId, setOpenId] = useState(null)
  const [notice, setNotice] = useState('')

  const records = useMemo(() => project?.records ?? [], [project])
  const validation = project?.validation ?? { duplicates: [], conflicts: [], missing: [], stats: {} }
  const summary = project?.summary ?? {}
  const stats = validation.stats ?? {}

  const fieldLabels = useMemo(() => {
    const map = {}
    categories.forEach((category) => category.fields.forEach((field) => (map[field.key] = field.label)))
    return map
  }, [categories])

  const fieldsFor = (record) => {
    const category = categories.find((item) => item.key === record.category)
    if (category?.fields?.length) return category.fields
    return Object.keys(record.fields).map((key) => ({ key, label: fieldLabels[key] ?? key, required: false }))
  }

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase()
    return records
      .filter((record) => !record.duplicate_of)
      .filter((record) => {
        if (filter === 'all') return true
        if (filter === 'pending') return !record.approved
        if (filter === 'approved') return record.approved
        return record.status === filter
      })
      .filter((record) => {
        if (!query) return true
        return (
          (record.display?.primary || '').toLowerCase().includes(query) ||
          (record.display?.secondary || '').toLowerCase().includes(query) ||
          (record.category_label || '').toLowerCase().includes(query) ||
          (record.source?.file || '').toLowerCase().includes(query)
        )
      })
  }, [records, filter, search])

  const pending = records.filter((record) => !record.approved && !record.duplicate_of).length
  const safeCandidates = records.filter(
    (record) =>
      !record.approved &&
      !record.duplicate_of &&
      !record.conflict &&
      ['auto', 'verified', 'review'].includes(record.status),
  ).length
  const duplicateCount = validation.duplicates.length
  const conflictCount = validation.conflicts.length
  const gapCount = validation.missing.length

  return (
    <div className="animate-rise space-y-5">
      <SectionHeader
        eyebrow="Step 3"
        title="Validate, review and approve"
        description="Extraction is a proposal, not the truth. Approve what is right, fix what is not, and resolve duplicates and conflicts before anything is rendered."
        actions={
          <>
            <button
              type="button"
              className="btn-ghost"
              disabled={busy || safeCandidates === 0}
              onClick={async () => {
                const result = await onApproveSafe()
                if (result) {
                  setNotice(
                    result.approved > 0
                      ? `${result.approved} record${result.approved === 1 ? '' : 's'} approved`
                      : 'Nothing left to auto-approve',
                  )
                }
              }}
            >
              Approve all safe
              {safeCandidates > 0 ? ` (${safeCandidates})` : ''}
            </button>
            <button type="button" className="btn-primary" onClick={onContinue} disabled={busy}>
              {pending > 0 ? `Continue · ${pending} pending` : 'Continue to export'}
            </button>
          </>
        }
      />

      {notice ? (
        <div className="flex items-center justify-between rounded-xl bg-emerald-50 px-3.5 py-2 text-xs font-medium text-emerald-800 ring-1 ring-emerald-200/70">
          {notice}
          <button type="button" className="text-emerald-700/70 hover:text-emerald-900" onClick={() => setNotice('')}>
            ✕
          </button>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Records" value={stats.records ?? summary.records ?? 0} hint={`${summary.images ?? 0} images`} />
        <StatTile label="Duplicates" value={duplicateCount} hint="groups" tone="amber" />
        <StatTile label="Conflicts" value={conflictCount} hint="values" tone="rose" />
        <StatTile label="Evidence gaps" value={gapCount} hint="missing" tone="amber" />
      </div>

      <div className="card overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
          <nav className="flex gap-1 rounded-xl bg-slate-100 p-1">
            {tabs.map(([key, label]) => {
              const count =
                key === 'records'
                  ? records.filter((record) => !record.duplicate_of).length
                  : key === 'duplicates'
                    ? duplicateCount
                    : key === 'conflicts'
                      ? conflictCount
                      : gapCount
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setTab(key)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    tab === key ? 'bg-white text-ink-900 shadow-sm' : 'text-ink-500 hover:text-ink-900'
                  }`}
                >
                  {label}
                  <span className={`ml-1.5 ${tab === key ? 'text-brand-600' : 'text-ink-300'}`}>{count}</span>
                </button>
              )
            })}
          </nav>

          {tab === 'records' ? (
            <div className="flex flex-1 flex-wrap items-center justify-end gap-2">
              <input
                className="input max-w-56 py-1.5 text-xs"
                placeholder="Search records, sources…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
              <select
                className="input w-36 py-1.5 text-xs"
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
              >
                {filters.map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
        </div>

        <Alert tone="rose">{error}</Alert>

        {tab === 'records' ? (
          visible.length === 0 ? (
            <div className="p-5">
              <EmptyState title="No records match" description="Try a different filter or clear the search." />
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {visible.map((record) => {
                const meta = statusMeta[record.status] ?? statusMeta.unverified
                const open = openId === record.id
                return (
                  <li key={record.id} className={`transition ${open ? 'bg-slate-50/70' : ''}`}>
                    <div className="flex flex-wrap items-start gap-3 px-5 py-3.5">
                      <button
                        type="button"
                        onClick={() => setOpenId(open ? null : record.id)}
                        className="min-w-0 flex-1 text-left"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="truncate text-sm font-semibold text-ink-900">
                            {record.display?.primary || 'Untitled record'}
                          </span>
                          <Chip tone="brand">{record.category_label}</Chip>
                          <span className={`chip ${toneClasses[meta.tone]}`}>{meta.label}</span>
                          {record.edited ? <Chip tone="slate">edited</Chip> : null}
                        </div>
                        <p className="mt-1 line-clamp-2 text-xs text-ink-500">{record.display?.secondary || '—'}</p>
                        <div className="mt-2 flex items-center gap-2">
                          <Meter
                            value={record.confidence * 100}
                            tone={record.confidence >= 0.9 ? 'emerald' : record.confidence >= 0.75 ? 'brand' : 'amber'}
                            className="max-w-40"
                          />
                          <span className="text-[11px] font-medium text-ink-500">
                            {Math.round(record.confidence * 100)}%
                          </span>
                          <span className="truncate text-[11px] text-ink-300">· {record.source?.file}</span>
                        </div>
                      </button>

                      <div className="flex shrink-0 items-center gap-2">
                        <button
                          type="button"
                          className={`btn px-3 py-1.5 text-xs ${
                            record.approved
                              ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
                              : 'bg-brand-600 text-white hover:bg-brand-700'
                          }`}
                          disabled={busy}
                          onClick={() => onPatch(record.id, { approved: !record.approved })}
                        >
                          {record.approved ? '✓ Approved' : 'Approve'}
                        </button>
                        <button
                          type="button"
                          className="btn-quiet px-2 py-1.5 text-xs"
                          onClick={() => setOpenId(open ? null : record.id)}
                        >
                          {open ? 'Close' : 'Edit'}
                        </button>
                      </div>
                    </div>

                    {open ? (
                      <RecordEditor
                        record={record}
                        fields={fieldsFor(record)}
                        categories={categories}
                        busy={busy}
                        onSave={(payload) => onPatch(record.id, payload)}
                        onClose={() => setOpenId(null)}
                      />
                    ) : null}
                  </li>
                )
              })}
            </ul>
          )
        ) : null}

        {tab === 'duplicates' ? (
          duplicateCount === 0 ? (
            <div className="p-5">
              <EmptyState icon="⧉" title="No duplicate groups" description="No records look like the same activity reported twice." />
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {validation.duplicates.map((group) => {
                const pair = group.record_ids.map((id) => records.find((record) => record.id === id)).filter(Boolean)
                return (
                  <li key={group.id} className="px-5 py-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-ink-900">{group.title}</p>
                        <p className="text-xs text-ink-500">{group.reason}</p>
                        <p className="mt-1 text-[11px] text-ink-300">
                          {group.sources.join('  ↔  ')}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="btn-ghost px-3 py-1.5 text-xs"
                          disabled={busy}
                          onClick={() => onResolveDuplicate(group.id, 'keep_both')}
                        >
                          Keep both
                        </button>
                        <button
                          type="button"
                          className="btn-primary px-3 py-1.5 text-xs"
                          disabled={busy}
                          onClick={() => onResolveDuplicate(group.id, 'discard')}
                        >
                          Discard duplicate
                        </button>
                      </div>
                    </div>
                    <div className="mt-3 grid gap-2 md:grid-cols-2">
                      {pair.map((record, index) => (
                        <div key={record.id} className="rounded-xl bg-slate-50 px-3.5 py-2.5">
                          <p className="text-[10px] font-semibold tracking-[0.08em] text-ink-500 uppercase">
                            {index === 0 ? 'Keep' : 'Duplicate'} · {record.source.file}
                          </p>
                          <p className="mt-0.5 truncate text-sm font-medium text-ink-900">{record.display?.primary}</p>
                          <p className="truncate text-xs text-ink-500">{record.display?.secondary}</p>
                        </div>
                      ))}
                    </div>
                  </li>
                )
              })}
            </ul>
          )
        ) : null}

        {tab === 'conflicts' ? (
          conflictCount === 0 ? (
            <div className="p-5">
              <EmptyState icon="≠" title="No conflicts" description="No two sources disagree on a critical field." />
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {validation.conflicts.map((conflict) => (
                <li key={conflict.id} className="px-5 py-4">
                  <p className="text-sm font-semibold text-ink-900">{conflict.title}</p>
                  <p className="text-xs text-ink-500">
                    {conflict.reason} — choose the value to keep. It is applied to every record in the group.
                  </p>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    {conflict.values.map((option) => (
                      <button
                        key={option.record_id}
                        type="button"
                        disabled={busy}
                        onClick={() => onResolveConflict(conflict.id, option.record_id)}
                        className="rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-left transition hover:border-brand-400 hover:bg-brand-50/50"
                      >
                        <p className="text-[10px] font-semibold tracking-[0.08em] text-ink-500 uppercase">
                          {option.source}
                        </p>
                        <p className="font-display mt-0.5 text-sm font-semibold text-ink-900">{option.value}</p>
                        <p className="mt-1 text-[11px] text-brand-600">Use this value →</p>
                      </button>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          )
        ) : null}

        {tab === 'gaps' ? (
          gapCount === 0 ? (
            <div className="p-5">
              <EmptyState icon="◎" title="No gaps" description="Every mapped section and required field has evidence." />
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {validation.missing.map((gap) => (
                <li key={gap.id} className="flex items-start gap-3 px-5 py-3.5">
                  <span
                    className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs ${
                      gap.type === 'section' ? 'bg-amber-50 text-amber-700' : 'bg-rose-50 text-rose-700'
                    }`}
                  >
                    {gap.type === 'section' ? '§' : '!'}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-medium text-ink-900">{gap.title}</p>
                      <Chip tone={gap.type === 'section' ? 'amber' : 'rose'}>{gap.type}</Chip>
                    </div>
                    <p className="mt-0.5 text-xs text-ink-500">{gap.detail}</p>
                  </div>
                  {gap.record_id ? (
                    <button
                      type="button"
                      className="btn-quiet shrink-0 px-2.5 py-1 text-xs"
                      onClick={() => {
                        setTab('records')
                        setFilter('all')
                        setSearch('')
                        setOpenId(gap.record_id)
                      }}
                    >
                      Fix record
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          )
        ) : null}
      </div>

      {busy ? (
        <p className="flex items-center gap-2 text-sm text-ink-500">
          <Spinner /> Applying change…
        </p>
      ) : null}
    </div>
  )
}

function RecordEditor({ record, fields, categories, busy, onSave, onClose }) {
  const [draft, setDraft] = useState(() => ({ ...record.fields }))
  const [category, setCategory] = useState(record.category)

  return (
    <div className="mx-5 mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {fields.map((field) => (
          <div key={field.key}>
            <label className="label" htmlFor={`${record.id}-${field.key}`}>
              {field.label}
              {field.required ? <span className="text-rose-500"> *</span> : null}
            </label>
            <input
              id={`${record.id}-${field.key}`}
              className="input py-1.5 text-xs"
              value={draft[field.key] ?? ''}
              onChange={(event) => setDraft((prev) => ({ ...prev, [field.key]: event.target.value }))}
            />
          </div>
        ))}
        <div>
          <label className="label" htmlFor={`${record.id}-category`}>
            Category
          </label>
          <select
            id={`${record.id}-category`}
            className="input py-1.5 text-xs"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            {categories.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
            <option value="unclassified">Unclassified</option>
          </select>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] text-ink-500">
          {record.source.file}
          {record.source.locator ? ` · ${record.source.locator}` : ''}
        </p>
        <div className="flex gap-2">
          <button type="button" className="btn-quiet px-3 py-1.5 text-xs" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary px-3 py-1.5 text-xs"
            disabled={busy}
            onClick={() => {
              const payload = { fields: draft }
              if (category !== record.category) payload.category = category
              onSave(payload)
              onClose()
            }}
          >
            Save & approve
          </button>
        </div>
      </div>
    </div>
  )
}
