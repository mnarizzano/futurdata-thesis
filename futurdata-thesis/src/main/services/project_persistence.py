"""Explicit JSON save use case and storage ID assignment.

No UI is consulted and no name-based merge is performed. The repository owns
transactions and durable IDs; this service assigns returned IDs to document nodes.
"""
import copy
from datetime import datetime
from typing import Optional
from ..models import ComponentBox, ActionCircle, DiamondStep, ArrowShape


class ProjectPersistence:
    def __init__(self, repository, diagram, product_id=None):
        self.repository = repository
        self.diagram = diagram
        self.current_product_id = product_id

    def _ensure_component_id(self, shape: ComponentBox) -> Optional[int]:
        """Return the component's storage id, creating the storage row if needed."""
        db_id = shape.properties.get("db_id")
        if db_id:
            row = self.repository.get_component(int(db_id))
            if isinstance(row, dict) and row.get("diagram_id") != self.diagram.diagram_id:
                raise ValueError("Component belongs to another diagram")
            if row:
                return int(db_id)
            shape.properties["db_id"] = None

        node_type = str(shape.properties.get("node_type", "Intermediate")).strip() or "Intermediate"
        node_type = node_type.capitalize()

        name = str(shape.properties.get("name") or shape.text or f"{node_type} Component").strip()
        color_id = shape.properties.get("color_id") or None
        material_id = shape.properties.get("material_id") or None
        weight_val = shape.properties.get("weight")
        try:
            weight = float(weight_val) if str(weight_val).strip() else None
        except (TypeError, ValueError):
            weight = None
        weight_unit = shape.properties.get("weight_unit") or "g"

        if node_type == "Root":
            comp_id = self.repository.create_component(
                name=name, color_id=color_id, material_id=material_id,
                weight=weight, weight_unit=weight_unit, node_type="Root",
                diagram_id=self.diagram.diagram_id,
            )
        else:
            root_component_id = self._get_root_component_id()
            if root_component_id is None:
                raise ValueError("Add a Root Component first so Leaf/Composite can link to it")
            comp_id = self.repository.create_component(
                name=name,
                product_id=root_component_id,
                color_id=color_id,
                material_id=material_id,
                weight=weight,
                weight_unit=weight_unit,
                node_type=node_type,
            )

        shape.properties["db_id"] = comp_id
        if node_type == "Root":
            self.current_product_id = comp_id
        return comp_id

    def _get_root_component_id(self) -> Optional[int]:
        """Return the storage id of the diagram's root component, if any."""
        for shape in self.diagram.shapes:
            if isinstance(shape, ComponentBox):
                node_type = str(shape.properties.get("node_type", "")).strip().lower()
                if node_type == "root":
                    return self._ensure_component_id(shape)
        return None

    def _ensure_step_id(self, step_shape: ActionCircle, input_shape: Optional[ComponentBox] = None) -> Optional[int]:
        """Return the step's storage id, creating the storage row if needed."""
        step_id = getattr(step_shape, "db_step_id", None)
        if input_shape is None:
            input_shape = self._resolve_input_shape_for_step(step_shape)

        if step_id:
            row = self.repository.get_step(int(step_id))
            if isinstance(row, dict) and row.get("diagram_id") != self.diagram.diagram_id:
                raise ValueError("Step belongs to another diagram")
            if row:
                if input_shape is not None:
                    self.repository.update_step(int(step_id), component_id=self._ensure_component_id(input_shape))
                return int(step_id)
            step_shape.db_step_id = None

        if input_shape is None:
            for shape in self.diagram.shapes:
                if isinstance(shape, ComponentBox) and str(shape.properties.get("node_type", "")).strip().lower() == "root":
                    input_shape = shape
                    break

        if input_shape is None:
            raise ValueError("Step needs an input component (connect a component to the circle first)")

        component_id = self._ensure_component_id(input_shape)
        step_order = self.repository.get_next_step_order(component_id)
        title = str(step_shape.text or "Disassembly Step").strip()
        description = str(step_shape.step_description or "").strip()
        image_path = str(step_shape.image_path or "").strip()

        step_id = self.repository.create_step(
            component_id=component_id,
            step_order=step_order,
            description=description,
            image_path=image_path,
            action_id=None,
            title=title,
        )
        # Keep display text/title aligned.
        step_shape.text = title
        step_shape.db_step_id = step_id
        return step_id

    def _resolve_input_shape_for_step(self, step_shape: ActionCircle) -> Optional[ComponentBox]:
        """Find the component feeding into a step, falling back to the root."""
        for conn in self.diagram.connections:
            if conn.to_shape == step_shape and isinstance(conn.from_shape, ComponentBox):
                return conn.from_shape

        for arrow in self.diagram.shapes:
            if isinstance(arrow, ArrowShape) and arrow.to_shape == step_shape and isinstance(arrow.from_shape, ComponentBox):
                return arrow.from_shape
        for shape in self.diagram.shapes:
            if isinstance(shape, ComponentBox) and str(shape.properties.get("node_type", "")).strip().lower() == "root":
                return shape
        return None

    def _ensure_action_id(self, action_shape: DiamondStep) -> Optional[int]:
        """Return the action's storage id, creating the storage row if needed."""
        action_id = getattr(action_shape, "db_action_id", None)
        if action_id:
            row = self.repository.get_action(int(action_id))
            if isinstance(row, dict) and row.get("diagram_id") != self.diagram.diagram_id:
                raise ValueError("Action belongs to another diagram")
            if row:
                return int(action_id)
            action_shape.db_action_id = None

        action_name = str(action_shape.name or action_shape.text or "Action").strip()
        tool_val = str(action_shape.tools or "").strip()
        root_id = self._get_root_component_id()
        if root_id is None:
            raise ValueError("Add a root component before saving actions")
        action_id = self.repository.create_action(name=action_name, description="", tool_id=None, diagram_id=self.diagram.diagram_id)
        action_shape.db_action_id = action_id
        if action_shape.name:
            action_shape.text = action_shape.name
        else:
            action_shape.name = action_name
            action_shape.text = action_name
        if tool_val:
            action_shape.tools = tool_val
        return action_id

    def save(self):
        """Atomically persist one owned diagram and its complete editable graph."""
        roots = [s for s in self.diagram.shapes if isinstance(s, ComponentBox) and str(s.properties.get("node_type", "")).lower() == "root"]
        if not self.diagram.shapes:
            if self.current_product_id:
                # Explicit Save of an empty canvas removes only this owned project.
                self.repository.delete_product(self.current_product_id)
                self.current_product_id = None
            self.diagram.modified = False
            return
        if len(roots) != 1:
            raise ValueError("Saving requires exactly one root component")
        # Roll back assigned model IDs as well as repository data after failure.
        states = [(shape, dict(shape.__dict__)) for shape in self.diagram.shapes]
        for shape, state in states:
            if isinstance(shape, ComponentBox):
                state["properties"] = copy.deepcopy(shape.properties)
        old_product = self.current_product_id
        try:
            with self.repository.transaction():
                for shape in roots + [s for s in self.diagram.shapes if s not in roots]:
                    self._persist_shape_properties(shape)
                snapshot = self.diagram.to_dict()
                snapshot["metadata"]["modified"] = datetime.now().isoformat()
                self.repository.save_diagram_snapshot(self.diagram.diagram_id, snapshot)
        except Exception:
            self.current_product_id = old_product
            for shape, state in states:
                shape.__dict__.clear()
                shape.__dict__.update(state)
            raise
        self.diagram.metadata["modified"] = snapshot["metadata"]["modified"]
        self.diagram.modified = False

    def _persist_shape_properties(self, shape):
        """Persist edited shape properties through the JSON repository."""
        if isinstance(shape, ComponentBox):
            # Older forms/projects may contain empty strings for optional IDs.
            for field in ('color_id', 'material_id'):
                value = shape.properties.get(field)
                if isinstance(value, str) and not value.strip():
                    shape.properties[field] = None
            component_id = self._ensure_component_id(shape)
            updates = dict(shape.properties)
            for internal_key in ("db_id", "root_component_id", "diagram_id", "_material_category_id", "_material_subcategory_id", "_material_type_id"):
                updates.pop(internal_key, None)
            self.repository.update_component(int(component_id), **updates)
            shape.properties["db_id"] = int(component_id)
            return

        if isinstance(shape, ActionCircle):
            step_id = self._ensure_step_id(shape)
            self.repository.update_step(
                int(step_id), title=str(shape.text or "").strip(),
                description=str(shape.step_description or "").strip(),
                image_path=str(shape.image_path or "").strip(),
            )
            shape.db_step_id = int(step_id)
            return

        if isinstance(shape, DiamondStep):
            action_id = self._ensure_action_id(shape)
            if not shape.tool_id and shape.tools:
                # Keep existing free-text diagrams saveable; catalog selections
                # already carry an ID and must not create another tool.
                shape.tool_id = self.repository.create_tool(str(shape.tools))
            self.repository.update_action(
                int(action_id), name=str(shape.name or shape.text or "").strip(),
                description=str(shape.description or "").strip(),
                tool_id=shape.tool_id or None, image_path=str(shape.image_path or "").strip(),
            )
            shape.db_action_id = int(action_id)

