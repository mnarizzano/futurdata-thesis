import tkinter as tk
from unittest.mock import MagicMock, patch
import pytest

from src.main.repositories.json_repository import JsonRepository
from src.main.controllers.catalog_controller import CatalogController
from src.main.controllers.app_controller import AppController
from src.main.views.main_window import MainWindow
from src.main.views.properties_panel import PropertiesPanel
from src.main.views.add_material_dialog import AddMaterialDialog, _SimpleNameDialog
from src.main.views.add_color_dialog import AddColorDialog
from src.main.views.add_tool_dialog import AddToolDialog
from src.main.views.manage_colors_dialog import ManageColorsDialog
from src.main.views.manage_materials_dialog import ManageMaterialsDialog
from src.main.models import ComponentBox, DiamondStep, ActionCircle, Diagram


@pytest.fixture(scope='module')
def workspace():
    root = tk.Tk()
    root.geometry('900x650+120+90')
    root.update()
    yield root
    root.destroy()


@pytest.fixture
def app(tmp_path, workspace):
    root = workspace
    repository = JsonRepository(str(tmp_path / 'catalog.json'))
    controller = AppController.__new__(AppController)
    controller.repository = repository
    controller.catalog = CatalogController(repository)
    panel = PropertiesPanel(root, data_provider=controller.catalog)
    view = MainWindow.__new__(MainWindow)
    view.root, view.properties_panel = root, panel
    view.set_status = MagicMock()
    controller.view = view
    yield controller, panel, root
    for child in root.winfo_children():
        child.destroy()
    root.update()


def leaf():
    shape = ComponentBox(200, 200)
    shape.properties['node_type'] = 'Leaf'
    return shape


def test_current_future_nodes_and_persistent_catalogs(app):
    controller, panel, _ = app
    panel.load_shape(leaf())
    name = panel.dynamic_fields['name']
    name.delete('1.0', 'end')
    name.insert('1.0', 'Unapplied component name')
    material_widget = panel.dynamic_fields['material_id']
    color_widget = panel.dynamic_fields['color_id']
    material_id = controller.add_new_material('Carbon Fiber')
    color_id = controller.add_new_color('Dark Navy', '#001133', 0, 17, 51)
    assert panel.dynamic_fields['name'] is name
    assert name.get('1.0', 'end-1c') == 'Unapplied component name'
    assert 'Carbon Fiber' in material_widget['values']
    assert 'Dark Navy' in color_widget['values']
    material_widget.set('Carbon Fiber')
    panel._on_material_category_changed(material_widget)
    color_widget.set('Dark Navy')
    controller.add_new_material('Another Material')
    assert material_widget.get() == 'Carbon Fiber'
    assert color_widget.get() == 'Dark Navy'
    proposed = panel._collect_proposed_properties()
    assert proposed['material_id'] == material_id
    assert proposed['color_id'] == color_id
    panel.load_shape(leaf())
    assert 'Carbon Fiber' in panel.dynamic_fields['material_id']['values']
    assert 'Dark Navy' in panel.dynamic_fields['color_id']['values']
    action = DiamondStep(200, 200)
    panel.load_shape(action)
    tool_widget = panel.dynamic_fields['tool_id']
    tool_id = controller.add_new_tool('Torx T25', 'Driver')
    assert panel.dynamic_fields['tool_id'] is tool_widget
    assert str(tool_widget['state']) == 'readonly'
    assert 'Torx T25' in tool_widget['values']
    tool_widget.set('Torx T25')
    controller.add_new_tool('Torx T30', 'Driver')
    assert tool_widget.get() == 'Torx T25'
    proposed = panel._collect_proposed_properties()
    assert proposed['tool_id'] == tool_id
    from src.main.utils.commands import EditShapePropertiesCommand
    EditShapePropertiesCommand(action, {}, proposed).execute()
    root_id = controller.repository.create_product('Test product')
    root_shape = ComponentBox(100, 100)
    root_shape.properties.update(node_type='Root', db_id=root_id)
    controller.diagram = Diagram()
    controller.diagram.diagram_id = controller.repository.get_product(root_id)['diagram_id']
    controller.diagram.shapes = [root_shape, action]
    with patch.object(controller.repository, 'create_tool', wraps=controller.repository.create_tool) as create:
        controller._persist_shape_properties(action)
        create.assert_not_called()
    assert controller.repository.get_action(action.db_action_id)['tool_id'] == tool_id
    for shape_type in ('diamond', 'action', 'component'):
        shape = controller._create_shape_instance(shape_type, 300, 300)
        if isinstance(shape, ComponentBox):
            shape.properties['node_type'] = 'Leaf'
        panel.load_shape(shape)
        if isinstance(shape, DiamondStep):
            assert 'Torx T25' in panel.dynamic_fields['tool_id']['values']
        elif isinstance(shape, ComponentBox):
            assert 'Carbon Fiber' in panel.dynamic_fields['material_id']['values']
        else:
            assert isinstance(shape, ActionCircle)
            assert 'tool_id' not in panel.dynamic_fields  # Steps do not own tools in the schema.
    reopened = JsonRepository(str(controller.repository.file_path))
    assert reopened.get_material(material_id)['name'] == 'Carbon Fiber'
    assert reopened.get_color(color_id)['name'] == 'Dark Navy'
    assert reopened.get_tool(tool_id)['name'] == 'Torx T25'


