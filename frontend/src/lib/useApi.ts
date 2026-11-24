import { useEffect, useState } from 'react'
import { ApiError } from './api'
import { GENERIC_ERROR } from './form'

/** Loads on mount. `load` must be a stable function, not one created during render. */
export function useApi<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T>()
  const [error, setError] = useState<string>()
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let live = true
    load()
      .then((d) => live && setData(d))
      .catch((err) => live && setError(err instanceof ApiError ? err.message : GENERIC_ERROR))
    return () => {
      live = false
    }
  }, [load, attempt])

  function retry() {
    setError(undefined)
    setAttempt((n) => n + 1)
  }

  return { data, error, retry }
}
