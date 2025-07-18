"""
Parameter Factory - Factory pattern for creating different parameter input types.

This module provides a factory pattern for generating numeric inputs, dropdowns, 
and radio button groups with consistent validation and command generation interfaces.
"""

import customtkinter as ctk
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any
from services.validation_service import ValidationService, ValidationResult
from services.device_command_mapper import DeviceCommandMapper


@dataclass
class ParameterDefinition:
    """Definition of a parameter with its properties and behavior."""
    name: str
    param_type: str  # 'numeric', 'dropdown', 'radio'
    display_label: str
    help_text: str
    at_command_template: str
    validation_rules: Dict
    group: str = "general"
    default_value: Any = None


class BaseParameter(ABC):
    """Base class for all parameter types with common validation and command generation."""
    
    def __init__(self, definition: ParameterDefinition, validation_service: ValidationService, 
                 i18n_service, send_command_callback: Callable[[str], None]):
        self.definition = definition
        self.validation_service = validation_service
        self.i18n = i18n_service
        self.send_command_callback = send_command_callback
        self.widget = None
        self.error_label = None
        self.send_button = None
        
    @abstractmethod
    def create_widget(self, parent) -> ctk.CTkFrame:
        """Create the UI widget for this parameter."""
        pass
    
    @abstractmethod
    def get_value(self) -> Any:
        """Get the current value from the widget."""
        pass
    
    @abstractmethod
    def set_value(self, value: Any) -> None:
        """Set the value in the widget."""
        pass
    
    def validate(self) -> ValidationResult:
        """Validate the current parameter value."""
        value = self.get_value()
        return self.validation_service.validate_parameter(self.definition.name, value)
    
    def send_command(self) -> None:
        """Validate and send the AT command for this parameter."""
        validation_result = self.validate()
        
        if not validation_result.is_valid:
            self._show_error(validation_result.error_message)
            return
        
        self._clear_error()
        value = self.get_value()
        
        if value is not None and str(value).strip():
            try:
                # Get the command mapper from the factory
                command_mapper = getattr(self, 'command_mapper', None)
                
                # If we have access to the command mapper, use it
                if command_mapper:
                    command = command_mapper.get_command(self.definition.name, value)
                else:
                    # Fall back to the template if no command mapper is available
                    command = self.definition.at_command_template.format(value=value)
                
                self.send_command_callback(command)
            except ValueError as e:
                self._show_error(str(e))
                return
    
    def _show_error(self, message: str) -> None:
        """Show validation error message."""
        if self.error_label:
            self.error_label.configure(text=message, text_color="red")
    
    def _clear_error(self) -> None:
        """Clear validation error message."""
        if self.error_label:
            self.error_label.configure(text="", text_color="gray")
    
    def update_language_display(self, i18n_service) -> None:
        """Update the parameter widget's language display."""
        # Update the i18n service reference
        self.i18n = i18n_service
        
        # Update send button text if it exists
        if self.send_button:
            self.send_button.configure(text=self.i18n.get("send", "Send"))
        
        # Update parameter label if it exists
        if hasattr(self, 'param_label'):
            self.param_label.configure(text=self.i18n.get(self.definition.display_label, self.definition.display_label))
    
    def _create_base_frame(self, parent) -> ctk.CTkFrame:
        """Create the base frame with label, input, and send button."""
        frame = ctk.CTkFrame(parent)
        frame.grid_columnconfigure(1, weight=1)  # Make input column expandable
        
        # Parameter label - store reference for language updates
        self.param_label = ctk.CTkLabel(frame, text=self.i18n.get(self.definition.display_label, self.definition.display_label))
        self.param_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Error label (initially empty)
        self.error_label = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=10))
        self.error_label.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="w")
        
        return frame