def test_named_materials_with_same_hierarchy_keep_exact_ids(app):
    controller, panel, _ = app
    category = controller.add_new_material_category('Test Composites')
    subcategory = controller.add_new_material_subcategory(category, 'Fiber')
    material_type = controller.add_new_material_type(category, 'Carbon', subcategory)
    first = controller.add_new_material('Carbon A', category, subcategory, material_type)
    second = controller.add_new_material('Carbon B', category, subcategory, material_type)
    panel.load_shape(leaf())
    widget = panel.dynamic_fields['material_id']
    for name, key in [('Carbon A', first), ('Carbon B', second)]:
        widget.set(name)
        panel._on_material_category_changed(widget)
        panel.refresh()
        assert panel._get_widget_value(widget) == key
        assert widget.get() == name
        assert widget.subcategory_var.get() == 'Fiber'
        assert widget.type_var.get() == 'Carbon'


def test_open_management_and_material_dialogs_refresh(app):
    controller, panel, root = app
    panel.load_shape(leaf())
    with patch.object(tk.Toplevel, 'wait_window'), patch.object(tk.Toplevel, 'grab_set'):
        colors = ManageColorsDialog(root, controller)
        materials = ManageMaterialsDialog(root, controller)
        editor = AddMaterialDialog(root, controller)
        editor.name_var.set('Draft material')
        controller.add_new_color('Test Teal', '#008080', 0, 128, 128)
        controller.add_new_material('Custom Composite')
        category = controller.add_new_material_category('New Category')
        assert 'Test Teal (#008080)' in colors.listbox.get(0, 'end')
        assert 'Custom Composite' in materials.listbox.get(0, 'end')
        assert 'New Category' in editor.category_combo['values']
        assert 'New Category' in panel.dynamic_fields['material_id']['values']
        assert editor.name_var.get() == 'Draft material'
        editor.category_var.set('New Category')
        editor._on_category_change()
        controller.add_new_material_subcategory(category, 'New Subcategory')
        assert 'New Subcategory' in editor.subcategory_combo['values']


@pytest.mark.parametrize('dialog_type', [AddColorDialog, AddToolDialog, AddMaterialDialog,
                                       ManageColorsDialog, ManageMaterialsDialog])
def test_catalog_dialogs_center_on_workspace(app, dialog_type):
    controller, _, root = app
    with patch.object(tk.Toplevel, 'wait_window'), patch.object(tk.Toplevel, 'grab_set'):
        dialog = dialog_type(root, controller)
        root.update()
        assert abs((dialog.winfo_x() + dialog.winfo_width() / 2) -
                   (root.winfo_rootx() + root.winfo_width() / 2)) <= 2
        assert abs((dialog.winfo_y() + dialog.winfo_height() / 2) -
                   (root.winfo_rooty() + root.winfo_height() / 2)) <= 2
        nested = _SimpleNameDialog(dialog, 'New Category', 'Name', lambda value: None)
        root.update()
        assert abs((nested.winfo_x() + nested.winfo_width() / 2) -
                   (root.winfo_rootx() + root.winfo_width() / 2)) <= 2


