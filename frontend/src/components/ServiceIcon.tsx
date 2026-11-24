import {
  BarbellIcon,
  DeviceMobileIcon,
  LightningIcon,
  MusicNoteIcon,
  TelevisionIcon,
  WifiHighIcon,
  type Icon,
} from '@phosphor-icons/react'

const ICONS: [RegExp, Icon][] = [
  [/gym|fitness/i, BarbellIcon],
  [/phone|mobile/i, DeviceMobileIcon],
  [/spotify|music/i, MusicNoteIcon],
  [/internet|wi-?fi/i, WifiHighIcon],
  [/electric|power/i, LightningIcon],
  [/\btv\b/i, TelevisionIcon],
]

const TONES: [RegExp, string][] = [
  [/entertainment/i, 'bg-[#fbeff0] text-[#a64042]'],
  [/health|fitness/i, 'bg-[#f6f1e8] text-[#886b3f]'],
  [/utilit/i, 'bg-[#f2eff7] text-[#75648d]'],
]

/** Decorative tile for a subscription: an icon when the name gives one away, else its initial. */
export default function ServiceIcon({ name, category }: { name: string; category: string | null }) {
  const Glyph = ICONS.find(([pattern]) => pattern.test(name))?.[1]
  const tone = TONES.find(([pattern]) => pattern.test(category ?? ''))?.[1] ?? 'bg-gray-100 text-gray-600'
  return (
    <span aria-hidden className={`grid size-9 shrink-0 place-items-center rounded-lg font-bold ${tone}`}>
      {Glyph ? <Glyph size={20} /> : name.charAt(0).toUpperCase()}
    </span>
  )
}
