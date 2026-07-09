# Futurdata Thesis / Disassembly Flow Diagram Builder
## User Requirements Specification Document (URS)

**Version:** 1.0

### Authors
Nicolas Rodriguez, María Begines Tirado, Katia Amorós Cristea, Lucía Bezares García, Davide Ferrando, Arbaz Khan

### Revision History

| Version | Date | Authors | Notes |
|---|---|---|---|
| 1.0 | 12/06/26 | Nicolas Rodriguez <br> María Begines Tirado <br> Katia Amorós Cristea <br> Lucía Bezares García <br> Davide Ferrando <br> Arbaz Khan | First revision |

## 1. Introduction

### 1.1 Document Scope
The purpose of this document is to define the user requirements for the Disassembly Flow Diagram Builder, which is a desktop application that lets users create, edit, save, load, and inspect graphical disassembly diagrams for products such as printers and capsule coffee machines. It represents a product as a node-based AND/OR graph of components (root, composite, leaf), disassembly steps, detailed actions, decision branches, and directed connections, persisting the model to a local database and a portable JSON format.

### 1.2 Definitions and Acronyms

| Acronym/Term | Definition |
|---|---|
| Action | A detailed operation inside a disassembly step. |
| Action node | Node describing a disassembly step or physical operation. |
| ARIADNE | The project name for this disassembly planning and software package. |
| BOM | Bill of Materials. A list of raw materials, sub-assemblies, intermediate parts, sub-components, and parts required to manufacture or disassemble a product. |
| Canvas | The drawing area where the diagram is displayed. |
| Component | A physical part or assembly of the product being disassembled. |
| Composite node | Intermediate component node that groups sub-components or action sequences. |
| Connection | A directed relationship between two diagram elements. |
| DAG | Directed Acyclic Graph. A directed graph with no directed cycles, used here to model hierarchical disassembly levels. |
| DB | Database. |
| Diamond node | Decision/condition node that branches the flow based on a YES/NO condition. |
| DSP | Disassembly Sequence Planning. The process of finding optimal sequences of disassembly steps to retrieve desired target parts. |
| GUI | Graphical User Interface. |
| JSON | JavaScript Object Notation, used for diagram serialization. |
| Leaf node | Terminal component node representing an individual, indivisible part. |
| MVC | Model-View-Controller. A software design pattern used to separate program logic, data, and user interface. |
| Root node | Top-level component node representing the complete product. |
| SDL | Software Design / Development Layer. |
| Step | A main disassembly operation in the procedure. |
| URS | User Requirements Specification. A document specifying what the user requires from the software. |

### 1.3 References

- Project source repository of the Futurdata disassembly flow diagram builder: `github.com/mnarizzano/futurdata-thesis`.
- Software Engineering course slides: Introduction, Process Model, Requirements Engineering.

## 2. System Description

This document outlines the User Requirements Specification for a disassembly flow diagram builder designed to help users model the disassembly of technical products in a graphical way.

### 2.1 Context and Motivation
The Disassembly Flow Diagram Builder allows users to create structured graphs representing the disassembly process of physical products. Nodes represent either components (root, composite, or leaf) or operations (actions, decisions), and arrows capture the sequencing and dependencies between them.

The current software already provides a graphical editor, a palette of shapes, a canvas for diagram construction, a properties panel, and persistence through saved diagram files and a database layer. The project is useful for educational purposes, technical documentation, thesis work, and structured analysis of product disassembly procedures.

### 2.2 Project Objectives

The purpose of this tool is to simplify and organize the representation of disassembly procedures in a way that is visually clear and easy to modify. The system shall help the user:

- build a diagram from a product manual,
- represent physical parts and disassembly steps,
- attach detailed actions to each step,
- save and reload diagrams,
- and improve the quality of technical documentation.

The system should also evolve into a more maintainable and well-documented software product through better design, clearer code, testing, and possible restructuring.

## 3. Requirements

| Priority | Meaning |
|---|---|
| M | Mandatory |
| D | Desirable |
| O | Optional |
| E | Future Enhancement |

### 3.1 Stakeholders

- The students who are developing the project.
- The course teacher / evaluator.
- Users who need to document, visualize, create and edit disassembly procedures.
- Future developers who will maintain or extend the software.
- Technical readers who will use the resulting diagrams for analysis or documentation.
- Developers responsible for maintaining and extending the application.

### 3.2 Functional Requirements

