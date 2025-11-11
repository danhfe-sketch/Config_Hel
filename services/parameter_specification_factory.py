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
            
            # Set value change callback for all fields to handle conditional logic
            full_field_name = f"{param_config.name}.{field_name}"
            ui_element.set_value_change_callback(lambda value, name=full_field_name: self._on_field_value_change(name, value))

            # Handle conditional visibility registration
            if field_config.visibility_condition:
                self.conditional_field_manager.register_field_widget(full_field_name, element_widget)
                self.field_element_mapping[full_field_name] = ui_element
            
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
    
    def _clean_time_parameter_value(self, param_name: str, field_name: str, field_value: Any) -> Any:
        """
        Clean time parameter values to show only numeric values.
        
        Args:
            param_name: Name of the parameter (e.g., 'report_intervals')
            field_name: Name of the field (e.g., 'moving_time')
            field_value: Raw field value (e.g., '60s' or 'ACC OFF:120s')
            
        Returns:
            Cleaned value for time parameters, original value for others
        """
        # Define time parameters and their fields that need cleaning
        time_parameters = {
            'report_intervals': ['moving_time', 'stopped_time'],
            'heartbeat_intervals': ['moving_heartbeat', 'stopped_heartbeat'],
            'sleep_time': ['sleep_time'],
            'speed_alert': ['detection_time'],
            'power_detection': ['power_detection_time'],
            'charge_settings': ['min_charge_time'],
            'jammer_detection': ['jammer_confirmation_time']
        }
        
        # Check if this is a time parameter field that needs cleaning
        if param_name in time_parameters and field_name in time_parameters[param_name]:
            if isinstance(field_value, str):
                cleaned_value = self._extract_numeric_value_from_time_string(field_value)
                print(f"DEBUG: Time parameter cleaning - {param_name}.{field_name}: '{field_value}' -> '{cleaned_value}'")
                return cleaned_value
        
        return field_value
    
    def _extract_numeric_value_from_time_string(self, time_string: str) -> str:
        """
        Extract numeric value from time parameter strings.
        
        Examples:
        - "60s" -> "60"
        - "ACC OFF:120s" -> "120"
        - "180" -> "180"
        
        Args:
            time_string: Time string that may contain units and prefixes
            
        Returns:
            str: Numeric value only
        """
        if not time_string:
            return ""
        
        # Extract all digits from the string
        import re
        digits = re.findall(r'\d+', str(time_string))
        
        # Return the last number found (handles cases like "ACC OFF:120s")
        return digits[-1] if digits else ""

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
                    # Apply time parameter cleaning for time-related fields
                    cleaned_value = self._clean_time_parameter_value(param_name, field_name, field_value)
                    param_widget.ui_elements[field_name].set_value(cleaned_value)
    
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
        print(f"Sending command for parameter: {param_name}")
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
            elif param_name == 'speed_alert':
                self._send_speed_alert_command(param_values)
            elif param_name == 'speed_buzzer':
                self._send_speed_buzzer_command(param_values)
            elif param_name == 'sleep_mode':
                self._send_sleep_mode_command(param_values)
            elif param_name == 'sleep_time':
                self._send_sleep_time_command(param_values)
            elif param_name == 'angle_report':
                self._send_angle_report_command(param_values)
            elif param_name == 'backup_battery_alert':
                self._send_backup_battery_alert_command(param_values)
            elif param_name == 'main_power_alert':
                self._send_main_power_alert_command(param_values)
            elif param_name == 'vibration_sensitivity':
                self._send_vibration_sensitivity_command(param_values)
            elif param_name == 'vibration_window':
                self._send_vibration_window_command(param_values)
            elif param_name == 'jammer_detection':
                self._send_jammer_detection_command(param_values)
            elif param_name == 'jammer_relay_action':
                self._send_jammer_relay_action_command(param_values)
            elif param_name == 'odometer':
                self._send_odometer_command(param_values)
            elif param_name == 'hourmeter':
                self._send_hourmeter_command(param_values)
            elif param_name == 'network_settings':
                self._send_network_settings_command(param_values)
            elif param_name == 'source_off_type':
                self._send_source_off_type_command(param_values)
            elif param_name == 'relay_control':
                self._send_relay_control_command(param_values)
            elif param_name == 'sends_control':
                self._send_sends_control_command(param_values)
            elif param_name in ['movement_alert', 'moving_alert', 'moving']:
                print(f"DEBUG: Sending moving alert command with values: {param_values}")
                # Format enabled correctly as boolean
                enabled = bool(param_values.get('enabled', False))
                radius = param_values.get('radius', 1000)
                alert_type = param_values.get('alert_type', 'Apenas GPRS')
                
                # Format command
                if not enabled:
                    command = "ATSMS:MOVING,OFF#"
                else:
                    notification_mode = 1 if alert_type == 'SMS+GPRS' else 0
                    command = f"ATSMS:MOVING,ON,{radius},{notification_mode}#"
                
                print(f"DEBUG: Sending command: {command}")
                if self.serial_service:
                    self.serial_service.send_command(command, 'moving_alert', bypass_validation=True)
                else:
                    print("ERROR: No serial service available to send command")
            elif param_name == 'motion_sensor_alert':
                self._send_motion_sensor_alert_command(param_values)
            elif param_name == 'distance_movement_action':
                self._send_distance_movement_action_command(param_values)
            elif param_name == 'acc_on_alert':
                self._send_acc_on_alert_command(param_values)
            elif param_name == 'acc_off_alert':
                self._send_acc_off_alert_command(param_values)
            elif param_name == 'backup_battery_protection_voltage':
                self._send_backup_battery_protection_voltage_command(param_values)
            else:
                # Generic parameter sending
                self._send_generic_parameter_command(param_name, param_values)
                
        except Exception as e:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                f"{self.i18n_service.get('send_command_error', 'Error sending command')}: {str(e)}"
            )
    
    def _get_current_parameter_values(self, param_name: str) -> dict:
        """Get current parameter values from UI for sending commands"""
        if not hasattr(self, 'section_widgets') or not self.section_widgets:
            return {}
        
        # First, try to find the parameter directly in section widgets
        for section_name, section_widget in self.section_widgets.items():
            if param_name in section_widget.parameters:
                param_widget = section_widget.parameters[param_name]
                values = {}
                
                # Extract values from UI elements.
                # Prefer the UI element's display/raw string (get_display_value) when available
                # so formatting like leading zeros is preserved for command construction.
                for field_name, ui_element in param_widget.ui_elements.items():
                    try:
                        # Use raw/display value if element provides it and it's not empty
                        display_value = None
                        if hasattr(ui_element, 'get_display_value'):
                            try:
                                display_value = ui_element.get_display_value()
                            except Exception:
                                display_value = None
                        
                        if display_value is not None and str(display_value) != '':
                            values[field_name] = display_value
                        else:
                            # Fallback to typed value
                            value = ui_element.get_value()
                            if isinstance(ui_element, ToggleSwitchElement):
                                # For toggle switches, ensure boolean conversion
                                values[field_name] = bool(value)
                            else:
                                values[field_name] = value
                    except Exception as e:
                        print(f"WARNING: Failed to get value for {param_name}.{field_name}: {e}")
                        values[field_name] = None
                
                # If this is a simple parameter with only one field, also add it with the parameter name as key
                if len(param_widget.ui_elements) == 1:
                    single_value = list(values.values())[0]
                    values[param_name] = single_value
                
                # Convert enabled to boolean if needed
                if 'enabled' in values and not isinstance(values['enabled'], bool):
                    values['enabled'] = bool(values['enabled'])
                
                # Debug: log the captured values and their types to help diagnose formatting issues
                try:
                    print(f"DEBUG: _get_current_parameter_values - captured values for '{param_name}': {values}")
                    for k, v in values.items():
                        try:
                            print(f"DEBUG: _get_current_parameter_values - field '{k}' type: {type(v).__name__}, repr: {v!r}")
                        except Exception:
                            print(f"DEBUG: _get_current_parameter_values - field '{k}' value (unprintable)")
                except Exception:
                    pass
                
                return values
        
        # If not found directly, try to use the existing get_parameter_value method
        # This handles the case where we need to get values from section.parameter structure
        try:
            # Map common parameter names to their section locations
            section_mapping = {
                'protocol': ('service_parameters', 'protocol'),
                'tcp_ack': ('service_parameters', 'tcp_ack'),
                'speed_buzzer': ('speed', 'speed_buzzer'),
                'sleep_mode': ('power_saving', 'sleep_mode'),
                'sleep_time': ('power_saving', 'sleep_time'),
                'backup_battery_alert': ('battery_alerts', 'backup_battery_alert'),
                'odometer': ('miscellaneous', 'odometer'),
                'hourmeter': ('miscellaneous', 'hourmeter')
            }
            
            if param_name in section_mapping:
                section_name, param_key = section_mapping[param_name]
                if hasattr(self, 'get_parameter_value'):
                    value = self.get_parameter_value(section_name, param_key, self.section_widgets)
                    if value is not None:
                        # Return the value in the expected format
                        return {param_name: value}
        except Exception as e:
            print(f"WARNING: Failed to get parameter value using section mapping for {param_name}: {e}")
        
        return {}
    
    def _get_parameter_values_for_command(self, param_name: str) -> dict:
        """Get parameter values from UI for sending commands"""
        # This method needs access to the section widgets to get current values
        # Since we don't have direct access here, we'll need to modify the approach
        # For now, return empty dict and handle this in the parameters frame
        return {}
    
    def set_section_widgets_reference(self, section_widgets: Dict[str, SectionWidget]):
        """Set reference to section widgets for getting parameter values"""
        self.section_widgets = section_widgets
    
    def _send_apn_command(self, values: dict):
        """Send APN configuration command"""
        server = str(values.get('apn', '')).strip()
        user = str(values.get('user', '')).strip()
        password = str(values.get('password', '')).strip()
        
        if not server:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("apn_server_required", "APN server is required")
            )
            return

        command = f"ATSMS:APN,{server},{user},{password}#"
        # This is a direct UI-initiated send; bypass pre-send validation to avoid
        # blocking well-formed APN commands from the user's Send button.
        self.serial_service.send_command(command, command_type='apn', bypass_validation=True)

        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("apn_command_sent", "APN configuration sent to device")
        )
    
    def _send_server_command(self, values: dict):
        """Send server configuration command"""
        address = str(values.get('address', '')).strip()
        port = str(values.get('port', '')).strip()
        
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
        # Bypass validation for UI-initiated server configuration sends
        self.serial_service.send_command(command, command_type='server', bypass_validation=True)

        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("server_command_sent", "Server configuration sent to device")
        )
    
    def _send_timer_command(self, values: dict):
        """Send timer intervals command"""
        moving_time = str(values.get('moving_time', '')).strip()
        stopped_time = str(values.get('stopped_time', '')).strip()
        
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
        moving_heartbeat = str(values.get('moving_heartbeat', '')).strip()
        stopped_heartbeat = str(values.get('stopped_heartbeat', '')).strip()
        
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
        protocol = str(values.get('protocol', '')).strip()
        
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
        command = f"ATSMS:SZCS#GT06SEL={protocol_value}"
        self.serial_service.send_command(command)
        
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("protocol_command_sent", "Protocol configuration sent to device")
        )
    
    def _send_tcp_ack_command(self, values: dict):
        """Send TCP ACK configuration command"""
        tcp_ack = str(values.get('tcp_ack', '')).strip()
        
        if not tcp_ack:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("tcp_ack_required", "TCP ACK setting is required")
            )
            return
        
        # Map boolean to command value
        ack_value = '1' if tcp_ack.lower() in ['true', 'enabled', '1'] else '0'
        command = f"ATSMS:SZCS#POSBYACK={ack_value}"
        self.serial_service.send_command(command)
        
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("tcp_ack_command_sent", "TCP ACK configuration sent to device")
        )
    
    def _send_ignition_command(self, values: dict):
        """Send ignition configuration command"""
        ignition_mode = str(values.get('ignition_mode', '')).strip()
        
        if not ignition_mode:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("ignition_type_required", "Ignition type is required")
            )
            return

        command = None
        if ignition_mode == 'Virtual por bateria (Virtual by battery)':
            on_voltage = str(values.get('on_voltage', '')).strip()
            off_voltage = str(values.get('off_voltage', '')).strip()
            
            if not on_voltage or not off_voltage:
                messagebox.showerror(
                    self.i18n_service.get("error", "Error"),
                    self.i18n_service.get("voltage_values_required", "ON and OFF voltage values are required for battery ignition")
                )
                return
            
            command = f"ATSMS:SZCS#ACCLINE=1#ACC_CFG=1-{on_voltage}-{off_voltage}"
        elif ignition_mode == 'Física (Physical)':
            command = "ATSMS:SZCS#ACCLINE=1#ACC_CFG=0-000-000"
        elif ignition_mode == 'Virtual por acelerômetro (Virtual by accelerometer)':
            command = "ATSMS:SZCS#ACCLINE=0#ACC_CFG=0-000-000"
        else:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("invalid_ignition_type", "Invalid ignition type")
            )
            return
        
        if command:
            self.serial_service.send_command(command)
        
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("ignition_command_sent", "Ignition configuration sent to device")
        )
    
    def _send_speed_alert_command(self, values: dict):
        """Send speed alert configuration command"""
        enabled = values.get('enabled', False)
        detection_time = str(values.get('detection_time', '')).strip()
        speed_limit = str(values.get('speed_limit', '')).strip()
        alert_type = str(values.get('alert_type', '')).strip()
        
        if enabled and (not detection_time or not speed_limit):
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("speed_alert_values_required", "Detection time and speed limit are required when speed alert is enabled")
            )
            return
        
        # Map alert type to command value
        alert_type_mapping = {
            'Apenas GPRS': '0',
            'GPRS+SMS': '1'
        }
        alert_value = alert_type_mapping.get(alert_type, '0')
        
        if enabled:
            command = f"ATSMS:SPEED,ON,{detection_time},{speed_limit},{alert_value}#"
        else:
            command = "ATSMS:SPEED,OFF#"
        
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("speed_alert_sent", "Speed alert configuration sent to device")
        )
    
    def _send_speed_buzzer_command(self, values: dict):
        """Send speed buzzer configuration command"""
        enabled = values.get('speed_buzzer', False)
        value = '1' if enabled else '0'
        
        command = f"ATSMS:SZCS#SPD_LED_SHOW={value}"
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("speed_buzzer_sent", "Speed buzzer configuration sent to device")
        )
    
    def _send_sleep_mode_command(self, values: dict):
        """Send sleep mode configuration command"""
        sleep_mode = str(values.get('sleep_mode', '')).strip()
        
        # Map sleep mode to command value
        sleep_mode_mapping = {
            'Desabilitado (Disabled)': '0',
            'Sleep (Habilitado)': '1',
            'Deep Sleep (Ultra-baixo)': '2'
        }
        
        mode_value = sleep_mode_mapping.get(sleep_mode, '0')
        command = f"ATSMS:SZCS#SLPDISCONNECT={mode_value}"
        
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("sleep_mode_sent", "Sleep mode configuration sent to device")
        )
    
    def _send_sleep_time_command(self, values: dict):
        """Send sleep time configuration command"""
        sleep_time = str(values.get('sleep_time', '')).strip()
        
        if not sleep_time:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("sleep_time_required", "Sleep time value is required")
            )
            return
        
        command = f"ATSMS:SZCS#SLEEPT={int(sleep_time)}"
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("sleep_time_sent", "Sleep time configuration sent to device")
        )
    
    def _send_angle_report_command(self, values: dict):
        """Send angle report configuration command"""
        enabled = values.get('enabled', False)
        min_speed = str(values.get('min_speed', '')).strip()
        angle_variation = str(values.get('angle_variation', '')).strip()
        
        # Debug logging to validate exact values and types coming from UI
        try:
            print(f"DEBUG: _send_angle_report_command - raw values: enabled={enabled!r}, min_speed={values.get('min_speed')!r}, angle_variation={values.get('angle_variation')!r}")
            # Also print the types
            print(f"DEBUG: _send_angle_report_command - types: enabled={type(enabled).__name__}, min_speed_type={type(values.get('min_speed')).__name__ if values.get('min_speed') is not None else 'None'}, angle_variation_type={type(values.get('angle_variation')).__name__ if values.get('angle_variation') is not None else 'None'}")
        except Exception:
            pass
        
        if enabled:
            if not min_speed or not angle_variation:
                messagebox.showerror(
                    self.i18n_service.get("error", "Error"),
                    self.i18n_service.get("angle_values_required", "Minimum speed and angle variation are required when angle report is enabled")
                )
                return
            # Use the exact strings (preserve leading zeros) that were captured from UI
            min_speed_str = f"{int(min_speed):02d}"
            angle_variation_str = f"{int(angle_variation):03d}"
            command = f"ATSMS:SZCS#ANGLEVALUE={min_speed_str}-{angle_variation_str}"
        else:
            command = f"ATSMS:SZCS#ANGLEVALUE=00-000#"
        
        # Log the final command for debugging
        try:
            print(f"DEBUG: _send_angle_report_command - sending command: {command}")
        except Exception:
            pass
        
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("angle_report_sent", "Angle report configuration sent to device")
        )
    
    def _send_backup_battery_alert_command(self, values: dict):
        """Send backup battery alert configuration command"""
        enabled = values.get('backup_battery_alert', False)
        
        if enabled:
            command = "ATSMS:BATALM,ON,0#"
        else:
            command = "ATSMS:BATALM,OFF#"
        
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("backup_battery_sent", "Backup battery alert configuration sent to device")
        )
    
    def _send_main_power_alert_command(self, values: dict):
        """Send main power alert configuration command"""
        enabled = values.get('enabled', False)
        alert_type = str(values.get('alert_type', '')).strip()
        detection_time = str(values.get('detection_time', '')).strip()
        min_charge_time = str(values.get('min_charge_time', '')).strip()
        
        if enabled and (not detection_time or not min_charge_time):
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("main_power_values_required", "Detection time and minimum charge time are required when main power alert is enabled")
            )
            return
        
        # Map alert type to command value
        alert_type_mapping = {
            'Apenas GPRS': '0',
            'GPRS+SMS': '1'
        }
        alert_value = alert_type_mapping.get(alert_type, '0')
        
        if enabled:
            command = f"ATSMS:POWERALM,ON,{alert_value},{detection_time},{min_charge_time}#"
        else:
            command = "ATSMS:POWERALM,OFF#"
        
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("main_power_sent", "Main power alert configuration sent to device")
        )

    def _send_network_settings_command(self, values: dict):
        """Send network settings command"""
        network_mode = str(values.get('main', '')).strip()
        
        if not network_mode:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("network_mode_required", "Network mode selection is required")
            )
            return
        
        # Map network mode to command value
        network_mode_mapping = {
            'AUTO': '0',
            '4G': '1',
            '2G': '2'
        }
        
        mode_value = network_mode_mapping.get(network_mode, '0')
        command = f"ATSMS:NETSELECT,{mode_value}#"
        
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("network_settings_sent", "Network settings sent to device")
        )
    
    def _send_vibration_sensitivity_command(self, values: dict):
        """Send vibration sensitivity configuration command"""
        level = str(values.get('level', '1')).strip()
        
        try:
            level_int = int(float(level)) # Convert to float first to handle "3.0" then to int
        except ValueError:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("vibration_level_invalid", "Vibration sensitivity level must be an integer")
            )
            return
        
        command = f"ATSMS:SZCS#VIBL={level_int}"
        
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("vibration_sent", "Vibration sensitivity configuration sent to device")
        )
    
    def _send_jammer_detection_command(self, values: dict):
        """Send jammer detection configuration command"""
        enabled = values.get('jammer_detection', False)
        
        if enabled:
            command = "ATSMS:JAMMER,ON,0#"
        else:
            command = "ATSMS:JAMMER,OFF#"
        
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("jammer_detection_sent", "Jammer detection configuration sent to device")
        )
    
    def _send_jammer_relay_action_command(self, values: dict):
        """Send jammer relay action configuration command"""
        output_operation = str(values.get('output_operation', '')).strip()
        confirmation_time = str(values.get('confirmation_time', '0')).strip()
        speed_limit = str(values.get('speed_limit', '0')).strip()
        param_d = str(values.get('param_d', '0')).strip()
        param_e = str(values.get('param_e', '0')).strip()
        param_f = str(values.get('param_f', '0')).strip()
        param_g_text = str(values.get('param_g', '')).strip()
        
        # Map output operation to command value
        operation_mapping = {
            'Sem Ação': '0',
            'Ativar e Manter': '1',
            'Ativar e Desativar com Jammer': '2'
        }
        op_value = operation_mapping.get(output_operation, '0')

        param_g_mapping = {
            'Manter ativada': '0',
            'Manter desativada': '1'
        }
        param_g_value = param_g_mapping.get(param_g_text, '0')
        
        command = f"ATSMS:JAMRELAY,{op_value},{confirmation_time},{speed_limit},{param_d},{param_e},{param_f},{param_g_value}#"
        
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("jammer_relay_sent", "Jammer relay action configuration sent to device")
        )
    
    def _send_odometer_command(self, values: dict):
        """Send odometer configuration command"""
        odometer_value = str(values.get('odometer', '')).strip()
        
        if not odometer_value:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("odometer_required", "Odometer value is required")
            )
            return
        
        # Ensure the odometer value is an integer (not a float)
        try:
            # Convert to float first, then to int to handle cases like "28.0"
            odometer_int = int(float(odometer_value))
            odometer_value = str(odometer_int)
        except ValueError:
            # If conversion fails, keep the original value but show a warning
            pass
        
        command = f"ATSMS:MILEAGE={odometer_value}#"
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("odometer_sent", "Odometer configuration sent to device")
        )
    
    def _send_hourmeter_command(self, values: dict):
        """Send hourmeter configuration command"""
        hourmeter_value = str(values.get('hourmeter', '')).strip()
        
        if not hourmeter_value:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("hourmeter_required", "Hourmeter value is required")
            )
            return
        
        # Ensure the hourmeter value is an integer (not a float)
        try:
            # Convert to float first, then to int to handle cases like "28.0"
            hourmeter_int = int(float(hourmeter_value))
            hourmeter_value = str(hourmeter_int)
        except ValueError:
            # If conversion fails, keep the original value but show a warning
            pass
        
        command = f"ATSMS:ACCONT,{hourmeter_value}#"
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("hourmeter_sent", "Hourmeter configuration sent to device")
        )

    def _send_source_off_type_command(self, values: dict):
        """Send source off type configuration command"""
        source_off_type = str(values.get('source_off_type', '')).strip()
        
        # Map source off type to command value
        source_off_type_mapping = {
            'Verifica FIX de GPS': '0',
            'Não verifica FIX de GPS': '1'
        }
        
        value = source_off_type_mapping.get(source_off_type, '0')
        command = f"ATSMS:SZCS#SOURCE_OFF_TYPE={value}"
        
        self.serial_service.send_command(command, command_type='source_off_type')
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("source_off_type_sent", "Source off type configuration sent to device")
        )

    def _send_relay_control_command(self, values: dict):
        """Send relay control command"""
        relay_control = str(values.get('relay_control', '')).strip()
        
        # Map relay control to command value
        relay_control_mapping = {
            'Desabilitada': '0',
            'Habilitada': '1'
        }
        
        value = relay_control_mapping.get(relay_control, '0')
        command = f"ATSMS:RELAY,{value}#"
        
        self.serial_service.send_command(command, command_type='relay_control')
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("relay_control_sent", "Relay control configuration sent to device")
        )

    def _send_sends_control_command(self, values: dict):
        """Send sends control command"""
        sends_control = str(values.get('sends_control', '')).strip()
        
        command = f"ATSMS:SENDS,{sends_control}#"
        
        self.serial_service.send_command(command, command_type='sends_control')
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("sends_control_sent", "Sends control configuration sent to device")
        )

    def _send_motion_sensor_alert_command(self, values: dict):
        """Send motion sensor alert command"""
        value = values.get('motion_sensor_alert')
        
        if value == 'Desabilitado':
            command = "ATSMS:SENALM,OFF#"
        elif value == 'Alerta Enviado Apenas GPRS':
            command = "ATSMS:SENALM,ON,0#"
        elif value == 'Alerta Enviado por SMS+GPRS':
            command = "ATSMS:SENALM,ON,1#"
        else:
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("invalid_motion_sensor_alert_value", "Invalid motion sensor alert value")
            )
            return

        self.serial_service.send_command(command, command_type='motion_sensor_alert')
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("motion_sensor_alert_sent", "Motion sensor alert configuration sent to device")
        )

    def _send_distance_movement_action_command(self, values: dict):
        """Send distance movement action configuration command"""
        distance_movement_action = str(values.get('distance_movement_action', '')).strip()
        
        # Map distance movement action to command value
        distance_movement_action_mapping = {
            'Automaticamente ativado após entrar no modo DEFENSE (quando a ignição é desligada)': '0',
            'Envia um alerta - Apenas uma vez independente da IGN on ou off': '1',
            'Envia um alerta uma vez e bloqueia o veículo - Apenas uma vez independente da IGN on ou off': '2'
        }
        
        value = distance_movement_action_mapping.get(distance_movement_action, '0')
        command = f"ATSMS:SZCS#MOVEALMFUN={value}"
        
        self.serial_service.send_command(command, command_type='distance_movement_action')
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("distance_movement_action_sent", "Distance movement action configuration sent to device")
        )
    def _send_acc_on_alert_command(self, values: dict):
        """Send ACC ON alert configuration command"""
        acc_on_alert = str(values.get('acc_on_alert', '')).strip()
        
        # Map ACC ON alert to command value
        acc_on_alert_mapping = {
            'Disabled': 'OFF',
            'Alerta Enviado Apenas GPRS': '0',
            'Alerta Enviado por SMS+GPRS': '1'
        }
        
        value_code = acc_on_alert_mapping.get(acc_on_alert, 'OFF')
        
        # Handle disabled state
        if value_code == 'OFF':
            command = f"ATSMS:ACCALM,OFF#"
        else:
            command = f"ATSMS:ACCALM,ON,{value_code}#"
        
        self.serial_service.send_command(command, command_type='acc_on_alert')
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("acc_on_alert_sent", "ACC ON alert configuration sent to device")
        )

    def _send_acc_off_alert_command(self, values: dict):
        """Send ACC OFF alert configuration command"""
        acc_off_alert = str(values.get('acc_off_alert', '')).strip()
        
        if acc_off_alert == 'Desabilitado':
            command = "ACCOFFALM,OFF#"
        elif acc_off_alert == 'Alerta Enviado Apenas GPRS':
            command = "ACCOFFALM,ON,0#"
        elif acc_off_alert == 'Alerta Enviado por SMS+GPRS':
            command = "ACCOFFALM,ON,1#"
        else:
            return

        self.serial_service.send_command(command, command_type='acc_off_alert')
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("acc_off_alert_sent", "ACC OFF alert configuration sent to device")
        )

    def _send_movement_alert_command(self, values: dict):
        """Send movement alert command"""
        enabled = values.get('enabled', False)
        alert_type = str(values.get('alert_type', '')).strip()

        if enabled:
            alert_type_mapping = {
                'Apenas GPRS': '0',
                'SMS+GPRS': '1'
            }
            alert_value = alert_type_mapping.get(alert_type, '0')
            command = f"ATSMS:SENALM,ON,{alert_value}#"
        else:
            command = "ATSMS:SENALM,OFF#"

        self.serial_service.send_command(command, command_type='movement_alert')
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("movement_alert_sent", "Movement alert configuration sent to device")
        )

    def _send_backup_battery_protection_voltage_command(self, values: dict):
        """Send backup battery protection voltage command"""
        voltage = str(values.get('backup_battery_protection_voltage', '')).strip()
        
        command = f"ATSMS:SZCS#BATSLPVALUE={voltage}"
        
        self.serial_service.send_command(command, command_type='backup_battery_protection_voltage')
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("backup_battery_protection_voltage_sent", "Backup battery protection voltage configuration sent to device")
        )

    def _send_generic_parameter_command(self, param_name: str, values: dict):
        """Send generic parameter command"""
        messagebox.showinfo(
            self.i18n_service.get("info", "Info"),
            f"{self.i18n_service.get('parameter_command_sent', 'Parameter command sent')}: {param_name}"
        )

    def _send_vibration_window_command(self, values: dict):
        """Send vibration window configuration command"""
        window = str(values.get('window', '10')).strip()
        threshold = str(values.get('threshold', '3')).strip()
        
        command = f"ATSMS:SZCS#VIBCHK={window}:{threshold}"
        
        self.serial_service.send_command(command)
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("vibration_window_sent", "Vibration window configuration sent to device")
        )
    def _send_blind_area_speed_command(self, values: dict):
        """Send blind area speed configuration command"""
        blind_area_speed = values.get('blind_area_speed', 0)
        
        # Ensure value is within valid range (0-20)
        try:
            speed_value = int(blind_area_speed)
            if speed_value < 0 or speed_value > 20:
                messagebox.showerror(
                    self.i18n_service.get("error", "Error"),
                    self.i18n_service.get("blind_area_speed_range_error", "Blind area speed value must be between 0 and 20")
                )
                return
        except (ValueError, TypeError):
            messagebox.showerror(
                self.i18n_service.get("error", "Error"),
                self.i18n_service.get("blind_area_speed_invalid", "Invalid blind area speed value")
            )
            return
        
        command = f"ATSMS:SZCS#BLINDSPD={speed_value}"
        
        self.serial_service.send_command(command, command_type='blind_area_speed')
        messagebox.showinfo(
            self.i18n_service.get("success", "Success"),
            self.i18n_service.get("blind_area_speed_sent", "Blind area speed configuration sent to device")
        )