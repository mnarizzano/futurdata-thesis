import tkinter as tk
from tkinter import ttk, colorchooser

class AddColorDialog(tk.Toplevel):
    """
    A modal dialog window that allows users to create and register a new color entry.
    
    Provides explicit entry fields for a color name, Hex color code and split 
    RGB integer components, while additionally embedding the native OS system 
    color picker as a quick convenience helper.
    """

    def __init__(self, parent, controller):
        """
        Initializes the dialog window, constructs the UI layout and blocks 
        interaction with the parent window until closed.

        Args:
            parent (tk.Misc): The parent widget/window hosting this dialog.
            controller (any): The application controller handling data persistence.
        """
        super().__init__(parent)
        self.transient(parent)
        self.title("Add New Color")
        self.controller = controller
        self.result = None

        self.name_var = tk.StringVar()
        self.hex_var = tk.StringVar()
        self.rgb_r_var = tk.StringVar()
        self.rgb_g_var = tk.StringVar()
        self.rgb_b_var = tk.StringVar()

        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Color Name:").grid(row=0, column=0, sticky="w", pady=5)
        name_entry = ttk.Entry(frame, textvariable=self.name_var, width=30)
        name_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5)

        ttk.Label(frame, text="Hex Code:").grid(row=1, column=0, sticky="w", pady=5)
        hex_entry = ttk.Entry(frame, textvariable=self.hex_var, width=20)
        hex_entry.grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Button(frame, text="Choose...", command=self.choose_color).grid(row=1, column=2, padx=(5, 0))

        rgb_frame = ttk.LabelFrame(frame, text="RGB")
        rgb_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10, padx=5)
        
        ttk.Label(rgb_frame, text="R:").pack(side="left", padx=5)
        ttk.Entry(rgb_frame, textvariable=self.rgb_r_var, width=5).pack(side="left", padx=5)
        ttk.Label(rgb_frame, text="G:").pack(side="left", padx=5)
        ttk.Entry(rgb_frame, textvariable=self.rgb_g_var, width=5).pack(side="left", padx=5)
        ttk.Label(rgb_frame, text="B:").pack(side="left", padx=5)
        ttk.Entry(rgb_frame, textvariable=self.rgb_b_var, width=5).pack(side="left", padx=5)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(button_frame, text="Save", command=self.on_save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="left")

        self.grab_set()
        self.wait_window(self)

    def choose_color(self):
        """
        Launches the native OS color selection dialog palette.
        
        If a color choice is accepted, it parses the composite tuple, 
        extracts the Hex code, converts float-based RGB coordinates into integers,
        and injects them back into the window's bound Tkinter variables.
        """
        color_code = colorchooser.askcolor(title="Choose color")
        if color_code and color_code[0] and color_code[1]:
            rgb, hex_code = color_code
            r, g, b = map(int, rgb)
            self.hex_var.set(hex_code)
            self.rgb_r_var.set(str(r))
            self.rgb_g_var.set(str(g))
            self.rgb_b_var.set(str(b))

    def on_save(self):
        """
        Validates compiled form inputs, translates text channels into domain integers
        and delegates object persistence requests directly to the application controller.
        """
        name = self.name_var.get()
        hex_code = self.hex_var.get()
        r = self.rgb_r_var.get()
        g = self.rgb_g_var.get()
        b = self.rgb_b_var.get()

        if not all([name, hex_code, r, g, b]):
            # In a real app, you would show a proper error message
            print("Error: All fields are required.")
            return

        try:
            self.controller.add_new_color(name, hex_code, int(r), int(g), int(b))
            self.destroy()
        except Exception as e:
            # In a real app, you would show a proper error message
            print(f"Error saving color: {e}")
