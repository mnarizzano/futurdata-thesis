# HTML + JavaScript Disassembly Wizard Exporter

A Python-based exporter that converts a Loader Intermediate Representation (IR) JSON file into a self-contained interactive HTML disassembly guide.

The exporter is **product-independent**. The included Nespresso Essenza Mini guide is only an example. The same exporter can generate a guide for a washing machine, air fryer, laptop, printer, or another product, provided that the Loader produces an IR JSON file with the expected schema.

---
## Purpose

The purpose of this exporter is to transform the Loader Intermediate Representation (IR) into an interactive HTML disassembly guide.

The generated guide can be used by operators or technicians to follow a structured disassembly workflow, evaluate recovered components, and generate a final recovery report.

---

## 1. System Architecture

```text
Builder JSON
     ↓
Loader
     ↓
IR JSON
     ↓
HTML + JavaScript Exporter
     ↓
Interactive wizard.html
```

The exporter does **not** parse the original Builder model. It reads only the normalized IR JSON produced by the Loader.

---

## 2. Main Features

- Product welcome screen with product image and basic information
- Start button that opens the disassembly workflow
- Step-by-step wizard navigation
- Previous and Next buttons
- Sidebar with all disassembly steps
- Progress bar and current-step indicator
- Action instructions and required tools
- Main action image for each step
- Recovered output-component cards
- Quality grading for every recovered component:
  - Excellent
  - Working
  - Damaged
  - Scrap
- Optional measured-weight input
- Automatic session saving in the browser using `localStorage`
- Final recovery summary generated from the user's grades and measurements
- Automatic destination suggestion based on the selected grade
- Print / Save as PDF support
- Restart workflow option
- Responsive layout for desktop and smaller screens
- Automatic copying of referenced local images into the output folder
- Fallback display when an image is missing

---

## 3. Requirements

No external Python packages are required.
The exporter relies only on the Python Standard Library.

---

## 4. Project Structure

```text
html-js-exporter/
│
├── main.py
├── README.md
│
├── data/
│   └── ir_output.json
│
├── images/
│   └── product and step images
│
├── exporters/
│   ├── html_exporter.py
│   ├── renderer.py
│   ├── scripts.py
│   └── styles.py
│
└── output/
    ├── wizard.html
    └── images/
```

### File responsibilities

- `main.py` — starts the export process and defines the input and output paths.
- `html_exporter.py` — loads the IR JSON, copies local images, and builds the final HTML page.
- `renderer.py` — generates the main HTML sections.
- `styles.py` — contains the CSS used by the generated guide.
- `scripts.py` — contains the JavaScript for navigation, grading, session storage, summary generation, and printing.
- `data/ir_output.json` — input file produced by the Loader.
- `images/` — source images referenced by the IR JSON.
- `output/wizard.html` — generated interactive guide.

---

## 5. How to Run the Exporter

### Step 1 — Open the project folder

In PowerShell or Command Prompt:

```powershell
cd path\to\html-js-exporter
```

Example:

```powershell
cd D:\Unige\Software Engineering\html-js-exporter
```

### Step 2 — Add the Loader IR file

Place the Loader output in:

```text
data/ir_output.json
```

The default `main.py` configuration is:

```python
exporter.export(
    ir_path="data/ir_output.json",
    output_path="output/wizard.html"
)
```

### Step 3 — Add the referenced images

Place local images in the project `images/` folder.

Example IR image reference:

```json
"image": {
  "path": "images/water_tank.jpg",
  "is_url": false
}
```

The physical file must therefore exist at:

```text
images/water_tank.jpg
```

During export, the file is copied automatically to:

```text
output/images/water_tank.jpg
```

### Step 4 — Generate the HTML guide

Run:

```powershell
python main.py
```

Expected terminal output:

```text
HTML wizard exported successfully to: output\wizard.html
```

### Step 5 — Open the generated guide

Open:

```text
output/wizard.html
```

The guide runs locally in the browser and does not require a web server.

---

## 6. User Workflow

### 1. Welcome screen

The user first sees:

- Product name
- Product image
- Number of steps
- Number of recoverable components
- Product weight
- `Start disassembly` button

### 2. Disassembly steps

After pressing Start, the guide displays:

- Current step number
- Operation title
- Required tools
- Main action image
- Instructions
- Remaining assembly after the current step
- Components removed during the step

### 3. Component assessment

For every recovered component, the user can select:

