# Futurdata Thesis / Disassembly Flow Diagram Builder

# User Requirements Specification Document (URS)

**VERSION : 1.0**

**Authors**  
Rubin Ronchieri Byrd

**REVISION HISTORY**

| Version | Date | Authors | Notes |
| ----------- | ----------- | ----------- | ----------- |
| 1.0 | 2026-06-07 | Rubin Ronchieri Byrd | First complete draft of the Disassembly Wizard URS. |

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
 	3. [Non-Functional Requirements](#sp3.3)



<a name="p1"></a>

## 1. Introduction

This document is the User Requirements Specification for the **Disassembly Wizard**, a new application to be developed within the Futurdata thesis project on Critical Raw Material recovery from end-of-life products. The Wizard builds on the existing Disassembly Flow Diagram Builder: it takes the disassembly model the Builder produces — an AND/OR graph stored as JSON — and turns it into instructions a technician can actually follow to take a product apart, while recording the data needed to decide what to do with each recovered part. This introduction states the document's scope, the terminology used throughout, and the external references the specification relies on.

<a name="sp1.1"></a>

### 1.1 Document Scope

This document specifies the user requirements for the **Disassembly Wizard**, a new application that does not yet exist and is to be designed from scratch (step zero).

The Wizard consumes a disassembly model expressed as a JSON file — the same format produced by the existing **Disassembly Flow Diagram Builder** — and turns it into human-usable disassembly instructions. The model encodes the product as an AND/OR graph of components (Root, Composite, Leaf), composite operations (diamonds) and sequential atomic sub-steps (action circles).

The scope of this URS covers: importing and validating the JSON model, letting the operator choose the desired depth of disassembly at runtime, guiding the operator step-by-step through the disassembly, capturing data during execution (quality grading, optionally measured weight), and producing two outputs — a procedural disassembly guide and a decisional recovery report.

The following are explicitly **out of scope** for this version and are recorded only as future enhancements where relevant: the assembly (reverse) direction, the post-export enrichment workflow ("phase two"), and any modification of the source JSON.

This document describes *what* the Wizard must do from the user's point of view; it does not prescribe implementation, architecture or technology choices beyond constraints required for interoperability with the existing toolchain.

<a name="sp1.2"></a>

### 1.2 Definitions and Acronyms

| Acronym / Term | Definition |
| ------------------------------------- | ----------- |
| URS | User Requirements Specification. |
| Wizard | The Disassembly Wizard application specified by this document. |
| Builder | The existing Disassembly Flow Diagram Builder that produces the input JSON model. |
| AND/OR graph | The graph formalism used to model disassembly, combining alternative and conjunctive decompositions. |
| Root | The top-level component representing the whole product to be disassembled. |
| Composite | An intermediate component that can be further decomposed into other components. |
| Leaf | A terminal component that is not decomposed further in the model. |
| Diamond | A node representing a composite disassembly operation that produces component outputs. |
| Action circle | A node representing a sequential atomic sub-step describing how a diamond's operation is performed. |
| Sub-root | A node (typically a Composite) that the operator decides not to decompose further at runtime, keeping it as a single recoverable/sellable block and pruning the subtree below it. |
| Grading | The quality classification assigned to a component during execution (e.g. Working, Broken) used to decide its destination. |
| Destination | The recovery decision associated with a graded component (e.g. resell, scrap, recover material). |
| CRM | Critical Raw Materials — materials of high economic importance and supply risk, targeted for recovery from end-of-life products. |
| BoM | Bill of Materials — a structured list of the components and their attributes. |
| GUI | Graphical User Interface. |
| Procedural guide | The first Wizard output: ordered, human-readable disassembly instructions. |
| Recovery report | The second Wizard output: the decisional summary of component destinations, gradings and recoverable materials. |

<a name="sp1.3"></a>

### 1.3 References

| Ref | Description |
| ------------------------------------- | ----------- |
| R1 | Disassembly Flow Diagram Builder source repository: `github.com/mnarizzano/futurdata-thesis`. |
| R2 | Phase A "Reverse Engineering" deliverable (`doc1`): problem summary, requirements R1–R22, use-case and findings appendices. |
| R3 | Disassembly model use-case: Bialetti Gioia CF90 capsule espresso machine (mass-balanced JSON model). |
| R4 | JSON model schema implicitly defined by the Builder serializer (`shapes`, `connections`, `metadata`). |

<a name="p2"></a>

## 2. System Description

The Disassembly Wizard is a guided application that transforms a disassembly model into actionable disassembly instructions. It imports a JSON model through its GUI, validates that the model is a well-formed AND/OR graph and reports any problems precisely, then lets the operator choose how deeply the product should be taken apart — from full disassembly down to material level, to keeping selected assemblies whole as recoverable blocks. Once the depth is confirmed, the Wizard guides the operator step-by-step through the procedure in real time, capturing a quality grading (and optionally a measured weight) for each component as it is removed. From the same session it produces two outputs: a procedural disassembly guide (PDF, optionally video) that documents how to take the product apart, and a decisional recovery report that records, for every component, its grading, its destination (resell, scrap, recover material) and its recovery-relevant materials. This section describes the context that motivates the Wizard and the objectives it is expected to meet.

<a name="sp2.1"></a>

### 2.1 Context and Motivation

The recovery of Critical Raw Materials from end-of-life products depends on disassembling those products effectively. The existing Builder lets a modeller describe how a product is taken apart, encoding the decomposition as an AND/OR graph stored in JSON. However, the Builder stops at modelling: it produces a graph, not instructions a technician can follow, and it performs no validation of the model it stores.

The Disassembly Wizard closes this gap. It takes the modelled JSON and makes it actionable: it checks that the model is well formed, lets the operator decide how deeply to disassemble a given unit, walks the operator through the procedure, and records the outcome of each step. Because the same product can be disassembled to different depths depending on the recovery goal (sell a working assembly whole vs. break it down to material level), the Wizard treats the disassembly depth as an explicit runtime decision rather than a fixed property of the model.

For this project the JSON model — not its graphical rendering — is the authoritative reference. The Wizard is therefore specified primarily against the JSON structure and its semantics.

<a name="sp2.2"></a>

### 2.2 Project Objectives

The objectives of the Disassembly Wizard are:

1. **Consume a disassembly model.** Import a JSON model through a GUI and parse it into the internal AND/OR graph representation.
2. **Guarantee model validity before use.** Validate the structure and grammar of the model, report any problems precisely, and let the operator make an informed decision to proceed or fix the model.
3. **Let the operator choose the disassembly depth.** Offer mutually exclusive disassembly-level options (full disassembly, keep main assemblies, manual selection of sub-roots) before generating the guide.
4. **Guide disassembly in real time.** Walk the operator through the steps following the graph order, in execution mode.
5. **Capture recovery-relevant data.** Record a configurable quality grading per component and, where applicable, supporting data needed for the recovery decision.
6. **Produce usable outputs.** Generate a procedural disassembly guide (PDF, and optionally video) and a decisional recovery report.
7. **Support CRM recovery.** Surface the components and materials that matter for Critical Raw Material recovery in the recovery report.

<a name="p3"></a>

## 3. Requirements

| Priority | Meaning |
| --------------- | ----------- |
| M | **Mandatory:** required for the first version; the Wizard has no value without it. |
| D | **Desiderable:** high added value; planned for the first version if time allows. |
| O | **Optional:** useful but expendable; implemented only if spare effort remains. |
| E | **Future Enhancement:** explicitly out of current scope; recorded for a later iteration. |

<a name="sp3.1"></a>
### 3.1 Stakeholders

| Stakeholder | Interest in the system |
| --------------- | ----------- |
| Disassembly operator / recovery technician | Primary user. Executes the guided procedure and records component data during disassembly. |
| Recycler / CRM recovery facility | Consumer of the recovery report; uses destinations and recoverable-material data to plan resell, scrap and material recovery. |
| Modeller | Creates the JSON model with the Builder; provides the Wizard's input and is the recipient of validation feedback. |
| Academic supervisor / Futurdata | Project owner; defines goals and evaluates the deliverable against the CRM-recovery context. |
| Quality reviewer | Reviews and may override the quality gradings that drive the recovery decisions. |

<a name="sp3.2"></a>
### 3.2 Functional Requirements

| ID | Description | Priority |
| --------------- | ----------- | ---------- |
| 1.0 | The Wizard shall let the user select and load a JSON model through the GUI (file picker). | M |
| 1.1 | The Wizard shall parse the loaded JSON into the internal AND/OR graph representation (Root, Composite, Leaf components; diamonds; action circles; connections). | M |
| 1.2 | The Wizard shall treat the input JSON as read-only and never modify the source file. | M |
| 2.0 | The Wizard shall validate the grammar of the model: a single Root, valid node types, and connections consistent with the diamond / action-circle / component roles. | M |
| 2.1 | The Wizard shall detect topological anomalies, including cycles, multiple roots, and orphan (disconnected) nodes. | M |
| 2.2 | The Wizard shall report validation problems as precise, point-by-point warnings that identify exactly which element(s) of the JSON are affected and why. | M |
| 2.3 | The Wizard shall allow the user to proceed despite validation warnings; in that case the responsibility for any resulting incorrect instructions rests with the user. | M |
| 2.4 | The Wizard shall verify mass balance per decomposition (input composite weight equals the sum of extracted leaves plus the reduced composite) and raise a warning where it does not hold. | D |
| 3.0 | Before generating the guide, the Wizard shall let the user choose the disassembly depth via mutually exclusive options: full disassembly, keep main assemblies whole, or manual selection of components to keep united. | M |
| 3.1 | The Wizard shall let the user designate a node as a sub-root, keeping it as a single block and pruning the subtree below it from the generated procedure. | M |
| 3.2 | The Wizard shall request explicit confirmation of the chosen disassembly depth before generating the disassembly guide. | M |
| 4.0 | The Wizard shall guide the operator step-by-step in execution mode, following the order encoded in the graph. | M |
| 4.1 | The Wizard shall track per-step completion progress during execution. | D |
| 5.0 | The Wizard shall let the operator assign a quality grading to each component from a configurable, fixed list of options (e.g. Working, Broken, Refurbishable, Recover material only) — a closed selection, not free text. | M |
| 5.1 | The Wizard shall derive a recovery destination (e.g. resell, scrap, recover material) from the assigned grading. | M |
| 5.2 | The Wizard shall let the operator record the measured (actual) weight of a component during execution, in addition to the nominal weight carried by the JSON. | D |
| 6.0 | The Wizard shall generate a procedural disassembly guide in PDF, exportable and shareable. | M |
| 6.1 | The Wizard shall generate the procedural disassembly guide in video form. | D |
| 7.0 | The Wizard shall generate a decisional recovery report covering, per component, its grading, destination, material and weight, including any sub-roots kept whole. | M |
| 7.1 | The recovery report shall highlight components and materials relevant to Critical Raw Material recovery, with their recoverable weight. | D |
| 7.2 | The recovery report shall provide aggregated recovery summaries (e.g. mass per destination, recovery percentage, weight per material). | D |
| 8.0 | The Wizard shall let the user save and resume a session, preserving the chosen options and the data collected during execution. | D |
| 9.0 | The Wizard shall provide an aggregated summary of the tools required and of any safety notices extracted from the steps. | E |
| 9.1 | The Wizard shall export a structured Bill of Materials (e.g. CSV/JSON) in addition to the human-readable outputs. | E |
| 9.2 | The Wizard shall support a two-step workflow in which a general nominal guide is exported first and real measured details are entered in a later enrichment phase. | E |
| 9.3 | The Wizard shall support localization of the generated guide into multiple languages. | E |

<a name="sp3.3"></a>
### 3.3 Non-Functional Requirements

| ID | Description | Priority |
| --------------- | ----------- | ---------- |
| 1.0 | The GUI shall be usable by a disassembly operator who is not a programmer. | M |
| 1.1 | Validation messages and warnings shall be understandable and shall localize each issue to the specific point of the JSON it refers to. | M |
| 2.0 | The Wizard shall be interoperable with the JSON schema produced by the Disassembly Flow Diagram Builder. | M |
| 2.1 | The Wizard shall not perform any destructive operation on the input model. | M |
| 3.0 | The Wizard shall run on the same platforms as the Builder (Python / Tk environment). | D |
| 3.1 | The validation engine shall be extensible to accommodate new model-checking rules. | D |
| 4.0 | The Wizard shall load and validate a typical model within interactive response times. | O |
