import { Link } from 'react-router'
import { PageTitle, TEXT_LINK } from './page-surfaces'

export function NotFoundPage() {
  return (
    <>
      <PageTitle title="Page not found" sub="That page doesn't exist in Second Serve." />
      <Link to="/dashboard" className={TEXT_LINK}>
        Back to dashboard
      </Link>
    </>
  )
}
