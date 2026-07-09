# User Requirements Specification (URS)

# ARIADNE

### A Visual Disassembly Sequence Planning (DSP) Diagram Builder

**Software Engineering Thesis Project**

**Date:** May 26, 2026
**Version:** 1.0

---

## Contents

1. [Introduction](#1-introduction)
   - [1.1 Purpose](#11-purpose)
   - [1.2 Scope](#12-scope)
   - [1.3 Definitions, Acronyms, and Abbreviations](#13-definitions-acronyms-and-abbreviations)
2. [General Description](#2-general-description)
   - [2.1 Product Perspective](#21-product-perspective)
   - [2.2 User Classes and Characteristics](#22-user-classes-and-characteristics)
   - [2.3 Operating Environment](#23-operating-environment)
3. [Functional Requirements](#3-functional-requirements)
   - [3.1 Visual Diagramming Canvas (VDC)](#31-visual-diagramming-canvas-vdc)
   - [3.2 Disassembly Domain Logic & Validation (DDL)](#32-disassembly-domain-logic--validation-ddl)
   - [3.3 Database Schema & Dynamic UI Integration (DUI)](#33-database-schema--dynamic-ui-integration-dui)
   - [3.4 File & Workspace Operations (FWO)](#34-file--workspace-operations-fwo)
4. [Non-Functional Requirements](#4-non-functional-requirements)
   - [4.1 Performance](#41-performance)
   - [4.2 Reliability](#42-reliability)
   - [4.3 Portability](#43-portability)
5. [Data Requirements & Database Dictionary](#5-data-requirements--database-dictionary)
   - [5.1 Database Tables Overview](#51-database-tables-overview)
   - [5.2 Table Schemas](#52-table-schemas)

---

## 1 Introduction

### 1.1 Purpose

This document outlines the complete User Requirements Specification (URS) for **ARIADNE**, a desktop-based Disassembly Sequence Planning (DSP) Flow Diagram Builder. ARIADNE is designed to allow researchers and manufacturing engineers to model, visualize, and persist product disassembly flows. The system represents disassembly strategies using an And/Or graph where nodes denote physical components or disassembly operations, and edges denote disassembly splits and step sequences.

### 1.2 Scope

The scope of ARIADNE covers:

- A visual, interactive diagramming canvas utilizing grid systems, snapping, multi-selection, alignment guides, and viewport navigation.
- A structural parser that enforces graph connectivity constraints (e.g., component to operation splits, ordered operation chains).
- An integrated local database manager that automatically maps and persists the diagram structure onto a relational SQLite database schema.
- A dynamic user interface (UI) properties panel that queries database table schemas at runtime to automatically render properties fields.
- A local file manager supporting diagram serialization, workspace saving, and full Command-Pattern-based Undo/Redo mechanisms.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
| --- | --- |
| **ARIADNE** | The project name for this disassembly planning and software package. |
| **BOM** | Bill of Materials. A list of raw materials, sub-assemblies, intermediate parts, sub-components, and parts required to manufacture or disassemble a product. |
| **DAG** | Directed Acyclic Graph. A directed graph with no directed cycles, used here to model hierarchical disassembly levels. |
| **DSP** | Disassembly Sequence Planning. The process of finding optimal sequences of disassembly steps to retrieve desired target parts. |
| **MVC** | Model-View-Controller. A software design pattern used to separate program logic, data, and user interface. |
| **SQLite** | A lightweight, serverless relational database engine used for local persistence. |
| **URS** | User Requirements Specification. A document specifying what the user requires from the software. |

---

## 2 General Description

### 2.1 Product Perspective

ARIADNE is a standalone desktop application developed using Python and Tkinter for the GUI, structured according to the Model-View-Controller (MVC) architecture. It uses a local SQLite database for data persistence and a JSON-based file system format for workspace serialization.

### 2.2 User Classes and Characteristics

- **Researchers / Analysts:** Interested in evaluating product disassemblability, structural recycling paths, and disassembly sequence optimization. Require precise modeling of attributes (materials, weight, scientific classifications) and strict enforcement of graph integrity constraints.
- **Manufacturing / Process Engineers:** Design and document standard operating procedures for product disassembly, remanufacturing, or repair. Require a clean visual builder, intuitive tools, and simple step-by-step documentation facilities.

### 2.3 Operating Environment

The application operates within the following environment:

- **Operating System:** Platform-independent (Windows, Linux, macOS) supporting Python 3.
- **GUI Toolkit:** Tkinter and ttk (Tk themed widgets).
- **Persistence Layer:** Embedded SQLite 3 database.

---

## 3 Functional Requirements

### 3.1 Visual Diagramming Canvas (VDC)

**VDC-1: Shape Palette** — The system shall provide a tool palette containing six core modeling shapes:

- **Root Component:** Rectangle representing the root product or main assembly.
- **Leaf Component:** Rectangle representing individual, indivisible component parts.
- **Composite Component:** Rectangle representing intermediate sub-assemblies.
- **Action Circle / Step:** Circle representing a disassembly operation step.
- **Diamond Step / Action:** Diamond shape representing specific manual/machined actions performed within a step.
- **Arrow / Flow connector:** Line indicating directional flow between components, steps, and actions.

**VDC-2: Interactive Shape Editing** — The system shall support interactive canvas manipulations:

- **Drag and Move:** Users can drag individual shapes or group selections across the canvas.
- **Multi-Selection:** Users can select multiple shapes simultaneously by holding down modifier keys (Ctrl/Shift) during click.
- **Duplication:** Selected shapes can be duplicated with identical attributes, shifted by a canvas offset.
- **Context Menu:** Right-clicking a shape shall trigger a context menu with options to Edit Properties, Duplicate, Delete, and Connect.
- **Keyboard Deletion:** Pressing the Delete key shall delete selected shapes, provided they do not have active connection lines.
- **Select All:** Ctrl+A shortcut shall select all shapes currently on the canvas.

**VDC-3: Layout Aids** — To assist in drafting neat diagrams, the system shall provide:

- **Grid System:** A coordinate grid drawn at regular intervals (50 units).
- **Grid Snapping:** Snapping shape center coordinates to the closest grid intersection upon mouse release.
- **Grid Toggle:** Ability to turn grid visibility on or off.
- **Alignment Guides:** Temporary vertical or horizontal guidelines drawn dynamically when a dragged shape aligns with other canvas shapes.

**VDC-4: Canvas Navigation** — The canvas shall support fluid workspace navigation:

- **Scrollbars:** Vertical and horizontal scrollbars to navigate expanded areas.
- **Mouse Wheel Scrolling:** Scroll vertical view (MouseWheel) and horizontal view (Shift+MouseWheel).
- **Automatic Viewport Expansion:** Dragging elements near the visible boundaries shall expand the scroll region dynamically and scroll the view.

**VDC-5: Connecting Elements** — The system shall support connecting shapes via directional lines:

- **Anchor Calculations:** Connecting lines shall auto-calculate start and end points using the closest cardinal connection ports (top, bottom, left, right) of the source and target shapes.
- **Connection Modes:** A temporary dotted preview line shall extend from the source shape to the current cursor position when in connection mode, which can be canceled by pressing the Escape key.

### 3.2 Disassembly Domain Logic & Validation (DDL)

**DDL-1: Bipartite Graph Connectivity Constraints** — The editor shall enforce domain-specific relational semantics on connection lines:

- **Component → Step:** A connection from a Component (Root, Composite, or Leaf) to an Action Circle (Step) indicates that the component is the input to that disassembly step.
- **Step → Component:** A connection from an Action Circle (Step) to a Component indicates that the component is generated as an output of that step.
- **Step → Action:** A connection from an Action Circle (Step) to a Diamond Step (Action) associates that specific action with the disassembly step.
- **Action → Action:** A connection between two Diamond Steps (Actions) defines a sequential chain of activities within a single step.

Connections violating these rules shall be rejected or warn the user.

**DDL-2: Product Consistency Constraints** — The system shall ensure that:

- Output components resulting from a disassembly step must belong to the same root product as the step's input component.
- A disassembly step must be linked to exactly one input component (Root, Intermediate, or Leaf).
- A root component cannot be designated as an output of a step.

### 3.3 Database Schema & Dynamic UI Integration (DUI)

**DUI-1: SQLite Persistence Backend** — The system must automatically initialize and sync diagram modifications to a local SQLite database file, maintaining relational integrity. The database schema shall represent tables for components, steps, actions, colors, materials, tools, and links.

**DUI-2: Dynamic Properties Panel** — The sidebar properties panel shall dynamically parse the database table columns at runtime using database PRAGMA queries:

- **Automatic Layout:** Table column names are converted to human-readable field labels, and fields are arranged based on data types (e.g., Entry boxes for VARCHAR/REAL, Text areas for TEXT, Checkboxes for BOOLEAN).
- **Reflective Dropdowns:** Foreign key relationships (like `color_id` and `material_id`) are resolved to populate Combobox dropdowns containing records from the color and material registries.
- **Apply Changes:** Modifying properties in the panel and clicking "Apply Changes" must sync the changes to both the memory diagram model and the SQLite database.

**DUI-3: Color and Material Registries** — The application must provide interfaces to register new catalogs:

- **Add Color:** A custom dialog to record color names and HEX values.
- **Add Material:** A custom dialog to record material names and scientific identifiers.
- **Catalog Synchronization:** Adding a color or material must immediately refresh current dropdowns.

### 3.4 File & Workspace Operations (FWO)

**FWO-1: JSON Workspace Serialization** — The system shall support loading and saving diagrams to file:

- **Save / Save As:** Serializes current canvas shapes, positions, connections, and custom properties into a standard JSON schema.
- **Open:** Parses a diagram file, validates its structure, reconstructs all canvas shapes/lines, and builds database links.
- **Structure Validation:** The loader must verify the existence of metadata, shapes, and connections fields before parsing.

**FWO-2: Transactional Command History (Undo/Redo)** — To prevent data loss and support recovery, all coordinate changes, shape placements, deletions, connection formations, and property changes must follow the Command Pattern:

- **Undo:** Reverts the last executed canvas command and reverts database modifications.
- **Redo:** Re-executes the last undone command.

**FWO-3: Unsaved Changes Guard** — The system must track the diagram modification state:

- A modified flag must be set to `True` upon any shape addition, deletion, move, or property change.
- When triggering New Diagram, Open Diagram, or Exit, the user must be prompted with a dialog to Save, Discard, or Cancel if unsaved changes exist.

---

## 4 Non-Functional Requirements

### 4.1 Performance

- **Interface Responsiveness:** Shape dragging and guide alignment checks must happen within 16 ms (60 FPS feel).
- **Canvas Update Optimization:** Moving items on the canvas must invoke coordinate updates directly rather than redrawing all shapes, ensuring smooth interaction for complex flowcharts containing over 100 elements.

### 4.2 Reliability

- **Transaction Rollbacks:** Database queries executed through the Database Manager must utilize connection context managers to automatically execute rollback operations if an SQL integrity error or exception occurs.
- **Foreign Key Constraints:** SQLite foreign key constraint enforcement must be enabled (`PRAGMA foreign_keys = ON`) on every connection to prevent orphaned steps, outputs, or actions.

### 4.3 Portability

- **Standardized File Formats:** Save data files must use ASCII-compliant UTF-8 encoded JSON format to facilitate external exchange.
- **Cross-platform GUI:** The application must not depend on platform-specific UI bindings, utilizing native Tkinter/ttk libraries compatible with Windows, macOS, and Linux.

---

## 5 Data Requirements & Database Dictionary

The database schema, defined in the SQLite persistence backend, comprises the following tables:

### 5.1 Database Tables Overview

1. **color:** Reference list of colors used for visual part identification.
2. **material:** Catalogue of part materials (e.g. polymers, metals).
3. **tool:** Reference database of disassembly tools.
4. **action:** Unique operation definitions mapped to tools.
5. **root_component:** Product metadata (BOM root).
6. **intermediate_component:** Composite sub-assemblies.
7. **leaf_component:** Base level components.
8. **disassembly_step:** Operation step representing an action node.
9. **disassembly_step_action:** Ordered actions within a step.
10. **step_output_intermediate:** Intermediate components produced by a step.
11. **step_output_leaf:** Leaf components produced by a step.

### 5.2 Table Schemas

#### 5.2.1 Table: `color`

Stores RGB and Hex values for parts.

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | VARCHAR(50) | NOT NULL, UNIQUE |
| hex_code | VARCHAR(7) | NOT NULL |
| rgb_r | INTEGER | – |
| rgb_g | INTEGER | – |
| rgb_b | INTEGER | – |

#### 5.2.2 Table: `material`

Stores material catalog.

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | VARCHAR(100) | NOT NULL, UNIQUE |
| scientific_name | VARCHAR(50) | – |
| color_id | INTEGER | FOREIGN KEY REFERENCES color(id) ON DELETE SET NULL |

#### 5.2.3 Table: `tool`

Stores tools used for disassembly.

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | VARCHAR(100) | NOT NULL, UNIQUE |
| category | VARCHAR(50) | – |

#### 5.2.4 Table: `action`

Stores operational details for disassembly steps.

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | VARCHAR(255) | NOT NULL |
| description | TEXT | – |
| tool_id | INTEGER | FOREIGN KEY REFERENCES tool(id) ON DELETE SET NULL |

#### 5.2.5 Table: `root_component`

The root item in the product hierarchy.

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | VARCHAR(255) | NOT NULL |
| brand | VARCHAR(100) | – |
| model | VARCHAR(100) | – |
| description | TEXT | – |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| modified_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| color_id | INTEGER | FOREIGN KEY REFERENCES color(id) ON DELETE SET NULL |
| material_id | INTEGER | FOREIGN KEY REFERENCES material(id) ON DELETE SET NULL |
| weight | DECIMAL | – |
| weight_unit | VARCHAR(10) | DEFAULT 'g' |
| node_type | VARCHAR(20) | DEFAULT 'Root' |

#### 5.2.6 Table: `intermediate_component`

Represents mid-level sub-assemblies.

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| root_component_id | INTEGER | NOT NULL, FOREIGN KEY REFERENCES root_component(id) ON DELETE CASCADE |
| color_id | INTEGER | FOREIGN KEY REFERENCES color(id) ON DELETE SET NULL |
| material_id | INTEGER | FOREIGN KEY REFERENCES material(id) ON DELETE SET NULL |
| name | VARCHAR(255) | NOT NULL |
| weight | DECIMAL | – |
| weight_unit | VARCHAR(10) | DEFAULT 'g' |
| node_type | VARCHAR(20) | DEFAULT 'Intermediate' |

#### 5.2.7 Table: `leaf_component`

Represents single physical parts.

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| root_component_id | INTEGER | NOT NULL, FOREIGN KEY REFERENCES root_component(id) ON DELETE CASCADE |
| color_id | INTEGER | FOREIGN KEY REFERENCES color(id) ON DELETE SET NULL |
| material_id | INTEGER | FOREIGN KEY REFERENCES material(id) ON DELETE SET NULL |
| name | VARCHAR(255) | NOT NULL |
| weight | DECIMAL | – |
| weight_unit | VARCHAR(10) | DEFAULT 'g' |
| node_type | VARCHAR(20) | DEFAULT 'Leaf' |

#### 5.2.8 Table: `disassembly_step`

A disassembly operation step mapping an input component.

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| input_root_component_id | INTEGER | FOREIGN KEY REFERENCES root_component(id) ON DELETE CASCADE |
| input_intermediate_component_id | INTEGER | FOREIGN KEY REFERENCES intermediate_component(id) ON DELETE CASCADE |
| input_leaf_component_id | INTEGER | FOREIGN KEY REFERENCES leaf_component(id) ON DELETE CASCADE |
| step_order | INTEGER | NOT NULL |
| title | VARCHAR(255) | – |
| description | TEXT | – |
| image_path | VARCHAR(500) | – |

**Step Constraints:**

- Exactly one of `input_root_component_id`, `input_intermediate_component_id`, or `input_leaf_component_id` must be non-NULL.
- Unique indices prevent duplicate step ordering values per specific component.

#### 5.2.9 Table: `disassembly_step_action`

Resolves step-to-action relationships with internal execution ordering.

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| disassembly_step_id | INTEGER | NOT NULL, FOREIGN KEY REFERENCES disassembly_step(id) ON DELETE CASCADE |
| action_id | INTEGER | NOT NULL, FOREIGN KEY REFERENCES action(id) ON DELETE CASCADE |
| action_order | INTEGER | NOT NULL |

**Step Action Constraints:**

- Unique constraint on `(disassembly_step_id, action_order)` ensures strict sequential chains.
- Unique constraint on `(disassembly_step_id, action_id)` prevents duplicate mappings of the same action to a single step.

#### 5.2.10 Table: `step_output_intermediate`

Outputs of a disassembly step (intermediate components).

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| disassembly_step_id | INTEGER | NOT NULL, FOREIGN KEY REFERENCES disassembly_step(id) ON DELETE CASCADE |
| intermediate_component_id | INTEGER | NOT NULL, FOREIGN KEY REFERENCES intermediate_component(id) ON DELETE CASCADE |

#### 5.2.11 Table: `step_output_leaf`

Outputs of a disassembly step (leaf components).

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| disassembly_step_id | INTEGER | NOT NULL, FOREIGN KEY REFERENCES disassembly_step(id) ON DELETE CASCADE |
| leaf_component_id | INTEGER | NOT NULL, FOREIGN KEY REFERENCES leaf_component(id) ON DELETE CASCADE |

---

*ARIADNE — Disassembly Flow Diagram Builder · User Requirements Specification · Version 1.0*
