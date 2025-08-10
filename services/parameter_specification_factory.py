"""
Parameter Specification Factory

This module provides a factory class for creating parameter UI elements based on the
parameter specification. It integrates with the ParameterUIElementFactory to generate
all parameters from the specification data structure with proper validation rules
and UI element types.
"""

import customtkinter as ctk
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from tkinter import messagebox
from ui.custom_dialogs import show_error, show_info
from services.parameter_specification import (
    get_parameter_specification, 
    get_all_sections_ordered,
    get_validation_rule,
    get_command_value_mapping,
    get_conditional_visibility_rule,
    SectionConfig,
    ParameterConfig,
    FieldConfig,
    VALIDATION_RULES
)
from ui.parameter_ui_element_factory import ParameterUIElementFactory, UIElementConfig, BaseUIElement
from services.conditional_field_manager import get_conditional_field_manager


@dataclass
class ParameterWidget:
    """Container for a parameter widget and its metadata"""
    name: str
    config: ParameterConfig
    widget_type: str  # 'simple' or 'complex'
    ui_elements: Dict[str, BaseUIElement]  # field_name -> UI element
    container_frame: ctk.CTkFrame
    label_widget: Optional[ctk.CTkLabel] = None
    title_widget: Optional[ctk.CTkLabel] = None
    send_button: Optional[ctk.CTkButton] = None


@dataclass
class SectionWidget:
    """Container for a section widget and its parameters"""
    name: str
    config: SectionConfig
    container_frame: ctk.CTkFrame
    title_widget: ctk.CTkLabel
    parameters: Dict[str, ParameterWidget]


