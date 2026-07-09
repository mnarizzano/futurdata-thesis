# Futurdata Thesis / Disassembly Flow Diagram Builder

# User Requirements Specification Document (URS)

**VERSION : 1.0**

**Authors**  
XXXX
YYYY

**REVISION HISTORY**

| Version    | Date        | Authors      | Notes        |
| ----------- | ----------- | ----------- | ----------- |
| 1.0 | 07/06/2026 | María Begines Tirado |  | 

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
 	3. [Non-functional Requirements](#sp3.3)
  
  

<a name="p1"></a>

## 1. Introduction

<a name="sp1.1"></a>

### 1.1 Document Scope

The objective of this document is to establish the users requirements for the Disassembly Flow Diagram Builder, an app created for designing graphs of the disassembly of machines such us printers or coffee machines. For that purpose, we have tested the software with multiple use cases.

<a name="sp1.2"></a>

### 1.2 Definitios and Acronyms


| Acronym				| Definition | 
| ------------------------------------- | ----------- | 
| XXXX                                  | XXXX |

<a name="sp1.3"></a>

### 1.3 References 

<a name="p2"></a>

## 2. System Description
<a name="sp2.15"></a>

### 2.1 Context and Motivation
As stated before, the objective of this software is to help the users create graphs to facilitate the comprehension of the dissasembly process of a product. In this way, users can employ different types of nodes, arrows to connect them and add practical information of the product and the process such us image URLs, materials, colours and tools used.
<a name="sp2.2"></a>

### 2.2 Project Obectives 
The main purpose of this project is to test the aforementioned software as well as trying to enhance it by resolving bugs and implementing new useful features. 

<a name="p3"></a>

## 3. Requirements

| Priority | Meaning | 
| ------ | ----------- | 
| M | **Mandatory:**   |
| D | **Desiderable:** |
| O | **Optional:**    |
| E | **future Enhancement:** |

<a name="sp3.1"></a>
### 3.1 Stakeholders
People who need to create or analyze disassembly diagrams.

<a name="sp3.2"></a>
### 3.2 Functional Requirements 

| ID   | Description                                                                       | Priority |
| ---- | ------------------------------------------------------------------------------------------ |-| 
| 1.0  | The system should allow the user to create a new disassembly graph                         |M|
| 2.0  | The system should allow the user to connect the nodes with arrows                          |M|
| 3.0  | The system should allow the user to delete nodes individually                              |M|
| 4.0  | The system should allow the user to clear the entire graph at once                         |M|
| 5.0  | The system should allow the user to export the graph in json format                        |M|
| 6.0  | The system should allow the user to load already-existing diagrams                         |M|
| 7.0  | The system should allow the user to edit their diagrams                                    |M|
| 8.0  | The system should allow the user to save their changes                                     |M|
| 9.0  | The system should allow the user to undo their actions                                     |D|
| 10.0 | The system should allow the user to duplicate existing nodes                               |D|
| 11.0 | The system should allow the user to change the colour of a component                       |D|
| 12.0 | The system should allow the user to change the material of a component                     |D|
| 13.0 | The system should allow the user to add a tool to an action                                |D|
| 14.0 | The system should allow the user to consult the documentation of the software              |O|
| 15.0 | The system should allow the user to zoom in/out                                            |E|
| 16.0 | The system should allow the user to copy and paste more than one element at once           |E|
| 17.0 | The system should allow the user to export the graph in pdf format                         |E|
| 18.0 | The system should allow the user to export the graph in png/jpeg format                    |E|
| 19.0 | The system should allow the user to filter nodes by colour/material/tool with a search bar |E|
| 20.0 | The system should allow multiple users to edit a graph at the same time                    |E|



<a name="sp3.3"></a>
### 3.2 Non-functional Requirements 
 
| ID  | Description                                            | Priority |
| --- | --------------------------------------------------------------- |-| 
| 1.0 | The system should have an understandable interface for the user |M|
| 2.0 | The system should have a reasonable time response               |M|