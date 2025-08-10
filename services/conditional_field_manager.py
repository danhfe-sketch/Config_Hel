"""
Conditional Field Manager for LT32 PRO Configurator

This module handles conditional field visibility based on parameter values.
It manages showing/hiding fields based on visibility conditions defined in the
parameter specification.
"""

from typing import Dict, List, Optional, Any, Callable
import re
from services.parameter_specification import (
    CONDITIONAL_VISIBILITY_RULES,
    get_parameter_specification
)


class ConditionalFieldManager:
    """
    Manages conditional field visibility based on parameter values.
    
    This class handles:
    - Registering conditional fields with their visibility conditions
    - Monitoring trigger field changes
    - Evaluating visibility conditions
    - Updating field visibility in the UI
    """
    
    def __init__(self):
        """Initialize the conditional field manager."""
        self.conditional_fields = {}  # field_name -> condition info
        self.trigger_listeners = {}   # trigger_field -> list of dependent fields
        self.field_widgets = {}       # field_name -> widget reference
        self.current_values = {}      # field_name -> current value
        
        # Load conditional rules from specification
        self._load_conditional_rules()
    
    def _load_conditional_rules(self):
        """Load conditional visibility rules from the parameter specification."""
        for field_name, rule in CONDITIONAL_VISIBILITY_RULES.items():
            self.register_conditional_field(
                field_name=field_name,
                condition=rule['condition'],
                trigger_field=rule['trigger_field']
            )
    
    def register_conditional_field(self, field_name: str, condition: str, trigger_field: str):
        """
        Register a conditional field with its visibility condition.
        
        Args:
            field_name: Full name of the field (section.parameter.field)
            condition: Condition string to evaluate for visibility
            trigger_field: Field that triggers condition evaluation
        """
        self.conditional_fields[field_name] = {
            'condition': condition,
            'trigger_field': trigger_field,
            'visible': True  # Default to visible
        }
        
        # Register trigger listener
        if trigger_field not in self.trigger_listeners:
            self.trigger_listeners[trigger_field] = []
        self.trigger_listeners[trigger_field].append(field_name)
        
        print(f"DEBUG: Registered conditional field {field_name} with condition '{condition}' triggered by {trigger_field}")
    
    def register_field_widget(self, field_name: str, widget):
        """
        Register a widget for a conditional field.
        
        Args:
            field_name: Full name of the field
            widget: Widget reference that can be shown/hidden
        """
        self.field_widgets[field_name] = widget
        print(f"DEBUG: Registered widget for conditional field {field_name}")
    
    def evaluate_condition(self, condition: str, current_values: Dict[str, Any]) -> bool:
        """
        Evaluate a visibility condition based on current parameter values.
        
        Args:
            condition: Condition string to evaluate
            current_values: Dictionary of current field values
            
        Returns:
            bool: True if condition is met (field should be visible)
        """
        try:
            # Handle different condition formats - check boolean conditions first
            if condition.endswith("== true"):
                # Handle boolean true conditions like "enabled == true"
                field_name = condition.replace("== true", "").strip()
                
                # Get current value for the field - try both short and full field names
                current_value = current_values.get(field_name, False)
                
                # If not found with short name, try to find with full path
                if current_value is False or current_value == "":
                    for key, value in current_values.items():
                        if key.endswith("." + field_name) or key == field_name:
                            current_value = value
                            break
                
                # Convert to boolean if needed
                if isinstance(current_value, str):
                    result = current_value.lower() in ['true', '1', 'yes', 'on', 'enabled']
                elif isinstance(current_value, bool):
                    result = current_value
                else:
                    result = bool(current_value)
                
                print(f"DEBUG: Evaluating boolean condition '{condition}': {field_name}='{current_value}' -> {result}")
                return result
            
            elif condition.endswith("== false"):
                # Handle boolean false conditions
                field_name = condition.replace("== false", "").strip()
                
                # Get current value for the field - try both short and full field names
                current_value = current_values.get(field_name, True)
                
                # If not found with short name, try to find with full path
                if current_value is True or current_value == "":
                    for key, value in current_values.items():
                        if key.endswith("." + field_name) or key == field_name:
                            current_value = value
                            break
                
                # Convert to boolean if needed
                if isinstance(current_value, str):
                    result = current_value.lower() not in ['true', '1', 'yes', 'on', 'enabled']
                elif isinstance(current_value, bool):
                    result = not current_value
                else:
                    result = not bool(current_value)
                
                print(f"DEBUG: Evaluating boolean condition '{condition}': {field_name}='{current_value}' -> {result}")
                return result
            
            elif "==" in condition:
                # Handle equality conditions like "ignition_mode == 'Virtual por bateria (Virtual by battery)'"
                parts = condition.split("==")
                if len(parts) == 2:
                    field_name = parts[0].strip()
                    expected_value = parts[1].strip().strip("'\"")
                    
                    # Get current value for the field - try both short and full field names
                    current_value = current_values.get(field_name, "")
                    
                    # If not found with short name, try to find with full path
                    if not current_value:
                        for key, value in current_values.items():
                            if key.endswith("." + field_name) or key == field_name:
                                current_value = value
                                break
                    
                    # Compare values
                    result = str(current_value) == expected_value
                    print(f"DEBUG: Evaluating condition '{condition}': {field_name}='{current_value}' == '{expected_value}' -> {result}")
                    return result
            
            # Default: try to evaluate as Python expression (safe subset)
            # Replace field names with their values
            eval_condition = condition
            for field_name, value in current_values.items():
                if field_name in eval_condition:
                    if isinstance(value, str):
                        eval_condition = eval_condition.replace(field_name, f"'{value}'")
                    else:
                        eval_condition = eval_condition.replace(field_name, str(value))
            
            # Only allow safe evaluation
            if any(unsafe in eval_condition for unsafe in ['import', 'exec', 'eval', '__']):
                print(f"WARNING: Unsafe condition detected: {condition}")
                return True
            
            result = eval(eval_condition)
            print(f"DEBUG: Evaluated condition '{condition}' as '{eval_condition}' -> {result}")
            return bool(result)
            
        except Exception as e:
            print(f"ERROR: Failed to evaluate condition '{condition}': {str(e)}")
            return True  # Default to visible on error
    
    def update_field_visibility(self, field_name: str, visible: bool):
        """
        Update the visibility of a field widget.
        
        Args:
            field_name: Full name of the field
            visible: True to show, False to hide
        """
        if field_name in self.field_widgets:
            widget = self.field_widgets[field_name]
            try:
                if visible:
                    widget.grid()  # Show widget
                    print(f"DEBUG: Showing field {field_name}")
                else:
                    widget.grid_remove()  # Hide widget
                    print(f"DEBUG: Hiding field {field_name}")
                
                # Update visibility state
                if field_name in self.conditional_fields:
                    self.conditional_fields[field_name]['visible'] = visible
                    
            except Exception as e:
                print(f"ERROR: Failed to update visibility for field {field_name}: {str(e)}")
        else:
            print(f"WARNING: No widget registered for conditional field {field_name}")
    
    def handle_trigger_change(self, trigger_field: str, new_value: Any):
        """
        Handle a change in a trigger field value.
        
        Args:
            trigger_field: Name of the field that changed
            new_value: New value of the trigger field
        """
        print(f"DEBUG: Trigger field {trigger_field} changed to '{new_value}'")
        
        # Update current value
        self.current_values[trigger_field] = new_value
        
        # Check if this field triggers any conditional fields
        if trigger_field in self.trigger_listeners:
            dependent_fields = self.trigger_listeners[trigger_field]
            print(f"DEBUG: Found {len(dependent_fields)} dependent fields for trigger {trigger_field}")
            
            for field_name in dependent_fields:
                if field_name in self.conditional_fields:
                    condition_info = self.conditional_fields[field_name]
                    condition = condition_info['condition']
                    
                    # Evaluate condition with current values
                    should_be_visible = self.evaluate_condition(condition, self.current_values)
                    
                    # Update visibility if it changed
                    current_visibility = condition_info.get('visible', True)
                    if should_be_visible != current_visibility:
                        self.update_field_visibility(field_name, should_be_visible)
    
    def update_current_value(self, field_name: str, value: Any):
        """
        Update the current value of a field.
        
        Args:
            field_name: Name of the field
            value: Current value of the field
        """
        self.current_values[field_name] = value
        
        # Check if this field is a trigger for any conditional fields
        self.handle_trigger_change(field_name, value)
    
    def get_visible_fields(self, section_name: str) -> List[str]:
        """
        Get list of currently visible fields in a section.
        
        Args:
            section_name: Name of the section
            
        Returns:
            List of visible field names
        """
        visible_fields = []
        
        for field_name, condition_info in self.conditional_fields.items():
            if field_name.startswith(section_name + ".") and condition_info.get('visible', True):
                visible_fields.append(field_name)
        
        return visible_fields
    
    def is_field_visible(self, field_name: str) -> bool:
        """
        Check if a field is currently visible.
        
        Args:
            field_name: Full name of the field
            
        Returns:
            bool: True if field is visible
        """
        if field_name in self.conditional_fields:
            return self.conditional_fields[field_name].get('visible', True)
        return True  # Non-conditional fields are always visible
    
    def initialize_field_visibility(self, current_values: Dict[str, Any]):
        """
        Initialize field visibility based on current parameter values.
        
        Args:
            current_values: Dictionary of current field values
        """
        print(f"DEBUG: Initializing field visibility with values: {current_values}")
        
        # Update current values
        self.current_values.update(current_values)
        
        # Evaluate all conditional fields
        for field_name, condition_info in self.conditional_fields.items():
            condition = condition_info['condition']
            should_be_visible = self.evaluate_condition(condition, self.current_values)
            self.update_field_visibility(field_name, should_be_visible)
    
    def get_conditional_fields_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all conditional fields.
        
        Returns:
            Dictionary with conditional field information
        """
        return self.conditional_fields.copy()
    
    def get_trigger_listeners_info(self) -> Dict[str, List[str]]:
        """
        Get information about trigger listeners.
        
        Returns:
            Dictionary mapping trigger fields to dependent fields
        """
        return self.trigger_listeners.copy()
    
    def reset(self):
        """Reset the conditional field manager state."""
        self.current_values.clear()
        for field_name in self.conditional_fields:
            self.conditional_fields[field_name]['visible'] = True
        print("DEBUG: Reset conditional field manager state")


# Global instance for use throughout the application
conditional_field_manager = ConditionalFieldManager()


def get_conditional_field_manager() -> ConditionalFieldManager:
    """
    Get the global conditional field manager instance.
    
    Returns:
        ConditionalFieldManager: The global instance
    """
    return conditional_field_manager