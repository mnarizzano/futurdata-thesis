# ARIADNE MVC architecture

## Dependency rule

`View -> Controller -> Model/Repository`

The View must never import or instantiate a repository. Repositories are persistence adapters on the Model side and are owned by controllers/services.

## Model

`src/main/models/` contains the in-memory domain state (`Diagram`, shapes, connections). `src/main/repositories/json_repository.py` is the JSON persistence adapter. There is no database layer.

## View

`src/main/views/` contains Tkinter widgets only. Views render model state, collect user input, and call controller APIs. `PropertiesPanel` receives a controller-backed data provider; `DiagramCanvas` receives a color resolver. Neither reaches into JSON persistence directly.

## Controller

`AppController` coordinates diagram editing and application commands. `CatalogController` is the controller boundary for catalog/product data needed by views. Controllers are the only UI-facing layer allowed to call repositories.

## Services

`src/main/services/` contains application operations that are not UI logic. `ProjectArchiveService` owns portable ZIP import/export and is independent of the internal JSON repository.

## Persistence and export

Internal persistence is JSON only. Portable export is a separate concern: an exported ZIP contains `diagram.json` and only the referenced images that exist. Missing images do not abort export.

## Tests and compatibility

Tests inject repository mocks into controller construction and controller-backed
catalog providers into views. No view imports the repository implementation.
`test_mvc_boundaries.py` checks layer imports; `test_export_services.py` exercises
the five document formats, including embedded PowerPoint images.

HTML rendering lives in `src/main/services/html_exporter/`. The separate demo
folder has been removed. The legacy Word API is retained because it produces a
different document layout from the application exporter.

## PowerPoint export integration

PowerPoint conversion is now part of the application service layer:

`View -> AppController -> PresentationExportService -> pptx_converter`

The converter receives an ephemeral JSON snapshot generated from the active
in-memory Diagram. It does not access the internal JSON repository. This keeps
presentation export independent from persistence in the same way as ZIP export.

## Other document exports

`View -> AppController -> DocumentExportService -> format renderer/shared loader`

The service stages images and temporary JSON, invokes the selected renderer,
and publishes assets for formats that reference external images. Models remain
independent of Tkinter and persistence; format renderers do not access repositories.
