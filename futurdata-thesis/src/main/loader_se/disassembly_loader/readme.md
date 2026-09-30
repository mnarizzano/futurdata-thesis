# Disassembly Loader

The **load phase** of the Disassembly Wizard. It takes a Builder JSON model of a
product's disassembly graph and turns it into a ready-to-use **guide**: an
ordered list of steps that an output generator (PDF, HTML, PPTX, …) can render
directly, with no graph logic on its side.

- The shape of the **input** file is described in [`INPUT.md`](INPUT.md).
- The shape of the **output** (the IR) is described in [`OUTPUT.md`](OUTPUT.md).

This README is only about **how to use the library**, step by step.

---

## Step 0 — Requirements

- Python 3.10 or newer.
- Nothing else to run the library itself. (To run the tests you also need
  `pytest` and `jsonschema`.)

Check your Python:

```bash
python3 --version
```

---

## Step 1 — Get the library into your project

The library is the folder `disassembly_loader/`. Put it where your code can
import it — the simplest way is to copy it next to your own script:

```
my_project/
├── disassembly_loader/     <- the library (this whole folder)
└── my_script.py            <- your code
```

That's it — no installation step, no pip package.

---

## Step 2 — Use it from Python

Create a file (e.g. `my_script.py`) next to the `disassembly_loader/` folder and
write:

```python
from disassembly_loader import build_guide

# point it at a Builder JSON model
guide = build_guide("path/to/model.json")

# the product being taken apart
print("Product:", guide.product.name)

# every disassembly step, in order
for step in guide.steps:
    print(step.index, step.operation)          # e.g. 1 "Open outer shell"
    for action in step.actions:                # how to do it
        print("   -", action.text)
    for part in step.outputs:                  # what you get
        print("   =>", part.name)
```

Run it:

```bash
python3 my_script.py
```

That is the whole basic usage: **call `build_guide(path)`, then iterate
`guide.steps`.**

---

## Step 3 — Get the output as a JSON file (for non-Python generators)

If your generator is not in Python (or you just want the result on disk), ask
the library to write the JSON for you:

```python
from disassembly_loader import build_ir_file

build_ir_file("path/to/model.json", "out/guide.json")
```

Now `out/guide.json` contains the full guide. Any language can read it:

```javascript
const guide = await fetch("guide.json").then(r => r.json());
guide.steps.forEach(s => console.log(s.index, s.operation));
```

The JSON has exactly the shape described in [`OUTPUT.md`](OUTPUT.md).

---

## Step 4 — Options (when you need them)

Both `build_guide` and `build_ir_file` accept the same optional settings. You can
ignore them at first; the defaults are sensible.

```python
from disassembly_loader import build_guide, DepthSpec, DepthMode

# how deep to take the product apart (default: all the way)
build_guide(path, depth=DepthSpec(mode=DepthMode.FULL))
build_guide(path, depth=DepthSpec(mode=DepthMode.KEEP_MAIN))   # keep main assemblies whole

# also produce the bill of materials (the list of final parts)
build_guide(path, include_bom=True)
```

| Option        | Default | What it does                                             |
|---------------|---------|----------------------------------------------------------|
| `depth`       | full    | How deep to disassemble.                                 |
| `include_bom` | `False` | If `True`, fills the bill of materials.                  |

---

## What if the model has mistakes?

The library never crashes on a flawed-but-readable model. It still produces the
best guide it can, and reports every problem as a **warning** you can read:

```python
guide = build_guide("path/to/model.json")
for w in guide.warnings:
    print(w.severity, w.rule, "-", w.message)
```

It raises an error **only** when the file cannot be read as a model at all
(corrupt JSON, or the required `shapes` is missing):

```python
from disassembly_loader import build_guide, UnparsableModelError

try:
    guide = build_guide("path/to/model.json")
except UnparsableModelError as e:
    print("The file could not be read as a model:", e)
```

What counts as a valid model, and what each warning means, is explained in
[`INPUT.md`](INPUT.md).

---

## Running the tests (optional)

From the folder that contains `disassembly_loader/` and `tests/`:

```bash
pip3 install pytest jsonschema     # once
python3 -m pytest                  # run all tests
```

The `tests/` folder also contains two small demo scripts — `try.py` (prints a
guide on screen) and `make_ir.py` (writes the output JSON to a file) — if you
want to see the library work without writing code. What the suite covers is
explained in [`TESTS.md`](TESTS.md). Make sure to have this folder and the test one in the same folder before running them. 