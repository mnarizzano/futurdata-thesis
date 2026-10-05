# ARIADNE: Design Requirements Specification

DIBRIS - Universita di Genova, Scuola Politecnica, Software Engineering 80154.



## Revision history

| Version | Date | Description |
|---|---|---|
| 1.0 | 18 June 2026 | Initial consolidated editor design. |
| 2.0 | 23 September 2026 | Updated against the merged application: MVC boundaries, JSON repository, portable ZIP projects, shared guide loader, and five document exporters. |

## 1. Purpose and scope

ARIADNE is a desktop application for creating and documenting product
disassembly procedures. This DRS describes the implemented design and its
current limitations. It covers diagram editing, catalog access, local
persistence, project exchange, and document generation.

The requirements baseline is the [consolidated URS](../urs/urs.md).
The [JSON storage and export guide](../JSON_STORAGE_AND_EXPORT.md) provides
user-facing instructions. This document explains the components and their
interactions so that developers can maintain and verify the system.

### 1.1 Terminology

| Term | Meaning in this application |
|---|---|
| Diagram | In-memory shapes, connections, selection, and editing state. |
| Root component | The complete product. |
| Intermediate component | An assembly that can be disassembled further; also called composite in the UI. |
| Leaf component | A final part in the modeled procedure. |
| Step | Main disassembly operation represented by an ActionCircle. |
| Action | Detailed operation represented by a DiamondStep. |
| Repository | Python persistence adapter for the local JSON record store. |
| Snapshot | Serialization of the active canvas for project or document export. |
| IR | Intermediate representation of an ordered disassembly guide. |
| BOM | Bill of materials derived from final step outputs. |

Diamonds participate in ordered action relationships. Their shape does not
establish a general executable YES/NO decision language. A drawable graph is
not necessarily a valid ordered disassembly procedure.

## 2. Runtime and deployment

The application uses Python 3.10 or newer with Tkinter/ttk and a desktop display.
The single [requirements.txt](../../requirements.txt) includes:

| Dependency | Responsibility |
|---|---|
| Pillow | Image handling and display support. |
| python-pptx | PowerPoint generation. |
| python-docx | Word generation. |
| pytest | Automated verification. |
| ruff | Static checks. |

Python's standard library supplies JSON, ZIP, paths, temporary directories,
file copying, and synchronization primitives. SQLite and a database server
are not runtime dependencies.

From the project directory:

~~~sh
python -m pip install -r requirements.txt
python run_app.py
~~~

[run_app.py](../../run_app.py) adds src to the import path and calls
[main.py](../../src/main/main.py). Startup creates the Tk root, AppController,
and MainWindow, binds the controller to the view, and enters the Tk event loop.

Default application data lives in the user's home directory, independently
of the source-code location. Moving the project folder to D: does not change
the storage path. There is currently no storage-location setting in the GUI.
A Windows directory junction can redirect the complete data directory to
another drive while retaining the path used by the application; moving only
the repository JSON would leave the separately managed images behind.

## 3. Architecture

### 3.1 Dependencies and responsibilities

~~~mermaid
flowchart TD
    UI["Tkinter views"] --> AC["AppController"]
    UI --> CC["CatalogController API"]
    AC --> DM["Diagram, shapes, connections"]
    AC --> CH["CommandHistory"]
    AC --> CC
    AC --> JR["JsonRepository"]
    CC --> JR
    AC --> DL["DiagramLoader"]
    DL --> JR
    AC --> ZIP["ProjectArchiveService"]
    AC --> DOC["DocumentExportService"]
    ZIP --> SNAP["EnhancedJSONExporter"]
    DOC --> SNAP
    DOC --> PPT["PresentationExportService"]
    PPT --> SNAP
    DOC --> GUIDE["Shared guide loader"]
    PPT --> ENGINE["PPTX converter"]
    ENGINE --> GUIDE
    GUIDE --> RENDER["Guide / IR consumed by format renderers"]
    JR --> DISK["ariadne_data.json"]
~~~

The diagram shows workflow dependencies; the individual export routes are
specified in section 7. The shared exporter object receives a repository,
but serialize_active_diagram does not consult it. ZIP and document export
therefore remain independent of repository persistence.

