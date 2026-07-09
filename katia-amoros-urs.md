# Futurdata Thesis / Disassembly Flow Diagram Builder

# User Requirements Specification Document (URS)

**VERSION : X.X**

**Authors**  
XXXX
YYYY

**REVISION HISTORY**

| Version    | Date         | Authors      | Notes        |
| ----------- | ----------- | -----------  | ----------- |
| 1.0         | 8/06/2026   | Katia Amorós |               |

# Table of Contents

1. [Introduction](#p1)
	1. [Document Scope](#sp1.1)
	2. [Definitios and Acronym](#sp1.2) 
	3. [References](#sp1.3)
2. [System Description](#p2)
	1. [Context and Motivation](#sp2.1)
	2. [Project Objectives](#sp2.2)
3. [Requirement](#p3)
 	1. [Stakeholders](#sp3.1)
 	2. [Functional Requirements](#sp3.2)
 	3. [Non-Functional Requirements](#sp3.3)
  
  

<a name="p1"></a>

## 1. Introduction

<a name="sp1.1"></a>

### 1.1 Document Scope

The scope of this document is to describe the user requirments about a graph program for a coffee maker. The program provides the options of representing dissasembly steps and how the nodes are connected between them with, root, composit components, and specific actions

<a name="sp1.2"></a>

### 1.2 Definitios and Acronym


| Acronym				| Definition | 
| ------------------------------------- | ----------- | 
| XXXX                                  | XXXX |

<a name="sp1.3"></a>

### 1.3 References 
Course slides from software engineering

<a name="p2"></a>

## 2. System Description


<a name="sp2.15"></a>

### 2.1 Context and Motivation

The purpose is to provide a software that enables creating dissasembly diagrams for products as coffee machines, in a way that a user is able to describe the dissasembly of a porduct as a graph with steps and actions. The steps and actions can be connected to each other with arrows.
<a name="sp2.2"></a>

### 2.2 Project Obectives 

The objective is to make the dissasembly graph representation intuitive and that the user can modify it easily

<a name="p3"></a>

## 3. Requirements

| Priorità | Significato | 
| --------------- | ----------- | 
| M | **Mandatory:**   |
| D | **Desiderable:** |
| O | **Optional:**    |
| E | **future Enhancement:** |

<a name="sp3.1"></a>
### 3.1 Stakeholders
Students who have to develop the project
Future users that will have to modify, create or analyze a dissasembly diagram
<a name="sp3.2"></a>
### 3.2 Functional Requirements 

| ID | Description | Priority |
| ----| ------------------------------------------------------------------------------------------------------|-| 
| 1.0 |  The system shall allow the user to delete each node when necessary                                   |M|
| 2.0 |  The system shall allow the user to add a root compmonent id to each created component                |M|
| 3.0 |  The system shall allow the user to save the diagram in local storage                                 |M|
| 4.0 |  The system shall allow the user to obtain the json file of the graph                                 |M|
| 5.0 |  The system shall allow the user to edit the json file                                                |M|
| 6.0 |  The system shall allow the user to associate a tool to diamond step                                  |M|
| 7.0 |  The system shall include the fields of brand and model for the associated machine                    |M|
| 8.0 |  The system shall allow the user to redo and undo steps with the keys ctrl z and ctrl y               |M|
| 9.0 |  The system shall allow the user to numerate each component that is created                           |M|
| 10.0 |  The system shall allow the user to move up and down with the scroll wheel                            |M|
| 11.0 | The system shall allow the user to reopen the document from local storage  |M|
| 12.0 |  The name of the materials shall be displayed in alphabetical order                                   |D|
| 13.0 |  The system shall allow the user to add personalized fields of color/ material/name/weight/ measure unit to the components|D|
| 14.0 |  The system shall provide the option to add a field to define the type of node of composite component and root component |D|
| 15.0 |  The system shall allow the user to select an area of the graph with the mouse                       |E|
| 16.0 |  The system shall allow the user to export the document in pdf or jpg format                         |E|
| 17.0 |  The system shall allow the user to save the document with the name they want and for it to be saved |E|
| 18.0 |  The system shall allow the user to add or remove materials, once created                            |E|
| 19.0 |  The system shall allow the user to distinguish between leaf component and composite component       |E|

<a name="sp3.3"></a>
### 3.2 Non-Functional Requirements 
 
| ID | Description | Priority |
| --------------- | ----------- | ---------- | 
| 1.0 | The system should ensure a user-friendly experience for non-programmers  |M|
