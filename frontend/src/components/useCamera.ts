import { useCallback, useEffect, useRef, useState } from 'react';

type CameraState = 'idle' | 'starting' | 'live' | 'denied' | 'unavailable';

/** Front camera stream for a <video> element, plus capturing a JPEG frame from it. */
export function useCamera() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<CameraState>('idle');

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) return setState('unavailable');
    setState('starting');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 960 } }, audio: false });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setState('live');
    } catch (err) {
      setState(err instanceof DOMException && err.name === 'NotAllowedError' ? 'denied' : 'unavailable');
    }
  }, []);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setState('idle');
  }, []);

  useEffect(() => stop, [stop]); // release the camera when the component unmounts

  const capture = useCallback(async (): Promise<Blob | null> => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return null;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d')!;
    ctx.translate(canvas.width, 0); // un-mirror: the preview is mirrored for a natural selfie view
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0);
    return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.9));
  }, []);

  return { videoRef, state, start, stop, capture };
}

export const CAMERA_HELP: Record<string, string> = {
  denied: 'Camera access was blocked. Allow the camera in your browser’s site settings, or upload a photo instead.',
  unavailable: 'No camera is available on this device. Upload a photo instead.',
};
