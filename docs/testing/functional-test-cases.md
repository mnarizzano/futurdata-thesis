# Functional Testing Document: Disassembly Flow Diagram Builder

## 1. Document Control
| Information | Details |
| :--- | :--- |
| **Project Name** | Disassembly Flow Diagram Builder |
| **Document Version** | 1.0 |
| **Prepared By** | Nicolas Rodriguez, María Begines Tirado, Katia Amorós Cristea, Lucía Bezares García, Davide Ferrando, Arbaz Khan |
| **Date Created** | 06-07-2026 |
| **Reviewed By** | Massimo Narizzano |

---

## 2. Introduction
### 2.1 Purpose
The purpose of this document is to define the functional testing approach, scope and specific test cases for the Disassembly Flow Diagram Builder. It ensures that the software meets the specified business requirements and functions as expected before deployment.

### 2.2 Target Audience
This document is intended for Engineers, Developers and Project Managers involved in Disassembly Flow Diagram Builder.

---

## 3. Test Scenarios & Test Cases

### Module: Diagram Editor

| Test Case ID | Test Scenario | Steps to Execute | Expected Result |
| :--- | :--- | :--- | :--- |
| **TC-001** | Create a new disassembly diagram | Click on file and then on new | A new empty diagram is created |
| **TC-002** | Add elements from a shape palette and place them on the canvas | 1. Go to the shape palette placed on the left. 2. Click on any of the elements | A new element is placed on the canvas |
| **TC-003** | Drag/move shapes/groups of nodes on the canvas | 1. Select the shape or group with ctrl and click. 2. Move it where wanted | The selected shape has been placed where the user wanted |
| **TC-004** | Select one or more elements (multi-select via modifier keys, select-all, or rubber-band area selection) | 1. Select the shape or group with ctrl and click onto the wanted shapes | The shape / group contour lines are blue, indicating that they are selected |
| **TC-005** | Delete elements/nodes and their connections | 1. Position the mouse on the Delete button on top of the canvas. 2. Click on it, or right-click the selected element and click on delete | The selected shape has been deleted |
| **TC-006** | Clear the entire diagram at once | 1. Position the mouse on 'Edit'. 2. Click on 'Clear canvas' | The canvas has been cleared |
| **TC-007** | Connect elements between them | 1. Place two components onto the diagram. 2. Click on arrow button. 3. Click on one of the elements. 4. Drag the arrow to the other element and click again | An arrow connects two or more elements |
| **TC-008** | Change properties of any element | 1. Select the element. 2. Go to its properties panel. 3. Change the desired field. 4. Click on Apply Changes button | The wanted properties have been modified by the user |
| **TC-009** | Duplicate selected nodes/shapes | 1. Select the element. 2. Press right button of mouse on it. 3. Select 'duplicate' | The selected nodes / shapes appear duplicated on the canvas |
| **TC-010** | Undo and redo editing actions (Ctrl+Z / Ctrl+Y) | 1. Press ctrl + z to undo the last action executed, or press ctrl + y to redo an action | The user has undone or redone a wanted action |
| **TC-011** | Scroll the canvas (scrollbars, mouse wheel) | 1. Select the scrollbar on the right side or use the mouse wheel. 2. Drag it up / down while selected | The canvas goes up / down |
| **TC-012** | Zoom in on the diagram | 1. Press ctrl + + | The canvas looks bigger |
| **TC-013** | Zoom out of the diagram | 1. Press ctrl + - | The canvas looks smaller |
| **TC-014** | Represent product components with distinct node types: root, composite/intermediate, and leaf | 1. Go to the shape palette on the left. 2. Select the type of node wanted to implement | The wanted node appears on the canvas |
| **TC-015** | Represent operations with step nodes and detailed action nodes and organize actions within a step in an ordered sequence | 1. Go to the shape palette on the left. 2. Select a Diamond Step. 3. Select an Action Circle. 4. Go to the properties panel of the Action Circle to change the step order | You have a Diamond Step to represent steps and an Action Circle to represent actions, and the diagram is organized |
| **TC-016** | Assign and edit component attributes: name, colour, material, weight, and measurement unit | 1. Select the element. 2. Go to its properties panel. 3. Change the desired field. 4. Click on Apply Changes button | The selected component attributes have been updated |
| **TC-017** | Add custom colors | 1. Go to 'Edit'. 2. Click on 'Add color'. 3. Choose a hex code or change the values of R G B. 4. Assign a name. 5. Click on save | A new color has been added |
| **TC-018** | Add custom materials | 1. Go to 'Edit'. 2. Click on 'Add material'. 3. Write its name. 4. Write its scientific name. 5. Choose its color. 6. Click on 'save' | A new material has been added |
| **TC-019** | Add custom tools | 1. Go to 'Edit'. 2. Click on 'Add tool'. 3. Write its name. 4. Write its category. 5. Click on 'save' | A new tool has been added |
| **TC-020** | Manage custom colors | 1. Go to 'Edit'. 2. Click on 'Manage colors'. 3. Click on the wanted color. 4. Click on 'delete'. 5. Click on 'yes' | The wanted color has been deleted |
| **TC-021** | Manage custom materials | 1. Go to 'Edit'. 2. Click on 'Manage materials'. 3. Click on the wanted material. 4. Click on 'delete'. 5. Click on 'yes' | The wanted material has been deleted |
| **TC-022** | Associate a tool with a diamond step | 1. Select the diamond step. 2. Go to its properties panel. 3. Go to tool field. 4. Select the wanted tool. 5. Click on apply changes | The diamond step has the wanted tool associated |
| **TC-023** | Attach descriptive text and warning/caution notes to steps and actions | 1. Click on a step/action. 2. Go to the properties panel on the right. 3. Write on the 'Description' field. 4. Click on 'Apply Changes' | A description has been assigned to the selected step/action |
| **TC-024** | Attach and display an image (file or URL) on a node | 1. Select the element. 2. Go to its properties panel. 3. Paste the URL or file on Image Path field. 4. Click on Apply Changes button | The image is attached to the node and displayed |
| **TC-025** | Save a diagram and its changes to local storage | 1. Go to 'File'. 2. Click on 'Save' or ctrl + s | The changes have been saved |
| **TC-026** | Load/reopen a previously saved diagram and continue editing it | 1. Open the diagram editor. 2. Go to 'File'. 3. Click on 'Load product'. 4. Select the wanted project | The saved diagram appears on the canvas |
| **TC-027** | Save/export the diagram in JSON format and view/edit the raw JSON directly | 1. Go to 'File'. 2. Click on 'export'. 3. Select format JSON | The diagram is saved as a JSON file |
