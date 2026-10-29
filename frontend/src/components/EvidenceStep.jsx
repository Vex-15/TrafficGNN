import { Alert, Chip, Dropzone, EmptyState, SectionHeader, Spinner, StatTile } from './ui'
import { formatBytes } from '../api'

const kindIcon = { document: '▤', image: '▣' }
const statusTone = { processed: 'emerald', 'no-data': 'amber', error: 'rose' }
const statusText = { processed: 'Extracted', 'no-data': 'No data found', error: 'Failed' }

export default function EvidenceStep({
  project,
  onUpload,
  onDeleteSource,
  onContinue,
  busy,
  error,
  uploadErrors = [],
}) {
  const sources = project?.sources ?? []
  const summary = project?.summary ?? {}
  const records = (project?.records ?? []).filter((record) => !record.duplicate_of)
  const canContinue = records.length > 0

  return (
    <div className="animate-rise space-y-5">
      <SectionHeader
        eyebrow="Step 2"
        title="Ingest the evidence"
        description="Documents are parsed, rows are normalised into one schema, and every extracted record keeps a pointer back to the file it came from."
        actions={
          <button type="button" className="btn-primary" onClick={onContinue} disabled={!canContinue}>
            Continue to validation
          </button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Sources" value={sources.length} hint={`${summary.images ?? 0} images`} />
        <StatTile label="Records" value={summary.records ?? 0} hint="normalised" tone="brand" />
        <StatTile
          label="Sections covered"
          value={`${summary.covered_sections ?? 0}/${summary.mapped_sections ?? 0}`}
          hint="mapped"
          tone="amber"
        />
        <StatTile label="Awaiting review" value={summary.pending_review ?? 0} hint="records" tone="amber" />
      </div>

      <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-4">
          <Dropzone
            accept=".docx,.xlsx,.xlsm,.csv,.pdf,.txt,.md,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
            multiple
            busy={busy}
            onFiles={onUpload}
            title="Drop evidence files"
            hint="DOCX · XLSX · CSV · PDF · TXT · PNG/JPG — multiple files supported"
          />
          <Alert tone="rose">{error}</Alert>
          {uploadErrors.length > 0 ? (
            <div className="rounded-xl bg-amber-50 px-3.5 py-2.5 text-sm text-amber-800 ring-1 ring-amber-200/70">
              <p className="font-semibold">Some files were skipped</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5">
                {uploadErrors.map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="card overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3.5">
              <h3 className="font-display text-sm font-semibold text-ink-900">Evidence library</h3>
              <span className="text-xs text-ink-500">{sources.length} files</span>
            </div>
            {sources.length === 0 ? (
              <div className="p-5">
                <EmptyState
                  icon="▤"
                  title="No evidence yet"
                  description="Add a few files — the demo dataset shows the expected mix of formats."
                />
              </div>
            ) : (
              <ul className="max-h-[26rem] divide-y divide-slate-100 overflow-y-auto">
                {sources.map((source) => (
                  <li key={source.id} className="flex items-center gap-3 px-5 py-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-sm text-ink-700">
                      {kindIcon[source.kind] ?? '▤'}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-ink-900" title={source.filename}>
                        {source.filename}
                      </p>
                      <p className="text-[11px] text-ink-500">
                        {formatBytes(source.size)} · {source.record_count} record
                        {source.record_count === 1 ? '' : 's'}
                        {source.detected_category ? ` · ${source.detected_category.replaceAll('_', ' ')}` : ''}
                      </p>
                    </div>
                    <Chip tone={statusTone[source.status] ?? 'slate'}>{statusText[source.status] ?? source.status}</Chip>
                    <button
                      type="button"
                      className="btn-quiet px-2 py-1 text-xs"
                      onClick={() => onDeleteSource(source.id)}
                      title="Remove source"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="card overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-3.5">
            <h3 className="font-display text-sm font-semibold text-ink-900">Extraction preview</h3>
            <p className="text-xs text-ink-500">First records normalised into the institutional schema</p>
          </div>
          {records.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon="◇"
                title="Nothing extracted yet"
                description="Records appear once a source file is parsed successfully."
              />
            </div>
          ) : (
            <ul className="max-h-[32rem] divide-y divide-slate-100 overflow-y-auto">
              {records.slice(0, 12).map((record) => (
                <li key={record.id} className="px-5 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink-900">{record.display?.primary}</p>
                      <p className="mt-0.5 line-clamp-2 text-xs text-ink-500">{record.display?.secondary || '—'}</p>
                    </div>
                    <Chip tone="brand">{record.category_label}</Chip>
                  </div>
                  <p className="mt-1.5 truncate text-[11px] text-ink-300">
                    {record.source.file} · {Math.round(record.confidence * 100)}% confidence
                  </p>
                </li>
              ))}
            </ul>
          )}
          {records.length > 12 ? (
            <p className="border-t border-slate-100 px-5 py-2.5 text-xs text-ink-500">
              + {records.length - 12} more records in the validation step
            </p>
          ) : null}
        </div>
      </div>

      {busy ? (
        <p className="flex items-center gap-2 text-sm text-ink-500">
          <Spinner /> Parsing files and re-running extraction…
        </p>
      ) : null}
    </div>
  )
}
