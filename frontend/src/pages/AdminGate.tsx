import { useState, type ReactNode } from 'react';
import { clearAdminKey, getAdminKey, setAdminKey } from '../lib/admin-key';

/** Admin pages need the server's admin key. It's checked by the API on every request. */
export default function AdminGate({ children }: { children: ReactNode }) {
  const [hasKey, setHasKey] = useState(Boolean(getAdminKey()));
  const [value, setValue] = useState('');

  if (hasKey) {
    return (
      <>
        {children}
        <button type="button" className="mt-10 text-sm text-muted underline" onClick={() => { clearAdminKey(); setHasKey(false); }}>
          Lock admin pages
        </button>
      </>
    );
  }

  return (
    <form className="mx-auto max-w-sm py-12" onSubmit={(e) => { e.preventDefault(); if (value.trim()) { setAdminKey(value.trim()); setHasKey(true); } }}>
      <h1 className="text-2xl font-extrabold">Admin access</h1>
      <p className="mt-1 text-sm text-muted">Enter the admin key from the server’s <code>ADMIN_API_KEY</code> setting.</p>
      <label htmlFor="admin-key" className="label mt-6">Admin key</label>
      <input id="admin-key" type="password" autoComplete="off" className="input" value={value} onChange={(e) => setValue(e.target.value)} />
      <button type="submit" className="btn-primary mt-4 w-full">Unlock</button>
    </form>
  );
}
