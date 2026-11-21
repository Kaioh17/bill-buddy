import SplitLayout from '../components/SplitLayout'
import { ButtonLink } from '../components/ui'

const points = [
  ['One list', 'Every subscription you pay for, in one place.'],
  ['No surprises', 'See what is due next before it is charged.'],
  ['Spot the forgotten', 'Catch payments you did not know were recurring.'],
]

export default function Landing() {
  return (
    <SplitLayout
      title="Never be surprised by a bill."
      lede="Bill Buddy tracks your subscriptions and upcoming payments in one calm view."
      actions={
        <>
          <ButtonLink to="/signup" arrow>
            Get started
          </ButtonLink>
          <ButtonLink to="/login" variant="soft">
            Log in
          </ButtonLink>
        </>
      }
    >
      <title>Bill Buddy - Track your subscriptions</title>
      <h2 className="text-2xl font-bold tracking-tight">What you get</h2>
      <ul className="mt-6 grid gap-3">
        {points.map(([name, text]) => (
          <li key={name} className="rounded-2xl bg-gray-50 px-4 py-3">
            <p className="font-semibold">{name}</p>
            <p className="mt-0.5 text-sm text-gray-500">{text}</p>
          </li>
        ))}
      </ul>
    </SplitLayout>
  )
}
