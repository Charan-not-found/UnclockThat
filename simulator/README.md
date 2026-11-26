# PROMETHEUS-X Production Line Simulator

Simulates a camera / production-line client streaming images from `.zip` archives in `simulator/sample_data/` to the PROMETHEUS-X server and receiving `True` (`PASS`) or `False` (`FAIL` / `REVIEW_REQUIRED`) for every image.

## Folder Structure

```text
simulator/
├── sample_data/           # Drop .zip archives here to select them from the dropdown
├── web_simulator.py       # Browser UI on http://127.0.0.1:5180 (launched by run.bat)
├── simulator_ui.py        # Optional desktop Tkinter UI
├── stream_simulator.py    # CLI stream runner
└── README.md
```

## Usage

### Web UI (Recommended — launched automatically by `run.bat`)
Open **http://127.0.0.1:5180**, select a **Scanner Unit** and a **Dataset ZIP** from `simulator/sample_data/`, and click **Start Stream**.

### CLI Stream
```bat
.venv\Scripts\python.exe simulator\stream_simulator.py --unit-id 1 --source simulator\sample_data\default_samples.zip --mode sync
```
Use `--mode async` to stream through the non-blocking `/api/v1/jobs` queue instead of synchronous `/api/v1/inspections`.
