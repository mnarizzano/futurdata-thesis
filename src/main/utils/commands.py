from typing import List, Any


class Command:
    """
    Abstract base interface implementing the Command Design Pattern.
    Defines the contract for executing, undoing and describing transactions.
    """

    def execute(self):
        """Executes the specific action encapsulated by the command."""
        raise NotImplementedError()

    def undo(self):
        """Reverses the operations performed during execution."""
        raise NotImplementedError()

    def get_description(self) -> str:
        """Returns a human-readable generic label identifying the command's context."""
        return "Command"


class CommandHistory:
    """
    Manages historical command states to support Undo and Redo operations.
    Maintains a pointer index and truncates stale future paths upon new actions.
    """

    def __init__(self, max_history: int = 100):
        """
        Initializes an empty command list and bounds history to a max capacity.

        Args:
            max_history (int): The maximum allowable size of the history stack. Defaults to 100.
        """
        self.history: List[Command] = []
        self.current_index = -1
        self.max_history = max_history

    def execute(self, command: Command):
        """
        Executes a new command, invalidates future redo histories, registers 
        the action and enforces bounded capacity constraints.

        Args:
            command (Command): The concrete command instance to run and track.*
        """
        command.execute()
        self.history = self.history[:self.current_index + 1]
        self.history.append(command)
        self.current_index += 1
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.current_index -= 1

    def undo(self) -> bool:
        """
        Triggers the undo logic on the active history index if available 
        and updates the history index backward.

        Returns:
            bool: True if a command was successfully reverted, False if history was empty.
        """
        if not self.can_undo():
            return False
        command = self.history[self.current_index]
        command.undo()
        self.current_index -= 1
        return True

    def redo(self) -> bool:
        """
        Advances the pointer index forward and re-runs the adjacent command 
        if a redo path exists.

        Returns:
            bool: True if a forward command was successfully re-executed, False otherwise.
        """
        if not self.can_redo():
            return False
        self.current_index += 1
        command = self.history[self.current_index]
        command.execute()
        return True

    def can_undo(self) -> bool:
        """
        Verifies if there are valid executed transactions available to revert.

        Returns:
            bool: True if the index pointer points to a valid command index, False otherwise.
        """
        return self.current_index >= 0

    def can_redo(self) -> bool:
        """
        Checks if the index pointer sits behind the absolute historical length boundary.

        Returns:
            bool: True if there are future commands available to redo, False otherwise.
        """
        return self.current_index < len(self.history) - 1

    def clear(self):
        """Resets and flushes out all items from historical memory caches."""
        self.history.clear()
        self.current_index = -1

    def get_undo_description(self) -> str:
        """
        Fetches the action name of the last executed command that can be reverted.

        Returns:
            str: The textual description of the undoable command or an empty string.
        """
        if self.can_undo():
            return self.history[self.current_index].get_description()
        return ""

    def get_redo_description(self) -> str:
        """
        Fetches the action name of the next forward command waiting to be redone.

        Returns:
            str: The textual description of the redoable command or an empty string.
        """
        if self.can_redo():
            return self.history[self.current_index + 1].get_description()
        return ""


class AddShapeCommand(Command):
    """Command for adding a shape into a diagram layout."""

    def __init__(self, diagram, shape):
        """
        Initializes references to the target canvas model and shape definition.

        Args:
            diagram (any): The parent diagram model container managing application shapes.
            shape (any): The concrete shape node instance to be introduced.
        """
        self.diagram = diagram
        self.shape = shape

    def execute(self):
        """Inserts the shape into the diagram model container."""
        self.diagram.add_shape(self.shape)

    def undo(self):
        """Removes the shape from the diagram model container."""
        self.diagram.remove_shape(self.shape)

    def get_description(self) -> str:
        """Returns a formatted descriptive string describing the shape creation event."""
        return f"Add {self.shape.shape_type}"


class RemoveShapeCommand(Command):
    """Handles systemic shape removals while tracking orphaned connectors for fallback recovery."""

    def __init__(self, diagram, shape):
        """
        Initializes the removal transaction state and empty connection cache hooks.

        Args:
            diagram (any): The parent diagram model context containing graph assets.
            shape (any): The node component target flagged for complete deletion.
        """
        self.diagram = diagram
        self.shape = shape
        self.removed_connections = []

    def execute(self):
        """Caches linked connections before purging the shape object entirely from canvas arrays."""
        self.removed_connections = self.diagram.get_connections_for_shape(self.shape)
        self.diagram.remove_shape(self.shape)

    def undo(self):
        """Restores the missing node and reconstructs its severed connector lines."""
        self.diagram.add_shape(self.shape)
        for conn in self.removed_connections:
            self.diagram.add_connection(conn)

    def get_description(self) -> str:
        """Returns a formatted descriptive label identifying the shape removal operation."""
        return f"Remove {self.shape.shape_type}"


