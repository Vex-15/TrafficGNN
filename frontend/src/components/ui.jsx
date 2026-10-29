import { toneClasses } from '../api'

export function Chip({ children, tone = 'slate', className = '' }) {
  return <span className={`chip ${toneClasses[tone] ?? toneClasses.slate} ${className}`}>{children}</span>
}

export function Meter({ value, tone = 'brand', className = '' }) {
  const palette = {
    brand: 'bg-brand-500',
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    rose: 'bg-rose-500',
    slate: 'bg-slate-400',
  }
  return (
    <div className={`h-1.5 w-full overflow-hidden rounded-full bg-slate-100 ${className}`}>
      <div
        className={`h-full rounded-full transition-all duration-500 ${palette[tone] ?? palette.brand}`}
        style={{ width: `${Math.max(2, Math.min(100, value))}%` }}
      />
    </div>
  )
}

export function ScoreRing({ value, label = 'Quality', size = 128 }) {
  const radius = (size - 14) / 2
  const circumference = 2 * Math.PI * radius
  const tone = value >= 88 ? '#10b981' : value >= 78 ? '#6366f1' : '#f59e0b'
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#eef1f7" strokeWidth="10" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={tone}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - (circumference * Math.min(100, value)) / 100}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-3xl font-semibold text-ink-900">{value}</span>
        <span className="text-[10px] font-semibold tracking-[0.12em] text-ink-500 uppercase">{label}</span>
      </div>
    </div>
  )
}

export function StatTile({ label, value, hint, tone = 'slate', icon }) {
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-semibold tracking-[0.1em] text-ink-500 uppercase">{label}</span>
        {icon ? <span className="text-lg leading-none opacity-80">{icon}</span> : null}
      </div>
      <div className="mt-2 flex items-end gap-2">
        <span className="font-display text-2xl font-semibold text-ink-900">{value}</span>
        {hint ? <Chip tone={tone}>{hint}</Chip> : null}
      </div>
    </div>
  )
}

export function SectionHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow ? (
          <p className="text-[11px] font-semibold tracking-[0.16em] text-brand-600 uppercase">{eyebrow}</p>
        ) : null}
        <h2 className="font-display mt-1 text-2xl font-semibold text-ink-900">{title}</h2>
        {description ? <p className="mt-1.5 max-w-2xl text-sm text-ink-500">{description}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  )
}

export function EmptyState({ title, description, action, icon = '◇' }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-12 text-center">
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-lg text-brand-600">
        {icon}
      </div>
      <h3 className="font-display text-base font-semibold text-ink-900">{title}</h3>
      {description ? <p className="mt-1 max-w-md text-sm text-ink-500">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  )
}

export function Spinner({ className = 'h-4 w-4' }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

export function Dropzone({ accept, multiple = false, onFiles, title, hint, busy = false }) {
  const handle = (fileList) => {
    const files = Array.from(fileList || []).filter(Boolean)
    if (!files.length) return
    onFiles(multiple ? files : files[0])
  }

  return (
    <label
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault()
        if (!busy) handle(event.dataTransfer.files)
      }}
      className={`group flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
        busy
          ? 'border-brand-300 bg-brand-50/60'
          : 'border-slate-300 bg-white hover:border-brand-400 hover:bg-brand-50/40'
      }`}
    >
      <input
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={busy}
        className="hidden"
        onChange={(event) => {
          handle(event.target.files)
          event.target.value = ''
        }}
      />
      <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
        {busy ? <Spinner className="h-5 w-5" /> : '↑'}
      </span>
      <span className="font-display text-sm font-semibold text-ink-900">{busy ? 'Processing…' : title}</span>
      <span className="text-xs text-ink-500">{hint}</span>
    </label>
  )
}

export function Alert({ tone = 'rose', children }) {
  if (!children) return null
  return (
    <div className={`rounded-xl px-3.5 py-2.5 text-sm ${toneClasses[tone] ?? toneClasses.rose}`}>{children}</div>
  )
}