| Package | Responsibility |
|---|---|
| src/main/models | Domain state and geometry for diagrams, shapes, and connections. |
| src/main/views | Tkinter widgets, event collection, rendering, dialogs, and status messages. |
| src/main/controllers | Editing orchestration, catalog APIs, persistence calls, and export commands. |
| src/main/repositories | JSON record operations and file persistence. |
| src/main/services | Archive and document export workflows and format implementations. |
| src/main/loader_se/disassembly_loader | Graph normalization, validation, ordering, and guide construction. |
| src/main/utils | Commands, serialization, image management, geometry, and product reconstruction. |

Views obtain catalog/product data through controller interfaces. They do not
instantiate repositories. PropertiesPanel receives a controller-backed data
provider, and DiagramCanvas receives a color resolver. Domain models do not
own Tkinter widgets or perform repository operations.

### 3.2 Main classes

| Class | Responsibility |
|---|---|
| MainWindow | Menus, toolbar, palette, canvas, properties panel, dialogs, and status bar. |
| DiagramCanvas | Render the diagram and expose pointer interactions to the controller. |
| PropertiesPanel | Display and edit properties supported by the selected shape. |
| AppController | Coordinate editing, persistence, product loading, and import/export. |
| CatalogController | Expose catalog and product data through a controller boundary. |
| Diagram | Hold shapes, connections, selections, metadata, and modified/file state. |
| Shape | Base geometric domain object for supported node and arrow types. |
| ComponentBox | Root, intermediate, or leaf component and its properties. |
| ActionCircle | Disassembly step, description, image, and associated storage ID. |
| DiamondStep | Detailed action, tools, description, image, and step/action links. |
| ArrowShape | Visual directed link between shapes. |
| Connection | Logical directed relation with endpoint anchors. |
| CommandHistory | Execute commands and maintain undo/redo stacks, default limit 100. |
| JsonRepository | Manage catalogs, product records, relationships, IDs, and JSON writes. |
| DiagramLoader | Rebuild a product diagram from repository records using generated positions. |
| EnhancedJSONExporter | Serialize active diagrams and reconstruct supported JSON snapshots; retain legacy enhanced JSON export. |
| DiagramSerializer | Legacy diagram file save/load support. |
| ImageHandler | Copy, deduplicate, and resolve managed image files. |
| ProjectArchiveService | Package/extract portable diagram ZIP archives. |
| DocumentExportService | Dispatch document formats and stage guide/image inputs. |
| PresentationExportService | Stage a canvas snapshot and invoke the PowerPoint converter. |

### 3.3 Core model relationships

~~~mermaid
classDiagram
    Shape <|-- ComponentBox
    Shape <|-- ActionCircle
    Shape <|-- DiamondStep
    Shape <|-- ArrowShape
    Diagram "1" o-- "*" Shape
    Diagram "1" o-- "*" Connection
    Connection --> Shape : source and target
    ArrowShape --> Shape : source and target
    AppController --> Diagram
    AppController --> CommandHistory
    AppController --> JsonRepository
    MainWindow --> AppController
    MainWindow *-- DiagramCanvas
    MainWindow *-- PropertiesPanel
~~~

Both logical connections and arrow shapes can represent relationships.
Portable serialization retains arrow shapes for editing and normalizes their
endpoint pairs into a deduplicated connections list for conversion.

## 4. Data design

### 4.1 Local repository

The default file is ~/.disassembly_diagram/ariadne_data.json.
Its document contains schema_version (initially 1), updated_at, counters,
and these collections:

| Collections | Stored information |
|---|---|
| colors, material_categories, material_subcategories, material_types, materials, tools | Shared catalogs and material hierarchy. |
| root_components | Product identity and properties. |
| intermediate_components, leaf_components | Assemblies and final components. |
| disassembly_steps, actions | Main operations and detailed actions. |
| disassembly_step_actions | Action membership and order within a step. |
| step_output_intermediate, step_output_leaf | Step output relationships. |

Integer IDs connect records. Per-collection counters allocate new IDs.
Controller-facing component identifiers use offsets: root IDs are unchanged,
intermediate IDs add 1,000,000, and leaf IDs add 2,000,000.
Legacy names such as db_id denote repository identifiers.

