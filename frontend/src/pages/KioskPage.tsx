import { useEffect, useState } from 'react';
import { api, type Challenge, type CheckInResult } from '../lib/api';
import { fmtClock } from '../lib/time';
import { CAMERA_HELP, useCamera } from '../components/useCamera';

const SITE_KEY = 'faceattend-site';
const RESET_AFTER_MS = 6000;
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

type Step =
  | { kind: 'idle' }
  | { kind: 'straight' }
  | { kind: 'turn'; direction: Challenge['direction'] }
  | { kind: 'checking' }
  | { kind: 'done'; result: CheckInResult }
  | { kind: 'error'; message: string };

/**
 * Shared tablet at a site entrance. A scan has two guided steps:
 *  1. look straight at the camera, then
 *  2. turn your head the way the server randomly asks (liveness check).
 */
export default function KioskPage() {
  const { videoRef, state, start, capture } = useCamera();
  const [site, setSite] = useState(() => localStorage.getItem(SITE_KEY) ?? '');
  const [step, setStep] = useState<Step>({ kind: 'idle' });
  const siteReady = site.trim().length >= 2;
  const busy = step.kind === 'straight' || step.kind === 'turn' || step.kind === 'checking';

  useEffect(() => {
    if (step.kind !== 'done' && step.kind !== 'error') return;
    const t = setTimeout(() => setStep({ kind: 'idle' }), RESET_AFTER_MS);
    return () => clearTimeout(t);
  }, [step]);

  const runScan = async () => {
    try {
      const challenge = await api.challenge();
      setStep({ kind: 'straight' });
      await wait(1200);
      const straight = await capture();

      setStep({ kind: 'turn', direction: challenge.direction });
      await wait(1800);
      const turned = await capture();
      if (!straight || !turned) throw new Error('The camera stopped. Turn it on and try again.');

      setStep({ kind: 'checking' });
      const result = await api.checkIn(straight, turned, challenge.token, site.trim());
      setStep({ kind: 'done', result });
    } catch (err) {
      setStep({ kind: 'error', message: err instanceof Error ? err.message : 'Something went wrong. Try again.' });
    }
  };

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_380px]">
      <section aria-labelledby="kiosk-heading">
        <h1 id="kiosk-heading" className="text-3xl font-extrabold">Check in or out</h1>
        <p className="mt-1 text-muted">Remove sunglasses or a helmet. You’ll look straight, then turn your head when asked.</p>

        <div className="relative mt-6 aspect-[4/3] overflow-hidden rounded-xl bg-asphalt">
          <video ref={videoRef} playsInline muted className="h-full w-full -scale-x-100 object-cover" aria-label="Camera preview" />
          {state === 'live' && (
            <div aria-hidden className="pointer-events-none absolute left-1/2 top-1/2 h-3/5 w-2/5 -translate-x-1/2 -translate-y-1/2 rounded-[50%] border-4 border-dashed border-caution/80" />
          )}
          {state === 'live' && (step.kind === 'straight' || step.kind === 'turn') && <Prompt step={step} />}
          {state !== 'live' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center text-white">
              {state === 'starting' ? <p>Starting camera…</p> : CAMERA_HELP[state] ? <p>{CAMERA_HELP[state]}</p> : null}
              {(state === 'idle' || state === 'denied') && <button type="button" className="btn-primary" onClick={start}>Turn on camera</button>}
            </div>
          )}
        </div>

        <button type="button" className="btn-primary mt-4 h-14 w-full text-lg" onClick={runScan} disabled={state !== 'live' || !siteReady || busy}>
          {step.kind === 'checking' ? 'Checking…' : busy ? 'Scanning…' : 'Start scan'}
        </button>
      </section>

      <aside className="space-y-6">
        <div>
          <label htmlFor="site" className="label">Work site</label>
          <input id="site" className="input" value={site} placeholder="e.g. NH-44 Toll Plaza, Km 212" disabled={busy}
            onChange={(e) => { setSite(e.target.value); localStorage.setItem(SITE_KEY, e.target.value); }} />
          {!siteReady && <p className="mt-1 text-xs text-muted">Set the site name once on this device.</p>}
        </div>

        <div aria-live="assertive" aria-atomic="true">
          {step.kind === 'done' && <ResultSign result={step.result} />}
          {step.kind === 'error' && (
            <div role="alert" className="rounded-xl border-4 border-stop bg-white p-5">
              <p className="text-lg font-extrabold text-stop">Not recorded</p>
              <p className="mt-1">{step.message}</p>
            </div>
          )}
          {(step.kind === 'straight' || step.kind === 'turn') && (
            <p className="sr-only">{step.kind === 'straight' ? 'Look straight at the camera.' : `Now turn your head to your ${step.direction}.`}</p>
          )}
          {step.kind === 'idle' && (
            <div className="rounded-xl border-2 border-dashed border-concrete-line p-6 text-center text-muted">Your result will appear here.</div>
          )}
        </div>
      </aside>
    </div>
  );
}

/** Big on-camera instruction. The preview is mirrored, so "your left" is shown on the left of the screen. */
function Prompt({ step }: { step: Extract<Step, { kind: 'straight' } | { kind: 'turn' }> }) {
  return (
    <div aria-hidden className="absolute inset-x-0 bottom-0 bg-asphalt/80 px-4 py-3 text-center text-xl font-extrabold text-white">
      {step.kind === 'straight' ? (
        'Look straight at the camera'
      ) : (
        <span className="inline-flex items-center gap-3">
          {step.direction === 'left' && <Arrow flip />}
          Turn your head to your {step.direction}
          {step.direction === 'right' && <Arrow />}
        </span>
      )}
    </div>
  );
}

function Arrow({ flip }: { flip?: boolean }) {
  return (
    <svg width="36" height="24" viewBox="0 0 36 24" className={flip ? '-scale-x-100' : ''}>
      <path d="M2 12h26M20 3l10 9-10 9" fill="none" stroke="#F2C200" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ResultSign({ result }: { result: CheckInResult }) {
  const first = result.technician.name.split(' ')[0];
  const heading = result.status === 'checked-in' ? `Welcome, ${first}` : result.status === 'checked-out' ? `Goodbye, ${first}` : `Already recorded, ${first}`;
  const line =
    result.status === 'checked-in' ? `Checked in at ${fmtClock(result.time)}` :
    result.status === 'checked-out' ? `Checked out at ${fmtClock(result.time)}` :
    `Your last scan at ${fmtClock(result.time)} was saved. No need to scan again.`;

  return (
    <div className="sign-panel" role="status">
      <div>
        <p className="text-2xl font-extrabold leading-tight">{heading}</p>
        <p className="mt-1 text-lg">{line}</p>
        <p className="mt-3 text-sm text-white/80">{result.technician.employee_code} · {result.technician.trade} · Liveness verified</p>
      </div>
    </div>
  );
}
