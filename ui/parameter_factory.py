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
                
                # If we have access to the command mapper, use it with validation
                if command_mapper:
                    command = command_mapper.get_command(self.definition.name, value, 
                                                       confirm_destructive=True, validate_command=True)
                else:
                    # Handle special cases for server parameters
                    if self.definition.name in ['server_ip', 'server_port']:
                        # Server parameters should not be sent individually
                        # They are handled by the ServerParameterGroup
                        self._show_error("Use the group 'Send' button to configure server settings")
                        return
                    else:
                        # Fall back to the template if no command mapper is available
                        command = self.definition.at_command_template.format(value=value)
                
                self.send_command_callback(command)
                
                # Show success message if command was sent successfully
                self._log_success(f"Command sent successfully: {self.definition.name}")
                
            except ValueError as e:
                error_msg = str(e)
                
                # Check if this is a validation error and provide better feedback
                if "Command validation failed" in error_msg:
                    # Extract the core error message and suggestions
                    if "Suggestions:" in error_msg:
                        parts = error_msg.split("Suggestions:")
                        core_error = parts[0].replace("Command validation failed for " + self.definition.name + ":", "").strip()
                        suggestions = parts[1].strip()
                        
                        # Show the core error in the UI
                        self._show_error(f"Validation failed: {core_error}")
                        
                        # Log suggestions for the user
                        if hasattr(self, '_log_message'):
                            self._log_message(f"Suggestions for {self.definition.name}: {suggestions}")
                    else:
                        core_error = error_msg.replace("Command validation failed for " + self.definition.name + ":", "").strip()
                        self._show_error(f"Validation failed: {core_error}")
                else:
                    self._show_error(str(e))
                return
                
            except KeyError as e:
                # Handle missing format keys
                missing_key = str(e).strip("'")
                self._show_error(f"Missing required parameter: {missing_key}")
                return
    
    def _show_error(self, message: str) -> None:
        """Show validation error message."""
        if self.error_label:
            self.error_label.configure(text=message, text_color="red")
    
    def _clear_error(self) -> None:
        """Clear validation error message."""
        if self.error_label:
            self.error_label.configure(text="", text_color="gray")
    
    def _log_success(self, message: str) -> None:
        """Log a success message."""
        # Try to access the app's log frame if available
        try:
            # This is a bit of a hack, but we need to access the app somehow
            import tkinter as tk
            root = self.widget
            while root and not isinstance(root, tk.Tk):
                root = root.master
            
            if root and hasattr(root, 'app') and hasattr(root.app, 'log_frame'):
                root.app.log_frame.log_message(f"SUCCESS: {message}\n")
        except:
            pass  # Ignore errors in logging
    
    def _log_message(self, message: str) -> None:
        """Log a general message."""
        # Try to access the app's log frame if available
        try:
            # This is a bit of a hack, but we need to access the app somehow
            import tkinter as tk
            root = self.widget
            while root and not isinstance(root, tk.Tk):
                root = root.master
            
            if root and hasattr(root, 'app') and hasattr(root.app, 'log_frame'):
                root.app.log_frame.log_message(f"INFO: {message}\n")
        except:
            pass  # Ignore errors in logging
    
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
    
    def add_update_indicator(self, value_changed: bool = True) -> None:
        """
        Add visual indicator to show this parameter was updated from device.
        
        Args:
            value_changed: True if the value changed, False if it was the same
        """
        try:
            if self.widget:
                if value_changed:
                    # Green border for changed values
                    original_border_color = self.widget.cget("border_color")
                    self.widget.configure(border_color="#00ff00", border_width=2)
                    
                    # Schedule removal after 3 seconds
                    if hasattr(self, '_master_widget'):
                        self._master_widget.after(3000, lambda: self._remove_update_indicator(original_border_color))
                else:
                    # Blue border for unchanged values
                    original_border_color = self.widget.cget("border_color")
                    self.widget.configure(border_color="#0066cc", border_width=1)
                    
                    # Schedule removal after 2 seconds
                    if hasattr(self, '_master_widget'):
                        self._master_widget.after(2000, lambda: self._remove_update_indicator(original_border_color))
                        
        except Exception as e:
            print(f"WARNING: Failed to add update indicator: {str(e)}")
    
    def _remove_update_indicator(self, original_border_color) -> None:
        """Remove the visual update indicator."""
        try:
            if self.widget:
                self.widget.configure(border_color=original_border_color, border_width=0)
        except Exception as e:
            print(f"WARNING: Failed to remove update indicator: {str(e)}")
    
    def _create_base_frame(self, parent) -> ctk.CTkFrame:
        """Create the base frame with label, input, and send button."""
        frame = ctk.CTkFrame(parent)
        frame.grid_columnconfigure(1, weight=1)  # Make input column expandable
        
        # Store reference to master widget for scheduling callbacks
        self._master_widget = parent
        
        # Parameter label - store reference for language updates
        self.param_label = ctk.CTkLabel(frame, text=self.i18n.get(self.definition.display_label, self.definition.display_label))
        self.param_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Error label (initially empty)
        self.error_label = ctk.CTkLabel(frame, text="", text_color="red", font=ctk.CTkFont(size=10))
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
        # self.send_button = ctk.CTkButton(
        #     frame, 
        #     text=self.i18n.get("send", "Send"), 
        #     width=60, 
        #     command=self.send_command
        # )
        # self.send_button.grid(row=0, column=2, padx=(5, 10), pady=5)
        
        # Add validation on focus out and key release
        self.widget.bind("<FocusOut>", self._on_focus_out)
        self.widget.bind("<KeyRelease>", self._on_key_release)
        
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
            
    def _on_key_release(self, event) -> None:
        """Validate on key release."""
        # Only validate if the field is not empty
        text = self.widget.get().strip()
        if text:
            # For numeric parameters, check if the input is a valid number
            try:
                # Try to convert to int or float based on the validation rules
                if self.definition.validation_rules.get('integer', True):
                    int(text)
                else:
                    float(text)
            except ValueError:
                # If conversion fails, show an error message
                display_name = self.i18n.get(self.definition.display_label, self.definition.display_label)
                error_message = self.i18n.get('validation_numeric_required', '{param_name} must be a numeric value').format(param_name=display_name)
                self._show_error(error_message)
                return
            
            # Perform regular validation
            validation_result = self.validate()
            if not validation_result.is_valid:
                self._show_error(validation_result.error_message)
            else:
                self._clear_error()


