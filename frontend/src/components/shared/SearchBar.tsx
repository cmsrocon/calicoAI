import { Search } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

interface Props {
  placeholder?: string
  value: string
  onChange: (value: string) => void
  debounceMs?: number
}

export default function SearchBar({ placeholder = 'Search…', value, onChange, debounceMs = 300 }: Props) {
  const [local, setLocal] = useState(value)

  useEffect(() => { setLocal(value) }, [value])

  const debounced = useCallback(
    (() => {
      let timer: ReturnType<typeof setTimeout>
      return (val: string) => {
        clearTimeout(timer)
        timer = setTimeout(() => onChange(val), debounceMs)
      }
    })(),
    [onChange, debounceMs]
  )

  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
      <input
        type="text"
        value={local}
        onChange={(e) => { setLocal(e.target.value); debounced(e.target.value) }}
        placeholder={placeholder}
        className="w-full bg-stone-900 border border-stone-700 rounded-lg pl-9 pr-4 py-2 text-sm text-stone-100 placeholder-stone-500 focus:outline-none focus:border-orange-500 transition-colors"
      />
    </div>
  )
}
