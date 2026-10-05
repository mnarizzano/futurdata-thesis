"""Catalog/product operations exposed to views through a controller boundary.

Views depend on this controller API instead of importing the persistence layer.
This keeps repository details on the Model side of MVC.
"""


class CatalogController:
    def __init__(self, repository):
        self._repository = repository

    def get_all_colors(self):
        return self._repository.get_all_colors()

    def get_color(self, color_id):
        return self._repository.get_color(color_id)

    def get_all_material_categories(self):
        return self._repository.get_all_material_categories()

    def get_all_materials(self):
        return self._repository.get_all_materials()

    def get_all_tools(self):
        return self._repository.get_all_tools()

    def get_subcategories_by_category(self, category_id):
        return self._repository.get_subcategories_by_category(category_id)

    def get_types_by_category(self, category_id, subcategory_id=None):
        return self._repository.get_types_by_category(category_id, subcategory_id)

    def get_component(self, component_id):
        return self._repository.get_component(component_id)

    def get_component_fields(self, component_kind):
        return self._repository.get_component_fields(component_kind)

    def get_action(self, action_id):
        return self._repository.get_action(action_id)

    def get_action_fields(self):
        return self._repository.get_action_fields()

    def get_step(self, step_id):
        return self._repository.get_step(step_id)

    def get_step_fields(self):
        return self._repository.get_step_fields()

    def get_all_products(self):
        return self._repository.get_all_products()

    def get_product(self, product_id):
        return self._repository.get_product(product_id)

    def create_material_category(self, name):
        return self._repository.create_material_category(name)

    def create_material_subcategory(self, category_id, name):
        return self._repository.create_material_subcategory(category_id, name)

    def create_material_type(self, category_id, name, subcategory_id=None):
        return self._repository.create_material_type(category_id, name, subcategory_id)

    def resolve_material_selection(self, category_id, subcategory_id=None, type_id=None):
        return self._repository.resolve_material_selection(category_id, subcategory_id, type_id)
