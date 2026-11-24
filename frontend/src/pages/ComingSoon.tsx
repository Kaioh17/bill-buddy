import PageHeader from '../components/PageHeader'
import { ButtonLink, Card } from '../components/ui'

/** Stands in for screens that are not built yet, so no link is dead. */
export default function ComingSoon({ title }: { title: string }) {
  return (
    <div className="page">
      <title>{`${title} - Bill Buddy`}</title>
      <PageHeader title={title} lede="This screen is not built yet." />
      <Card className="mt-7">
        <p className="text-gray-500">It is on the way. Everything you can use today is on the dashboard.</p>
        <ButtonLink to="/dashboard" className="mt-6">
          Back to dashboard
        </ButtonLink>
      </Card>
    </div>
  )
}
