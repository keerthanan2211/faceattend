import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type Technician } from '../lib/api';
import EnrollPanel from './EnrollPanel';

const EMPTY = { employee_code: '', name: '', trade: '', phone: '' };

export default function TechniciansPage() {
  const qc = useQueryClient();
  const { data: techs, isLoading, error } = useQuery({ queryKey: ['technicians'], queryFn: api.technicians });
  const [form, setForm] = useState(EMPTY);
  const [enrolling, setEnrolling] = useState<Technician | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: ['technicians'] });

  const create = useMutation({
    mutationFn: () => api.createTechnician({ ...form, employee_code: form.employee_code.trim(), name: form.name.trim(), trade: form.trade.trim() }),
    onSuccess: (t) => { setForm(EMPTY); refresh(); setEnrolling(t); },
  });
  const toggle = useMutation({ mutationFn: (t: Technician) => api.updateTechnician(t.id, { active: !t.active }), onSuccess: refresh });
  const remove = useMutation({ mutationFn: api.deleteTechnician, onSuccess: refresh });
  const reset = useMutation({ mutationFn: api.resetFaces, onSuccess: refresh });

  const field = (name: keyof typeof EMPTY, label: string, props: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <div>
      <label htmlFor={`t-${name}`} className="label">{label}</label>
      <input id={`t-${name}`} className="input" required value={form[name]} onChange={(e) => setForm((f) => ({ ...f, [name]: e.target.value }))} {...props} />
    </div>
  );

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-extrabold">Technicians</h1>

      <form className="grid gap-4 rounded-xl border border-concrete-line bg-white p-5 sm:grid-cols-2 lg:grid-cols-5" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
        {field('employee_code', 'Employee code', { placeholder: 'NH-101', pattern: '[A-Za-z0-9-]{2,20}' })}
        {field('name', 'Full name', { minLength: 2 })}
        {field('trade', 'Trade', { placeholder: 'Electrician', minLength: 2 })}
        {field('phone', 'Mobile', { inputMode: 'numeric', pattern: '[6-9][0-9]{9}', title: '10-digit Indian mobile number' })}
        <div className="flex items-end"><button type="submit" className="btn-primary w-full" disabled={create.isPending}>Add technician</button></div>
        {create.error && <p role="alert" className="text-sm text-stop sm:col-span-2 lg:col-span-5">{create.error.message}</p>}
      </form>

      {enrolling && <EnrollPanel key={enrolling.id} tech={enrolling} onDone={() => setEnrolling(null)} />}

      {isLoading && <p role="status" className="text-muted">Loading technicians…</p>}
      {error && <p role="alert" className="text-stop">{error.message}</p>}
      {techs && (
        <div className="overflow-x-auto rounded-xl border border-concrete-line bg-white">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-concrete-line text-muted">
              <tr>{['Code', 'Name', 'Trade', 'Face photos', 'Status', ''].map((h) => <th key={h} scope="col" className="px-4 py-2 font-semibold">{h || <span className="sr-only">Actions</span>}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-concrete-line">
              {techs.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-muted">No technicians yet. Add one above.</td></tr>}
              {techs.map((t) => (
                <tr key={t.id} className={t.active ? '' : 'opacity-60'}>
                  <td className="px-4 py-3 font-semibold">{t.employee_code}</td>
                  <td className="px-4 py-3">{t.name}</td>
                  <td className="px-4 py-3">{t.trade}</td>
                  <td className="px-4 py-3">{t.face_count === 0 ? <span className="font-semibold text-stop">Not enrolled</span> : `${t.face_count} enrolled`}</td>
                  <td className="px-4 py-3">{t.active ? 'Active' : 'Inactive'}</td>
                  <td className="space-x-3 whitespace-nowrap px-4 py-3 text-right">
                    <button type="button" className="font-semibold text-sign underline" onClick={() => setEnrolling(t)}>Enrol faces<span className="sr-only"> for {t.name}</span></button>
                    {t.face_count > 0 && <button type="button" className="text-muted underline" onClick={() => window.confirm(`Remove all face photos for ${t.name}?`) && reset.mutate(t.id)}>Reset faces</button>}
                    <button type="button" className="text-muted underline" onClick={() => toggle.mutate(t)}>{t.active ? 'Deactivate' : 'Activate'}</button>
                    <button type="button" className="text-stop underline" onClick={() => window.confirm(`Delete ${t.name} and their attendance history?`) && remove.mutate(t.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
