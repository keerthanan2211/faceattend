/** Local calendar date as YYYY-MM-DD (for date inputs and API filters). */
export function isoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const clock = new Intl.DateTimeFormat('en-IN', { hour: 'numeric', minute: '2-digit' });
const dayTime = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });

export const fmtClock = (iso: string) => clock.format(new Date(iso));
export const fmtDayTime = (iso: string) => dayTime.format(new Date(iso));

/** Pairs each check-in with the next check-out to compute hours on site per person per day. */
export function hoursOnSite(records: { technician_id: number; kind: 'in' | 'out'; created_at: string }[]): Map<number, number> {
  const sorted = [...records].sort((a, b) => a.created_at.localeCompare(b.created_at));
  const openSince = new Map<number, number>();
  const totals = new Map<number, number>();
  for (const r of sorted) {
    const t = new Date(r.created_at).getTime();
    if (r.kind === 'in') openSince.set(r.technician_id, t);
    else if (openSince.has(r.technician_id)) {
      const hours = (t - openSince.get(r.technician_id)!) / 3_600_000;
      totals.set(r.technician_id, (totals.get(r.technician_id) ?? 0) + hours);
      openSince.delete(r.technician_id);
    }
  }
  return totals;
}

export const fmtHours = (h: number) => `${Math.floor(h)}h ${String(Math.round((h % 1) * 60)).padStart(2, '0')}m`;