class TextParameter(BaseParameter):
    """Text parameter with entry field."""
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        """Create text input widget with validation."""
        frame = self._create_base_frame(parent)
        
        # Entry field
        self.widget = ctk.CTkEntry(frame, width=150)
        self.widget.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Set default value if provided
        if self.definition.default_value is not None:
            self.widget.insert(0, str(self.definition.default_value))
        
        # Send button
        # self.send_button = ctk.CTkButton(
        #     frame, 
        #     text=self.i18n.get("send", "Send"), 
        #     width=60, 
        #     command=self.send_command
        # )
        # self.send_button.grid(row=0, column=2, padx=(5, 10), pady=5)
        
        # Add validation on focus out and key release
        self.widget.bind("<FocusOut>", self._on_focus_out)
        self.widget.bind("<KeyRelease>", self._on_key_release)
        
        return frame
    
    def get_value(self) -> Optional[str]:
        """Get text value from entry field."""
        if not self.widget:
            return None
        
        text = self.widget.get().strip()
        if not text:
            return None
        
        return text
    
    def set_value(self, value: Any) -> None:
        """Set text value in entry field."""
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
            
    def _on_key_release(self, event) -> None:
        """Validate on key release."""
        # Only validate if the field is not empty
        if self.widget.get().strip():
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
        self.radio_var = None
        self.radio_buttons = []
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        """Create radio button group widget."""
        frame = self._create_base_frame(parent)
        
        # Get allowed values from validation rules
        allowed_values = self.definition.validation_rules.get('allowed_values', [])
        
        # Create radio button variable
        self.radio_var = ctk.StringVar(value=allowed_values[0] if allowed_values else "")
        
        # Create radio buttons in a horizontal layout
        radio_frame = ctk.CTkFrame(frame)
        radio_frame.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        for i, value in enumerate(allowed_values):
            radio_button = ctk.CTkRadioButton(
                radio_frame,
                text=self.i18n.get(value.lower(), value),
                variable=self.radio_var,
                value=value
            )
            radio_button.grid(row=0, column=i, padx=5, pady=5, sticky="w")
            self.radio_buttons.append(radio_button)
        
        # Set default value if provided
        if self.definition.default_value is not None and self.definition.default_value in allowed_values:
            self.radio_var.set(self.definition.default_value)
        
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
        if not self.radio_var:
            return None
        return self.radio_var.get()
    
    def set_value(self, value: Any) -> None:
        """Set selected radio button value."""
        if self.radio_var and value is not None:
            self.radio_var.set(str(value))
    
    def update_language_display(self, i18n_service) -> None:
        """Update radio button labels for language changes."""
        super().update_language_display(i18n_service)
        
        # Update radio button text
        allowed_values = self.definition.validation_rules.get('allowed_values', [])
        for i, (button, value) in enumerate(zip(self.radio_buttons, allowed_values)):
            button.configure(text=self.i18n.get(value.lower(), value))


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


