import SplitLayout from '../components/SplitLayout'
import { ButtonLink } from '../components/ui'

export default function NotFound() {
  return (
    <SplitLayout title="That page does not exist." lede="The link may be broken, or the page may have moved.">
      <title>Page not found - Bill Buddy</title>
      <h2 className="text-2xl font-bold tracking-tight">Head back</h2>
      <p className="mt-1 text-gray-500">Your account and data are untouched.</p>
      <ButtonLink to="/" arrow className="mt-6 w-full">
        Go to the app
      </ButtonLink>
    </SplitLayout>
  )
}