| ID | Description | Priority |
|---|---|---|
| 1.0 | The system shall allow the user to create a new empty disassembly diagram. | M |
| 2.0 | The system shall allow the user to add elements from a graphical shape/node palette and place them on the canvas. | M |
| 3.0 | The system shall allow the user to drag and move individual shapes or group selections on the canvas. | M |
| 4.0 | The system shall allow the user to select one or more elements (multi-select via modifier keys, select-all, or rubber-band area selection). | M |
| 5.0 | The system shall allow the user to delete elements/nodes and their connections. | M |
| 6.0 | The system shall allow the user to clear the entire diagram at once. | M |
| 7.0 | The system shall allow the user to connect elements with directed arrows — including arrow labels (e.g. YES/NO/retry), automatic anchor ports, and a connection preview. | M |
| 8.0 | The system shall allow the user to edit the properties/content of a selected element via a properties panel. | M |
| 9.0 | The system shall allow the user to duplicate selected nodes/shapes | M |
| 10.0 | The system shall provide a right-click context menu (edit, duplicate, delete, connect). | M |
| 11.0 | The system shall allow the user to undo and redo editing actions (Ctrl+Z / Ctrl+Y). | M |
| 12.0 | The system shall help the user align and organize elements with dynamic alignment guides. | D |
| 13.0 | The system shall provide a grid with snapping and a visibility toggle | M |
| 14.0 | The system shall allow the user to scroll the canvas (scrollbars, mouse wheel, automatic viewport expansion). | M |
| 15.0 | The system shall allow the user to zoom in and out of the diagram. | D |
| 16.0 | The system shall allow the user to copy and paste multiple elements at once. | E |
| 17.0 | The system shall allow the user to represent product components with distinct node types: root, composite/intermediate, and leaf. | M |
| 18.0 | The system shall allow the user to represent operations with step nodes and detailed action nodes, and to organize actions within a step in an ordered sequence. | M |
| 19.0 | The system shall allow the user to create decision/diamond nodes for conditional branching (YES/NO). | M |
| 20.0 | The system shall support back-edges (arrows pointing to earlier nodes) to represent retry loops. | M |
| 21.0 | The system shall enforce domain connectivity and consistency constraints (valid component–step–action connections; exactly one input per step; outputs share the same root; root cannot be an output; a leaf cannot be a connection source; the root role is preserved). | M |
| 22.0 | The system shall allow the user to assign and edit component attributes: name, colour, material, weight, and measurement unit. | M |
| 23.0 | The system shall allow the user to manage custom colour and material catalogs (create/remove entries, visual colour picker, materials listed alphabetically). | D |
| 24.0 | The system shall allow the user to associate a tool with an action / diamond step. | M |
| 25.0 | The system shall allow the user to attach descriptive text and warning/caution notes to steps and actions. | D |
| 26 | The system shall allow the user to attach and display an image (file or URL) on a node. | D |
| 27.0 | The system shall support component identification and product metadata fields: root-component id, automatic component numbering, node-type designation, and product brand/model. | M |
| 28.0 | The system shall allow the user to model repeated operations (e.g. multiple screws/hooks) as separate actions. | D |
| 29.0 | The system shall allow the user to save a diagram and its changes to local storage. | M |
| 30.0 | The system shall allow the user to load/reopen a previously saved diagram and continue editing it. | M |
| 31.0 | The system shall allow the user to save/export the diagram in JSON format and to view/edit the raw JSON directly. | M |
| 32.0 | The system shall validate the diagram file structure on load (metadata, shapes, connections). | M |
| 33.0 | The system shall guard against losing unsaved changes (prompt to Save/Discard/Cancel on New/Open/Exit). | M |
| 34.0 | The system shall allow the user to save the document under a user-chosen filename. | E |
| 35.0 | The system shall allow the user to export the diagram as an image (PNG/JPEG) or PDF. | E |
| 36.0 | The system shall allow the user to build diagrams from a service manual/procedure, reproducing the disassembly order, to visually document a device's disassembly. | M |
| 37.0 | The system shall allow the user to produce diagrams suitable for a thesis/technical report, clearer than plain text. | D |
| 38.0 | The system shall provide an in-app help window explaining the node types and main features. | D |
| 39.0 | The system shall allow the user to search/filter elements within a diagram (by colour, material, or tool). | E |
| 40.0 | The system shall allow the user to compare two diagram versions. | E |
| 41.0 | The system shall allow the user to manage multiple product models in the same project. | E |
| 42.0 | The system shall allow the user to generate documentation automatically from the diagram. | E |
| 43.0 | The system shall allow multiple users to edit a graph simultaneously. | E |

### 3.3 Non-Functional Requirements

| ID | Description | Priority |
|---|---|---|
| 1.0 | The system shall provide an understandable GUI usable by non-programmers, displaying diagrams in a clear and readable form | M |
| 2.0 | The system shall respond to user actions within a reasonable, interactive time (2s), remaining smooth for complex diagrams (100+ elements). | M |
| 3.0 | The system shall preserve user data reliably across save and load operation | M |
| 4.0 | The system shall be maintainable through clear code structure and documentation | M |
| 5.0 | The system shall be extensible to new diagram elements and validation rules | M |
| 6.0 | The system shall run as a cross-platform desktop application(Python/Tkinter-ttk, Windows, macOS, Linux) | M |
| 7.0 | The system shall support testing and verification through a well-defined structure | D |
| 8.0 | The system shall ensure database reliability via automatic transaction rollback on errors | E |
| 9.0 | The system shall render diagrams with back-edges/loops without visual artifacts. | M |
| 10.0 | The system shall ensure exported/saved JSON faithfully represents the full graph structure, including loops. | M |
