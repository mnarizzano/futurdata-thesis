# Futurdata Thesis / Disassembly Flow Diagram Builder

# User Requirements Specification Document (URS)

**VERSION : 1.0**

**Authors**

---

## REVISION HISTORY

| Version | Date       | Authors | Notes                                                           |
| ------- | ---------- | ------- | --------------------------------------------------------------- |
| 1.0     | 2026-05-15 | Ferrando Davide | Initial URS draft for the Futurdata disassembly diagram project |

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

<a name="sp1.1"></a>

### 1.1 Document Scope

The purpose of this document is to define the user requirements for a desktop software tool that allows users to create, edit, save, load, and inspect graphical disassembly diagrams for products such as printers. The tool supports a node-based representation of components, disassembly steps, detailed actions, and directed connections between them.

<a name="sp1.2"></a>

### 1.2 Definitions and Acronyms

| Acronym / Term | Definition                                                    |
| -------------- | ------------------------------------------------------------- |
| URS            | User Requirements Specification                               |
| GUI            | Graphical User Interface                                      |
| DB             | Database                                                      |
| JSON           | JavaScript Object Notation, used for diagram serialization    |
| SDL            | Software Design / Development Layer                           |
| Component      | A physical part or assembly of the product being disassembled |
| Step           | A main disassembly operation in the procedure                 |
| Action         | A detailed operation inside a disassembly step                |
| Connection     | A directed relationship between two diagram elements          |
| Canvas         | The drawing area where the diagram is displayed               |

<a name="sp1.3"></a>

### 1.3 References

* Project source code of the Futurdata disassembly flow diagram builder
* Epson Stylus Photo 810/820/830 service manual (disassembly section and appendix)
* Software Engineering course slides: Introduction, Process Model, Requirements Engineering

<a name="p2"></a>

## 2. System Description

This document outlines the User Requirements Specification for a disassembly flow diagram builder designed to help users model the disassembly of technical products in a graphical way.

<a name="sp2.1"></a>

### 2.1 Context and Motivation

The software is intended to support the creation of structured disassembly diagrams for products such as printers. The user can represent the product as a hierarchy of components and can connect steps and actions to describe how the product is disassembled.

The current software already provides a graphical editor, a palette of shapes, a canvas for diagram construction, a properties panel, and persistence through saved diagram files and a database layer. The project is useful for educational purposes, technical documentation, thesis work, and structured analysis of product disassembly procedures.

<a name="sp2.2"></a>

### 2.2 Project Objectives

The purpose of this tool is to simplify and organize the representation of disassembly procedures in a way that is visually clear and easy to modify. The system shall help the user:

* build a diagram from a product manual,
* represent physical parts and disassembly steps,
* attach detailed actions to each step,
* save and reload diagrams,
* and improve the quality of technical documentation.

The system should also evolve into a more maintainable and well-documented software product through better design, clearer code, testing, and possible restructuring.

<a name="p3"></a>

## 3. Requirements

| Priority | Meaning            |
| -------- | ------------------ |
| M        | Mandatory          |
| D        | Desirable          |
| O        | Optional           |
| E        | Future Enhancement |

<a name="sp3.1"></a>

### 3.1 Stakeholders

* The students developing the project
* The course teacher / evaluator
* Users who need to document or visualize disassembly procedures
* Future developers who will maintain or extend the software
* Technical readers who will use the resulting diagrams for analysis or documentation

<a name="sp3.2"></a>

### 3.2 Functional Requirements

### 3.2.1 Diagram Creation and Editing

| ID   | Description                                                                            	| Priority |
| ---- | ---------------------------------------------------------------------------------------------- | -------- |
| 1.0  | The system should allow the user to create a new empty disassembly diagram             	| M        |
| 2.0  | The system should allow the user to add diagram elements through a graphical palette   	| M        |
| 3.0  | The system should allow the user to place shape elements on a canvas                         	| M        |
| 4.0  | The system should allow the user to move shape elements on the canvas                        	| M        |
| 5.0  | The system should allow the user to select one or more diagram elements                	| M        |
| 6.0  | The system should allow the user to delete diagram elements                            	| M        |
| 7.0  | The system should allow the user to connect elements with directed links               	| M        |
| 8.0  | The system should allow the user to edit the properties of the selected element        	| M        |
| 9.0  | The system should allow the user to undo and redo editing actions                      	| D        |
| 10.0 | The system should allow the user to align and organize elements visually on the canvas 	| D        |
| 11.0 | The system should allow the user to scroll the diagram up and down using the mouse wheel	| D	   |
| 12.0 | The system should allow the user to zoom in and out of the diagram 				| D	   | 

