"""
Diagram Loader - Loads complete diagram from database
Reconstructs the visual diagram from relational database structure
"""
from typing import Dict, List, Any, Optional
from ..models import Diagram, ComponentBox, ActionCircle, DiamondStep, ArrowShape, Connection


class DiagramLoader:
    """Loads diagrams from database and reconstructs visual representation."""
    
    def __init__(self, database):
        """
        Initialize diagram loader.
        
        Args:
            database: DatabaseManager instance
        """
        self.db = database
    
    def load_product_diagram(self, product_id: int) -> Optional[Diagram]:
        """
        Load complete diagram for a product from database.
        
        Args:
            product_id: Root component ID
            
        Returns:
            Diagram object with all shapes and connections, or None if not found
        """
        # Get product
        product = self.db.get_product(product_id)
        if not product:
            return None
        
        diagram = Diagram()
        shape_map = {}  # db_id -> shape object
        
        # Layout configuration
        layout = self._calculate_layout(product_id)
        
        # 1. Create root product shape
        root_shape = self._create_product_shape(product, layout['root'])
        diagram.shapes.append(root_shape)
        shape_map[('root', product_id)] = root_shape
        
        # 2. Load all components for this product
        components = self.db.get_components_by_product(product_id)
        for comp in components:
            comp_shape = self._create_component_shape(comp, layout)
            diagram.shapes.append(comp_shape)
            shape_map[('component', comp['component_id'])] = comp_shape
        
        # 3. Load all steps (circles) for root component
        steps = self._get_steps_for_component(product_id, 'root')
        for step in steps:
            step_shape = self._create_step_shape(step, layout)
            diagram.shapes.append(step_shape)
            shape_map[('step', step['id'])] = step_shape
            
            # 4. Load actions (diamonds) for this step
            actions = self._get_actions_for_step(step['id'])
            for action_data in actions:
                action_shape = self._create_action_shape(action_data, layout)
                diagram.shapes.append(action_shape)
                shape_map[('action', action_data['action_id'])] = action_shape
        
        # 5. Load steps for intermediate/leaf components
        for comp in components:
            comp_steps = self._get_steps_for_component(
                comp['id'],  # This is the raw DB ID
                comp['source_table']
            )
            for step in comp_steps:
                step_shape = self._create_step_shape(step, layout)
                diagram.shapes.append(step_shape)
                shape_map[('step', step['id'])] = step_shape
                
                # Load actions for this step
                actions = self._get_actions_for_step(step['id'])
                for action_data in actions:
                    action_shape = self._create_action_shape(action_data, layout)
                    diagram.shapes.append(action_shape)
                    shape_map[('action', action_data['action_id'])] = action_shape
        
        # 6. Create connections based on relationships
        self._create_connections(diagram, shape_map, product_id)
        
        return diagram
    
    def _calculate_layout(self, product_id: int) -> Dict[str, Any]:
        """
        Calculate automatic layout for diagram shapes.
        
        Returns:
            Dictionary with position information for different shape types
        """
        # Simple grid-based layout
        # TODO: Implement smarter layout algorithm (hierarchical, force-directed, etc.)
        
        return {
            'root': {'x': 400, 'y': 100},
            'step_x': 400,
            'step_y_start': 300,
            'step_y_gap': 200,
            'component_x_start': 150,
            'component_x_gap': 250,
            'component_y': 500,
            'action_x_offset': 250,
            'action_y_offset': 0,
            'current_step_y': 300,
            'current_comp_x': 150,
            'step_counter': 0,
            'comp_counter': 0,
        }
    
    def _create_product_shape(self, product: Dict, layout: Dict) -> ComponentBox:
        """Create product (root component) shape."""
        shape = ComponentBox(layout['x'], layout['y'])
        shape.text = product.get('name', 'Product')
        shape.properties['db_id'] = product['id']
        shape.properties['node_type'] = 'Root'
        shape.properties['name'] = product.get('name', '')
        shape.properties['brand'] = product.get('brand', '')
        shape.properties['model'] = product.get('model', '')
        shape.properties['description'] = product.get('description', '')
        shape.properties['color_id'] = product.get('color_id')
        shape.properties['material_id'] = product.get('material_id')
        shape.properties['weight'] = product.get('weight')
        shape.properties['weight_unit'] = product.get('weight_unit', 'g')
        return shape
    
    def _create_component_shape(self, component: Dict, layout: Dict) -> ComponentBox:
        """Create component shape (intermediate or leaf)."""
        # Auto-position
        x = layout['component_x_start'] + (layout['comp_counter'] * layout['component_x_gap'])
        y = layout['component_y']
        layout['comp_counter'] += 1
        
        shape = ComponentBox(x, y)
        shape.text = component.get('name', 'Component')
        shape.properties['db_id'] = component['component_id']
        shape.properties['node_type'] = component.get('node_type', 'Intermediate')
        shape.properties['name'] = component.get('name', '')
        shape.properties['color_id'] = component.get('color_id')
        shape.properties['material_id'] = component.get('material_id')
        shape.properties['weight'] = component.get('weight')
        shape.properties['weight_unit'] = component.get('weight_unit', 'g')
        return shape
    
    def _create_step_shape(self, step: Dict, layout: Dict) -> ActionCircle:
        """Create step (action circle) shape."""
        # Auto-position
        y = layout['step_y_start'] + (layout['step_counter'] * layout['step_y_gap'])
        layout['step_counter'] += 1
        layout['current_step_y'] = y
        
        shape = ActionCircle(layout['step_x'], y)
        shape.text = step.get('title', 'Step')
        shape.db_step_id = step['id']
        shape.step_description = step.get('description', '')
        shape.image_path = step.get('image_path', '')
        return shape
    
    def _create_action_shape(self, action_data: Dict, layout: Dict) -> DiamondStep:
        """Create action (diamond) shape."""
        # Position relative to step
        x = layout['step_x'] + layout['action_x_offset'] + (action_data['action_order'] - 1) * 150
        y = layout['current_step_y'] + layout['action_y_offset']
        
        shape = DiamondStep(x, y)
        
        action = action_data['action']
        shape.text = action.get('name', 'Action')
        shape.name = action.get('name', '')
        shape.description = action.get('description', '')
        shape.image_path = action.get('image_path', '')
        shape.db_action_id = action['id']
        shape.db_step_id = action_data['step_id']
        shape.db_step_action_id = action_data['link_id']
        shape.db_action_order = action_data['action_order']
        
        # Tool info
        if action.get('tool_name'):
            shape.tools = action['tool_name']
        
        return shape
    
    def _get_steps_for_component(self, component_id: int, table_name: str) -> List[Dict]:
        """Get all disassembly steps for a component."""
        if table_name == 'root' or table_name == 'root_component':
            where_clause = "input_root_component_id = ?"
        elif table_name == 'intermediate_component':
            # Decode the encoded ID
            if component_id >= self.db._INTERMEDIATE_OFFSET:
                component_id = component_id - self.db._INTERMEDIATE_OFFSET
            where_clause = "input_intermediate_component_id = ?"
        else:  # leaf_component
            if component_id >= self.db._LEAF_OFFSET:
                component_id = component_id - self.db._LEAF_OFFSET
            where_clause = "input_leaf_component_id = ?"
        
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM disassembly_step WHERE {where_clause} ORDER BY step_order",
                (component_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def _get_actions_for_step(self, step_id: int) -> List[Dict]:
        """Get all actions for a step in order."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    dsa.id as link_id,
                    dsa.action_order,
                    dsa.disassembly_step_id as step_id,
                    a.*,
                    t.name as tool_name,
                    t.category as tool_category
                FROM disassembly_step_action dsa
                JOIN action a ON dsa.action_id = a.id
                LEFT JOIN tool t ON a.tool_id = t.id
                WHERE dsa.disassembly_step_id = ?
                ORDER BY dsa.action_order
            ''', (step_id,))
            
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                # Restructure for easier access
                results.append({
                    'link_id': data['link_id'],
                    'action_order': data['action_order'],
                    'step_id': data['step_id'],
                    'action_id': data['id'],
                    'action': {
                        'id': data['id'],
                        'name': data['name'],
                        'description': data['description'],
                        'tool_id': data['tool_id'],
                        'image_path': data.get('image_path', ''),
                        'tool_name': data.get('tool_name'),
                        'tool_category': data.get('tool_category'),
                    }
                })
            return results
    
    def _create_connections(self, diagram: Diagram, shape_map: Dict, product_id: int):
        """Create arrows/connections based on database relationships."""
        
        # 1. Product -> Steps
        steps = self._get_steps_for_component(product_id, 'root')
        if steps:
            root_shape = shape_map.get(('root', product_id))
            for step in steps:
                step_shape = shape_map.get(('step', step['id']))
                if root_shape and step_shape:
                    arrow = ArrowShape(0, 0, root_shape, step_shape)
                    arrow.update_from_shapes()
                    diagram.shapes.append(arrow)
        
        # 2. Steps -> Output Components
        for step in steps:
            step_shape = shape_map.get(('step', step['id']))
            if not step_shape:
                continue
            
            # Get output components for this step
            output_components = self.db.get_components_from_step(step['id'])
            for comp in output_components:
                comp_shape = shape_map.get(('component', comp['component_id']))
                if comp_shape:
                    arrow = ArrowShape(0, 0, step_shape, comp_shape)
                    arrow.update_from_shapes()
                    diagram.shapes.append(arrow)
        
        # 3. Steps -> Actions (Diamonds)
        for step in steps:
            step_shape = shape_map.get(('step', step['id']))
            if not step_shape:
                continue
            
            actions = self._get_actions_for_step(step['id'])
            prev_action_shape = step_shape
            
            for action_data in actions:
                action_shape = shape_map.get(('action', action_data['action_id']))
                if action_shape:
                    arrow = ArrowShape(0, 0, prev_action_shape, action_shape)
                    arrow.update_from_shapes()
                    diagram.shapes.append(arrow)
                    prev_action_shape = action_shape
        
        # 4. Component -> Step (for intermediate/leaf components)
        components = self.db.get_components_by_product(product_id)
        for comp in components:
            comp_shape = shape_map.get(('component', comp['component_id']))
            if not comp_shape:
                continue
            
            comp_steps = self._get_steps_for_component(
                comp['id'],  # Raw DB ID
                comp['source_table']
            )
            
            for step in comp_steps:
                step_shape = shape_map.get(('step', step['id']))
                if step_shape:
                    arrow = ArrowShape(0, 0, comp_shape, step_shape)
                    arrow.update_from_shapes()
                    diagram.shapes.append(arrow)