class ServerParameterGroup(ParameterGroup):
    """A special parameter group for server settings that includes a single send button."""
    def create_widget(self, parent) -> ctk.CTkFrame:
        """Create the group frame with all parameters and a single send button."""
        super().create_widget(parent)

        # Add a single send button for the entire group
        send_button = ctk.CTkButton(
            self.frame, 
            text=self.i18n.get("send", "Send"), 
            width=60, 
            command=self.send_group_command
        )
        send_button.grid(row=len(self.parameters) + 1, column=0, padx=10, pady=10, sticky="ew")

        return self.frame

    def send_group_command(self) -> None:
        """Validate and send combined server command with IP and port."""
        all_valid = True
        server_ip = None
        server_port = None
        
        # Validate all parameters and collect values
        for parameter in self.parameters:
            validation_result = parameter.validate()
            if not validation_result.is_valid:
                all_valid = False
                parameter._show_error(validation_result.error_message)
            else:
                parameter._clear_error()
                # Collect parameter values
                if parameter.definition.name == 'server_ip':
                    server_ip = parameter.get_value()
                elif parameter.definition.name == 'server_port':
                    server_port = parameter.get_value()

        if all_valid and server_ip and server_port:
            # Send combined server command with both IP and port
            # Format: ATSMS:SERVER,0,IP,PORT,0#
            combined_command = f"ATSMS:SERVER,0,{server_ip},{server_port},0#"
            
            # Use the send command callback from the first parameter
            if self.parameters:
                self.parameters[0].send_command_callback(combined_command)
                
            # Log success message
            if hasattr(self.parameters[0], '_log_success'):
                self.parameters[0]._log_success(f"Server configuration sent: {server_ip}:{server_port}")
        elif all_valid:
            # Show error if missing values
            error_msg = "Both server IP and port are required"
            for parameter in self.parameters:
                parameter._show_error(error_msg)


