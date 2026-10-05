import tkinter as tk

from .controllers import AppController
from .views import MainWindow


def main():
    root = tk.Tk()

    controller = AppController()
    main_window = MainWindow(root, controller)
    controller.set_view(main_window)
    migration = controller.repository.get_migration_summary()
    if migration["unresolved"]:
        count = sum(migration["unresolved"].values())
        root.after_idle(lambda: main_window.show_info(
            "Repository migration needs review",
            f"{count} legacy records have unresolved ownership and were preserved separately. "
            "They have not been assigned to an arbitrary product.\n\n"
            f"Details: migration_report and legacy_unresolved in {migration['repository_path']}\n"
            "Version 1 backups are stored beside that file."
        ))

    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()
