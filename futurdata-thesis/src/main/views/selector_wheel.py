"""Shared wheel policy for reference-data comboboxes and their native popups."""

from tkinter import ttk

_EVENTS = ("<MouseWheel>", "<Shift-MouseWheel>", "<Button-4>", "<Button-5>",
           "<Shift-Button-4>", "<Shift-Button-5>")


def create_combobox(parent, **options):
    widget = ttk.Combobox(parent, **options)
    for event in _EVENTS:
        widget.tk.call("bind", str(widget), event, "break")

    def protect_dropdown():
        popup = widget.tk.call("ttk::combobox::PopdownWindow", str(widget))
        pending = [popup]
        while pending:
            path = pending.pop()
            if widget.tk.call("winfo", "class", path) == "Listbox":
                scripts = {
                    "<MouseWheel>": f"{path} yview scroll [expr {{%D > 0 ? -3 : 3}}] units; break",
                    "<Button-4>": f"{path} yview scroll -3 units; break",
                    "<Button-5>": f"{path} yview scroll 3 units; break",
                }
                for event in _EVENTS:
                    script = scripts.get(event, scripts.get(event.replace("Shift-", ""), "break"))
                    widget.tk.call("bind", path, event, script)
            pending.extend(widget.tk.splitlist(widget.tk.call("winfo", "children", path)))

    widget.configure(postcommand=protect_dropdown)
    return widget