class ParameterFactory:
    """Factory class for creating parameter instances based on definitions."""
    
    def __init__(self, validation_service: ValidationService, i18n_service, 
                 send_command_callback: Callable[[str], None]):
        self.validation_service = validation_service
        self.i18n_service = i18n_service
        self.send_command_callback = send_command_callback
        self.command_mapper = DeviceCommandMapper(validation_service, i18n_service)
        self.parameter_definitions = self._init_parameter_definitions()
    
    def _create_parameter_from_definition(self, definition: ParameterDefinition) -> BaseParameter:
        """Create a parameter instance based on its definition."""
        parameter_classes = {
            'numeric': NumericParameter,
            'text': TextParameter,
            'dropdown': DropdownParameter,
            'radio': RadioParameter
        }
        
        parameter_class = parameter_classes.get(definition.param_type)
        if not parameter_class:
            raise ValueError(f"Unknown parameter type: {definition.param_type}")
        
        parameter = parameter_class(
            definition, 
            self.validation_service, 
            self.i18n_service, 
            self.send_command_callback
        )
        
        # Inject command mapper for parameters that need it
        parameter.command_mapper = self.command_mapper
        
        return parameter
    
    def create_group(self, name: str, display_label: str, 
                    parameter_definitions: Optional[List[ParameterDefinition]] = None) -> ParameterGroup:
        """Create a parameter group with optional parameters."""
        if name == "server":
            group = ServerParameterGroup(name, display_label, self.i18n_service)
        else:
            group = ParameterGroup(name, display_label, self.i18n_service)
        
        if parameter_definitions:
            for definition in parameter_definitions:
                parameter = self.create_parameter(definition)
                group.add_parameter(parameter)
        
        return group
    
    def _init_parameter_definitions(self) -> Dict[str, ParameterDefinition]:
        """Initialize parameter definitions from validation rules and command templates."""
        definitions = {}
        
        # Define parameter configurations with their UI properties
        param_configs = {
            'server_ip': {
                'param_type': 'text',
                'display_label': 'server_url_ip',
                'help_text': 'Enter server URL or IP address',
                'at_command_template': 'ATSMS:SERVER,0,{value},{port},0#',  # Requires port context
                'group': 'server'
            },
            'server_port': {
                'param_type': 'numeric',
                'display_label': 'server_port',
                'help_text': 'Enter server port number',
                'at_command_template': 'ATSMS:SERVER,0,{ip},{value},0#',  # Requires ip context
                'group': 'server'
            },
            'gt06_protocol': {
                'param_type': 'dropdown',
                'display_label': 'gt06_protocol',
                'help_text': 'Select GT06 protocol version',
                'at_command_template': 'ATSMS:PROTOCOL,{value}#',
                'group': 'protocol'
            },
            'tcp_ack_config': {
                'param_type': 'radio',
                'display_label': 'tcp_ack_config',
                'help_text': 'Configure TCP+ACK response',
                'at_command_template': 'ATSMS:TCPACK,{value}#',
                'group': 'protocol'
            },
            'vibration': {
                'param_type': 'numeric',
                'display_label': 'vibration',
                'help_text': 'Set vibration sensitivity (0-255)',
                'at_command_template': 'ATSMS:VIBRATION,{value}#',
                'group': 'sensors'
            },
            'sensitivity': {
                'param_type': 'numeric',
                'display_label': 'sensitivity',
                'help_text': 'Set sensitivity level (1-10)',
                'at_command_template': 'ATSMS:SENSITIVITY,{value}#',
                'group': 'sensors'
            },
            'curve_sensor': {
                'param_type': 'dropdown',
                'display_label': 'curve_sensor',
                'help_text': 'Select curve sensor mode',
                'at_command_template': 'ATSMS:CURVE,{value}#',
                'group': 'sensors'
            },
            'ignition_type': {
                'param_type': 'radio',
                'display_label': 'ignition_type',
                'help_text': 'Select ignition detection type',
                'at_command_template': 'ATSMS:IGNITION,{value}#',
                'group': 'sensors'
            },
            'timer_ign_on': {
                'param_type': 'numeric',
                'display_label': 'timer_ign_on',
                'help_text': 'Timer when ignition is on (seconds)',
                'at_command_template': 'ATSMS:TIMER,ON,{value}#',
                'group': 'timers'
            },
            'timer_ign_off': {
                'param_type': 'numeric',
                'display_label': 'timer_ign_off',
                'help_text': 'Timer when ignition is off (seconds)',
                'at_command_template': 'ATSMS:TIMER,OFF,{value}#',
                'group': 'timers'
            },
            'heartbeat_ign_on': {
                'param_type': 'numeric',
                'display_label': 'heartbeat_ign_on',
                'help_text': 'Heartbeat interval when ignition is on (seconds)',
                'at_command_template': 'ATSMS:HEARTBEAT,ON,{value}#',
                'group': 'timers'
            },
            'heartbeat_ign_off': {
                'param_type': 'numeric',
                'display_label': 'heartbeat_ign_off',
                'help_text': 'Heartbeat interval when ignition is off (seconds)',
                'at_command_template': 'ATSMS:HEARTBEAT,OFF,{value}#',
                'group': 'timers'
            },
            'heartbeat_interval': {
                'param_type': 'dropdown',
                'display_label': 'heartbeat_interval',
                'help_text': 'Select heartbeat interval',
                'at_command_template': 'ATSMS:HEARTBEAT,{value}#',
                'group': 'timers'
            },
            'lock_type': {
                'param_type': 'radio',
                'display_label': 'lock_type',
                'help_text': 'Select lock type',
                'at_command_template': 'ATSMS:LOCK,{value}#',
                'group': 'security'
            }
        }
        
        # Create ParameterDefinition objects
        for param_name, config in param_configs.items():
            # Get validation rules from validation service
            validation_rules = self.validation_service.validation_rules.get(param_name, {})
            
            # Create parameter definition
            definitions[param_name] = ParameterDefinition(
                name=param_name,
                param_type=config['param_type'],
                display_label=config['display_label'],
                help_text=config['help_text'],
                at_command_template=config['at_command_template'],
                validation_rules=validation_rules,
                group=config['group']
            )
        
        return definitions
    
    def get_parameter_definition(self, param_name: str) -> Optional[ParameterDefinition]:
        """Get parameter definition by name."""
        return self.parameter_definitions.get(param_name)
    
    def create_parameter(self, param_name: str) -> Optional[BaseParameter]:
        """Create a parameter instance by name."""
        definition = self.get_parameter_definition(param_name)
        if not definition:
            return None
        
        return self._create_parameter_from_definition(definition)
    
    def get_all_groups(self) -> List[str]:
        """Get all unique group names from parameter definitions."""
        groups = set()
        for definition in self.parameter_definitions.values():
            groups.add(definition.group)
        return sorted(list(groups))
    
    def get_parameters_by_group(self, group_name: str) -> List[str]:
        """Get all parameter names that belong to a specific group."""
        parameters = []
        for param_name, definition in self.parameter_definitions.items():
            if definition.group == group_name:
                parameters.append(param_name)
        return parameters





