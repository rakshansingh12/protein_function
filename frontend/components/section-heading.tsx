import { Reveal } from '@/components/motion-primitives'

export function SectionHeading({
  eyebrow,
  title,
  description,
  id,
}: {
  eyebrow: string
  title: string
  description?: React.ReactNode
  id?: string
}) {
  return (
    <Reveal className="max-w-2xl">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">{eyebrow}</p>
      <h2 id={id} className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
        {title}
      </h2>
      {description ? <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">{description}</p> : null}
    </Reveal>
  )
}
