"""
Downloads the two open-source face models used by FaceAttend into ./models (about 37 MB in total).

  YuNet  - face detection + 5 landmarks      (OpenCV Zoo, MIT licence)
  SFace  - face recognition, 128-d embedding (OpenCV Zoo, Apache 2.0 licence)

Usage:  python scripts/download_models.py [target_dir]
"""

import sys
import urllib.request
from pathlib import Path

BASE = "https://github.com/opencv/opencv_zoo/raw/main/models"
MODELS = {
    "face_detection_yunet_2023mar.onnx": f"{BASE}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx": f"{BASE}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "models")
    target.mkdir(parents=True, exist_ok=True)
    for name, url in MODELS.items():
        path = target / name
        if path.exists() and path.stat().st_size > 100_000:
            print(f"✓ {name} already present")
            continue
        print(f"↓ {name}")
        urllib.request.urlretrieve(url, path)
        if path.stat().st_size < 100_000:  # an error page or Git LFS pointer, not the model
            path.unlink()
            sys.exit(f"Download of {name} failed. Try again, or download it manually from {url}")
        print(f"✓ {name} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
