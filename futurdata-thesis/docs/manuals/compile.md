# Validation

This is a Python application with no separate packaged build configuration.
After installing `requirements.txt`, run from `futurdata-thesis/`:

```sh
python -m compileall -q src run_app.py
python -m pytest -q
python -m ruff check src run_app.py --select F,E9,B012,B014,B018
```

The test suite includes Tkinter UI tests and therefore needs a working display.
