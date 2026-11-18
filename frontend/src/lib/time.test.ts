import { describe, expect, it } from 'vitest';
import { fmtHours, hoursOnSite, isoDate } from './time';

describe('hoursOnSite', () => {
  it('pairs check-ins with the following check-outs', () => {
    const totals = hoursOnSite([
      { technician_id: 1, kind: 'out', created_at: '2026-11-18T13:00:00Z' },
      { technician_id: 1, kind: 'in', created_at: '2026-11-18T09:00:00Z' },
      { technician_id: 2, kind: 'in', created_at: '2026-11-18T10:00:00Z' },
    ]);
    expect(totals.get(1)).toBe(4);
    expect(totals.has(2)).toBe(false); // still on site, no check-out yet
  });

  it('adds up several shifts in one day', () => {
    const totals = hoursOnSite([
      { technician_id: 1, kind: 'in', created_at: '2026-11-18T08:00:00Z' },
      { technician_id: 1, kind: 'out', created_at: '2026-11-18T12:00:00Z' },
      { technician_id: 1, kind: 'in', created_at: '2026-11-18T13:00:00Z' },
      { technician_id: 1, kind: 'out', created_at: '2026-11-18T14:30:00Z' },
    ]);
    expect(totals.get(1)).toBe(5.5);
  });
});

describe('formatting', () => {
  it('formats hours and dates', () => {
    expect(fmtHours(5.5)).toBe('5h 30m');
    expect(isoDate(new Date(2026, 0, 7))).toBe('2026-01-07');
  });
});
