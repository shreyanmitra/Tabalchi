import os
import importlib
from pathlib import Path

import Tabalchi.main as tmain
from Tabalchi import BolParser, Bhatkande, Paluskar

def main() -> int:
    root = Path.cwd()
    tabla_file = root / "template.tabla"

    if not tabla_file.exists():
        raise FileNotFoundError(f"Missing template file: {tabla_file}")

    bol = BolParser.parse(str(tabla_file))
    print(f"Parsed beats: {len(bol.beats)}")

    missing = []
    decode_errors = []
    multiplier_errors = []
    requires_tempo_adjustment = 0

    backend_ok = tmain.hasPydubBackend()
    print(f"Pydub backend available (ffmpeg+ffprobe): {backend_ok}")

    AudioSegment = None
    if backend_ok:
        try:
            AudioSegment = importlib.import_module("pydub").AudioSegment
        except Exception as exc:
            print(f"Could not import pydub for decode checks: {exc}")
            backend_ok = False

    for beat in bol.beats:
        for idx, file_path in enumerate(beat.soundFiles):
            if not os.path.exists(file_path):
                missing.append(file_path)
                continue

            multiplier = beat.multipliers[idx]
            if abs(multiplier - 1.0) > 1e-9:
                requires_tempo_adjustment += 1

            if backend_ok and AudioSegment is not None:
                try:
                    AudioSegment.from_file(file_path)
                except Exception as exc:
                    decode_errors.append((file_path, str(exc)))

        for m in beat.multipliers:
            if m <= 0:
                multiplier_errors.append((beat.number, m))

    print(f"Missing audio files: {len(missing)}")
    print(f"Audio decode errors: {len(decode_errors)}")
    print(f"Non-positive multipliers: {len(multiplier_errors)}")
    print(f"Tempo-adjusted phrase count: {requires_tempo_adjustment}")

    original_play = tmain.pydubplay
    original_playsound = tmain.playsound

    try:
        tmain.pydubplay = lambda segment: None
        tmain.playsound = lambda path: None

        dry_run_count = min(len(bol.beats), 16)
        for beat in bol.beats[:dry_run_count]:
            beat.play()
        print(f"Playback dry-run on first {dry_run_count} beats: OK")
    finally:
        tmain.pydubplay = original_play
        tmain.playsound = original_playsound

    out_dir = root / "recordings" / "_audit"
    out_dir.mkdir(parents=True, exist_ok=True)

    bhatkande_out = out_dir / "audit_bhatkande.txt"
    paluskar_out = out_dir / "audit_paluskar.txt"

    bol.write(str(bhatkande_out), Bhatkande)
    bol.write(str(paluskar_out), Paluskar)
    print(f"Wrote notation files: {bhatkande_out.name}, {paluskar_out.name}")

    if missing or decode_errors or multiplier_errors:
        print("AUDIT_STATUS: FAIL")
        return 1

    print("AUDIT_STATUS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
