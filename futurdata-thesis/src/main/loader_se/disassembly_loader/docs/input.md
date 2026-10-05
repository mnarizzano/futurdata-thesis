# Input format — the Builder graph

This describes the JSON model the loader reads. It is for whoever **authors the
graph** (the Builder GUI). If you only consume the loader's output, you can skip
this file and read [`OUTPUT.md`](OUTPUT.md) instead.

---

## The big picture

A model is a **directed graph** of shapes. The loader reads three kinds of node,
each with a distinct role:

| Node type     | Role                                                            |
|---------------|----------------------------------------------------------------|
| **component** | a part: the whole product, an intermediate sub-assembly, or a final piece |
| **diamond**   | an **operation** — one disassembly action (e.g. "Remove the cover") |
| **action**    | a single **instruction** — how to perform an operation (e.g. "Unscrew the 4 screws") |

Edges connect them into the disassembly flow: the product enters an operation,
the operation produces parts, some parts continue into further operations.

---

## The rules a valid model must follow

1. **One root.** Exactly one component has no incoming edge and starts the
   disassembly. (A shape with no edges at all is an orphan — it is ignored, not
   treated as a root.)

2. **A component continues into exactly one operation.** A part that is not yet
   fully taken apart leads to **one** diamond. You extract one piece, and the
   rest continues to the next single operation — forming a chain. Never wire two
   diamonds off the same component.

3. **An operation produces one or more components.** A diamond's component
   children are the parts obtained. Any number of them can be final pieces; one
   **or more** can themselves continue into further operations — so the
   disassembly may **branch** here (several sub-assemblies, each taken apart
   along its own path). An operation never connects directly to another
   operation: a continuation always passes through a component.

4. **Instructions are optional.** A diamond may carry action nodes that describe
   how it is performed, wired either as a **chain** (action → action → …) or as a
   **fan-out** (several actions directly under the diamond). Both are accepted,
   and you get all of them. An operation whose name already says everything
   ("Unscrew 4 screws") may have **no** actions at all.

5. **An action is a single step.** When chained, it has at most one predecessor
   and one successor.

Weights, materials, colors and images on components are **optional**. When every
part carries a weight, the loader checks that they sum to the product's weight.

---

## What happens if a rule is broken

The loader is permissive: a model that breaks these rules **still produces a
guide**, on a best-effort basis, and reports each problem as a warning (see the
warnings list in [`OUTPUT.md`](OUTPUT.md)). It refuses the file **only** when it
cannot be parsed as a graph at all (corrupt JSON, or the `shapes` array missing).

---

## Minimal shape reference

The top level of the JSON has a `shapes` array (the nodes and the arrow-edges).
Edges may instead live in a top-level `connections` array — the loader accepts
either. Field names may vary slightly (the loader absorbs the differences); the
fields that matter per node:

**A component / diamond node:**

```json
{
  "id": 1,
  "type": "component",              // or "diamond"
  "text": "Bialetti Gioia",         // the name / operation label
  "x": 900, "y": 60,                // position (used to order siblings)
  "weight": "2500", "weight_unit": "g",   // optional
  "material": "Aluminium",          // optional
  "color": "Silver",                // optional
  "image_path": "images/body.jpg"   // optional
}
```

**An action node:**

```json
{
  "id": 10,
  "type": "action",
  "step_description": "Unscrew the 4 rear screws",   // the instruction text
  "x": 1000, "y": 200,
  "tools": "Phillips PH1"            // optional
}
```

**An edge** — either as an entry in `connections`:

```json
{ "from_id": 1, "to_id": 2 }
```

or as an `arrow` shape inside `shapes`:

```json
{ "type": "arrow", "from_shape_id": 1, "to_shape_id": 2 }
```

---

## A tiny complete example

A product, one operation with two instructions, one extracted part and one part
that continues:

```
        Coffee machine (component, id 1)
                     |
        Remove outer shell (diamond, id 2)
        /          |            \
  action id 10   Outer shell    Chassis
  "Unscrew..."   (component,     (component, id 4,
      |           id 3 — a        continues into the
  action id 11    final leaf)     next operation)
  "Slide up..."
```

Edges: 1→2, 2→10, 10→11, 2→3, 2→4. From this the loader produces one step
("Remove outer shell") whose instructions are the two actions, whose output is
the Outer shell, and which continues as the Chassis. See [`OUTPUT.md`](OUTPUT.md)
for exactly what that step looks like.