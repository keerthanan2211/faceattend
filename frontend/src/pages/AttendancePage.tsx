import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { fmtDayTime, fmtHours, hoursOnSite, isoDate } from '../lib/time';

export default function AttendancePage() {
  const today = isoDate(new Date());
  const [start, setStart] = useState(today);
  const [end, setEnd] = useState(today);
  const summary = useQuery({ queryKey: ['summary'], queryFn: api.summary, refetchInterval: 30_000 });
  const records = useQuery({ queryKey: ['attendance', start, end], queryFn: () => api.attendance(start, end) });
  const hours = useMemo(() => hoursOnSite(records.data ?? []), [records.data]);

  const download = useMutation({
    mutationFn: () => api.exportCsv(start, end),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = Object.assign(document.createElement('a'), { href: url, download: `attendance_${start}_${end}.csv` });
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const s = summary.data;
  const people = [...new Map((records.data ?? []).map((r) => [r.technician_id, r])).values()];

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-extrabold">Attendance</h1>

      {s && (
        <dl className="grid gap-px overflow-hidden rounded-xl border border-concrete-line bg-concrete-line sm:grid-cols-3">
          <div className="bg-white p-5"><dt className="text-sm text-muted">Present today</dt><dd className="text-3xl font-extrabold">{s.present_today} <span className="text-base font-normal text-muted">of {s.active_technicians}</span></dd></div>
          <div className="bg-white p-5"><dt className="text-sm text-muted">On site now</dt><dd className="text-3xl font-extrabold">{s.on_site_now.length}</dd>{s.on_site_now.length > 0 && <dd className="mt-1 text-xs text-muted">{s.on_site_now.join(', ')}</dd>}</div>
          <div className="bg-white p-5"><dt className="text-sm text-muted">Unrecognised scans today</dt><dd className={`text-3xl font-extrabold ${s.unrecognised_today ? 'text-stop' : ''}`}>{s.unrecognised_today}</dd></div>
        </dl>
      )}

      <div className="flex flex-wrap items-end gap-4">
        <div><label htmlFor="from" className="label">From</label><input id="from" type="date" className="input" value={start} max={end} onChange={(e) => setStart(e.target.value)} /></div>
        <div><label htmlFor="to" className="label">To</label><input id="to" type="date" className="input" value={end} min={start} max={today} onChange={(e) => setEnd(e.target.value)} /></div>
        <button type="button" className="btn-secondary" onClick={() => download.mutate()} disabled={download.isPending}>Export CSV</button>
        {download.error && <p role="alert" className="text-sm text-stop">{download.error.message}</p>}
      </div>

      {records.isLoading && <p role="status" className="text-muted">Loading records…</p>}
      {records.error && <p role="alert" className="text-stop">{records.error.message}</p>}

      {records.data && (
        <div className="grid gap-8 lg:grid-cols-[1fr_300px]">
          <div className="overflow-x-auto rounded-xl border border-concrete-line bg-white">
            <table className="w-full min-w-[560px] text-left text-sm">
              <caption className="sr-only">Check-ins and check-outs, newest first</caption>
              <thead className="border-b border-concrete-line text-muted">
                <tr>{['Time', 'Technician', 'Type', 'Site', 'Match'].map((h) => <th key={h} scope="col" className="px-4 py-2 font-semibold">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-concrete-line">
                {records.data.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-muted">No check-ins in this period.</td></tr>}
                {records.data.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-3 tabular-nums">{fmtDayTime(r.created_at)}</td>
                    <td className="px-4 py-3"><span className="font-semibold">{r.technician_name}</span> <span className="text-muted">{r.employee_code}</span></td>
                    <td className="px-4 py-3">{r.kind === 'in' ? 'Check-in' : 'Check-out'}</td>
                    <td className="px-4 py-3">{r.site}</td>
                    <td className="px-4 py-3 tabular-nums text-muted">{Math.round(r.score * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <section aria-labelledby="hours" className="h-fit rounded-xl border border-concrete-line bg-white p-5">
            <h2 id="hours" className="font-extrabold">Hours on site</h2>
            {people.length === 0 ? <p className="mt-2 text-sm text-muted">No completed shifts.</p> : (
              <ul className="mt-3 space-y-2 text-sm">
                {people.map((p) => (
                  <li key={p.technician_id} className="flex justify-between">
                    <span>{p.technician_name}</span>
                    <span className="tabular-nums">{hours.has(p.technician_id) ? fmtHours(hours.get(p.technician_id)!) : 'On site'}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