def test_material_hierarchy_still_works_after_named_selection(app):
    controller, panel, _ = app
    category = controller.add_new_material_category('Regression Category')
    subcategory = controller.add_new_material_subcategory(category, 'Regression Subcategory')
    first_type = controller.add_new_material_type(category, 'First Type', subcategory)
    second_type = controller.add_new_material_type(category, 'Second Type', subcategory)
    first = controller.add_new_material('Named First', category, subcategory, first_type)
    second = controller.add_new_material('Named Second', category, subcategory, second_type)
    panel.load_shape(leaf())
    widget = panel.dynamic_fields['material_id']
    widget.set('Named First')
    panel._on_material_category_changed(widget)
    assert panel._get_widget_value(widget) == first
    widget.type_var.set('Second Type')
    panel._clear_saved_material(widget)
    assert widget.get() == 'Regression Category'
    assert panel._get_widget_value(widget) == second
    panel.refresh()
    assert widget.type_var.get() == 'Second Type'
    assert panel._get_widget_value(widget) == second
    widget.set('')
    panel._on_material_category_changed(widget)
    assert panel._get_widget_value(widget) is None


def test_properties_material_labels_are_static_and_consistent(app):
    controller, panel, root = app
    panel.load_shape(leaf())
    widget = panel.dynamic_fields['material_id']
    labels = []
    for container, expected in [(widget.master, 'Category:'),
                                (widget.subcategory_frame, 'Sub-Category:'),
                                (widget.type_frame, 'Type:')]:
        label = next(child for child in container.winfo_children()
                     if child.winfo_class() == 'TLabel')
        assert label.cget('text') == expected
        labels.append(label)
    for key in ('font', 'style', 'padding', 'anchor'):
        assert len({str(label.cget(key)) for label in labels}) == 1
    for key in ('sticky', 'padx', 'pady'):
        assert len({str(label.grid_info()[key]) for label in labels}) == 1


def test_all_properties_selectors_ignore_wheel(app):
    from tkinter import ttk
    controller, panel, root = app
    panel.pack(fill='both', expand=True)
    def selectors(parent):
        for child in parent.winfo_children():
            if isinstance(child, ttk.Combobox):
                yield child
            yield from selectors(child)
    for shape in (leaf(), DiamondStep(100, 100)):
        panel.load_shape(shape)
        root.update()
        for widget in selectors(panel):
            widget.configure(values=('First', 'Second', 'Third'))
            widget.set('Second')
            before = panel.viewport.yview()
            for event, options in [('<MouseWheel>', {'delta': 120}),
                                   ('<MouseWheel>', {'delta': -120}),
                                   ('<Button-4>', {}), ('<Button-5>', {})]:
                widget.event_generate(event, **options)
                root.update()
                assert widget.get() == 'Second'
                assert panel.viewport.yview() == before


