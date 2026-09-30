# Installation

Use Python 3.10 or newer with Tkinter. From `futurdata-thesis/`:

```sh
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python run_app.py
```

Pillow, python-pptx, and python-docx are required for image and document exports.
Tkinter must be provided by your Python installation or operating system.
Run `python -m tkinter` to check that it can open a window.

For development, install `requirements.txt` and see
[the test guide](../../src/tests/README.md).