- `Excellent` — component is in excellent condition and reusable
- `Working` — component functions correctly but may show normal wear
- `Damaged` — component is damaged or partially functional
- `Scrap` — component is unusable and should be recycled or disposed of

The user may also enter the measured component weight.

### 4. Final recovery summary

After the last step, the user can open the final summary. It includes:

- Component image
- Component name
- Material
- Nominal weight
- Measured weight
- Selected grade
- Suggested destination

The summary can be printed or saved as a PDF through the browser print dialog.

---
## 7. Using the Exporter with Another Product

The exporter is not limited to the included Nespresso example.

To generate a guide for another product:

1. Create the product model in the Builder.
2. Process the Builder JSON using the Loader.
3. Replace the existing:

```text
data/ir_output.json
```

with the new Loader-generated IR JSON.

4. Replace or add the corresponding images inside the `images/` folder.

5. Run:

```powershell
python main.py
```

The exporter will automatically generate a new interactive HTML guide.

No changes to the Python source code, HTML templates, CSS, or JavaScript are required, provided that the Loader generates a valid IR JSON following the expected schema.

---


## 8. Expected IR Data

The exporter reads these main sections:

```json
{
  "schema_version": "1.0",
  "product": {},
  "depth": {},
  "steps": [],
  "warnings": [],
  "bill_of_materials": []
}
```

Each step can contain:

```json
{
  "index": 1,
  "operation": "Remove external components",
  "actions": [],
  "outputs": [],
  "continues_as": {},
  "tools_required": []
}
```

Important fields:

- `product.name` — displayed product name
- `product.image.path` — welcome-screen product image
- `steps[].operation` — step title
- `steps[].actions[].text` — instruction text
- `steps[].actions[].image.path` — action image
- `steps[].outputs[]` — components removed during the step
- `steps[].continues_as` — remaining assembly after the step
- `bill_of_materials[]` — all recovered components used in the final report

---

## 9. Local and URL Images

### Local image

```json
"image": {
  "path": "images/component.jpg",
  "is_url": false
}
```

The exporter copies this image to the output folder.

### Online image

```json
"image": {
  "path": "https://example.com/component.jpg",
  "is_url": true
}
```

Online images are referenced directly and are not copied.

For a completely offline guide, use local images.

---

## 10. Browser Session Storage

Grades, measured weights, and wizard progress are saved automatically in the browser using `localStorage`.

This means that refreshing the page does not immediately delete the user's assessment data.

The `Restart` button clears the saved session and returns to the welcome screen.

> Session data is saved only in the current browser and device. It is not uploaded to a server.

---

## 11. Print or Save the Final Report as PDF

1. Complete the steps.
2. Open the final summary.
3. Click `Print / Save PDF`.
4. Select `Save as PDF` in the browser print dialog.
5. Choose the destination and save the file.

---

## 12. Troubleshooting

### The HTML file is not generated

Make sure that:

- Python is installed
- The command is executed from the project root
- `data/ir_output.json` exists
- The JSON syntax is valid

### An image is not displayed

Check that:

- The path in the IR JSON exactly matches the filename
- The file exists in the project folder
- Capitalization is correct
- Windows path separators are not used inside JSON image paths

Correct:

```text
images/water_tank.jpg
```

Avoid:

```text
images\water_tank.jpg
```

### Changes are not visible

Regenerate the guide:

```powershell
python main.py
```

Then refresh the browser with:

```text
Ctrl + F5
```

### The wrong product is displayed

Check the input file selected in `main.py`:

```python
ir_path="data/ir_output.json"
```

### Old grades are still visible

Click `Restart`, or clear the browser's local site data for the HTML file.

### Browser shows an old version

If the browser still displays an older version of the guide:

- Regenerate the HTML guide.
- Refresh the browser using `Ctrl + F5`.
- If necessary, clear the browser cache.

---

## 13. Export Process Summary

```text
1. Create or obtain a product model
2. Run the Loader
3. Obtain the IR JSON
4. Add the referenced images
5. Replace the IR JSON in data/ir_output.json
6. Run python main.py
7. Open output/wizard.html
8. Follow the disassembly steps
9. Grade and measure recovered components
10. View and print the final recovery report
```

---

## 14. Current Example

The repository currently includes a complete Nespresso Essenza Mini example used to demonstrate the exporter.

The example contains:

- 9 disassembly steps
- 17 recovered components
- Local product, action, component, and remaining-assembly images
- Interactive grading and measured-weight fields
- Final recovery report

This example validates the exporter, but the exporter itself remains generic and reusable for other products.
