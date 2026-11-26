# PROMETHEUS-X Production Line Simulator

Simulates a camera / production-line client sending image-by-image scan requests to the PROMETHEUS-X server and receiving `True` (`PASS`) or `False` (`FAIL` / `REVIEW_REQUIRED`) for every image.

## Folder Structure

```text
simulator/
├── sample_data/         # Sample normal & defective images (add your own PNG/JPGs here)
├── stream_simulator.py  # CLI stream runner
├── simulator_ui.py      # Basic desktop UI (Tkinter)
└── README.md
```

## Usage

Make sure the PROMETHEUS-X backend (`run.bat`) is running and at least one **Scanner Unit** exists.

### Basic UI
```bat
.venv\Scripts\python.exe simulator\simulator_ui.py
```

### CLI Stream
```bat
.venv\Scripts\python.exe simulator\stream_simulator.py --unit-id 1 --mode sync
```
Use `--mode async` to stream through the non-blocking `/api/v1/jobs` queue instead of synchronous `/api/v1/inspections`.
