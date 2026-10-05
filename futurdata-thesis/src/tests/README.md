# Tests

From `futurdata-thesis/`, install `requirements.txt` and run `python -m pytest -q`.
`pytest.ini` adds the project root to the test import path. All tests use the
`src.main` package identity; runtime entry points retain their existing imports.

The suite includes unittest cases and pytest functions. Running unittest discovery
alone omits pytest functions, including persistence/archive integration coverage.
GUI tests create real Tkinter widgets and require a working display. Persistence
integration tests use temporary JSON files; controller tests mock repository access.

Two `unittest.expectedFailure` cases in `test_shape.py` document existing legacy
`product` label behavior. The cleanup deliberately preserves that JSON logic.
Exporter integration tests cover all five formats, model preservation, external
images for text/web formats, and embedded Word/PowerPoint images. PowerPoint tests
reopen saved presentations after temporary staging files have been removed and
verify product, instruction, and output pictures and their aspect ratios. Local
relative/absolute paths, data URIs, remote streams (mocked without network), and
optional missing/corrupt images are covered.
