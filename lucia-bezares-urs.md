# Futurdata Thesis / Disassembly Flow Diagram Builder

# User Requirements Specification Document (URS)

**VERSION : 1.0**

**Authors**  
Lucia Bezares Garcia

**REVISION HISTORY**

| Version    | Date        | Authors      | Notes        |
| ----------- | ----------- | ----------- | ----------- |
| 1.0 | 08-06-2026 | Lucia Bezares Garcia |  |

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
The purpose of this document is to define the user requirements for the Disassembly Flow Diagram Builder, a desktop application designed to create and manage graphical representations of product disassembly processes. The software enables users to model components, disassembly steps, and their relationships through an intuitive diagram-based interface, providing a clear and structured view of the disassembly workflow.


<a name="sp1.2"></a>

### 1.2 Definitions and Acronyms


| Acronym				| Definition | 
| ------------------------------------- | ----------- | 
| XXXX                                  | XXXX |

<a name="sp1.3"></a>

### 1.3 References 

<a name="p2"></a>

## 2. System Description
<a name="sp2.15"></a>

### 2.1 Context and Motivation
The purpose of this software is to help users create graphical representations of product disassembly processes. Instead of relying only on text descriptions, users can build diagrams that show the different components of a product, the steps required to disassemble it, and the relationships between those steps.

The Disassembly Flow Diagram Builder provides a visual and organized way to document disassembly procedures. Users can create and connect different types of nodes, add information related to components and actions, and include additional details such as images, materials, colours, or tools. This makes the disassembly process easier to understand, analyse, and communicate.


<a name="sp2.2"></a>

### 2.2 Project Obectives
The objective of this project is to improve the existing Disassembly Flow Diagram Builder application. This includes testing the current software, fixing identified issues, and adding new features that can enhance the user experience.

The tool should allow users to create and manage graphical disassembly diagrams in an easy and organized way. At the same time, the project aims to improve the quality, maintainability, and documentation of the software to support its future development.

<a name="p3"></a>

## 3. Requirements

| Priority | Meaning | 
| --------------- | ----------- | 
| M | **Mandatory:**   |
| D | **Desiderable:** |
| O | **Optional:**    |
| E | **future Enhancement:** |

<a name="sp3.1"></a>
### 3.1 Stakeholders
- End users who create and edit disassembly diagrams.
- Students and researchers using the tool for academic purposes.
- Developers responsible for maintaining and extending the application.
- Futurdata, as the organization providing the software.

<a name="sp3.2"></a>
### 3.2 Functional Requirements 

| ID | Description | Priority |
| --------------- | ----------- | ---------- | 

| 1.0  | The system shall allow the user to create a new disassembly diagram.| M |
| 2.0  | The system shall allow the user to create graphs using different node types.| M |
| 3.0  | The system shall allow the user to connect nodes using directed arrows.| M |
| 4.0  | The system shall allow the user to edit the properties of existing nodes.| M |
| 5.0  | The system shall allow the user to delete nodes and connections.| M |
| 6.0  | The system shall allow the user to clear an entire diagram.| D |
| 7.0  | The system shall allow the user to zoom in and out of the diagram.| D |
| 8.0  | The system shall allow the user to modify the name of a component.| M |
| 9.0  | The system shall allow the user to modify the material of a component.| M |
| 10.0 | The system shall allow the user to modify the colour of a component.| M |
| 11.0 | The system shall allow the user to modify the weight of a component.| M |
| 12.0 | The system shall allow the user to create custom colours.| M |
| 13.0 | The system shall allow the user to create custom materials.| M |
| 14.0 | The system shall allow the user to remove custom colours and materials.| D |
| 15.0 | The system shall allow the user to change the colour of a component through a visual colour selector.| D |
| 16.0 | The system shall allow the user to modify the properties of leaf nodes.| M |
| 17.0 | The system shall allow the user to modify the properties of composite component nodes.| M |
| 18.0 | The system shall allow the user to modify the description associated with a step node.| D |
| 19.0 | The system shall allow the user to modify the tool associated with a step node.| D |
| 20.0 | The system shall allow the user to modify the name of an action node.| D |
| 21.0 | The system shall allow the user to attach an image to a node.| D |
| 22.0 | The system shall allow the user to display images attached to nodes.| D |
| 23.0 | The system shall allow the user to save a diagram. | M |
| 24.0 | The system shall allow the user to load a previously saved diagram.| M |
| 25.0 | The system shall allow the user to export diagram data in JSON format.| M |
| 26.0 | The system shall not allow a connection to originate from a leaf node.| D |
| 27.0 | The system shall preserve the root node role and shall not allow it to be transformed into an intermediate node through property modifications. | D |
| 28.0 | The system shall provide a help window explaining the purpose and usage of the different node types.| D |
| 29.0 | The system shall provide documentation describing the main features of the application.| O |


<a name="sp3.3"></a>
### 3.2 Non-Functional Requirements 
 
| ID | Description | Priority |
| --------------- | ----------- | ---------- | 
| 1.0 | The system shall provide a graphical user interface that is easy to use for non-technical users. | M |
| 2.0 | The system shall display diagrams in a clear and readable manner. | M |
| 3.0 | The system shall preserve user data when saving and loading diagrams. | M |
| 4.0 | The system shall respond to user actions within a reasonable time during normal operation. | M |