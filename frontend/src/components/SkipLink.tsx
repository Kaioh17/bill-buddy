/** First tab stop on every page. The layout's main landmark must have id="main". */
export default function SkipLink() {
  return (
    <a
      href="#main"
      className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-5 focus:py-3 focus:text-sm focus:font-semibold focus:shadow-float"
    >
      Skip to content
    </a>
  )
}