class NumericParameter(BaseParameter):
    """Numeric parameter with entry field and range validation."""
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        """Create numeric input widget with validation."""
        frame = self._create_base_frame(parent)
        
        # Entry field
        self.widget = ctk.CTkEntry(frame, width=150)
        self.widget.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Set default value if provided
        if self.definition.default_value is not None:
            self.widget.insert(0, str(self.definition.default_value))
        
        # Send button
        self.send_button = ctk.CTkButton(
            frame, 
            text=self.i18n.get("send", "Send"), 
            width=60, 
            command=self.send_command
        )
        self.send_button.grid(row=0, column=2, padx=(5, 10), pady=5)
        
        # Add validation on focus out
        self.widget.bind("<FocusOut>", self._on_focus_out)
        
        return frame
    
    def get_value(self) -> Optional[int]:
        """Get numeric value from entry field."""
        if not self.widget:
            return None
        
        text = self.widget.get().strip()
        if not text:
            return None
        
        try:
            if self.definition.validation_rules.get('integer', True):
                return int(text)
            else:
                return float(text)
        except ValueError:
            return None
    
    def set_value(self, value: Any) -> None:
        """Set numeric value in entry field."""
        if self.widget:
            self.widget.delete(0, ctk.END)
            if value is not None:
                self.widget.insert(0, str(value))
    
    def _on_focus_out(self, event) -> None:
        """Validate on focus out."""
        validation_result = self.validate()
        if not validation_result.is_valid:
            self._show_error(validation_result.error_message)
        else:
            self._clear_error()


class DropdownParameter(BaseParameter):
    """Dropdown parameter with predefined options."""
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        """Create dropdown widget with validation."""
        frame = self._create_base_frame(parent)
        
        # Get allowed values from validation rules
        allowed_values = self.definition.validation_rules.get('allowed_values', [])
        
        # Dropdown
        self.widget = ctk.CTkComboBox(
            frame, 
            values=allowed_values,
            state="readonly"
        )
        self.widget.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Set default value if provided
        if self.definition.default_value is not None and self.definition.default_value in allowed_values:
            self.widget.set(self.definition.default_value)
        elif allowed_values:
            self.widget.set(allowed_values[0])
        
        # Send button
        self.send_button = ctk.CTkButton(
            frame, 
            text=self.i18n.get("send", "Send"), 
            width=60, 
            command=self.send_command
        )
        self.send_button.grid(row=0, column=2, padx=(5, 10), pady=5)
        
        return frame
    
    def get_value(self) -> Optional[str]:
        """Get selected value from dropdown."""
        if not self.widget:
            return None
        return self.widget.get()
    
    def set_value(self, value: Any) -> None:
        """Set selected value in dropdown."""
        if self.widget and value is not None:
            self.widget.set(str(value))


