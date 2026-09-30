# Output format — the guide (IR)

This describes what the loader **produces**: the guide your generator consumes.
It is for whoever writes an output generator (PDF, TXT, MD, HTML+JS, PPTX, DOCX,
VIDEO).

The formal, machine-checkable contract is `disassembly_loader/ir_schema.json`
(JSON Schema, Draft 2020-12). This file is the readable explanation of it.
Current version: **1.1**.

> **Key idea.** The output is **not** the graph. It is a flat, ordered list of
> steps. Each graph node becomes a *role* inside a step, not a separate element.
> You iterate the list and render it — you never traverse a graph.

---

## Top level

Whether you get a Python `Guide` object or a JSON file, the shape is the same:

| Field               | Type                    | Meaning                                             |
|---------------------|-------------------------|-----------------------------------------------------|
| `schema_version`    | string                  | Contract version (`"1.1"`).                         |
| `product`           | Component               | The whole product being taken apart.                |
| `depth`             | object                  | Which disassembly depth was applied.                |
| `tools`             | [string]                | Every tool used across the whole guide (de-duplicated). Render at the top. |
| `steps`             | [Step]                  | The operations, in order. **This is what you iterate.** |
| `warnings`          | [Warning]               | Validation findings (may be empty).                 |
| `bill_of_materials` | [Component] or `null`   | The final parts, or `null` if not requested.        |

---

## A step

Each entry of `steps` is one disassembly operation:

| Field            | Type          | Meaning                                                       |
|------------------|---------------|---------------------------------------------------------------|
| `index`          | int           | 1-based position in the order.                                |
| `operation`      | string        | The operation name.                                           |
| `input`          | Component     | The piece this operation is performed **on**.                 |
| `actions`        | [Action]      | The instructions, in order (may be empty).                    |
| `outputs`        | [Component]   | The final parts obtained here.                                |
| `continues_as`   | [Component]   | The pieces that continue into later steps (may be empty).     |
| `tools_required` | [string]      | Tools used in this step (de-duplicated).                      |

**How to render a step, in words:** take `input`, perform `operation` by
following the `actions` in order, and you obtain the `outputs`. Each entry of
`continues_as` will be taken apart by a **later** step.

---

## How steps chain together

A guide can **branch** (one operation may yield several sub-assemblies, each
disassembled on its own). So do **not** assume the next item in the list
continues the current one. The reliable link is by id:

> a component in one step's `continues_as` reappears as the `input` of a later
> step — matched by `node_id`.

Steps are ordered depth-first (one branch finished before the next starts). An
empty `continues_as` means *that branch* is done — not that the guide is over.

---

## Sub-objects

**Component** — a part (the product, an output, a continuing piece, a BoM line):

| Field                  | Type            | Notes                                                |
|------------------------|-----------------|------------------------------------------------------|
| `node_id`              | int             | Id from the source model (use it to match steps).    |
| `name`                 | string          |                                                      |
| `weight`               | number or null  | `null` when unknown.                                 |
| `weight_unit`          | string or null  |                                                      |
| `material`             | string or null  |                                                      |
| `color`                | string or null  |                                                      |
| `image`                | object or null  | `{ "path": ..., "is_url": bool }`, or `null`.        |
| `kept_whole`           | bool            | `true` if kept intact by a depth cut.                |
| `contained_leaf_count` | int or null     | For a kept-whole block, how many parts are inside.   |

**Action** — one instruction:

| Field     | Type           | Notes                                             |
|-----------|----------------|---------------------------------------------------|
| `node_id` | int            |                                                   |
| `text`    | string         | The human-readable instruction.                   |
| `tools`   | string or null | Tool(s) as given by the source.                   |
| `image`   | object or null | Same `{path, is_url}` shape as a component image.  |

**Warning** — a validation finding:

| Field      | Type                          | Notes                                    |
|------------|-------------------------------|------------------------------------------|
| `rule`     | string                        | Which check fired.                       |
| `severity` | `"info"`/`"warning"`/`"error"`| **All non-blocking** — the guide exists. |
| `message`  | string                        | Human-readable explanation.              |
| `node_ids` | [int]                         | The source node(s) concerned.            |

---

## Two things that are always true

- **Optional fields are never omitted.** An empty optional field is present and
  set to `null` (an image, a weight) or to an empty list (`continues_as`,
  `actions`). You can always read the key; you never have to check if it exists.
- **Images:** `image` is `null` or `{ "path": "...", "is_url": true|false }`.
  `is_url` tells you whether to fetch a URL or load a local/relative path. The
  path is passed through unchanged.

> Note: the JSON always carries images as `{path, is_url}`. The Python `Component`
> object exposes the raw `image_path` string instead; compute `is_url` yourself
> if you consume the object directly rather than the JSON.

---

## A real step

Step 1 of the Bialetti guide (trimmed for readability):

```json
{
  "index": 1,
  "operation": "Open outer shell",
  "input":  { "node_id": 1, "name": "Bialetti Gioia" },
  "actions": [
    { "text": "Place the machine upside-down ...", "tools": "Soft cloth" },
    { "text": "Unscrew the 4 Torx T10 screws ...", "tools": "Torx T10 screwdriver" }
  ],
  "outputs":      [ { "node_id": 8, "name": "Outer shell" } ],
  "continues_as": [ { "node_id": 9, "name": "Chassis (full)" } ],
  "tools_required": [ "Soft cloth", "Torx T10 screwdriver", "..." ]
}
```

Here the Chassis (`node_id` 9) reappears as the `input` of a later step — that id
match, not list position, is how the steps connect.

Two full real outputs are in `disassembly_loader/examples/`:
`example_bialetti_ir.json` (clean, linear) and `example_airfryer_ir.json`
(branching, with instruction-less operations and a warning).