def test_open_properties_dropdown_ignores_wheel_but_accepts_click_and_keyboard(app):
    controller, panel, root = app
    panel.pack(fill='both', expand=True)
    widget = panel._create_combobox(panel, values=('First', 'Second', 'Third'), state='readonly')
    widget.grid(row=2, column=0)
    widget.set('Second')
    root.update()
    widget.tk.call('ttk::combobox::Post', str(widget))
    root.update()
    popup = widget.tk.call('ttk::combobox::PopdownWindow', str(widget))
    listing = str(popup) + '.f.l'
    selected = widget.tk.call(listing, 'curselection')
    for event, options in [('<MouseWheel>', ('-delta', 120)),
                           ('<MouseWheel>', ('-delta', -120)),
                           ('<Button-4>', ()), ('<Button-5>', ())]:
        widget.tk.call('event', 'generate', listing, event, *options)
        root.update()
        assert widget.get() == 'Second'
        assert widget.tk.call(listing, 'curselection') == selected
    x, y, width, height = map(int, widget.tk.call(listing, 'bbox', 2))
    for event in ('<Motion>', '<ButtonPress-1>', '<ButtonRelease-1>'):
        widget.tk.call('event', 'generate', listing, event, '-x', x + 2, '-y', y + height // 2)
    root.update()
    assert widget.get() == 'Third'
    widget.tk.call('ttk::combobox::Post', str(widget))
    root.update()
    widget.tk.call('focus', '-force', listing)
    widget.tk.call('event', 'generate', listing, '<KeyPress-Up>')
    widget.tk.call('event', 'generate', listing, '<KeyPress-Return>')
    root.update()
    assert widget.get() == 'Second'


def configure_property_saving(controller, panel):
    from src.main.utils.commands import CommandHistory
    controller.diagram = Diagram()
    controller.command_history = CommandHistory()
    controller.current_product_id = None
    controller._update_view = MagicMock()
    controller.view.show_error = MagicMock()
    panel.on_apply_callback = controller.apply_properties
    root = ComponentBox(100, 100)
    root.properties.update(node_type='Root', name='Machine')
    controller.diagram.add_shape(root)
    return root


def test_blank_leaf_catalogs_save_and_clear_existing_values(app):
    controller, panel, _ = app
    root = configure_property_saving(controller, panel)
    shape = leaf()
    controller.diagram.add_shape(shape)
    color = controller.add_new_color('Regression Blue', '#0011ff', 0, 17, 255)
    material = controller.add_new_material('Regression Material')
    panel.load_shape(shape)
    panel._on_apply()
    controller.view.show_error.assert_not_called()
    assert controller.save_diagram()
    row = controller.repository.get_component(shape.properties['db_id'])
    assert row['color_id'] is None and row['material_id'] is None
    shape.properties.update(color_id=color, material_id=material)
    panel.load_shape(shape)
    panel.dynamic_fields['color_id'].set('')
    widget = panel.dynamic_fields['material_id']
    widget.set('')
    panel._on_material_category_changed(widget)
    panel._on_apply()
    controller.view.show_error.assert_not_called()
    assert controller.save_diagram()
    row = controller.repository.get_component(shape.properties['db_id'])
    assert row['color_id'] is None and row['material_id'] is None
    assert len(controller.repository.get_all_products()) == 1


def test_legacy_blank_leaf_ids_are_normalized_at_persistence(app):
    controller, panel, _ = app
    configure_property_saving(controller, panel)
    shape = leaf()
    shape.properties.update(color_id='', material_id='  ')
    controller.diagram.add_shape(shape)
    controller._persist_shape_properties(shape)
    row = controller.repository.get_component(shape.properties['db_id'])
    assert row['color_id'] is None and row['material_id'] is None


@pytest.mark.parametrize('operation', ['component_root', 'product', 'duplicate'])
def test_duplicate_root_is_reported_in_window_before_adding(app, operation):
    controller, panel, _ = app
    root = configure_property_saving(controller, panel)
    if operation == 'duplicate':
        controller._duplicate_shape(root)
    else:
        controller.add_shape(operation)
    controller.view.show_error.assert_called_once()
    assert 'already has a Root Component' in controller.view.show_error.call_args.args[1]
    assert controller.diagram.shapes == [root]
    assert not controller.command_history.can_undo()


def test_invalid_project_save_is_visible_and_keeps_unsaved_edit(app):
    controller, panel, _ = app
    root = configure_property_saving(controller, panel)
    # A second root from a pre-existing project must also report save failure.
    controller._persist_shape_properties(root)
    second = ComponentBox(300, 300)
    second.properties.update(node_type='Root', name='Original name')
    controller.diagram.add_shape(second)
    panel.load_shape(second)
    name = panel.dynamic_fields['name']
    name.delete('1.0', 'end')
    name.insert('1.0', 'Attempted edit')
    panel._on_apply()
    assert not controller.save_diagram()
    controller.view.show_error.assert_called_once()
    assert 'root' in controller.view.show_error.call_args.args[1].lower()
    assert second.properties['name'] == 'Attempted edit'
    assert controller.command_history.can_undo()
    assert controller.diagram.modified
    assert len(controller.repository.get_all_products()) == 1


def test_apply_legacy_tool_keeps_new_catalog_id(app):
    controller, panel, _ = app
    configure_property_saving(controller, panel)
    shape = DiamondStep(200, 200)
    shape.tools = 'Legacy custom driver'
    controller.diagram.add_shape(shape)
    panel.load_shape(shape)
    panel._on_apply()
    controller.view.show_error.assert_not_called()
    assert controller.save_diagram()
    assert shape.tool_id is not None
    assert controller.repository.get_action(shape.db_action_id)['tool_id'] == shape.tool_id


@pytest.mark.parametrize('kind', ['color', 'material', 'tool'])
def test_properties_add_new_opens_existing_dialog_selects_result_and_preserves_draft(app, kind):
    controller, panel, root = app
    panel.on_add_catalog = controller.show_add_catalog_dialog
    shape = DiamondStep(100, 100) if kind == 'tool' else leaf()
    panel.load_shape(shape)
    widget = panel.dynamic_fields[kind + '_id']
    assert '' not in widget['values']
    assert widget['values'][-1] == 'Add new...'
    name = panel.dynamic_fields['name']
    name.delete('1.0', 'end')
    name.insert('1.0', 'Keep my draft')
    previous = widget.get()
    dialog_class = {'color': 'AddColorDialog', 'material': 'AddMaterialDialog', 'tool': 'AddToolDialog'}[kind]
    def create_dialog(*args):
        assert widget.get() == previous
        if kind == 'color':
            key = controller.add_new_color('New dropdown color', '#123456', 18, 52, 86)
        elif kind == 'material':
            key = controller.add_new_material('New dropdown material')
        else:
            key = controller.add_new_tool('New dropdown tool', 'Driver')
        return type('Result', (), {'result': key})()
    with patch('src.main.views.add_' + kind + '_dialog.' + dialog_class, side_effect=create_dialog) as dialog:
        widget.set(widget['values'][-1])
        widget.event_generate('<<ComboboxSelected>>')
        root.update()
        dialog.assert_called_once_with(root, controller)
    assert widget.get() == 'New dropdown ' + kind
    assert panel._get_widget_value(widget) is not None
    assert name.get('1.0', 'end-1c') == 'Keep my draft'
    chosen = widget.get()
    with patch('src.main.views.add_' + kind + '_dialog.' + dialog_class) as dialog:
        dialog.return_value.result = None
        widget.set(widget['values'][-1])
        widget.event_generate('<<ComboboxSelected>>')
        root.update()
    assert widget.get() == chosen
    assert '' not in widget['values']
    assert widget['values'][-1] == 'Add new...'


def test_manage_tools_refresh_delete_and_protect_used_tools(app):
    from src.main.views.manage_tools_dialog import ManageToolsDialog
    controller, panel, root = app
    controller.diagram = Diagram()
    panel.load_shape(DiamondStep(100, 100))
    key = controller.add_new_tool('Tool to remove', 'Driver')
    with patch.object(tk.Toplevel, 'wait_window'), patch.object(tk.Toplevel, 'grab_set'):
        dialog = ManageToolsDialog(root, controller)
        assert any('Tool to remove' in name for name in dialog.listbox.get(0, 'end'))
        second = controller.add_new_tool('Another tool', 'Driver')
        assert any('Another tool' in name for name in dialog.listbox.get(0, 'end'))
        index = next(i for i, name in enumerate(dialog.listbox.get(0, 'end')) if 'Tool to remove' in name)
        dialog.listbox.selection_set(index)
        with patch('tkinter.messagebox.askyesno', return_value=True), patch('tkinter.messagebox.showinfo'):
            dialog.on_delete()
        assert controller.repository.get_tool(key) is None
        assert 'Tool to remove' not in panel.dynamic_fields['tool_id']['values']
        shape = DiamondStep(0, 0)
        shape.tool_id = second
        controller.diagram.add_shape(shape)
        with pytest.raises(ValueError, match='assigned to an action'):
            controller.delete_tool(second)
        controller.diagram.shapes.clear()
        root_id = controller.repository.create_product('Tool test')
        controller.repository.create_action('Used action', tool_id=second,
                                            diagram_id=controller.repository.get_product(root_id)['diagram_id'])
        with pytest.raises(ValueError, match='assigned to an action'):
            controller.delete_tool(second)
