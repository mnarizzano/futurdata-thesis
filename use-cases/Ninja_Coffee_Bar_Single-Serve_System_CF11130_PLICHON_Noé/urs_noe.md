# User Requirements Specification (URS)

**PROJECT:** Disassembly Flow Diagram Builder  
**VERSION:** 1.0  
**AUTHOR:** Noé Plichon  
**DATE:** June 30, 2026  

---

## 1. Introduction

### 1.1 Document Scope
The purpose of this document is to define the User Requirements Specification (URS) for the Disassembly Flow Diagram Builder. This desktop application is designed to create, manage, and analyze graphical representations of product disassembly processes. The software enables users to model components, disassembly steps, and their relationships through an intuitive diagram-based interface, providing a clear view of the disassembly workflow to optimize recycling and maintenance processes.

### 1.2 Definitions and Acronyms

| Acronym / Term | Definition |
| :--- | :--- |
| **URS** | User Requirements Specification. |
| **Root Node** | Top-level component node representing the complete product before any operations. |
| **Composite Node** | Intermediate component node that groups sub-components or action sequences. |
| **Leaf Node** | Terminal component node representing an individual, indivisible part. |
| **Action Node** | Node describing a disassembly step or physical operation. |

### 1.3 References

---

## 2. General System Description

### 2.1 Context and Motivation
Traditional textual documentation of disassembly procedures lacks operational clarity and does not allow for efficient analysis of component dependencies. The Disassembly Flow Diagram Builder addresses this need by providing an interactive workspace where physical structures are converted into visual diagrams.

By associating technical attributes with each node of the diagram (weight, material, required tool), the system enables users to evaluate disassembly complexity and the relationship between steps directly from their workstation.

### 2.2 Project Objectives
The objective of this project is to improve the existing Disassembly Flow Diagram Builder application. The priority focus areas are:
* Provide an interactive canvas allowing the creation of diagrams and connections using directed arrows.
* Integrate a local dictionary management system to standardize custom materials and associated color palettes.
* Ensure perfect persistence of diagram configurations through a standardized JSON file structure.

---

## 3. Specific Requirements

### Priority Grid
* **M (Mandatory):** Essential functionality indispensable for the first release.
* **D (Desirable):** Significant added value for ergonomics or efficiency.
* **O (Optional):** Visual comfort or secondary extension.
* **E (Enhancement):** Planned evolution in the long-term roadmap.

### 3.1 Stakeholders
* End users who create and edit disassembly diagrams.
* Students and researchers using the tool for academic purposes.
* Developers responsible for maintaining and extending the application.
* Futurdata, as the organization providing the software.

### 3.2 Functional Requirements

#### Module A: Canvas and File Management (MNG)
* **REQ-MNG-1.0:** The system shall allow the user to create a new disassembly diagram, save the state of the diagram, and load an existing project. (**Priority: M**)
* **REQ-MNG-2.0:** The system shall allow the user to export and import diagram data in JSON format. (**Priority: M**)
* **REQ-MNG-3.0:** The system shall allow the user to clear an entire diagram via a global reset command. (**Priority: D**)

#### Module B: Node Editing and Manipulation (MOD)
* **REQ-MOD-1.0:** The system shall allow the user to create graphs using different node types: Root, Composite, Leaf, and Action Nodes. (**Priority: M**)
* **REQ-MOD-2.0:** The system shall allow the user to connect nodes using directed arrows to capture the sequencing. (**Priority: M**)
* **REQ-MOD-3.0:** The system shall allow the user to modify the name, the weight, and the properties of existing nodes. (**Priority: M**)
* **REQ-MOD-4.0:** The system shall allow the user to delete nodes and connections individually. (**Priority: M**)
* **REQ-MOD-5.0:** The system shall allow the user to modify the description and the tool associated with a step or action node. (**Priority: D**)

#### Module C: Directory and Style Management (DICT)
* **REQ-DICT-1.0:** The application shall allow the user to create custom materials and custom colors. (**Priority: M**)
* **REQ-DICT-2.0:** The system shall allow the user to remove custom colors and materials that are no longer used. (**Priority: D**)
* **REQ-DICT-3.0:** The system shall allow the user to change the color of a component through a visual color selector. (**Priority: D**)

#### Module D: Business Rules and Structural Validation (VAL)
* **REQ-VAL-1.0:** The system shall not allow a connection to originate from a leaf node. (**Priority: D**)
* **REQ-VAL-2.0:** The system shall preserve the root node role and shall not allow it to be transformed into an intermediate node through property modifications. (**Priority: D**)

#### Module E: Navigation and Help (NAV)
* **REQ-NAV-1.0:** The system shall allow the user to zoom in and out of the diagram on the canvas. (**Priority: D**)
* **REQ-NAV-2.0:** The system shall provide a help window explaining the purpose and usage of the different node types. (**Priority: D**)

### 3.3 Non-Functional Requirements
* **REQ-NF-1.0:** The system shall provide a graphical user interface that is easy to use for non-technical users. (**Priority: M**)
* **REQ-NF-2.0:** The system shall display diagrams in a clear and readable manner without visual artifacts. (**Priority: M**)
* **REQ-NF-3.0:** The system shall preserve user data when saving and loading diagrams. (**Priority: M**)
* **REQ-NF-4.0:** The system shall respond to user actions within a reasonable time during normal operation. (**Priority: M**)