The repository loads records into memory. Updates rewrite the JSON document:
create a temporary file in the same directory, serialize UTF-8, flush/fsync,
and atomically replace the destination with os.replace. A local RLock protects
the write path. This is not a transaction spanning a complete diagram save
and does not coordinate separate application processes.

First use seeds default colors and materials. Loading reconciles counters
and supplies missing collections. For handled read or parse errors, the
repository attempts to rename the original file with a .json.broken suffix
and initialize new data. This does not provide general schema migration or
comprehensive malformed-document recovery.

### 4.2 Images

Image files reside under ~/.disassembly_diagram/images/, in product-specific
or default_product folders with component, step, and action subfolders.
JSON contains paths rather than image bytes. Supported upload extensions are
PNG, JPG/JPEG, GIF, BMP, and WebP. Content hashing supports duplicate detection
within the upload destination.

A complete local backup includes both ariadne_data.json and images/.
Managed relative images/... references support portable export.

### 4.3 Portable diagram contract

A ZIP snapshot's diagram.json has four top-level sections:

| Section | Meaning |
|---|---|
| metadata | Export version 2.0, timestamps, and descriptive fields. |
| diagram | Grid/snap settings and serializer-provided canvas/zoom values. |
| shapes | Type, ID, coordinates, text, image reference, and type-specific properties. |
| connections | Source/target shape IDs and endpoint anchors. |

Snapshot shape IDs are based on Python object identities and only link objects
inside that export. They are distinct from persistent record IDs. The active
serializer uses fixed canvas_size and zoom_level values, so this is not a
complete viewport-state snapshot.

The inherited metadata value export_type: full does not indicate a repository
backup. Active ZIP snapshots do not include the repository section used by
the older enhanced JSON export_diagram API.

### 4.4 Guide contract

The shared loader produces a Guide with schema version 1.1, product,
ordered steps, warnings, depth, a union of required tools, and an optional BOM.
Steps describe an input component, operation, detailed actions, outputs, and
continuing assemblies. The BOM deduplicates final output components by node ID.

Repository JSON, portable diagram JSON, and guide IR have different contracts.
They cannot be substituted for one another by renaming files.

## 5. Interface and editor design

The main window combines a menu and toolbar, shape palette, scrollable canvas,
properties panel, and status bar. Catalog dialogs provide colors, materials,
and tools; the product list provides access to saved products.

Current File commands include New, Load Product, Save, Export Project ZIP,
Export Document, and Import Project. Export Document offers PowerPoint, Word,
Markdown, Text, and HTML. Legacy open_diagram and save_diagram_as controller
methods remain in the code and do not define the main ZIP workflow.

Editing events pass to AppController. Commands implement additions, removals,
movement, connections, and property edits; MultiCommand groups operations.
Undo/redo concerns editing commands and must not be described as rollback
of all repository writes.

Typical interaction:

1. The user selects a palette type and places or edits an element.
2. The controller changes the model and records supported reversible commands.
3. Controller persistence paths synchronize supported records and relationships.
4. The view redraws the model and refreshes the properties/status display.

Component-to-step links identify step inputs. Step-to-component links identify
outputs. Step-to-action and action-to-action links associate and order detailed
actions. Controller/repository checks enforce supported relationships, while
guide validation checks the resulting graph for conversion.

The Diagram.modified flag supports change prompts. Individual paths update it
differently; Save and Export must not be modeled as a universal transition to
a fully persisted, unmodified state. Exporting a document does not save the
product repository.

## 6. Save and load workflows

### 6.1 Save

~~~mermaid
sequenceDiagram
    actor User
    participant View as MainWindow
    participant Controller as AppController
    participant Repository as JsonRepository
    participant Disk
    User->>View: Save (Ctrl+S)
    View->>Controller: save_diagram()
    Controller->>Controller: _persist_diagram()
    loop Roots, then other shapes
        Controller->>Repository: Create/update supported records
        Repository->>Disk: Temporary JSON, flush/fsync, replace
    end
    loop Connections and arrow relationships
        Controller->>Repository: Synchronize supported links
        Repository->>Disk: Persist changed records
    end
    Controller->>View: Status or reported error
~~~

Editing can also update storage before Save. _persist_diagram catches and skips
some per-shape and relationship failures; the success status is not proof that
every invalid/disconnected element was stored.

### 6.2 Load Product

