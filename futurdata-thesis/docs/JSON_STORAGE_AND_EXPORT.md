# JSON storage, saving, ZIP export, extraction, and conversion

This guide describes the current ARIADNE implementation. Start the application
with python run_app.py from the project directory after installing
requirements.txt.

## 1. How JSON replaces a database

ARIADNE uses JsonRepository as its persistence boundary. Controllers call Python
methods to create, find, update, and delete records. The repository loads a JSON
document into memory and writes the updated document back to disk. No SQL
queries, database server, or database connection configuration are required.

Default storage:

~~~
~/.disassembly_diagram/
    ariadne_data.json
    images/
        default_product/
            components/
            steps/
            actions/
        <product-specific folders>/
~~~

The tilde means the current user's home folder, for example C:/Users/YourName
on Windows. JSON stores image paths; image bytes remain in the images folder.
Image uploads copy supported local files into managed folders and use content
hashes to detect duplicates within the destination folder.

The repository has schema_version, updated_at, and counters, followed by arrays
of records:

| Collections | Purpose |
|---|---|
| colors, material_categories, material_subcategories, material_types, materials, tools | Reusable catalogs |
| root_components | Saved products |
| intermediate_components, leaf_components | Assemblies and final parts |
| disassembly_steps, actions | Operations and detailed actions |
| disassembly_step_actions | Ordered links between steps and actions |
| step_output_intermediate, step_output_leaf | Links from steps to resulting components |

Each record has an integer id. Other fields refer to those IDs, much like
foreign keys, but Python code manages the relationships. Counters allocate IDs.
Controller-facing component IDs distinguish roots, intermediates, and leaves
using offsets of 0, 1,000,000, and 2,000,000 respectively.

On first use, the repository creates the file and seeds default colors and
materials. On load, it fills missing collections and reconciles counters with
existing IDs. For handled read/parse failures it attempts to rename the file
to ariadne_data.json.broken and starts fresh. This is limited recovery handling,
not a full schema-validation or backup system.

## 2. What Save does

Choose File > Save or press Ctrl+S. The controller persists root components
first, then other shapes, then relationships from connections and arrow shapes.
Editing operations can also persist changes immediately; Save is not the only
time the repository changes.

For each repository write, the application:

1. Serializes the current repository document to a temporary file in the same folder.
2. Writes UTF-8, flushes the file, and calls fsync.
3. Uses os.replace to replace ariadne_data.json.

Atomic replacement reduces the risk of a partially written JSON file. A complete
diagram save performs several writes and is not one transaction. The persistence
loop can skip individual failures, so a Save status alone does not establish
that every invalid or disconnected node was stored.

File > Load Product reconstructs shapes and connections from stored records.
It calculates a new layout rather than restoring the canvas x/y positions.
Use a project ZIP when you need the active diagram's positions for sharing or
later import.

For a full local backup, close the app and copy the entire
~/.disassembly_diagram folder, including images. Avoid editing the repository
file while the app is open: subsequent writes use the in-memory data. The lock
is local to the repository instance; concurrent application instances are not
coordinated.

## 3. Three different JSON representations

| Representation | Contents | Consumer |
|---|---|---|
| Local repository | Products, catalogs, records, relationships, counters | JsonRepository and Load Product |
| Portable diagram | metadata, diagram settings, shapes, connections | ZIP import and document conversion |
| Guide IR (intermediate representation) | Product, ordered steps, tools, warnings, depth, bill of materials | Document renderers |

These formats are not interchangeable. Do not rename ariadne_data.json to
diagram.json and expect project import to work.

The portable snapshot has this general structure:

~~~json
{
  "metadata": {
    "version": "2.0",
    "export_type": "full"
  },
  "diagram": {
    "canvas_size": [2000, 2000],
    "zoom_level": 1.0,
    "grid_enabled": true,
    "snap_to_grid": true
  },
  "shapes": [],
  "connections": []
}
~~~

This is a structural example, not a complete disassembly model. Actual exports
include timestamps and other metadata. Shapes include IDs, type, x/y position,
text, and type-specific properties. Connections refer to shape IDs using
from_shape_id and to_shape_id. Arrow shapes are also retained, while their
relationships are normalized into connections for converters.

Shape IDs are snapshot references derived from Python object identities; they
are not durable cross-file IDs. Fields such as db_id and db_step_id are legacy
names for local repository identifiers, not evidence of a SQL database.
The inherited export_type value full also does not mean the ZIP includes the
whole repository. Canvas size and zoom in this serializer are fixed defaults,
so the snapshot should not be treated as a complete viewport-state backup.

## 4. How Export Project ZIP works

Choose File > Export Project ZIP and select a filename.

ProjectArchiveService asks serialize_active_diagram for a snapshot of the
current in-memory canvas. It does not read or update repository records.
Unsaved canvas content can therefore be exported directly.

The service creates a compressed ZIP:

~~~
my-project.zip
    diagram.json
    images/
        default_product/
            components/
                component-photo.jpg
            actions/
                action-photo.jpg
~~~

