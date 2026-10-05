"""Shared positioning for modal catalog windows."""


def center_on_workspace(dialog, parent):
    workspace = parent.winfo_toplevel()
    while workspace.master is not None:
        workspace = workspace.master.winfo_toplevel()
    dialog.update_idletasks()
    workspace.update_idletasks()
    x = workspace.winfo_rootx() + (workspace.winfo_width() - dialog.winfo_width()) // 2
    y = workspace.winfo_rooty() + (workspace.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