The controller checks unsaved changes, obtains the selected product ID, and
calls DiagramLoader.load_product_diagram. The loader queries product,
component, step, action, and relationship records, creates domain objects,
assigns a generated layout, and reconstructs connections.

Loading a product does not restore the original canvas coordinates from the
repository. Export Project ZIP preserves those coordinates for later import.

## 7. Project exchange and conversion

### 7.1 ZIP export

~~~mermaid
sequenceDiagram
    actor User
    participant Controller as AppController
    participant Archive as ProjectArchiveService
    participant Serializer as EnhancedJSONExporter
    participant Images as ImageHandler
    participant ZIP as Output ZIP
    User->>Controller: Export Project ZIP
    Controller->>Archive: export_zip(active diagram, path)
    Archive->>Serializer: serialize_active_diagram(diagram)
    Serializer-->>Archive: metadata, diagram, shapes, connections
    Archive->>ZIP: Write UTF-8 diagram.json
    loop Referenced images
        Archive->>Images: Resolve image path
        alt Image exists
            Archive->>ZIP: Add images/... once per archive path
        else Image missing
            Archive->>Archive: Record warning and continue
        end
    end
    Archive-->>Controller: Result and image warnings
~~~

The ZIP uses deflate compression and contains diagram.json at its root plus
available referenced images. It serializes the active canvas without reading
or persisting repository records. It omits unused images and unrelated products.

ZIP writes are direct, unlike atomic repository replacement. Non-managed image
paths fall back to a basename in the archive without rewriting the JSON path;
portability therefore depends on normal managed image references.

### 7.2 ZIP extraction and import

1. AppController checks unsaved changes and asks for a ZIP or JSON path.
2. For ZIP input, ProjectArchiveService creates a temporary directory.
3. Every member destination is resolved and checked to remain inside that directory.
4. The archive is extracted and diagram.json is required at the root.
5. Images are copied into the managed images directory.
6. EnhancedJSONExporter.import_diagram creates non-arrow shapes, maps old
   snapshot IDs to objects, then reconstructs arrows and logical connections.
7. The controller clears imported entity IDs, resets file/autosync state and
   command history, and persists the diagram locally.
8. The temporary directory is removed and the canvas is refreshed.

The archive service itself does not write repository records; that is the
controller's responsibility. A root with an existing name can be reused during
persistence, and matching image paths can overwrite managed image files.
Import is not a transactional or isolated full-repository restore.

For manual inspection, extract the ZIP and keep its folder structure intact.
Import the ZIP itself to execute image restoration. Direct JSON import also
supports the older sibling <json-basename>_images convention, which differs
from ZIP extraction.

### 7.3 Document conversion

~~~mermaid
flowchart TD
    Canvas["Active Diagram"] --> Snapshot["Portable snapshot and staged images"]
    Snapshot --> Common["Shared loader: normalize, validate, order"]
    Common --> Guide["Guide with steps, tools, warnings, BOM"]
    Guide --> IR["Temporary IR JSON"]
    IR --> HTML["HTML renderer"]
    IR --> TXT["TXT renderer"]
    Guide --> MD["Markdown renderer"]
    Guide --> DOCX["Application DOCX renderer"]
    Snapshot --> PPTX["PPTX engine using shared guide loader"]
    PPTX --> Slides["PowerPoint presentation"]
~~~

DocumentExportService stages temporary JSON and image files. For DOCX,
Markdown, TXT, and HTML, it calls build_guide with include_bom=True and writes
the guide IR. HTML and TXT consume IR files; Markdown and the application's
DOCX rendering path use the Guide object.

PowerPoint is delegated to PresentationExportService, then export_to_pptx
and the PPTX engine. This route uses the shared guide loader and its own
rendering/validation options. Blocking validation issues stop PPTX export by
default; other format paths do not necessarily use the same stopping policy.

| Format | Output design |
|---|---|
| PPTX | Editable presentation with supported images embedded. |
| DOCX | Word document with headings, steps, warnings, BOM, and supported local images embedded. |
| Markdown | Text guide with references to external images. |
| TXT | Plain-text guide; image references do not render pictures. |
| HTML | Browser-readable guide with external image assets. |

