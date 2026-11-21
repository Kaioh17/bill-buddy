export type Errors = Record<string, string>

/** Moves focus to the first field with an error so keyboard and screen reader users land on it. */
export function focusFirstError(form: HTMLFormElement, errors: Errors) {
  const first = form.elements.namedItem(Object.keys(errors)[0])
  if (first instanceof HTMLElement) first.focus()
}

export const GENERIC_ERROR = 'Something went wrong. Try again.'