### 3.2.2 Disassembly Modeling

| ID   | Description                                                                                                        | Priority |
| ---- | ------------------------------------------------------------------------------------------------------------------ | -------- |
| 1.0  | The system should allow the user to represent a product as a root component                                        | M        |
| 2.0  | The system should allow the user to represent subassemblies as component nodes                                     | M        |
| 3.0  | The system should allow the user to represent individual parts as leaf nodes                                  	    | M        |
| 4.0  | The system should allow the user to represent major disassembly steps as step nodes                                | M        |
| 5.0  | The system should allow the user to represent detailed actions as action nodes                                     | M        |
| 6.0  | The system should allow the user to organize actions inside a step in a meaningful sequence                        | M        |
| 7.0  | The system should allow the user to model repeated operations such as multiple hooks or screws as separate actions | D        |
| 8.0  | The system should allow the user to attach descriptive text to a step or action                                    | D        |
| 9.0  | The system should allow the user to attach a tool reference to an action                                           | E        |
| 10.0 | The system should allow the user to attach warning or caution notes to steps                                       | E        |

### 3.2.3 Saving, Loading, and Data Handling

| ID  | Description                                                                        | Priority |
| --- | ---------------------------------------------------------------------------------- | -------- |
| 1.0 | The system should allow the user to save a diagram to local storage                | M        |
| 2.0 | The system should allow the user to load a previously saved diagram                | M        |
| 3.0 | The system should allow the user to save a diagram in .json form		   | M	      |
| 4.0 | The system should allow the user to persist diagram data in a reusable format      | M        |
| 5.0 | The system should allow the user to reopen a saved diagram and continue editing it | M        |
| 6.0 | The system should allow the user to export diagram data in a structured form       | D        |
| 7.0 | The system should allow the user to export a diagram as an image                   | E        |

### 3.2.4 Technical Documentation Support

| ID  | Description                                                                                           | Priority |
| --- | ----------------------------------------------------------------------------------------------------- | -------- |
| 1.0 | The system should support the creation of diagrams based on a service manual or disassembly procedure | M        |
| 2.0 | The system should allow the user to reproduce the order of disassembly described in a manual          | M        |
| 3.0 | The system should allow the user to visually document a device's disassembly process                  | M        |
| 4.0 | The system should allow the user to build a diagram that can be used in a thesis or technical report  | D        |
| 5.0 | The system should allow the user to produce clearer documentation than a plain text procedure         | D        |

### 3.2.5 Future Enhancements

| ID  | Description                                                                                 | Priority |
| --- | ------------------------------------------------------------------------------------------- | -------- |
| 1.0 | The system should allow the user to search elements inside a diagram                        | E        |
| 2.0 | The system should allow the user to validate whether the diagram is structurally consistent | E        |
| 3.0 | The system should allow the user to compare two diagram versions                            | E        |
| 4.0 | The system should allow the user to manage multiple product models in the same project      | E        |
| 5.0 | The system should allow the user to generate documentation automatically from the diagram   | E        |

<a name="sp3.3"></a>

### 3.3 Non-Functional Requirements

| ID   | Description                                                                             | Priority |
| ---- | --------------------------------------------------------------------------------------- | -------- |
| 1.0  | The system should be easy to use for a user who is not an expert programmer             | M        |
| 2.0  | The system should display diagrams in a clear and readable form                         | M        |
| 3.0  | The system should respond in a reasonable time when the user edits the diagram          | M        |
| 4.0  | The system should preserve saved data so that diagrams can be reopened later            | M        |
| 5.0  | The system should be maintainable through clear code structure and documentation        | M        |
| 6.0  | The system should be extensible so that new diagram elements can be added in the future | D        |
| 7.0  | The system should be reliable during normal save and load operations                    | M        |
| 8.0  | The system should be suitable for desktop use in a software engineering project         | M        |
| 9.0  | The system should support testing and verification through a well-defined structure     | D        |

---

## 4. Notes

This URS is intentionally written in the same structural style as the example document, but adapted to the Futurdata disassembly flow diagram builder. It separates the system into:

* introduction,
* system description,
* stakeholders,
* functional requirements,
* non-functional requirements.

The priority codes follow the same interpretation as the example document:

* M = Mandatory
* D = Desirable
* O = Optional
* E = Future Enhancement