It writes diagram.json as UTF-8 and collects image references from the current
shapes. Existing files are added under images/, retaining managed relative
paths. Repeated archive paths are added once. Missing files are skipped and
reported as warnings. The ZIP includes neither unused images nor the complete
product/catalog repository.

Portable images should use the application's managed images/... paths. The
archive service falls back to a basename for other paths without rewriting the
JSON reference, so externally edited absolute paths may not import portably.
ZIP export writes the selected archive directly; atomic repository replacement
does not apply to ZIP creation.

## 5. Extracting and importing

To inspect an export, use an archive tool's Extract All command. Keep
diagram.json and its images folder together and preserve the subfolders.
Opening diagram.json in a text editor shows the diagram data; the image
references point to files rather than embedded image content.

To resume editing, choose File > Import Project and select the ZIP itself.
There is no need to extract it manually:

1. The service creates a temporary directory.
2. It checks that each archive member resolves inside that directory.
3. It extracts the archive and requires diagram.json at its root.
4. It copies extracted images into the application's managed images folder.
5. The JSON importer creates non-arrow shapes first, builds an old-ID-to-shape
   map, then reconstructs arrows and connections.
6. The controller clears imported storage IDs, disables JSON autosync for the
   imported diagram, and persists it through the local repository.
7. The temporary extraction directory is removed.

The archive service alone reconstructs the diagram; the controller performs
the local record persistence. Import can reuse an existing root with the same
name, and image copying can overwrite files with matching relative paths.
It is not an isolated restore of a complete repository or a guaranteed new
independent product.

The Import Project picker also accepts supported diagram JSON. Legacy enhanced
JSON exports can have a sibling <json-basename>_images folder and a repository
section. That legacy export_diagram path differs from ZIP serialization.
Importing an extracted ZIP's JSON alone does not run ZIP image restoration;
use the ZIP import workflow to restore its images.

## 6. How conversion works

Choose File > Export Document and select PowerPoint, Word, Markdown, Text,
or HTML. Select the destination file. To convert an existing ZIP, import it
first, then export the document from the active canvas.

The common starting point is the active diagram snapshot, not the saved
repository. Export stages a temporary diagram.json and copies available images
beside it, adjusting staged image references.

The shared disassembly loader normalizes JSON into a graph, validates it,
orders disassembly operations, and creates a Guide. The guide contains a
product, steps with input components/actions/outputs/continuations, required
tools, warnings, depth, and optionally a bill of materials. The current IR
schema version is 1.1. The bill of materials is derived from final step outputs
and avoids counting the same output node twice.

For DOCX, Markdown, TXT, and HTML, DocumentExportService calls
build_guide(..., include_bom=True) and writes temporary ir.json. HTML and TXT
renderers read that IR file; Markdown and the service's DOCX renderer use the
Guide object. DOCX output is assembled with python-docx.

PowerPoint follows PresentationExportService and export_to_pptx, which feed
the staged JSON through the PPTX engine and shared guide loader. It has its
own rendering/validation options and stops on blocking validation errors by
default. Other formats can surface warnings without identical stopping rules.

| Output | Result and images |
|---|---|
| PPTX | Editable PowerPoint presentation with supported images embedded |
| DOCX | Word guide with supported local images embedded |
| Markdown | Text guide with image references; keep the adjacent images folder |
| TXT | Plain-text guide; image references cannot display pictures in plain text |
| HTML | Browser-readable guide; keep the adjacent images folder |

For Markdown, TXT, and HTML, the service publishes staged assets to images/
beside the output before deleting temporary files. Share that folder with the
document. Exports into the same directory share that images folder.

Conversions generate reading/presentation documents. They are not editable
ARIADNE project backups, and there is no reverse document-to-diagram conversion
in this workflow. Retain the ZIP if further diagram editing is required.

## 7. Practical end-to-end workflow

1. Create a root product and connected steps, actions, and output components.
2. Fill in properties and attach local images.
3. Save to retain the product records locally.
4. Export Project ZIP to capture the current diagram coordinates and images.
5. On another installation, import that ZIP and inspect the reconstructed diagram.
6. Export the desired document format.
7. Share the Office file, or share the Markdown/TXT/HTML file with its images folder.

If an image is missing, check its managed file and reattach it before export.
If conversion fails, check root selection, step inputs, connections, and action
ordering and review the reported validation issue.

## 8. Implementation references

- [JSON repository](../src/main/repositories/json_repository.py): record storage and atomic replacement.
- [Application controller](../src/main/controllers/app_controller.py): Save, Import Project, and export commands.
- [Image handler](../src/main/utils/image_handler.py): managed image files and paths.
- [Diagram loader](../src/main/utils/diagram_loader.py): reconstructing a saved product.
- [JSON exporter](../src/main/utils/json_exporter.py): portable serialization and JSON reconstruction.
- [Archive service](../src/main/services/archive_service.py): ZIP creation and extraction.
- [Document export service](../src/main/services/document_export_service.py): DOCX, Markdown, TXT, and HTML.
- [Presentation service](../src/main/services/presentation_service.py): PPTX staging and conversion.
- [Guide builder](../src/main/loader_se/disassembly_loader/builder.py): normalization, validation, ordering, and guide construction.