For Markdown, TXT, and HTML, staged images are published under images/ beside
the final document before temporary files are removed. Documents written to
the same output directory share that asset folder. The legacy word_exporter
API remains separate from the DOCX renderer used by DocumentExportService.

Conversion consumes the current canvas and does not require an intermediate
repository save or a user-created ZIP. To convert a previously exported ZIP,
import it first. Generated documents are not editable ARIADNE backups, and
reverse document-to-diagram conversion is not implemented.

## 8. Reliability and current limitations

| Area | Implemented behavior and boundary |
|---|---|
| Storage durability | Atomic replacement per JSON write; no whole-diagram transaction or cross-process lock. |
| Invalid records | Some validation is performed in Python; not all malformed data or partial persistence is rejected. |
| Archive extraction | Member destinations are checked before extraction; malformed imports may return failure. |
| Missing images | ZIP export continues with warnings; document staging skips absent files. |
| Layout retention | Repository load generates layout; portable snapshots retain node coordinates. |
| Catalog portability | Active ZIP export does not carry a full catalog snapshot or remap all imported catalog IDs. |
| Change tracking | Modified flags and persistence are separate; save/export paths do not guarantee a universal clean state. |
| Import collisions | Matching root names may be reused; matching image paths may be overwritten. |
| Graph conversion | Validation warnings and blocking conditions vary by converter path. |
| Responsiveness | Current UI commands invoke services synchronously; large exports can occupy the Tk event thread. |
| Product scope | One active canvas; multiple stored products. No simultaneous multi-user editing. |

PDF/image document export, collaborative editing, diagram version comparison,
and a GUI storage-location selector are outside the current implementation.

## 9. Requirements traceability and verification

| URS requirement | Design implementation | Relevant existing verification |
|---|---|---|
| FR-01 to FR-04 | Diagram, shapes, canvas, controller, commands | test_diagram.py, test_shape.py, test_canvas_view.py, test_commands.py |
| FR-05 | PropertiesPanel and ImageHandler | test_properties_panel.py and image/export integration checks |
| FR-06 | CatalogController and catalog dialogs | Color/material/tool dialog tests and test_json_repository.py |
| FR-07 | JsonRepository and controller persistence | test_json_repository.py, test_app_controller.py |
| FR-08 | Product list and DiagramLoader | test_product_list_dialog.py, test_diagram_loader.py |
| FR-09 and FR-10 | ProjectArchiveService and JSON reconstruction | test_export_services.py, test_json_exporter.py, test_app_controller.py |
| FR-11 and FR-12 | Document services, shared loader, format renderers | test_export_services.py, test_pptx_images.py |
| FR-13 and FR-14 | Controller prompts and export error/status handling | test_app_controller.py, test_main_window.py, test_export_services.py |

The table identifies relevant tests, not a claim of exhaustive acceptance
coverage. test_mvc_boundaries.py checks architectural import boundaries.
See [test documentation](../../src/tests/README.md) for current limitations.

From the project directory:

~~~sh
python -m pytest -q
python -m ruff check src run_app.py --select F,E9,B012,B014,B018
python -m compileall -q src run_app.py
~~~

GUI tests require a working display. These commands describe the verification
workflow; updating this DRS does not establish that a new runtime test run
has passed.

Manual acceptance should create a connected product, attach images, save and
load it, export/import a ZIP, and inspect all five document formats. Check
that externally referenced image folders accompany text/web documents.

## 10. Source references

- [MVC architecture](../../MVC_ARCHITECTURE.md)
- [Application controller](../../src/main/controllers/app_controller.py)
- [Catalog controller](../../src/main/controllers/catalog_controller.py)
- [Models](../../src/main/models/diagram.py)
- [JSON repository](../../src/main/repositories/json_repository.py)
- [Diagram loader](../../src/main/utils/diagram_loader.py)
- [JSON exporter/importer](../../src/main/utils/json_exporter.py)
- [Image handler](../../src/main/utils/image_handler.py)
- [Archive service](../../src/main/services/archive_service.py)
- [Document export service](../../src/main/services/document_export_service.py)
- [Presentation export service](../../src/main/services/presentation_service.py)
- [Shared guide builder](../../src/main/loader_se/disassembly_loader/builder.py)

The inline architecture and sequence diagrams above replace the previous
DRS's SQLite-era diagram references. Existing image assets remain in the
repository as historical material.