class MoveShapeCommand(Command):
    """Encapsulates translation operations across single or multiple diagram items."""

    def __init__(self, shapes, dx, dy):
        """
        Standardizes single instances into lists and caches directional coordinate offsets.

        Args:
            shapes (any or List[any]): A single shape or list of shapes to apply displacement offsets onto.
            dx (float or int): Horizontal delta coordinate translation offset.
            dy (float or int): Vertical delta coordinate translation offset.
        """
        self.shapes = shapes if isinstance(shapes, list) else [shapes]
        self.dx = dx
        self.dy = dy

    def execute(self):
        """Applies positive coordinate translations to all tracked canvas entities."""
        for shape in self.shapes:
            shape.move(self.dx, self.dy)

    def undo(self):
        """Applies inverse coordinate offsets to snap entities back to their origins."""
        for shape in self.shapes:
            shape.move(-self.dx, -self.dy)

    def get_description(self) -> str:
        """
        Constructs context labels showing whether single or multiple shapes were moved.

        Returns:
            str: Text indicating either the singular shape name or the collective displacement count.
        """
        if len(self.shapes) == 1:
            return f"Move {self.shapes[0].shape_type}"
        return f"Move {len(self.shapes)} shapes"


class AddConnectionCommand(Command):
    """Manages structural graph linking operations between node endpoints."""

    def __init__(self, diagram, connection):
        """
        Initializes targeted data references for diagram scopes and connection objects.

        Args:
            diagram (any): The active diagram data instance managing relationships.
            connection (any): The new edge entity containing link nodes metadata.
        """
        self.diagram = diagram
        self.connection = connection

    def execute(self):
        """Establishes a connection path link across diagram nodes."""
        self.diagram.add_connection(self.connection)

    def undo(self):
        """Severs the established connection path link from the diagram layout."""
        self.diagram.remove_connection(self.connection)

    def get_description(self) -> str:
        """
        Provides a descriptor label for new path routing operations.

        Returns:
            str: Describing text ("Add connection").
        """
        return "Add connection"


class RemoveConnectionCommand(Command):
    """Manages manual disconnection events of structural edge components."""

    def __init__(self, diagram, connection):
        """
        Initializes diagram containers and connection descriptors for deletion.

        Args:
            diagram (any): The active diagram tracking schema components.
            connection (any): The specific layout connection line target to safely slice out.
        """
        self.diagram = diagram
        self.connection = connection

    def execute(self):
        """Removes the designated visual link line connection."""
        self.diagram.remove_connection(self.connection)

    def undo(self):
        """Reinserts the visual link line configuration back into the active pool."""
        self.diagram.add_connection(self.connection)

    def get_description(self) -> str:
        """
        Provides a descriptor label for path removal activities.

        Returns:
            str: Describing text ("Remove connection").
        """
        return "Remove connection"


class EditShapePropertiesCommand(Command):
    """Manages attributes mutations, supporting reversible changes on properties schemas."""

    def __init__(self, shape, old_properties, new_properties):
        """
        Caches snapshot data structures representing properties before and after changes.

        Args:
            shape (any): The target node entity receiving attribute updates.
            old_properties (Dict[str, Any]): A snapshot capturing the property parameters before modification.
            new_properties (Dict[str, Any]): A dictionary mapping the new configuration variables.
        """
        self.shape = shape
        self.old_properties = old_properties
        self.new_properties = new_properties

    def execute(self):
        """Applies new property updates directly to the destination shape."""
        self._apply_properties(self.new_properties)

    def undo(self):
        """Re-injects initial property values to restore original shape attributes."""
        self._apply_properties(self.old_properties)

    def _apply_properties(self, properties):
        """
        Introspects and maps keys into internal property mappings or direct class attributes.

        Args:
            properties (Dict[str, Any]): The collection dataset containing attributes to append.
        """
        for key, value in properties.items():
            if hasattr(self.shape, "properties") and key in getattr(self.shape, "properties", {}):
                self.shape.properties[key] = value
            elif hasattr(self.shape, key):
                setattr(self.shape, key, value)

    def get_description(self) -> str:
        """
        Builds a customized contextual name for model properties modifications.

        Returns:
            str: Text string declaring an asset customization event.
        """
        return f"Edit {self.shape.shape_type} properties"


class MultiCommand(Command):
    """Macro command container that aggregates independent commands into a single transactional block."""

    def __init__(self, commands: List[Command], description: str = "Multiple actions"):
        self.commands = commands
        self.description = description

    def execute(self):
        """Processes nested command instructions sequentially in forward order."""
        for command in self.commands:
            command.execute()

    def undo(self):
        """Reverts aggregated tasks sequentially in reverse execution order to ensure system integrity."""
        for command in reversed(self.commands):
            command.undo()

    def get_description(self) -> str:
        """Returns the descriptive text summarizing the bundled transactional execution."""
        return self.description
