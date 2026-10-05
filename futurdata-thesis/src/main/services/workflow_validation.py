"""Existing editor connection rules, callable without a GUI.

Class names reflect legacy storage terminology. Do not tighten this permissive
validator during an architectural refactor; import/export grammar is separate.
"""
from ..models import ComponentBox, ActionCircle, DiamondStep


def connection_error(source, target):
    if isinstance(source, ComponentBox) and isinstance(target, ActionCircle):
        return (
            "A Component cannot connect directly to a Step.\n\n"
            "Use:  Component \u2192 Diamond (operation) \u2192 Step (instruction).\n\n"
            "The connection was not created.",
            "Invalid connection: Component \u2192 Action is not allowed.")
    if isinstance(source, DiamondStep) and isinstance(target, DiamondStep):
        return (
            "A Diamond cannot connect directly to another Diamond.\n\n"
            "A diamond operation must first produce a Component/state before another operation begins.\n\n"
            "Use:  Diamond \u2192 Component \u2192 Diamond.\n\n"
            "The connection was not created.",
            "Invalid connection: Diamond \u2192 Diamond is not allowed.")
    return None