class RadioParameter(BaseParameter):
    """Radio button group parameter with exclusive selection."""
    
    def __init__(self, definition: ParameterDefinition, validation_service: ValidationService, 
                 i18n_service, send_command_callback: Callable[[str], None]):
        super().__init__(definition, validation_service, i18n_service, send_command_callback)
        
        # Store the current value until widget is created
        self.radio_var = None
        self._current_value = None
        
        # Set default value
        allowed_values = self.definition.validation_rules.get('allowed_values', [])
        if self.definition.default_value is not None and self.definition.default_value in allowed_values:
            self._current_value = self.definition.default_value
        elif allowed_values:
            self._current_value = allowed_values[0]
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        """Create radio button group widget."""
        frame = self._create_base_frame(parent)
        
        # Get allowed values from validation rules
        allowed_values = self.definition.validation_rules.get('allowed_values', [])
        
        # Create radio variable now that we have a parent window
        self.radio_var = ctk.StringVar()
        
        # Set the current value if we have one stored
        if self._current_value is not None:
            self.radio_var.set(self._current_value)
        elif allowed_values:
            self.radio_var.set(allowed_values[0])
            self._current_value = allowed_values[0]
        
        # Create radio buttons with responsive layout
        radio_frame = ctk.CTkFrame(frame)
        radio_frame.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Make radio frame expandable
        radio_frame.grid_columnconfigure(0, weight=1)
        
        # Create a container for radio buttons that can wrap if needed
        radio_container = ctk.CTkFrame(radio_frame, fg_color="transparent")
        radio_container.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Configure columns with flexible sizing - reduce minsize for better responsiveness
        for i in range(len(allowed_values)):
            radio_container.grid_columnconfigure(i, weight=1, minsize=60)
        
        self.radio_buttons = []
        for i, value in enumerate(allowed_values):
            radio_btn = ctk.CTkRadioButton(
                radio_container, 
                text=self.i18n.get(value.lower(), value), 
                variable=self.radio_var, 
                value=value,
                command=self._on_radio_change
            )
            radio_btn.grid(row=0, column=i, padx=3, pady=5, sticky="w")
            self.radio_buttons.append(radio_btn)
        
        # Send button
        self.send_button = ctk.CTkButton(
            frame, 
            text=self.i18n.get("send", "Send"), 
            width=60, 
            command=self.send_command
        )
        self.send_button.grid(row=0, column=2, padx=(5, 10), pady=5)
        
        return frame
    
    def get_value(self) -> Optional[str]:
        """Get selected radio button value."""
        if hasattr(self, 'radio_var') and self.radio_var is not None:
            return self.radio_var.get()
        return self._current_value
    
    def set_value(self, value: Any) -> None:
        """Set selected radio button value."""
        if value is not None:
            str_value = str(value)
            self._current_value = str_value
            if hasattr(self, 'radio_var') and self.radio_var is not None:
                self.radio_var.set(str_value)
    
    def _on_radio_change(self) -> None:
        """Handle radio button selection change."""
        # Clear any previous error when user makes a selection
        self._clear_error()
        # Optional: You can add additional logic here if needed
        # For example, auto-validation or immediate feedback
    
    def update_language_display(self, i18n_service) -> None:
        """Update the radio parameter widget's language display."""
        # Call parent method to update common elements
        super().update_language_display(i18n_service)
        
        # Update radio button text
        if hasattr(self, 'radio_buttons'):
            allowed_values = self.definition.validation_rules.get('allowed_values', [])
            for i, (radio_btn, value) in enumerate(zip(self.radio_buttons, allowed_values)):
                radio_btn.configure(text=self.i18n.get(value.lower(), value))


class ParameterGroup:
    """Group of related parameters for logical organization."""
    
    def __init__(self, name: str, display_label: str, i18n_service):
        self.name = name
        self.display_label = display_label
        self.i18n = i18n_service
        self.parameters: List[BaseParameter] = []
        self.frame = None
    
    def add_parameter(self, parameter: BaseParameter) -> None:
        """Add a parameter to this group."""
        self.parameters.append(parameter)
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        """Create the group frame with all parameters."""
        self.frame = ctk.CTkFrame(parent)
        self.frame.grid_columnconfigure(0, weight=1)
        
        # Group title
        title = ctk.CTkLabel(
            self.frame, 
            text=self.i18n.get(self.display_label, self.display_label), 
            font=ctk.CTkFont(weight="bold")
        )
        title.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Add parameters
        for i, parameter in enumerate(self.parameters):
            param_widget = parameter.create_widget(self.frame)
            param_widget.grid(row=i+1, column=0, padx=10, pady=5, sticky="ew")
        
        return self.frame
    
    def get_values(self) -> Dict[str, Any]:
        """Get all parameter values in this group."""
        return {param.definition.name: param.get_value() for param in self.parameters}
    
    def set_values(self, values: Dict[str, Any]) -> None:
        """Set parameter values in this group."""
        for parameter in self.parameters:
            if parameter.definition.name in values:
                parameter.set_value(values[parameter.definition.name])
    
    def update_language_display(self, i18n_service) -> None:
        """Update the group's language display."""
        # Update the i18n service reference
        self.i18n = i18n_service
        
        # Update group title if frame exists
        if self.frame:
            # Find the title label (first child that's a CTkLabel with bold font)
            for child in self.frame.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    try:
                        if child.cget("font").cget("weight") == "bold":
                            child.configure(text=self.i18n.get(self.display_label, self.display_label))
                            break
                    except:
                        # If font checking fails, assume it's the title label if it's the first one
                        child.configure(text=self.i18n.get(self.display_label, self.display_label))
                        break
        
        # Update all parameters in this group
        for parameter in self.parameters:
            if hasattr(parameter, 'update_language_display'):
                parameter.update_language_display(i18n_service)


