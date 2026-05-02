import { Loader2, LockKeyhole } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../components/auth/AuthProvider'

export default function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)
    try {
      await login(email, password)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || 'Login failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100 grid place-items-center px-4">
      <div className="w-full max-w-md rounded-3xl border border-stone-800 bg-stone-900/80 p-8 shadow-2xl shadow-black/40">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-500/15 text-orange-400">
            <LockKeyhole className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-orange-300">calicoAI</h1>
            <p className="text-sm text-stone-400">Secure production sign-in</p>
          </div>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block space-y-2">
            <span className="text-sm text-stone-300">Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-xl border border-stone-700 bg-stone-950 px-4 py-3 outline-none transition focus:border-orange-400"
              autoComplete="email"
              required
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm text-stone-300">Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-xl border border-stone-700 bg-stone-950 px-4 py-3 outline-none transition focus:border-orange-400"
              autoComplete="current-password"
              required
            />
          </label>

          {error && (
            <div className="rounded-xl border border-red-900/60 bg-red-950/30 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-orange-500 px-4 py-3 font-medium text-white transition hover:bg-orange-400 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Sign in
          </button>
        </form>
      </div>
    </div>
  )
}
