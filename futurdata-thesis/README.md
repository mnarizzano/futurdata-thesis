# ARIADNE Disassembly Workflow Builder

ARIADNE is a Tkinter desktop application for editing disassembly diagrams,
managing product/material/tool catalogs, and exporting guides as PowerPoint,
Word, Markdown, text, HTML, or portable project ZIP files.

## Run

Use Python 3.10 or newer with Tkinter (cleanup verified on Python 3.11).
From this directory:

```sh
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python run_app.py
```

Pillow handles images; python-pptx and python-docx provide Office exports.
Application data is stored in `~/.disassembly_diagram/ariadne_data.json`, with
images under `~/.disassembly_diagram/images/`. No database server or new
environment-variable configuration is required.

## Structure

- `src/main/models/`: diagram, shape, and connection state.
- `src/main/views/`: Tkinter widgets and UI presentation.
- `src/main/controllers/`: editing workflows and catalog access.
- `src/main/repositories/`: JSON persistence.
- `src/main/services/`: ZIP and document export services.
- `src/main/loader_se/disassembly_loader/`: graph validation and guide generation.
- `src/main/utils/`: commands, geometry, serialization, and image handling.
- `src/tests/`: unit and integration tests.
- `use-cases/` and `docs/`: sample inputs, manuals, and project references.

See [MVC_ARCHITECTURE.md](MVC_ARCHITECTURE.md) for dependency boundaries and
[ARCHITECTURE.md](ARCHITECTURE.md) for persistence/export details.

## Verify

```sh
python -m pip install -r requirements.txt
python -m pytest -q
python -m ruff check src run_app.py --select F,E9,B012,B014,B018
python -m compileall -q src run_app.py
```

GUI tests need a working Tkinter desktop/display. There is no separate packaged
build configuration. Two existing expected failures document legacy product-label
serialization behavior; see [src/tests/README.md](src/tests/README.md).

## Project documentation

- [Project requirements (single URS)](docs/urs/urs.md)
- [JSON storage, saving, ZIP export/import, and conversion](docs/JSON_STORAGE_AND_EXPORT.md)

requirements.txt is the single dependency list for running and developing the application.