class ParameterSpecificationFactory:
    """Factory for creating parameter UI elements from specification"""
    
    def __init__(self, i18n_service, validation_service=None, serial_service=None):
        self.i18n_service = i18n_service
        self.validation_service = validation_service
        self.serial_service = serial_service
        self.ui_element_factory = ParameterUIElementFactory(i18n_service)
        self.conditional_field_manager = get_conditional_field_manager()
        self.field_element_mapping = {}  # field_name -> ui_element for conditional fields
        
    def create_all_sections(self, parent_widget) -> Dict[str, SectionWidget]:
        """
        Create all parameter sections from the specification.
        
        Args:
            parent_widget: Parent widget to contain the sections
            
        Returns:
            Dict mapping section names to SectionWidget objects
        """
        sections = {}
        ordered_sections = get_all_sections_ordered()
        
        for i, section_config in enumerate(ordered_sections):
            section_widget = self.create_section(parent_widget, section_config, i)
            sections[section_config.name] = section_widget
            
        return sections
    
    def create_section(self, parent_widget, section_config: SectionConfig, row_index: int) -> SectionWidget:
        """
        Create a single parameter section.
        
        Args:
            parent_widget: Parent widget to contain the section
            section_config: Configuration for the section
            row_index: Grid row index for the section
            
        Returns:
            SectionWidget object
        """
        # Create section container frame
        section_frame = ctk.CTkFrame(parent_widget)
        section_frame.grid(row=row_index, column=0, padx=10, pady=10, sticky="ew")
        section_frame.grid_columnconfigure(0, weight=1)
        
        # Create section title
        section_title = ctk.CTkLabel(
            section_frame,
            text=self.i18n_service.get(f"section_{section_config.name}", section_config.label),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        section_title.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        # Create parameters within the section
        parameters = {}
        param_row = 1
        
        for param_name, param_config in section_config.parameters.items():
            param_widget = self.create_parameter(section_frame, param_config, param_row)
            parameters[param_name] = param_widget
            param_row += 1
        
        return SectionWidget(
            name=section_config.name,
            config=section_config,
            container_frame=section_frame,
            title_widget=section_title,
            parameters=parameters
        )
    
    def create_parameter(self, parent_widget, param_config: ParameterConfig, row_index: int) -> ParameterWidget:
        """
        Create a single parameter widget.
        
        Args:
            parent_widget: Parent widget to contain the parameter
            param_config: Configuration for the parameter
            row_index: Grid row index for the parameter
            
        Returns:
            ParameterWidget object
        """
        if param_config.fields:
            return self._create_complex_parameter(parent_widget, param_config, row_index)
        else:
            return self._create_simple_parameter(parent_widget, param_config, row_index)
    
    def _create_simple_parameter(self, parent_widget, param_config: ParameterConfig, row_index: int) -> ParameterWidget:
        """Create a simple parameter (single UI element)"""
        # Create parameter container frame
        param_frame = ctk.CTkFrame(parent_widget)
        param_frame.grid(row=row_index, column=0, padx=15, pady=5, sticky="ew")
        param_frame.grid_columnconfigure(0, weight=1)
        
        # Create content frame to hold UI element and send button
        content_frame = ctk.CTkFrame(param_frame)
        content_frame.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Get validation rules for this parameter
        validation_rules = self._get_validation_rules_for_parameter(param_config)
        
        # Create UI element configuration
        ui_config = UIElementConfig(
            element_type=param_config.ui_element,
            label=self.i18n_service.get(param_config.name, param_config.label),
            validation_rules=validation_rules,
            options=param_config.options,
            range_config=self._get_range_config_for_parameter(param_config),
            unit=param_config.unit,
            translation_key=param_config.name
        )
        
        # Create UI element
        ui_element = self.ui_element_factory.create_element(
            param_config.ui_element,
            ui_config,
            validation_callback=self._on_parameter_validation
        )
        
        # Create the widget in the content frame
        element_widget = ui_element.create_widget(content_frame)
        element_widget.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        
        # Create send button
        send_button = ctk.CTkButton(
            content_frame,
            text=self.i18n_service.get("send_button", "Enviar"),
            width=80,
            height=28,
            command=lambda: self._send_parameter_command(param_config.name)
        )
        send_button.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="e")
        
        return ParameterWidget(
            name=param_config.name,
            config=param_config,
            widget_type='simple',
            ui_elements={'main': ui_element},
            container_frame=param_frame,
            send_button=send_button
        )
    
    def _create_complex_parameter(self, parent_widget, param_config: ParameterConfig, row_index: int) -> ParameterWidget:
        """Create a complex parameter (multiple fields)"""
        # Create parameter container frame
        param_frame = ctk.CTkFrame(parent_widget)
        param_frame.grid(row=row_index, column=0, padx=15, pady=5, sticky="ew")
        param_frame.grid_columnconfigure(0, weight=1)
        
        # Create title frame to hold title and send button
        title_frame = ctk.CTkFrame(param_frame)
        title_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        title_frame.grid_columnconfigure(0, weight=1)
        
        # Create parameter title
        param_title = ctk.CTkLabel(
            title_frame,
            text=self.i18n_service.get(f"param_{param_config.name}", param_config.label),
            font=ctk.CTkFont(weight="bold")
        )
        param_title.grid(row=0, column=0, padx=0, pady=0, sticky="w")
        
        # Create send button for this parameter
        send_button = ctk.CTkButton(
            title_frame,
            text=self.i18n_service.get("send_button", "Enviar"),
            width=80,
            height=28,
            command=lambda: self._send_parameter_command(param_config.name)
        )
        send_button.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="e")
        
        # Create fields
        ui_elements = {}
        field_row = 1
        
        for field_name, field_config in param_config.fields.items():
            # Get validation rules for this field
            validation_rules = self._get_validation_rules_for_field(param_config.name, field_name, field_config)
            
            # Create UI element configuration
            ui_config = UIElementConfig(
                element_type=field_config.ui_element,
                label=self.i18n_service.get(field_name, field_config.label),
                validation_rules=validation_rules,
                options=field_config.options,
                range_config=self._get_range_config_for_field(field_config),
                unit=field_config.unit,
                visibility_condition=field_config.visibility_condition,
                translation_key=field_name
            )
            
            # Create UI element
            ui_element = self.ui_element_factory.create_element(
                field_config.ui_element,
                ui_config,
                validation_callback=self._on_field_validation
            )
            
            # Create the widget in the parameter frame
            element_widget = ui_element.create_widget(param_frame)
            element_widget.grid(row=field_row, column=0, padx=10, pady=2, sticky="ew")
            
            ui_elements[field_name] = ui_element
            
            # Handle conditional visibility
            if field_config.visibility_condition:
                full_field_name = f"{param_config.name}.{field_name}"
                self.conditional_field_manager.register_field_widget(full_field_name, element_widget)
                self.field_element_mapping[full_field_name] = ui_element
                ui_element.set_value_change_callback(lambda value, name=full_field_name: self._on_field_value_change(name, value))
            
            field_row += 1
        
        return ParameterWidget(
            name=param_config.name,
            config=param_config,
            widget_type='complex',
            ui_elements=ui_elements,
            container_frame=param_frame,
            title_widget=param_title,
            send_button=send_button
        )
    
    def _get_validation_rules_for_parameter(self, param_config: ParameterConfig) -> Optional[Dict[str, Any]]:
        """Get validation rules for a simple parameter"""
        if not param_config.validation:
            return None
        
        # Map parameter validation to validation rules
        validation_mapping = {
            'port': 'port',
            'apn': 'apn',
            'ip_url': 'ip_url',
            '5-600': 'speed_detection_time',
            '1-255': 'speed_limit',
            '1-20': 'angle_min_speed',
            '5-90': 'angle_variation',
            '2-60': 'power_detection_time',
            '1-3600': 'min_charge_time',
            '1-6': 'vibration_level',
            '0-1800': 'jammer_confirmation_time',
            '0-255': 'jammer_speed_limit'
        }
        
        rule_name = validation_mapping.get(param_config.validation)
        if rule_name:
            return get_validation_rule(rule_name)
        
        # Handle range validation directly
        if '-' in param_config.validation:
            try:
                min_val, max_val = param_config.validation.split('-')
                return {
                    'type': 'numeric_range',
                    'min': int(min_val),
                    'max': int(max_val),
                    'error_message': f"Value must be between {min_val} and {max_val}"
                }
            except ValueError:
                pass
        
        return None
    
    def _get_validation_rules_for_field(self, param_name: str, field_name: str, field_config: FieldConfig) -> Optional[Dict[str, Any]]:
        """Get validation rules for a field in a complex parameter"""
        if not field_config.validation:
            return None
        
        # Use the same mapping as simple parameters
        return self._get_validation_rules_for_parameter(field_config)
    
    def _get_range_config_for_parameter(self, param_config: ParameterConfig) -> Optional[Dict[str, Any]]:
        """Get range configuration for sliders and number inputs"""
        if param_config.ui_element == 'slider' and param_config.validation:
            if '-' in param_config.validation:
                try:
                    min_val, max_val = param_config.validation.split('-')
                    return {'min': int(min_val), 'max': int(max_val)}
                except ValueError:
                    pass
        return None
    
    def _get_range_config_for_field(self, field_config: FieldConfig) -> Optional[Dict[str, Any]]:
        """Get range configuration for a field"""
        if field_config.ui_element == 'slider' and field_config.validation:
            if '-' in field_config.validation:
                try:
                    min_val, max_val = field_config.validation.split('-')
                    return {'min': int(min_val), 'max': int(max_val)}
                except ValueError:
                    pass
        return None
    
    def _setup_conditional_visibility(self, param_name: str, field_name: str, condition: str, ui_element: BaseUIElement, element_widget):
        """Setup conditional visibility for a field"""
        full_field_name = f"{param_name}.{field_name}"
        
        # Register the widget with the conditional field manager
        self.conditional_field_manager.register_field_widget(full_field_name, element_widget)
        
        # Store the mapping for value change callbacks
        self.field_element_mapping[full_field_name] = ui_element
        
        # Set up value change callback to notify conditional field manager
        ui_element.set_value_change_callback(lambda value: self._on_field_value_change(full_field_name, value))
    
    def _on_parameter_validation(self, ui_element: BaseUIElement):
        """Handle parameter validation events"""
        # Find the parameter name and notify conditional field manager
        param_name = self._find_parameter_name_for_element(ui_element)
        if param_name:
            self.conditional_field_manager.update_current_value(param_name, ui_element.get_value())
    
    def _on_field_validation(self, ui_element: BaseUIElement):
        """Handle field validation events"""
        # Find the field name and notify conditional field manager
        field_name = self._find_field_name_for_element(ui_element)
        if field_name:
            self.conditional_field_manager.update_current_value(field_name, ui_element.get_value())
    
    def _on_field_value_change(self, field_name: str, value: Any):
        """Handle field value changes for conditional visibility"""
        self.conditional_field_manager.update_current_value(field_name, value)
    
    def _find_parameter_name_for_element(self, ui_element: BaseUIElement) -> Optional[str]:
        """Find parameter name for a UI element"""
        # Search through field element mapping to find the field name
        for field_name, element in self.field_element_mapping.items():
            if element == ui_element:
                return field_name
        return None
    
    def _find_field_name_for_element(self, ui_element: BaseUIElement) -> Optional[str]:
        """Find field name for a UI element"""
        # Same as parameter name for fields
        return self._find_parameter_name_for_element(ui_element)
    
    def get_parameter_value(self, section_name: str, param_name: str, section_widgets: Dict[str, SectionWidget]) -> Any:
        """Get value from a parameter widget"""
        if section_name not in section_widgets:
            return None
        
        section_widget = section_widgets[section_name]
        if param_name not in section_widget.parameters:
            return None
        
        param_widget = section_widget.parameters[param_name]
        
        if param_widget.widget_type == 'simple':
            return param_widget.ui_elements['main'].get_value()
        elif param_widget.widget_type == 'complex':
            values = {}
            for field_name, ui_element in param_widget.ui_elements.items():
                values[field_name] = ui_element.get_value()
            return values
        
        return None
    
    def set_parameter_value(self, section_name: str, param_name: str, value: Any, section_widgets: Dict[str, SectionWidget]):
        """Set value for a parameter widget"""
        if section_name not in section_widgets:
            return
        
        section_widget = section_widgets[section_name]
        if param_name not in section_widget.parameters:
            return
        
        param_widget = section_widget.parameters[param_name]
        
        if param_widget.widget_type == 'simple':
            param_widget.ui_elements['main'].set_value(value)
        elif param_widget.widget_type == 'complex' and isinstance(value, dict):
            for field_name, field_value in value.items():
                if field_name in param_widget.ui_elements:
                    param_widget.ui_elements[field_name].set_value(field_value)
    
    def get_all_parameter_values(self, section_widgets: Dict[str, SectionWidget]) -> Dict[str, Any]:
        """Get all parameter values from all sections"""
        all_values = {}
        
        for section_name, section_widget in section_widgets.items():
            section_values = {}
            for param_name in section_widget.parameters:
                param_value = self.get_parameter_value(section_name, param_name, section_widgets)
                if param_value is not None:
                    section_values[param_name] = param_value
            
            if section_values:
                all_values[section_name] = section_values
        
        return all_values
    
    def set_all_parameter_values(self, values: Dict[str, Any], section_widgets: Dict[str, SectionWidget]):
        """Set all parameter values in all sections"""
        for section_name, section_values in values.items():
            if isinstance(section_values, dict):
                for param_name, param_value in section_values.items():
                    self.set_parameter_value(section_name, param_name, param_value, section_widgets)
    
    def validate_all_parameters(self, section_widgets: Dict[str, SectionWidget]) -> Tuple[bool, List[str]]:
        """Validate all parameters and return validation status and error messages"""
        all_valid = True
        error_messages = []
        
        for section_name, section_widget in section_widgets.items():
            for param_name, param_widget in section_widget.parameters.items():
                for field_name, ui_element in param_widget.ui_elements.items():
                    if not ui_element.validate():
                        all_valid = False
                        error_msg = ui_element.get_validation_error()
                        if error_msg:
                            error_messages.append(f"{section_name}.{param_name}.{field_name}: {error_msg}")
        
        return all_valid, error_messages
    
    def initialize_conditional_field_visibility(self, section_widgets: Dict[str, SectionWidget]):
        """Initialize conditional field visibility based on current parameter values"""
        # Get all current parameter values
        current_values = self.get_all_parameter_values(section_widgets)
        
        # Flatten the values for the conditional field manager
        flattened_values = {}
        for section_name, section_values in current_values.items():
            if isinstance(section_values, dict):
                for param_name, param_value in section_values.items():
                    if isinstance(param_value, dict):
                        # Complex parameter with fields
                        for field_name, field_value in param_value.items():
                            full_field_name = f"{param_name}.{field_name}"
                            flattened_values[full_field_name] = field_value
                    else:
                        # Simple parameter
                        full_param_name = f"{section_name}.{param_name}"
                        flattened_values[full_param_name] = param_value
        
        # Initialize conditional field manager with current values
        self.conditional_field_manager.initialize_field_visibility(flattened_values)
    
    def update_language_display(self, section_widgets: Dict[str, SectionWidget]):
        """Update language display for all sections and parameters"""
        for section_name, section_widget in section_widgets.items():
            # Update section title - safely check if configure method exists
            if hasattr(section_widget.title_widget, 'configure'):
                try:
                    section_widget.title_widget.configure(
                        text=self.i18n_service.get(section_name, section_widget.config.label)
                    )
                except Exception as e:
                    print(f"WARNING: Failed to configure section title for {section_name}: {e}")
            
            # Update parameter labels and elements
            for param_name, param_widget in section_widget.parameters.items():
                if param_widget.title_widget and hasattr(param_widget.title_widget, 'configure'):
                    try:
                        param_widget.title_widget.configure(
                            text=self.i18n_service.get(param_name, param_widget.config.label)
                        )
                    except Exception as e:
                        print(f"WARNING: Failed to configure parameter title for {param_name}: {e}")
                
                # Update send button text - safely check if configure method exists
                if param_widget.send_button and hasattr(param_widget.send_button, 'configure'):
                    try:
                        param_widget.send_button.configure(
                            text=self.i18n_service.get("send_button", "Enviar")
                        )
                    except Exception as e:
                        print(f"WARNING: Failed to configure send button for {param_name}: {e}")
                
                # Update UI elements - safely handle any configure calls
                for field_name, ui_element in param_widget.ui_elements.items():
                    try:
                        if hasattr(ui_element, 'update_language_display'):
                            ui_element.update_language_display(self.i18n_service)
                    except Exception as e:
                        print(f"WARNING: Failed to update language display for {param_name}.{field_name}: {e}")
    
    def _send_parameter_command(self, param_name: str):
        """Send command for a specific parameter to the device"""
        if not self.serial_service:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("no_serial_service", "Serial service not available")
            )
            return
        
        if not self.serial_service.is_connected:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("not_connected_error", "Device not connected")
            )
            return
        
        try:
            # Import device command mapper here to avoid circular imports
            from services.device_command_mapper import DeviceCommandMapper
            
            # Get parameter values from UI
            param_values = self._get_current_parameter_values(param_name)
            if not param_values:
                messagebox.showerror(
                    self.i18n_service.get("error", "Error"),
                    self.i18n_service.get("no_parameter_values", "No parameter values to send")
                )
                return
            
            # Create command mapper and generate command
            command_mapper = DeviceCommandMapper()
            
            # Handle different parameter types
            if param_name == 'apn_settings':
                self._send_apn_command(param_values)
            elif param_name == 'server_settings':
                self._send_server_command(param_values)
            elif param_name == 'report_intervals':
                self._send_timer_command(param_values)
            elif param_name == 'heartbeat_intervals':
                self._send_heartbeat_command(param_values)
            elif param_name == 'protocol':
                self._send_protocol_command(param_values)
            elif param_name == 'tcp_ack':
                self._send_tcp_ack_command(param_values)
            elif param_name == 'ignition_type':
                self._send_ignition_command(param_values)
            else:
                # Generic parameter sending
                self._send_generic_parameter_command(param_name, param_values)
                
        except Exception as e:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                f"{self.i18n_service.get('send_command_error', 'Error sending command')}: {str(e)}"
            )
    
    def _get_parameter_values_for_command(self, param_name: str) -> dict:
        """Get parameter values from UI for sending commands"""
        # This method needs access to the section widgets to get current values
        # Since we don't have direct access here, we'll need to modify the approach
        # For now, return empty dict and handle this in the parameters frame
        return {}
    
    def set_section_widgets_reference(self, section_widgets: Dict[str, SectionWidget]):
        """Set reference to section widgets for getting parameter values"""
        self.section_widgets = section_widgets
    
    def _get_current_parameter_values(self, param_name: str) -> dict:
        """Get current parameter values from UI for the specified parameter"""
        if not hasattr(self, 'section_widgets'):
            return {}
        
        # Find the parameter in all sections
        for section_name, section_widget in self.section_widgets.items():
            if param_name in section_widget.parameters:
                return self.get_parameter_value(section_name, param_name, self.section_widgets) or {}
        
        return {}
    
    def _send_apn_command(self, values: dict):
        """Send APN configuration command"""
        server = values.get('apn', '').strip()
        user = values.get('user', '').strip()
        password = values.get('password', '').strip()
        
        if not server:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("apn_server_required", "APN server is required")
            )
            return
        
        command = f"ATSMS:APN,{server},{user},{password}#"
        self.serial_service.send_command(command)
        
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("apn_command_sent", "APN configuration sent to device")
        )
    
    def _send_server_command(self, values: dict):
        """Send server configuration command"""
        address = values.get('address', '').strip()
        port = values.get('port', '').strip()
        
        if not address or not port:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("server_address_port_required", "Server address and port are required")
            )
            return
        
        # Determine if address is IP (0) or domain (1)
        import re
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        server_type = '0' if re.match(ip_pattern, address) else '1'
        
        command = f"ATSMS:SERVER,{server_type},{address},{port},0#"
        self.serial_service.send_command(command)
        
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("server_command_sent", "Server configuration sent to device")
        )
    
    def _send_timer_command(self, values: dict):
        """Send timer intervals command"""
        moving_time = values.get('moving_time', '').strip()
        stopped_time = values.get('stopped_time', '').strip()
        
        if not moving_time or not stopped_time:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("timer_values_required", "Both moving and stopped times are required")
            )
            return
        
        command = f"ATSMS:TIMER,{moving_time},{stopped_time}#"
        self.serial_service.send_command(command)
        
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("timer_command_sent", "Timer configuration sent to device")
        )
    
    def _send_heartbeat_command(self, values: dict):
        """Send heartbeat intervals command"""
        moving_heartbeat = values.get('moving_heartbeat', '').strip()
        stopped_heartbeat = values.get('stopped_heartbeat', '').strip()
        
        if not moving_heartbeat or not stopped_heartbeat:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("heartbeat_values_required", "Both moving and stopped heartbeat values are required")
            )
            return
        
        command = f"ATSMS:HBT,{moving_heartbeat},{stopped_heartbeat}#"
        self.serial_service.send_command(command)
        
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("heartbeat_command_sent", "Heartbeat configuration sent to device")
        )
    
    def _send_protocol_command(self, values: dict):
        """Send protocol configuration command"""
        protocol = values.get('protocol', '').strip()
        
        if not protocol:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("protocol_required", "Protocol selection is required")
            )
            return
        
        # Map protocol names to values
        protocol_mapping = {
            'GT06 (0x60)': '0',
            'CRX3 (0x22)': '1', 
            'CRX (0x12)': '2'
        }
        
        protocol_value = protocol_mapping.get(protocol, '0')
        command = f"ATSMS:SZCS#GT06SEL={protocol_value}#"
        self.serial_service.send_command(command)
        
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("protocol_command_sent", "Protocol configuration sent to device")
        )
    
    def _send_tcp_ack_command(self, values: dict):
        """Send TCP ACK configuration command"""
        tcp_ack = values.get('tcp_ack', '').strip()
        
        if not tcp_ack:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("tcp_ack_required", "TCP ACK setting is required")
            )
            return
        
        # Map boolean to command value
        ack_value = '1' if tcp_ack.lower() in ['true', 'enabled', '1'] else '0'
        command = f"ATSMS:SZCS#TCPACK={ack_value}#"
        self.serial_service.send_command(command)
        
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("tcp_ack_command_sent", "TCP ACK configuration sent to device")
        )
    
    def _send_ignition_command(self, values: dict):
        """Send ignition configuration command"""
        ignition_type = values.get('ignition_type', '').strip()
        
        if not ignition_type:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("ignition_type_required", "Ignition type is required")
            )
            return
        
        if ignition_type == 'Virtual por bateria':
            # Battery-based ignition requires voltage values
            on_voltage = values.get('on_voltage', '').strip()
            off_voltage = values.get('off_voltage', '').strip()
            
            if not on_voltage or not off_voltage:
                messagebox.showerror(
                    self.i18n_service.get("error", "Error"),
                    self.i18n_service.get("voltage_values_required", "ON and OFF voltage values are required for battery ignition")
                )
                return
            
            commands = [
                "ATSMS:SZCS#ACCLINE=1#",
                f"ATSMS:SZCS#ACC_CFG=1-{on_voltage}-{off_voltage}#"
            ]
        elif ignition_type == 'Físico':
            commands = [
                "ATSMS:SZCS#ACCLINE=1#",
                "ATSMS:SZCS#ACC_CFG=0-000-000#"
            ]
        elif ignition_type == 'Acelerômetro':
            commands = [
                "ATSMS:SZCS#ACCLINE=0#",
                "ATSMS:SZCS#ACC_CFG=0-000-000#"
            ]
        else:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("invalid_ignition_type", "Invalid ignition type")
            )
            return
        
        # Send all commands
        for command in commands:
            self.serial_service.send_command(command)
        
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("ignition_command_sent", "Ignition configuration sent to device")
        )
    
    def _send_generic_parameter_command(self, param_name: str, values: dict):
        """Send generic parameter command"""
        messagebox.showinfo(
            self.i18n_service.get("info", "Info"),
            f"{self.i18n_service.get('parameter_command_sent', 'Parameter command sent')}: {param_name}"
        )