class ParameterFactory:
    """Factory for creating parameter widgets with consistent interfaces."""
    
    def __init__(self, validation_service: ValidationService, i18n_service, 
                 send_command_callback: Callable[[str], None]):
        self.validation_service = validation_service
        self.i18n = i18n_service
        self.send_command_callback = send_command_callback
        self.groups: Dict[str, ParameterGroup] = {}
        self.command_mapper = DeviceCommandMapper()
        self._init_parameter_definitions()
    
    def _init_parameter_definitions(self) -> None:
        """Initialize parameter definitions based on validation rules."""
        # Get command templates from the command mapper
        cmd_templates = {}
        for param_name in self.command_mapper.command_templates:
            template = self.command_mapper.command_prefix + self.command_mapper.command_templates[param_name]
            cmd_templates[param_name] = template
        
        self.parameter_definitions = {
            # Numeric parameters
            'vibration': ParameterDefinition(
                name='vibration',
                param_type='numeric',
                display_label='vibration_level',
                help_text='Set vibration sensitivity level (0-255)',
                at_command_template=cmd_templates.get('vibration', 'ATSMS:SZCS#VIBL={value}#'),
                validation_rules=self.validation_service.get_parameter_info('vibration') or {},
                group='sensors',
                default_value=128
            ),
            'sensitivity': ParameterDefinition(
                name='sensitivity',
                param_type='numeric',
                display_label='sensitivity_level',
                help_text='Set movement sensitivity level (1-10)',
                at_command_template=cmd_templates.get('sensitivity', 'ATSMS:SZCS#SENSITIVITY={value}#'),
                validation_rules=self.validation_service.get_parameter_info('sensitivity') or {},
                group='sensors',
                default_value=5
            ),
            'timer_ign_on': ParameterDefinition(
                name='timer_ign_on',
                param_type='numeric',
                display_label='timer_ignition_on',
                help_text='Reporting interval when ignition is ON (1-65500 seconds)',
                at_command_template=cmd_templates.get('timer_ign_on', 'ATSMS:TIMER,{value},#'),
                validation_rules=self.validation_service.get_parameter_info('timer_ign_on') or {},
                group='timers',
                default_value=30
            ),
            'timer_ign_off': ParameterDefinition(
                name='timer_ign_off',
                param_type='numeric',
                display_label='timer_ignition_off',
                help_text='Reporting interval when ignition is OFF (1-65500 seconds)',
                at_command_template=cmd_templates.get('timer_ign_off', 'ATSMS:TIMER,,{value}#'),
                validation_rules=self.validation_service.get_parameter_info('timer_ign_off') or {},
                group='timers',
                default_value=300
            ),
            'heartbeat_ign_on': ParameterDefinition(
                name='heartbeat_ign_on',
                param_type='numeric',
                display_label='heartbeat_ignition_on',
                help_text='Heartbeat interval when ignition is ON (60-300 seconds)',
                at_command_template=cmd_templates.get('heartbeat_ign_on', 'ATSMS:HBT,{value},#'),
                validation_rules=self.validation_service.get_parameter_info('heartbeat_ign_on') or {},
                group='timers',
                default_value=60
            ),
            'heartbeat_ign_off': ParameterDefinition(
                name='heartbeat_ign_off',
                param_type='numeric',
                display_label='heartbeat_ignition_off',
                help_text='Heartbeat interval when ignition is OFF (60-300 seconds)',
                at_command_template=cmd_templates.get('heartbeat_ign_off', 'ATSMS:HBT,,{value}#'),
                validation_rules=self.validation_service.get_parameter_info('heartbeat_ign_off') or {},
                group='timers',
                default_value=300
            ),
            
            # Dropdown parameters
            'heartbeat_interval': ParameterDefinition(
                name='heartbeat_interval',
                param_type='dropdown',
                display_label='heartbeat_interval',
                help_text='Select heartbeat reporting interval',
                at_command_template=cmd_templates.get('heartbeat_interval', 'ATSMS:HBT,{value}#'),
                validation_rules=self.validation_service.get_parameter_info('heartbeat_interval') or {},
                group='timers',
                default_value='1min'
            ),
            'curve_sensor': ParameterDefinition(
                name='curve_sensor',
                param_type='dropdown',
                display_label='curve_sensor',
                help_text='Configure curve sensor behavior',
                at_command_template=cmd_templates.get('curve_sensor', 'ATSMS:SZCS#CURVE={value}#'),
                validation_rules=self.validation_service.get_parameter_info('curve_sensor') or {},
                group='sensors',
                default_value='Auto'
            ),
            
            # Radio button parameters
            'lock_type': ParameterDefinition(
                name='lock_type',
                param_type='radio',
                display_label='lock_type',
                help_text='Select device lock type',
                at_command_template=cmd_templates.get('lock_type', 'ATSMS:SZCS#LOCKTYPE={value}#'),
                validation_rules=self.validation_service.get_parameter_info('lock_type') or {},
                group='security',
                default_value='PIN'
            ),
            'ignition_type': ParameterDefinition(
                name='ignition_type',
                param_type='radio',
                display_label='ignition_type',
                help_text='Select ignition detection type',
                at_command_template=cmd_templates.get('ignition_type', 'ATSMS:SZCS#ACCLINE={value}#'),
                validation_rules=self.validation_service.get_parameter_info('ignition_type') or {},
                group='sensors',
                default_value='Digital'
            ),
            'transmission_mode': ParameterDefinition(
                name='transmission_mode',
                param_type='radio',
                display_label='transmission_mode',
                help_text='Select data transmission protocol',
                at_command_template=cmd_templates.get('transmission_mode', 'ATSMS:SZCS#PROTOCOL={value}#'),
                validation_rules=self.validation_service.get_parameter_info('transmission_mode') or {},
                group='communication',
                default_value='TCP'
            )
        }
    
    def create_parameter(self, param_name: str) -> Optional[BaseParameter]:
        """Create a parameter widget by name."""
        if param_name not in self.parameter_definitions:
            return None
        
        definition = self.parameter_definitions[param_name]
        
        if definition.param_type == 'numeric':
            return NumericParameter(definition, self.validation_service, self.i18n, self.send_command_callback)
        elif definition.param_type == 'dropdown':
            return DropdownParameter(definition, self.validation_service, self.i18n, self.send_command_callback)
        elif definition.param_type == 'radio':
            return RadioParameter(definition, self.validation_service, self.i18n, self.send_command_callback)
        
        return None
    
    def create_group(self, group_name: str, display_label: str) -> ParameterGroup:
        """Create or get a parameter group."""
        if group_name not in self.groups:
            self.groups[group_name] = ParameterGroup(group_name, display_label, self.i18n)
        return self.groups[group_name]
    
    def get_group(self, group_name: str) -> Optional[ParameterGroup]:
        """Get an existing parameter group."""
        return self.groups.get(group_name)
    
    def get_all_groups(self) -> Dict[str, ParameterGroup]:
        """Get all parameter groups."""
        return self.groups.copy()
    
    def get_parameter_definition(self, param_name: str) -> Optional[ParameterDefinition]:
        """Get parameter definition by name."""
        return self.parameter_definitions.get(param_name)
    
    def get_all_parameter_names(self) -> List[str]:
        """Get all available parameter names."""
        return list(self.parameter_definitions.keys())