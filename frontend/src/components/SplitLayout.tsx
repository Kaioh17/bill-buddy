import type { ReactNode } from 'react'
import { Card } from './ui'

/** Editorial split: big headline on the left, one card on the right. Stacks on mobile. */
export default function SplitLayout({
  title,
  lede,
  actions,
  children,
}: {
  title: ReactNode
  lede: string
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="mx-auto grid w-full max-w-6xl flex-1 content-center gap-12 px-4 pt-28 pb-16 lg:grid-cols-2 lg:gap-20 lg:py-32">
      <div className="animate-rise">
        <h1 className="text-4xl leading-[1.04] font-semibold tracking-tight text-balance sm:text-6xl">{title}</h1>
        <p className="mt-6 max-w-md text-lg text-gray-500">{lede}</p>
        {actions && <div className="mt-8 flex flex-wrap gap-3">{actions}</div>}
      </div>
      <Card className="w-full max-w-md animate-rise justify-self-center [animation-delay:150ms] lg:justify-self-end">{children}</Card>
    </div>
  )
}
