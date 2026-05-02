import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { createUser, deleteUser, fetchActivity, fetchUsers, updateUser } from '../api/admin'
import type { AdminUser } from '../types'

function roleBadge(role: string): string {
  if (role === 'superadmin') return 'bg-red-500/15 text-red-300'
  if (role === 'admin') return 'bg-amber-500/15 text-amber-300'
  return 'bg-stone-700 text-stone-300'
}

export default function AdminPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    email: '',
    full_name: '',
    password: '',
    role: 'user' as 'user' | 'admin' | 'superadmin',
    monthly_token_limit: '',
  })

  const { data: users } = useQuery({ queryKey: ['admin-users'], queryFn: fetchUsers })
  const { data: activity } = useQuery({ queryKey: ['admin-activity'], queryFn: () => fetchActivity(120) })

  const refreshAdminData = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
      queryClient.invalidateQueries({ queryKey: ['admin-activity'] }),
    ])
  }

  const createUserMutation = useMutation({
    mutationFn: createUser,
    onSuccess: async () => {
      setForm({ email: '', full_name: '', password: '', role: 'user', monthly_token_limit: '' })
      await refreshAdminData()
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ user, is_active }: { user: AdminUser; is_active: boolean }) =>
      updateUser(user.id, { is_active }),
    onSuccess: refreshAdminData,
  })

  const deleteUserMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: refreshAdminData,
  })

  return (
    <div className="space-y-6">
      <section className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <div className="rounded-2xl border border-stone-800 bg-stone-950 p-5">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-stone-100">Users</h2>
            <p className="text-sm text-stone-500">Create, disable, and remove accounts. Token quotas are per rolling 30-day window.</p>
          </div>

          <div className="space-y-3">
            {users?.map((user) => (
              <div key={user.id} className="rounded-xl border border-stone-800 bg-stone-900/60 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-stone-100">{user.full_name}</p>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${roleBadge(user.role)}`}>
                        {user.role}
                      </span>
                      {!user.is_active && (
                        <span className="rounded-full bg-stone-700 px-2 py-0.5 text-[11px] text-stone-300">inactive</span>
                      )}
                    </div>
                    <p className="text-sm text-stone-400">{user.email}</p>
                    <p className="mt-2 text-xs text-stone-500">
                      Token use: {user.quota.used_tokens.toLocaleString()}
                      {user.quota.monthly_token_limit ? ` / ${user.quota.monthly_token_limit.toLocaleString()}` : ' / unlimited'}
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => toggleActiveMutation.mutate({ user, is_active: !user.is_active })}
                      className="rounded-lg border border-stone-700 px-3 py-2 text-xs text-stone-200 transition hover:border-stone-500"
                    >
                      {user.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => deleteUserMutation.mutate(user.id)}
                      className="rounded-lg border border-red-900/70 px-3 py-2 text-xs text-red-300 transition hover:border-red-700"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-stone-800 bg-stone-950 p-5">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-stone-100">Create User</h2>
            <p className="text-sm text-stone-500">Superadmins can create operator and reader accounts.</p>
          </div>

          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault()
              createUserMutation.mutate({
                ...form,
                monthly_token_limit: form.monthly_token_limit ? Number(form.monthly_token_limit) : null,
              })
            }}
          >
            <input
              value={form.full_name}
              onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))}
              placeholder="Full name"
              className="w-full rounded-xl border border-stone-700 bg-stone-900 px-4 py-3 text-sm outline-none focus:border-orange-400"
              required
            />
            <input
              type="email"
              value={form.email}
              onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              placeholder="Email"
              className="w-full rounded-xl border border-stone-700 bg-stone-900 px-4 py-3 text-sm outline-none focus:border-orange-400"
              required
            />
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              placeholder="Temporary password"
              className="w-full rounded-xl border border-stone-700 bg-stone-900 px-4 py-3 text-sm outline-none focus:border-orange-400"
              required
            />
            <select
              value={form.role}
              onChange={(event) => setForm((current) => ({ ...current, role: event.target.value as 'user' | 'admin' | 'superadmin' }))}
              className="w-full rounded-xl border border-stone-700 bg-stone-900 px-4 py-3 text-sm outline-none focus:border-orange-400"
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
              <option value="superadmin">Superadmin</option>
            </select>
            <input
              type="number"
              min={1}
              value={form.monthly_token_limit}
              onChange={(event) => setForm((current) => ({ ...current, monthly_token_limit: event.target.value }))}
              placeholder="Monthly token limit (optional)"
              className="w-full rounded-xl border border-stone-700 bg-stone-900 px-4 py-3 text-sm outline-none focus:border-orange-400"
            />
            <button
              type="submit"
              disabled={createUserMutation.isPending}
              className="w-full rounded-xl bg-orange-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-orange-400 disabled:opacity-60"
            >
              Create user
            </button>
          </form>
        </div>
      </section>

      <section className="rounded-2xl border border-stone-800 bg-stone-950 p-5">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-stone-100">Activity</h2>
          <p className="text-sm text-stone-500">Recent authenticated actions across the application.</p>
        </div>
        <div className="space-y-2">
          {activity?.map((item) => (
            <div key={item.id} className="grid gap-1 rounded-xl border border-stone-800 bg-stone-900/50 px-4 py-3 md:grid-cols-[170px_1fr_140px] md:items-center">
              <div>
                <p className="text-xs font-medium text-stone-300">{item.user_email || 'Unknown user'}</p>
                <p className="text-[11px] text-stone-500">{new Date(item.created_at).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-stone-200">{item.action}</p>
                <p className="text-[11px] text-stone-500">{item.method} {item.path}</p>
              </div>
              <div className="text-[11px] text-stone-500 md:text-right">
                <p>Status {item.status_code}</p>
                {item.ip_address && <p>{item.ip_address}</p>}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
