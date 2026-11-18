import { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type Technician } from '../lib/api';
import { CAMERA_HELP, useCamera } from '../components/useCamera';

const TIPS = ['Look straight at the camera', 'Turn your head slightly left', 'Turn your head slightly right'];

/** Capture up to 3 face photos (or upload them) and enrol them for one technician. */
export default function EnrollPanel({ tech, onDone }: { tech: Technician; onDone: () => void }) {
  const qc = useQueryClient();
  const { videoRef, state, start, capture } = useCamera();
  const [shots, setShots] = useState<Blob[]>([]);
  const previews = useObjectUrls(shots);
  const slots = Math.min(3, 5 - tech.face_count);

  const enroll = useMutation({
    mutationFn: () => api.enroll(tech.id, shots),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['technicians'] }); onDone(); },
  });

  const add = (b: Blob | null) => b && setShots((s) => (s.length < slots ? [...s, b] : s));

  return (
    <section aria-label={`Enrol ${tech.name}`} className="rounded-xl border border-concrete-line bg-white p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-extrabold">Enrol {tech.name}</h2>
          <p className="text-sm text-muted">{tech.face_count} photo(s) enrolled. Add up to {slots} more. Only face measurements are saved, never the photos.</p>
        </div>
        <button type="button" className="text-sm text-muted underline" onClick={onDone}>Close</button>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-[1fr_220px]">
        <div className="relative aspect-[4/3] overflow-hidden rounded-lg bg-asphalt">
          <video ref={videoRef} playsInline muted className="h-full w-full -scale-x-100 object-cover" aria-label="Camera preview" />
          {state !== 'live' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-4 text-center text-white">
              {CAMERA_HELP[state] && <p className="text-sm">{CAMERA_HELP[state]}</p>}
              {(state === 'idle' || state === 'denied') && <button type="button" className="btn-primary" onClick={start}>Turn on camera</button>}
            </div>
          )}
        </div>
        <div>
          <p className="text-sm font-semibold">{shots.length < slots ? `Photo ${shots.length + 1}: ${TIPS[shots.length] ?? TIPS[0]}` : 'Ready to enrol'}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" disabled={state !== 'live' || shots.length >= slots} onClick={async () => add(await capture())}>Capture</button>
            <label className="btn-secondary cursor-pointer">
              Upload
              <input type="file" accept="image/jpeg,image/png,image/webp" multiple className="sr-only"
                onChange={(e) => { Array.from(e.target.files ?? []).forEach(add); e.target.value = ''; }} />
            </label>
          </div>
          <ul className="mt-3 grid grid-cols-3 gap-2" aria-label="Photos to enrol">
            {previews.map((url, i) => (
              <li key={url} className="relative">
                <img src={url} alt={`Photo ${i + 1}`} className="aspect-square w-full rounded object-cover" />
                <button type="button" aria-label={`Remove photo ${i + 1}`} onClick={() => setShots((s) => s.filter((_, j) => j !== i))}
                  className="absolute right-0.5 top-0.5 rounded bg-white/90 px-1 text-xs font-bold">×</button>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {enroll.error && <p role="alert" className="mt-3 text-sm text-stop">{enroll.error.message}</p>}
      <button type="button" className="btn-primary mt-4" disabled={shots.length === 0 || enroll.isPending} onClick={() => enroll.mutate()}>
        {enroll.isPending ? 'Enrolling…' : `Enrol ${shots.length} photo${shots.length === 1 ? '' : 's'}`}
      </button>
    </section>
  );
}

function useObjectUrls(blobs: Blob[]) {
  const [urls, setUrls] = useState<string[]>([]);
  useEffect(() => {
    const next = blobs.map((b) => URL.createObjectURL(b));
    setUrls(next);
    return () => next.forEach(URL.revokeObjectURL);
  }, [blobs]);
  return urls;
}
