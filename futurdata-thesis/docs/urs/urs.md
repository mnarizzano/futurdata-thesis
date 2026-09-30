# ARIADNE: User Requirements Specification

Version 2.0 — consolidated project specification, 23 September 2026.

## Purpose and scope

ARIADNE is a Python/Tkinter desktop application for describing how a physical
product is taken apart. Users draw a disassembly diagram, record component and
operation details, attach photographs, save their work locally, and generate
technical guides. Typical users are students, engineers, repair technicians,
and authors of disassembly documentation.

This is the single project URS, replacing the individual author and use-case
drafts. Contributor information remains in [AUTHORS.md](../../AUTHORS.md).
Sample product JSON files and photographs remain in the use-cases directory.

## Diagram model

- A root component represents the complete product.
- Intermediate components represent assemblies that can be disassembled further.
- Leaf components represent final parts.
- Circles represent disassembly steps.
- Diamonds represent detailed actions associated with steps.
- Directed connections describe step inputs, outputs, and action ordering.

A typical procedure connects a product to a step, attaches detailed actions to
that step, and connects the step to resulting components. Users can describe
names, brand/model, weights and units, materials, colors, tools, descriptions,
and images where the selected node supports those properties.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | Create, edit, clear, and reopen disassembly diagrams. |
| FR-02 | Add, select, move, duplicate, and delete diagram elements and connect them with directed relationships. |
| FR-03 | Provide a properties panel, undo/redo, grid and snapping controls, scrolling, and zoom. |
| FR-04 | Distinguish root, intermediate, and leaf components, steps, and detailed actions. |
| FR-05 | Associate component details, action tools, descriptions, and local images with supported node types. |
| FR-06 | Manage reusable color, material, and tool catalogs. |
| FR-07 | Save product records and relationships in a local JSON repository without a database server. |
| FR-08 | List saved products and reconstruct a selected product diagram for continued editing. |
| FR-09 | Export the active diagram as a ZIP containing diagram.json and available referenced images, including current canvas coordinates. |
| FR-10 | Import a project ZIP or supported diagram JSON, rebuild shapes and connections, and synchronize the imported diagram with local storage. |
| FR-11 | Export guides as PowerPoint, Word, Markdown, plain text, and HTML. |
| FR-12 | Normalize and validate the diagram graph for guide generation, order the steps, and derive a bill of materials. |
| FR-13 | Prompt about unsaved changes when replacing the active diagram where the controller's unsaved-change check applies. |
| FR-14 | Report export failures and warn when a referenced ZIP image is missing. |

## Architecture and data requirements

The application separates models, Tkinter views, controllers, repositories,
and export services. The repository stores records in
~/.disassembly_diagram/ariadne_data.json. Images are separate files under
~/.disassembly_diagram/images/. Integer identifiers connect JSON records.

The in-memory canvas is the source for portable ZIP and document exports.
Those exports do not require saving to the repository first. Converter services
turn a diagram snapshot into an ordered guide and then into the chosen format.

## Non-functional requirements

- Use Python 3.10 or newer with a working Tkinter installation.
- Keep one requirements.txt containing runtime and development dependencies.
- Keep JSON readable as UTF-8 and replace the repository file atomically.
- Keep UI, persistence, and conversion responsibilities separately maintainable.
- Include the assets needed to share a portable project when those files exist.
- Validate archive member destinations before extracting a project ZIP.
- Maintain automated checks for models, persistence, controllers, and exporters.

## Current boundaries

Local storage is intended for a desktop workflow. It does not provide database
transactions across a whole diagram save or coordinated multi-process editing.
Load Product generates a layout from stored records; ZIP export is the route
for retaining the active canvas coordinates. Import clears old entity IDs,
but an existing root with the same name can be reused. ZIP files contain an
active diagram, not a backup of all products and catalogs.

PDF export, simultaneous multi-user editing, and diagram version comparison
are outside the current export/workflow scope. Guide validation and rendering
capabilities differ by output format; a diagram that can be drawn may still
require corrections before it produces a useful ordered guide.

## Acceptance workflow

1. Install requirements.txt and launch python run_app.py.
2. Create a root, a disassembly step, an action, and an output component;
   connect them and enter their properties.
3. Attach an image, save, and reopen the product using Load Product.
4. Export a project ZIP and confirm it contains diagram.json and the image.
5. Import the ZIP and inspect the shapes, connections, coordinates, and image.
6. Export each document format and inspect the resulting guide and image assets.

See [JSON storage, ZIP, and conversion guide](../JSON_STORAGE_AND_EXPORT.md)
for the detailed workflow and implementation references.
