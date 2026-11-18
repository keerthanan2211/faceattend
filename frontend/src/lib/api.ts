import { getAdminKey } from './admin-key';

const BASE = `${import.meta.env.VITE_API_URL ?? ''}/api`;

export interface Technician {
  id: number;
  employee_code: string;
  name: string;
  trade: string;
  phone: string;
  active: boolean;
  face_count: number;
  created_at: string;
}

export interface Challenge {
  token: string;
  direction: 'left' | 'right';
  expires_at: string;
}

export interface CheckInResult {
  status: 'checked-in' | 'checked-out' | 'already-recorded';
  technician: Technician;
  time: string;
  score: number;
}

export interface AttendanceRecord {
  id: number;
  kind: 'in' | 'out';
  site: string;
  score: number;
  created_at: string;
  technician_id: number;
  technician_name: string;
  employee_code: string;
}

export interface Summary {
  present_today: number;
  on_site_now: string[];
  unrecognised_today: number;
  active_technicians: number;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}, admin = false): Promise<T> {
  const headers = new Headers(init.headers);
  if (admin) headers.set('X-Admin-Key', getAdminKey() ?? '');
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, 'Can’t reach the server. Check the connection.');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    throw new ApiError(res.status, Array.isArray(detail) ? (detail[0]?.msg ?? 'Invalid request') : (detail ?? `Request failed (${res.status})`));
  }
  if (res.status === 204) return undefined as T;
  return (res.headers.get('content-type')?.includes('text/csv') ? res.blob() : res.json()) as Promise<T>;
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } });

export const api = {
  challenge: () => request<Challenge>('/attendance/challenge'),
  checkIn: (straight: Blob, turned: Blob, token: string, site: string) => {
    const form = new FormData();
    form.append('straight', straight, 'straight.jpg');
    form.append('turned', turned, 'turned.jpg');
    form.append('token', token);
    form.append('site', site);
    return request<CheckInResult>('/attendance/check-in', { method: 'POST', body: form });
  },
  technicians: () => request<Technician[]>('/technicians', {}, true),
  createTechnician: (data: Pick<Technician, 'employee_code' | 'name' | 'trade' | 'phone'>) =>
    request<Technician>('/technicians', { method: 'POST', ...json(data) }, true),
  updateTechnician: (id: number, data: Partial<Pick<Technician, 'name' | 'trade' | 'phone' | 'active'>>) =>
    request<Technician>(`/technicians/${id}`, { method: 'PATCH', ...json(data) }, true),
  deleteTechnician: (id: number) => request<void>(`/technicians/${id}`, { method: 'DELETE' }, true),
  enroll: (id: number, photos: Blob[]) => {
    const form = new FormData();
    photos.forEach((p, i) => form.append('files', p, `face-${i + 1}.jpg`));
    return request<Technician>(`/technicians/${id}/faces`, { method: 'POST', body: form }, true);
  },
  resetFaces: (id: number) => request<Technician>(`/technicians/${id}/faces`, { method: 'DELETE' }, true),
  attendance: (start: string, end: string) => request<AttendanceRecord[]>(`/attendance?start=${start}&end=${end}`, {}, true),
  summary: () => request<Summary>('/attendance/summary', {}, true),
  exportCsv: (start: string, end: string) => request<Blob>(`/attendance/export.csv?start=${start}&end=${end}`, {}, true),
};
