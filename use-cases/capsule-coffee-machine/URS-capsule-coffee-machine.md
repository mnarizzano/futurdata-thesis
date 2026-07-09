# Futurdata Thesis / Disassembly Flow Diagram Builder

# User Requirements Specification Document (URS)

**VERSION : 1.0**

**Authors**  
Nicolas Rodriguez

**REVISION HISTORY**

| Version | Date       | Authors          | Notes |
| ------- | ---------- | ---------------- | ----- |
| 1.0     | 01/06/2026 | Nicolas Rodriguez |       |

# Table of Contents

1. [Introduction](#p1)
	1. [Document Scope](#sp1.1)
	2. [Definitions and Acronyms](#sp1.2)
	3. [References](#sp1.3)
2. [System Description](#p2)
	1. [Context and Motivation](#sp2.1)
	2. [Project Objectives](#sp2.2)
3. [Requirements](#p3)
	1. [Stakeholders](#sp3.1)
	2. [Functional Requirements](#sp3.2)
	3. [Non-functional Requirements](#sp3.3)


<a name="p1"></a>

## 1. Introduction

<a name="sp1.1"></a>

### 1.1 Document Scope

The objective of this document is to establish the user requirements derived from testing the Disassembly Flow Diagram Builder using the capsule coffee machine as a use case. This use case covers a multi-phase disassembly process including conditional branching (lever position check, deep-clean decision) and tool-assisted steps, allowing us to validate the software against a realistic and moderately complex scenario.

<a name="sp1.2"></a>

### 1.2 Definitions and Acronyms

| Acronym        | Definition                                                                  |
| -------------- | --------------------------------------------------------------------------- |
| URS            | User Requirements Specification                                             |
| Root node      | Top-level component node representing the complete product                  |
| Composite node | Intermediate component node that groups sub-components or action sequences  |
| Leaf node      | Terminal component node representing an individual, indivisible part        |
| Action node    | Node describing a disassembly step or physical operation                    |
| Diamond node   | Decision/condition node that branches the flow based on a YES/NO condition  |
| T20 Torx       | Torx-head screwdriver bit, size T20, required in Phase 2 of the disassembly |

<a name="sp1.3"></a>

### 1.3 References

- Video reference for the disassembly process: https://www.youtube.com/watch?v=5E5DRJqs9JU
- Use case diagram: `capsule-coffee-machine.json`
- Disassembly steps description: `steps.md`

<a name="p2"></a>

## 2. System Description

<a name="sp2.1"></a>

### 2.1 Context and Motivation

The Disassembly Flow Diagram Builder allows users to create structured graphs representing the disassembly process of physical products. Nodes represent either components (root, composite, or leaf) or operations (actions, decisions), and arrows capture the sequencing and dependencies between them.

The capsule coffee machine was selected as a use case because its disassembly involves both sequential steps and conditional logic — specifically, a lever-position check that may require retrying before proceeding, and a deep-clean decision that determines whether the user continues to a further disassembly phase. This makes it a suitable case for validating conditional branching and loop-back flows within the diagram builder.

<a name="sp2.2"></a>

### 2.2 Project Objectives

The main purpose of this use case is to test the software against a realistic, multi-phase disassembly scenario and to identify any bugs or missing features that arise when working with decision nodes, back-edges (retry loops), and tool annotations.

<a name="p3"></a>

## 3. Requirements

| Priority | Meaning                    |
| -------- | -------------------------- |
| M        | **Mandatory:**             |
| D        | **Desirable:**             |
| O        | **Optional:**              |
| E        | **Future Enhancement:**    |

<a name="sp3.1"></a>

### 3.1 Stakeholders

Technicians, repair engineers, and students who need to plan or document the disassembly of consumer appliances such as capsule coffee machines.

<a name="sp3.2"></a>

### 3.2 Functional Requirements

| ID   | Description                                                                                              | Priority |
| ---- | -------------------------------------------------------------------------------------------------------- | -------- |
| 1.0  | The system should allow the user to create a root component node representing the complete product        | M        |
| 2.0  | The system should allow the user to create composite component nodes to group sub-components             | M        |
| 3.0  | The system should allow the user to create leaf component nodes for individual, indivisible parts        | M        |
| 4.0  | The system should allow the user to create action nodes describing disassembly steps                     | M        |
| 5.0  | The system should allow the user to create decision (diamond) nodes for conditional branching            | M        |
| 6.0  | The system should allow the user to connect nodes with directed arrows                                   | M        |
| 7.0  | The system should allow the user to label arrows (e.g. YES, NO, retry)                                   | M        |
| 8.0  | The system should allow back-edges (arrows pointing to earlier nodes) to represent retry loops           | M        |
| 9.0  | The system should allow the user to annotate action nodes with the required tool (e.g. T20 Torx)        | M        |
| 10.0 | The system should allow the user to delete nodes individually                                            | M        |
| 11.0 | The system should allow the user to clear the entire graph at once                                       | M        |
| 12.0 | The system should allow the user to export the graph in JSON format                                      | M        |
| 13.0 | The system should allow the user to load an existing diagram from a JSON file                            | M        |
| 14.0 | The system should allow the user to edit node content after creation                                     | M        |
| 15.0 | The system should allow the user to save changes to the diagram                                          | M        |
| 16.0 | The system should allow the user to undo recent actions                                                  | D        |
| 17.0 | The system should allow the user to duplicate existing nodes                                             | D        |
| 18.0 | The system should allow the user to assign a colour to a component node                                  | D        |
| 19.0 | The system should allow the user to assign a material to a component node                                | D        |
| 20.0 | The system should allow the user to add an image URL to an action node                                   | D        |
| 21.0 | The system should allow the user to zoom in and out on the canvas                                        | O        |
| 22.0 | The system should allow the user to consult the documentation of the software                            | O        |
| 23.0 | The system should allow the user to export the graph in PDF format                                       | E        |
| 24.0 | The system should allow the user to export the graph in PNG/JPEG format                                  | E        |
| 25.0 | The system should allow the user to filter nodes by colour, material, or tool using a search bar         | E        |
| 26.0 | The system should allow multiple users to edit a graph simultaneously                                    | E        |

<a name="sp3.3"></a>

### 3.3 Non-functional Requirements

| ID  | Description                                                                              | Priority |
| --- | ---------------------------------------------------------------------------------------- | -------- |
| 1.0 | The system should present an understandable interface suitable for non-expert users      | M        |
| 2.0 | The system should respond to user interactions within a reasonable time                  | M        |
| 3.0 | The system should correctly render diagrams with back-edges without visual artifacts     | M        |
| 4.0 | The exported JSON should faithfully represent the full graph structure, including loops  | M        |
