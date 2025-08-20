import customtkinter as ctk
import re
import traceback
from ipaddress import ip_address
from tkinter import messagebox
from typing import Any, Dict, List
from typing import Any, Dict
from ui.parameter_factory import ParameterFactory
from ui.custom_dialogs import show_error, show_info
from ui.validation_mixin import ValidationMixin, ValidationResult
from ui.apn_help_tooltip import APNCarrierHelper
from services.validation_service import ValidationService
from services.parameter_specification import get_all_sections_ordered, get_parameter_specification
from services.parameter_specification_factory import ParameterSpecificationFactory
from services.profile_ui_populator import ProfileUIPopulator
from components.apn_validation_component import APNValidationComponent
from utils.widget_parent_resolver import (
    get_widget_parent, get_widget_parent_with_details, log_widget_access_debug,
    log_widget_access_failure, log_widget_access_warning, log_widget_hierarchy_analysis,
    ensure_application_continues
)

class ParametersFrame(ctk.CTkScrollableFrame, ValidationMixin):
    def __init__(self, master, i18n):
        super().__init__(master, label_text=i18n.get("parameters"))
        ValidationMixin.__init__(self)  # Initialize validation mixin
        self.i18n = i18n
        self.serial_service = master.serial_service  # Get serial service from master
        
        # Initialize validation service and parameter specification factory
        self.validation_service = ValidationService(i18n)
        self.parameter_specification_factory = ParameterSpecificationFactory(i18n, self.validation_service, self.serial_service)
        
        # Initialize ProfileUIPopulator
        from services.parameter_specification_parser import ParameterSpecificationParser
        spec_parser = ParameterSpecificationParser("Parameter UI List.md")
        self.profile_ui_populator = ProfileUIPopulator(spec_parser)
        
        # Initialize APN validation component
        self.apn_validation_component = APNValidationComponent()
        
        # Store section widgets created by the specification factory
        self.section_widgets = {}
        
        # Legacy parameter widgets for backward compatibility
        self.parameter_widgets = {}
        self.parameter_sections = {}
        self.section_frames = {}

        # Configure responsive grid
        self.grid_columnconfigure(0, weight=1)
        
        # Create all parameter sections using specification factory
        self._create_parameter_sections_from_specification()
        
        # Set section widgets reference for command sending
        self.parameter_specification_factory.set_section_widgets_reference(self.section_widgets)
        
        # Initialize conditional field visibility
        self.parameter_specification_factory.initialize_conditional_field_visibility(self.section_widgets)
        
        # Set up enhanced APN validation using ValidationMixin
        self._setup_enhanced_apn_validation_with_mixin()
    
    def populate_ui_from_profile(self, profile):
        """
        Populate UI elements with values from a profile.
        
        Args:
            profile: UniversalProfile containing parameter values
            
        Returns:
            ValidationResult: Result of the population operation
        """
        # Check if profile_ui_populator is available
        if not hasattr(self, 'profile_ui_populator') or not self.profile_ui_populator:
            from models.validation_result import ValidationResult
            result = ValidationResult(is_valid=False)
            result.add_error("ProfileUIPopulator not available")
            return result
        
        # Check if section_widgets is available and populated
        if not hasattr(self, 'section_widgets') or not self.section_widgets:
            from models.validation_result import ValidationResult
            result = ValidationResult(is_valid=False)
            result.add_error("Section widgets not available")
            return result
        
        # Use the ProfileUIPopulator to populate UI from profile
        result = self.profile_ui_populator.update_ui_elements_from_profile(profile, self.section_widgets)
        return result
    
    def extract_validated_field_values(self):
        """
        Extract validated values from all UI elements.
        
        Returns:
            Tuple[Dict[str, Any], ValidationResult]: Extracted values and validation result
        """
        # Create a mapping of parameter names to UI elements
        ui_elements = {}
        
        # Collect all UI elements from section widgets
        for section_name, section_widget in self.section_widgets.items():
            for param_name, param_widget in section_widget.parameters.items():
                if param_widget.widget_type == 'simple':
                    # For simple parameters, add the main UI element
                    full_param_name = f"{section_name}.{param_name}"
                    ui_elements[full_param_name] = param_widget.ui_elements['main']
                elif param_widget.widget_type == 'complex':
                    # For complex parameters, add each field's UI element
                    for field_name, field_element in param_widget.ui_elements.items():
                        full_field_name = f"{section_name}.{param_name}.{field_name}"
                        ui_elements[full_field_name] = field_element
        
        # Use the ProfileUIPopulator to extract validated values
        return self.profile_ui_populator.extract_validated_field_values(ui_elements)
    
    def apply_visibility_conditions(self, context: Dict[str, Any]):
        """
        Apply visibility conditions to UI elements based on context values.
        
        Args:
            context: Current parameter values for evaluating conditions
        """
        # Create a mapping of parameter names to UI elements
        ui_elements = {}
        
        # Collect all UI elements from section widgets
        for section_name, section_widget in self.section_widgets.items():
            for param_name, param_widget in section_widget.parameters.items():
                full_param_name = f"{section_name}.{param_name}"
                if param_widget.widget_type == 'simple':
                    ui_elements[full_param_name] = param_widget.ui_elements['main']
                elif param_widget.widget_type == 'complex':
                    # For complex parameters, add each field element
                    for field_name, field_element in param_widget.ui_elements.items():
                        field_full_name = f"{full_param_name}.{field_name}"
                        ui_elements[field_full_name] = field_element
        
        # Use the ProfileUIPopulator to apply visibility conditions
        self.profile_ui_populator.apply_visibility_conditions(ui_elements, context)
    
    def get_field_dependencies(self, param_name: str) -> List[str]:
        """
        Get field dependencies for a parameter based on visibility conditions.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            List[str]: List of parameter names this parameter depends on
        """
        return self.profile_ui_populator.get_field_dependencies(param_name)

    def _validate_apn_field_comprehensive(self, value: str) -> ValidationResult:
        """Validate the APN field with comprehensive rules."""
        if not value:
            return ValidationResult(False, "APN is required", "apn_required")
        return self.apn_validation_component.validate_apn(value)

    def _validate_apn_user_field_comprehensive(self, value: str) -> ValidationResult:
        """Validate the APN username field."""
        # Username is optional if no password is provided
        if not value and (not hasattr(self, 'apn_widgets') or 
                         'password' not in self.apn_widgets or 
                         not self.apn_widgets['password'].get().strip()):
            return ValidationResult(True, "", "")
        return self.apn_validation_component.validate_apn_user(value)

    def _validate_apn_password_field_comprehensive(self, value: str) -> ValidationResult:
        """Validate the APN password field."""
        # Password is optional if no username is provided
        if not value and (not hasattr(self, 'apn_widgets') or 
                         'user' not in self.apn_widgets or 
                         not self.apn_widgets['user'].get().strip()):
            return ValidationResult(True, "", "")
        return self.apn_validation_component.validate_apn_password(value)

    def _create_parameter_sections_from_specification(self):
        """Create all parameter sections using the specification factory."""
        # Use the specification factory to create all sections
        self.section_widgets = self.parameter_specification_factory.create_all_sections(self)
        
        # Create legacy parameter_widgets mapping for backward compatibility
        self._create_legacy_parameter_mapping()
    
    def _create_legacy_parameter_mapping(self):
        """Create legacy parameter_widgets mapping for backward compatibility."""
        for section_name, section_widget in self.section_widgets.items():
            # Create legacy section mapping
            self.parameter_sections[section_name] = {
                'config': section_widget.config,
                'frame': section_widget.container_frame,
                'title': section_widget.title_widget,
                'parameters': {}
            }
            self.section_frames[section_name] = section_widget.container_frame
            
            # Create legacy parameter mapping
            for param_name, param_widget in section_widget.parameters.items():
                legacy_param_key = f"{section_name}.{param_name}"
                
                # Convert new parameter widget to legacy format
                legacy_param_widget = {
                    'config': param_widget.config,
                    'frame': param_widget.container_frame,
                    'type': param_widget.widget_type
                }
                
                if param_widget.widget_type == 'simple':
                    legacy_param_widget['element'] = param_widget.ui_elements['main']
                    legacy_param_widget['label'] = None  # UI element handles its own label
                elif param_widget.widget_type == 'complex':
                    legacy_param_widget['title'] = param_widget.title_widget
                    legacy_param_widget['fields'] = {}
                    
                    for field_name, ui_element in param_widget.ui_elements.items():
                        legacy_param_widget['fields'][field_name] = {
                            'config': param_widget.config.fields[field_name],
                            'element': ui_element,
                            'label': None  # UI element handles its own label
                        }
                
                self.parameter_widgets[legacy_param_key] = legacy_param_widget
                self.parameter_sections[section_name]['parameters'][param_name] = legacy_param_widget
    



    
    def _send_command_callback(self, command: str):
        """Callback for parameter factory to send commands."""
        if self.serial_service:
            self.serial_service.send_command(command)
    
    def get_all_parameter_values(self):
        """Get all parameter values from the specification-based widgets."""
        return self.parameter_specification_factory.get_all_parameter_values(self.section_widgets)
    
    def set_all_parameter_values(self, values):
        """Set parameter values in the specification-based widgets."""
        self.parameter_specification_factory.set_all_parameter_values(values, self.section_widgets)
    
    def _get_parameter_value(self, parameter_widget):
        """Get value from a parameter widget based on its type (legacy compatibility)."""
        if parameter_widget['type'] == 'simple':
            return parameter_widget['element'].get_value()
        elif parameter_widget['type'] == 'complex':
            values = {}
            for field_name, field_data in parameter_widget['fields'].items():
                values[field_name] = field_data['element'].get_value()
            return values
        return None
    
    def _set_parameter_value(self, parameter_widget, value):
        """Set value for a parameter widget based on its type (legacy compatibility)."""
        if parameter_widget['type'] == 'simple':
            parameter_widget['element'].set_value(value)
        elif parameter_widget['type'] == 'complex' and isinstance(value, dict):
            for field_name, field_value in value.items():
                if field_name in parameter_widget['fields']:
                    parameter_widget['fields'][field_name]['element'].set_value(field_value)
    
    def highlight_updated_parameter(self, param_name: str, value_changed: bool = True):
        """
        Highlight a parameter that was updated from device configuration.
        
        Args:
            param_name: Name of the parameter to highlight
            value_changed: True if the value changed, False if it was the same
        """
        try:
            if param_name in self.parameter_widgets:
                parameter_widget = self.parameter_widgets[param_name]
                
                # Get the container frame to highlight
                container_frame = None
                if parameter_widget['type'] == 'simple':
                    ui_element = parameter_widget['element']
                    if hasattr(ui_element, 'container_frame'):
                        container_frame = ui_element.container_frame
                elif parameter_widget['type'] == 'complex':
                    container_frame = parameter_widget['frame']
                
                if container_frame and hasattr(container_frame, 'configure'):
                    if value_changed:
                        # Green border for changed values
                        original_border_color = container_frame.cget("border_color")
                        container_frame.configure(border_color="#00ff00", border_width=2)
                        
                        # Schedule removal after 3 seconds
                        self.after(3000, lambda: self._remove_parameter_highlight(container_frame, original_border_color))
                    else:
                        # Blue border for unchanged values
                        original_border_color = container_frame.cget("border_color")
                        container_frame.configure(border_color="#0066cc", border_width=1)
                        
                        # Schedule removal after 2 seconds
                        self.after(2000, lambda: self._remove_parameter_highlight(container_frame, original_border_color))
                        
        except Exception as e:
            print(f"WARNING: Failed to highlight parameter {param_name}: {str(e)}")
    
    def _remove_parameter_highlight(self, widget, original_border_color):
        """Remove the highlight from a parameter widget."""
        try:
            if hasattr(widget, 'configure'):
                border_color = original_border_color if original_border_color else "gray"
                widget.configure(border_color=border_color, border_width=0)
        except Exception as e:
            print(f"WARNING: Failed to remove parameter highlight: {str(e)}")
    
    def get_parameter_widget(self, param_name: str):
        """Get a specific parameter widget by name."""
        return self.parameter_widgets.get(param_name)
    
    def get_section_widget(self, section_name: str):
        """Get a specific section widget by name."""
        return self.parameter_sections.get(section_name)

    def _send_command_if_value(self, command_template: str, value: str):
        """Helper to send a command if the value is not empty."""
        if value:
            self.serial_service.send_command(command_template.format(value=value))
    

    
    def _get_apn_values_from_section(self):
        """Get APN values from the network parameters section."""
        return self.parameter_specification_factory.get_parameter_value(
            'network_parameters', 'apn_settings', self.section_widgets
        )
    
    def send_apn_command(self):
        """Validates and sends the complete APN configuration command with enhanced validation."""
        if not self.serial_service.is_connected:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("not_connected_error")
            )
            return

        # Check if form submission should be prevented due to validation errors
        if self.prevent_form_submission_on_validation_errors():
            validation_errors = self.get_validation_errors()
            error_messages = []
            
            for field_name, error_message in validation_errors.items():
                field_display = field_name.replace('_', ' ').title()
                error_messages.append(f"{field_display}: {error_message}")
            
            show_error(
                self,
                self.i18n.get("validation_errors", "Validation Errors"),
                "Please fix the following validation errors before sending:\n\n" + "\n".join(error_messages)
            )
            return

        # Get APN values from the network parameters section
        apn_values = self._get_apn_values_from_section()
        if not apn_values:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("apn_server_required")
            )
            return

        server = apn_values.get('apn', '').strip()
        user = apn_values.get('user', '').strip()
        password = apn_values.get('password', '').strip()

        # APN server is mandatory if any APN setting is being sent.
        if not server:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("apn_server_required")
            )
            return

        # Final comprehensive validation using the APN validation component
        validation_result = self.apn_validation_component.validate_apn_configuration(server, user, password)
        if not validation_result.is_valid:
            show_error(
                self,
                self.i18n.get("invalid_apn_server_title", "Invalid APN Configuration"),
                validation_result.error_message + 
                (f"\n\nSuggestions:\n• " + "\n• ".join(validation_result.suggestions) if validation_result.suggestions else "")
            )
            return

        # Construct the command. User and password can be empty.
        command = f"ATSMS:APN,{server},{user},{password}#"
        # Direct UI send - bypass command validation to avoid blocking
        # well-formed APN commands initiated by the user.
        self.serial_service.send_command(command, command_type='apn', bypass_validation=True)

        # Show success feedback
        show_info(
            self,
            self.i18n.get("success", "Success"),
            f"APN configuration sent successfully:\nAPN: {server}\nUser: {user if user else '(none)'}"
        )

    def send_trans_mode_command(self):
        """Sends the Transmission Mode command to the device (always TCP)."""
        # Always use TCP (0) for transmission mode
        self._send_command_if_value("ATSMS:SZCS#PROTOCOL={value}#", "0")
    
    def update_language_display(self):
        """Updates all UI elements with the current language."""
        # Update frame label
        self.configure(label_text=self.i18n.get("parameters"))
        
        # Update all sections and parameters using the specification factory
        self.parameter_specification_factory.update_language_display(self.section_widgets)
    
    def update_apn_fields(self, server=None, user=None, password=None):
        """
        Update APN fields with values read from the device.
        
        Args:
            server: APN server value
            user: APN user value
            password: APN password value
        """
        print(f"DEBUG: update_apn_fields called with server={server}, user={user}, password={password}")
        
        # Build APN values dictionary
        apn_values = {}
        if server is not None:
            apn_values['apn'] = server
            print(f"Updated APN server to {server}")
        if user is not None:
            apn_values['user'] = user
            print(f"Updated APN user to {user}")
        if password is not None:
            apn_values['password'] = password
            print(f"Updated APN password to {password}")
        
        if apn_values:
            # Update APN settings in the network parameters section
            self.parameter_specification_factory.set_parameter_value(
                'network_parameters', 'apn_settings', apn_values, self.section_widgets
            )
            self.highlight_updated_parameter("network_parameters.apn_settings", True)
    
    def update_parameter_value(self, param_name, value):
        """
        Update a parameter value.
        
        Args:
            param_name: Name of the parameter to update (format: section_name.param_name)
            value: Value to set
        """
        print(f"DEBUG: update_parameter_value called with param_name={param_name}, value={value}")
        
        # Parse section and parameter name
        if '.' in param_name:
            section_name, param_name_only = param_name.split('.', 1)
            self.parameter_specification_factory.set_parameter_value(
                section_name, param_name_only, value, self.section_widgets
            )
            print(f"Updated parameter {param_name} to {value}")
            
            # Highlight the parameter to show it was updated
            self.highlight_updated_parameter(param_name, True)
        else:
            print(f"Invalid parameter name format: {param_name}")

    def update_fields_from_dict(self, ui_field_values: Dict[str, Any]):
        """
        Update UI fields from a dictionary of profile-derived values.

        Keys can be simple parameter names (e.g., 'apn_settings') or complex
        field names (e.g., 'apn_settings.user'). Values are applied to the
        corresponding widgets using the specification factory.
        """
        try:
            factory = self.parameter_specification_factory
            section_widgets = self.section_widgets
            mapping = self._get_ui_parameter_mapping()

            for key, value in ui_field_values.items():
                try:
                    # Handle complex field keys like 'param.field'
                    if '.' in key:
                        base_param, field_name = key.split('.', 1)
                        section_info = mapping.get(base_param)
                        if not section_info:
                            print(f"WARNING: No UI mapping found for parameter {base_param}")
                            continue
                        section_name = section_info['section']
                        param_key = section_info['parameter']

                        # Get current complex value, update only the field, then set
                        current_value = {}
                        try:
                            current_value = factory.get_parameter_value(section_name, param_key, section_widgets) or {}
                        except Exception:
                            current_value = {}
                        if not isinstance(current_value, dict):
                            current_value = {}
                        current_value[field_name] = value
                        factory.set_parameter_value(section_name, param_key, current_value, section_widgets)
                        self.highlight_updated_parameter(f"{section_name}.{param_key}", True)
                    else:
                        # Simple parameter
                        section_info = mapping.get(key)
                        if not section_info:
                            print(f"WARNING: No UI mapping found for parameter {key}")
                            continue
                        section_name = section_info['section']
                        param_key = section_info['parameter']
                        factory.set_parameter_value(section_name, param_key, value, section_widgets)
                        self.highlight_updated_parameter(f"{section_name}.{param_key}", True)
                except Exception as e:
                    print(f"ERROR: Failed to apply UI value for '{key}': {e}")
        except Exception as e:
            print(f"ERROR: update_fields_from_dict failed: {e}")
    
    def get_section_names(self):
        """Get all section names in order."""
        return [section['config'].name for section in sorted(
            self.parameter_sections.values(), 
            key=lambda x: x['config'].order
        )]
    
    def get_parameter_names_in_section(self, section_name):
        """Get all parameter names in a specific section."""
        if section_name in self.parameter_sections:
            return list(self.parameter_sections[section_name]['parameters'].keys())
        return []
    
    def is_parameter_visible(self, param_name):
        """Check if a parameter is currently visible (for conditional parameters)."""
        if param_name in self.parameter_widgets:
            param_widget = self.parameter_widgets[param_name]
            return param_widget['frame'].winfo_viewable()
        return False

    def update_parameter_fields(self, parsed_parameters: dict):
        """
        Update parameter fields from parsed device responses.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            print(f"DEBUG: update_parameter_fields called with {len(parsed_parameters)} parameters")
            
            # Use the parameter specification factory to update fields
            if hasattr(self, 'parameter_specification_factory') and hasattr(self, 'section_widgets'):
                factory = self.parameter_specification_factory
                section_widgets = self.section_widgets
                
                # Map parameter names to section/parameter structure
                parameter_mapping = self._get_ui_parameter_mapping()
                
                for param_name, parsed_values in parsed_parameters.items():
                    try:
                        # Get section and parameter name from mapping
                        section_info = parameter_mapping.get(param_name)
                        if not section_info:
                            print(f"WARNING: No UI mapping found for parameter {param_name}")
                            continue
                        
                        section_name = section_info['section']
                        param_key = section_info['parameter']
                        
                        print(f"DEBUG: Updating {section_name}.{param_key} with values: {parsed_values}")
                        
                        # Update the parameter value using the factory
                        factory.set_parameter_value(section_name, param_key, parsed_values, section_widgets)
                        
                        # Highlight the updated parameter
                        full_param_name = f"{section_name}.{param_key}"
                        self.highlight_updated_parameter(full_param_name, True)
                        
                        print(f"DEBUG: Successfully updated {param_name}")
                        
                    except Exception as e:
                        print(f"ERROR: Failed to update parameter {param_name}: {str(e)}")
                
                print(f"DEBUG: Completed updating {len(parsed_parameters)} parameters")
            else:
                print("WARNING: Parameter specification factory or section widgets not available")
                # Fallback to legacy update methods
                self._update_parameters_legacy(parsed_parameters)
                
        except Exception as e:
            print(f"ERROR: Failed to update parameter fields: {str(e)}")

    def _get_ui_parameter_mapping(self) -> dict:
        """
        Get mapping of parameter names to their UI section and parameter keys.
        
        Returns:
            Dictionary mapping parameter names to section info
        """
        return {
            # Network Parameters
            'apn_settings': {'section': 'network_parameters', 'parameter': 'apn_settings'},
            'server_settings': {'section': 'network_parameters', 'parameter': 'server_settings'},
            
            # Time Parameters
            'report_intervals': {'section': 'time_parameters', 'parameter': 'report_intervals'},
            'heartbeat_intervals': {'section': 'time_parameters', 'parameter': 'heartbeat_intervals'},
            
            # Service Parameters
            'protocol': {'section': 'service_parameters', 'parameter': 'protocol'},
            'tcp_ack': {'section': 'service_parameters', 'parameter': 'tcp_ack'},
            
            # Ignition Parameters
            'ignition_type': {'section': 'ignition', 'parameter': 'ignition_type'},
            
            # Speed Parameters
            'speed_alert': {'section': 'speed', 'parameter': 'speed_alert'},
            'speed_buzzer': {'section': 'speed', 'parameter': 'speed_buzzer'},
            
            # Power Saving Parameters
            'sleep_mode': {'section': 'power_saving', 'parameter': 'sleep_mode'},
            'sleep_time': {'section': 'power_saving', 'parameter': 'sleep_time'},
            
            # Angle Parameters
            'angle_report': {'section': 'angle', 'parameter': 'angle_report'},
            
            # Battery Alert Parameters
            'backup_battery_alert': {'section': 'battery_alerts', 'parameter': 'backup_battery_alert'},
            'main_power_alert': {'section': 'battery_alerts', 'parameter': 'main_power_alert'},
            
            # Vibration Sensor Parameters
            'vibration_sensitivity': {'section': 'vibration_sensor', 'parameter': 'vibration_sensitivity'},
            
            # Jammer Detection Parameters
            'jammer_detection': {'section': 'jammer_detection', 'parameter': 'jammer_detection'},
            'jammer_relay_action': {'section': 'jammer_detection', 'parameter': 'jammer_relay_action'},
            
            # Miscellaneous Parameters
            'odometer': {'section': 'miscellaneous', 'parameter': 'odometer'},
            'hourmeter': {'section': 'miscellaneous', 'parameter': 'hourmeter'}
        }

    def _update_parameters_legacy(self, parsed_parameters: dict):
        """
        Update parameters using legacy methods as fallback.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            print("DEBUG: Using legacy parameter update methods")
            
            # Handle specific parameter types with legacy methods
            if 'apn_settings' in parsed_parameters:
                apn_data = parsed_parameters['apn_settings']
                self.update_apn_fields(
                    server=apn_data.get('apn', ''),
                    user=apn_data.get('user', ''),
                    password=apn_data.get('password', '')
                )
            
            # Add more legacy parameter updates as needed
            for param_name, values in parsed_parameters.items():
                if isinstance(values, dict):
                    for field_name, field_value in values.items():
                        full_param_name = f"{param_name}.{field_name}"
                        self.update_parameter_value(full_param_name, field_value)
                else:
                    self.update_parameter_value(param_name, values)
                    
        except Exception as e:
            print(f"ERROR: Failed to update parameters using legacy methods: {str(e)}")

    def get_parameter_update_summary(self) -> dict:
        """
        Get a summary of recent parameter updates.
        
        Returns:
            Dictionary with update summary information
        """
        try:
            # This would integrate with the configuration reader service
            # to get update statistics and information
            if hasattr(self.master, 'configuration_reader_service'):
                config_reader = self.master.configuration_reader_service
                if hasattr(config_reader, 'get_update_statistics'):
                    return config_reader.get_update_statistics()
            
            return {
                'total_updates': 0,
                'changed_updates': 0,
                'unchanged_updates': 0,
                'last_update': None,
                'error': 'Configuration reader service not available'
            }
            
        except Exception as e:
            return {'error': f'Failed to get update summary: {str(e)}'}

    def export_parameter_updates(self, file_path: str = None) -> str:
        """
        Export parameter update log.
        
        Args:
            file_path: Optional file path to save the log
            
        Returns:
            Log content as string or error message
        """
        try:
            if hasattr(self.master, 'configuration_reader_service'):
                config_reader = self.master.configuration_reader_service
                if hasattr(config_reader, 'export_parameter_update_log'):
                    return config_reader.export_parameter_update_log(file_path)
            
            return "ERROR: Configuration reader service not available for export"
            
        except Exception as e:
            return f"ERROR: Failed to export parameter updates: {str(e)}"
    
    def _setup_enhanced_apn_validation_with_mixin(self):
        """Set up enhanced APN validation using ValidationMixin with progressive feedback."""
        try:
            # Get APN settings parameter widget
            network_section = self.section_widgets.get('network_parameters')
            if not network_section:
                print("Warning: Network parameters section not found for APN validation setup")
                return
            
            apn_parameter = network_section.parameters.get('apn_settings')
            if not apn_parameter:
                print("Warning: APN settings parameter not found for validation setup")
                return
            
            # Store APN widgets for validation
            self.apn_widgets = apn_parameter.ui_elements
            
            # Set up enhanced real-time validation for APN fields using ValidationMixin
            if 'apn' in self.apn_widgets:
                apn_widget = self.apn_widgets['apn']
                self.setup_real_time_validation(
                    field_name='apn',
                    widget=apn_widget,
                    validation_callback=self._validate_apn_field_comprehensive,
                    debounce_ms=500,
                    enable_tooltips=True,
                    enable_message_display=True
                )
                
                user_widget = self.apn_widgets['user']
                self.setup_real_time_validation(
                    field_name='apn_user',
                    widget=user_widget,
                    validation_callback=self._validate_apn_user_field_comprehensive,
                    debounce_ms=300,
                    enable_tooltips=True,
                    enable_message_display=True
                )
            
            if 'password' in self.apn_widgets:
                password_widget = self.apn_widgets['password']
                self.setup_real_time_validation(
                    field_name='apn_password',
                    widget=password_widget,
                    validation_callback=self._validate_apn_password_field_comprehensive,
                    debounce_ms=300,
                    enable_tooltips=True,
                    enable_message_display=True
                )
            
            print("Enhanced APN validation with progressive feedback setup completed successfully")
            
        except Exception as e:
            print(f"Error setting up enhanced APN validation with mixin: {e}")
    
    def send_apn_command(self):
        """Validates and sends the complete APN configuration command with enhanced validation."""
        if not self.serial_service.is_connected:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("not_connected_error")
            )
            return

        # Check if form submission should be prevented due to validation errors
        if self.prevent_form_submission_on_validation_errors():
            validation_errors = self.get_validation_errors()
            error_messages = []
            
            for field_name, error_message in validation_errors.items():
                field_display = field_name.replace('_', ' ').title()
                error_messages.append(f"{field_display}: {error_message}")
            
            show_error(
                self,
                self.i18n.get("validation_errors", "Validation Errors"),
                "Please fix the following validation errors before sending:\n\n" + "\n".join(error_messages)
            )
            return

        # Get APN values from the network parameters section
        apn_values = self._get_apn_values_from_section()
        if not apn_values:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("apn_server_required")
            )
            return

        server = apn_values.get('apn', '').strip()
        user = apn_values.get('user', '').strip()
        password = apn_values.get('password', '').strip()

        # APN server is mandatory if any APN setting is being sent.
        if not server:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("apn_server_required")
            )
            return

        # Final comprehensive validation using the APN validation component
        validation_result = self.apn_validation_component.validate_apn_configuration(server, user, password)
        if not validation_result.is_valid:
            show_error(
                self,
                self.i18n.get("invalid_apn_server_title", "Invalid APN Configuration"),
                validation_result.error_message + 
                (f"\n\nSuggestions:\n• " + "\n• ".join(validation_result.suggestions) if validation_result.suggestions else "")
            )
            return

        # Construct the command. User and password can be empty.
        command = f"ATSMS:APN,{server},{user},{password}#"
        self.serial_service.send_command(command)
        
        # Show success feedback
        show_info(
            self,
            self.i18n.get("success", "Success"),
            f"APN configuration sent successfully:\nAPN: {server}\nUser: {user if user else '(none)'}"
        )

    def send_trans_mode_command(self):
        """Sends the Transmission Mode command to the device (always TCP)."""
        # Always use TCP (0) for transmission mode
        self._send_command_if_value("ATSMS:SZCS#PROTOCOL={value}#", "0")
    
    def update_language_display(self):
        """Updates all UI elements with the current language."""
        # Update frame label
        self.configure(label_text=self.i18n.get("parameters"))
        
        # Update all sections and parameters using the specification factory
        self.parameter_specification_factory.update_language_display(self.section_widgets)
    
    def update_apn_fields(self, server=None, user=None, password=None):
        """
        Update APN fields with values read from the device.
        
        Args:
            server: APN server value
            user: APN user value
            password: APN password value
        """
        print(f"DEBUG: update_apn_fields called with server={server}, user={user}, password={password}")
        
        # Build APN values dictionary
        apn_values = {}
        if server is not None:
            apn_values['apn'] = server
            print(f"Updated APN server to {server}")
        if user is not None:
            apn_values['user'] = user
            print(f"Updated APN user to {user}")
        if password is not None:
            apn_values['password'] = password
            print(f"Updated APN password to {password}")
        
        if apn_values:
            # Update APN settings in the network parameters section
            self.parameter_specification_factory.set_parameter_value(
                'network_parameters', 'apn_settings', apn_values, self.section_widgets
            )
            self.highlight_updated_parameter("network_parameters.apn_settings", True)
    
    def update_parameter_value(self, param_name, value):
        """
        Update a parameter value.
        
        Args:
            param_name: Name of the parameter to update (format: section_name.param_name)
            value: Value to set
        """
        print(f"DEBUG: update_parameter_value called with param_name={param_name}, value={value}")
        
        # Parse section and parameter name
        if '.' in param_name:
            section_name, param_name_only = param_name.split('.', 1)
            self.parameter_specification_factory.set_parameter_value(
                section_name, param_name_only, value, self.section_widgets
            )
            print(f"Updated parameter {param_name} to {value}")
            
            # Highlight the parameter to show it was updated
            self.highlight_updated_parameter(param_name, True)
        else:
            print(f"Invalid parameter name format: {param_name}")
    
    def get_section_names(self):
        """Get all section names in order."""
        return [section['config'].name for section in sorted(
            self.parameter_sections.values(), 
            key=lambda x: x['config'].order
        )]
    
    def get_parameter_names_in_section(self, section_name):
        """Get all parameter names in a specific section."""
        if section_name in self.parameter_sections:
            return list(self.parameter_sections[section_name]['parameters'].keys())
        return []
    
    def is_parameter_visible(self, param_name):
        """Check if a parameter is currently visible (for conditional parameters)."""
        if param_name in self.parameter_widgets:
            param_widget = self.parameter_widgets[param_name]
            return param_widget['frame'].winfo_viewable()
        return False

    def update_parameter_fields(self, parsed_parameters: dict):
        """
        Update parameter fields from parsed device responses.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            print(f"DEBUG: update_parameter_fields called with {len(parsed_parameters)} parameters")
            
            # Use the parameter specification factory to update fields
            if hasattr(self, 'parameter_specification_factory') and hasattr(self, 'section_widgets'):
                factory = self.parameter_specification_factory
                section_widgets = self.section_widgets
                
                # Map parameter names to section/parameter structure
                parameter_mapping = self._get_ui_parameter_mapping()
                
                for param_name, parsed_values in parsed_parameters.items():
                    try:
                        # Get section and parameter name from mapping
                        section_info = parameter_mapping.get(param_name)
                        if not section_info:
                            print(f"WARNING: No UI mapping found for parameter {param_name}")
                            continue
                        
                        section_name = section_info['section']
                        param_key = section_info['parameter']
                        
                        print(f"DEBUG: Updating {section_name}.{param_key} with values: {parsed_values}")
                        
                        # Update the parameter value using the factory
                        factory.set_parameter_value(section_name, param_key, parsed_values, section_widgets)
                        
                        # Highlight the updated parameter
                        full_param_name = f"{section_name}.{param_key}"
                        self.highlight_updated_parameter(full_param_name, True)
                        
                        print(f"DEBUG: Successfully updated {param_name}")
                        
                    except Exception as e:
                        print(f"ERROR: Failed to update parameter {param_name}: {str(e)}")
                
                print(f"DEBUG: Completed updating {len(parsed_parameters)} parameters")
            else:
                print("WARNING: Parameter specification factory or section widgets not available")
                # Fallback to legacy update methods
                self._update_parameters_legacy(parsed_parameters)
                
        except Exception as e:
            print(f"ERROR: Failed to update parameter fields: {str(e)}")

    def _get_ui_parameter_mapping(self) -> dict:
        """
        Get mapping of parameter names to their UI section and parameter keys.
        
        Returns:
            Dictionary mapping parameter names to section info
        """
        return {
            # Network Parameters
            'apn_settings': {'section': 'network_parameters', 'parameter': 'apn_settings'},
            'server_settings': {'section': 'network_parameters', 'parameter': 'server_settings'},
            
            # Time Parameters
            'report_intervals': {'section': 'time_parameters', 'parameter': 'report_intervals'},
            'heartbeat_intervals': {'section': 'time_parameters', 'parameter': 'heartbeat_intervals'},
            
            # Service Parameters
            'protocol': {'section': 'service_parameters', 'parameter': 'protocol'},
            'tcp_ack': {'section': 'service_parameters', 'parameter': 'tcp_ack'},
            
            # Ignition Parameters
            'ignition_type': {'section': 'ignition', 'parameter': 'ignition_type'},
            
            # Speed Parameters
            'speed_alert': {'section': 'speed', 'parameter': 'speed_alert'},
            'speed_buzzer': {'section': 'speed', 'parameter': 'speed_buzzer'},
            
            # Power Saving Parameters
            'sleep_mode': {'section': 'power_saving', 'parameter': 'sleep_mode'},
            'sleep_time': {'section': 'power_saving', 'parameter': 'sleep_time'},
            
            # Angle Parameters
            'angle_report': {'section': 'angle', 'parameter': 'angle_report'},
            
            # Battery Alert Parameters
            'backup_battery_alert': {'section': 'battery_alerts', 'parameter': 'backup_battery_alert'},
            'main_power_alert': {'section': 'battery_alerts', 'parameter': 'main_power_alert'},
            
            # Vibration Sensor Parameters
            'vibration_sensitivity': {'section': 'vibration_sensor', 'parameter': 'vibration_sensitivity'},
            
            # Jammer Detection Parameters
            'jammer_detection': {'section': 'jammer_detection', 'parameter': 'jammer_detection'},
            'jammer_relay_action': {'section': 'jammer_detection', 'parameter': 'jammer_relay_action'},
            
            # Miscellaneous Parameters
            'odometer': {'section': 'miscellaneous', 'parameter': 'odometer'},
            'hourmeter': {'section': 'miscellaneous', 'parameter': 'hourmeter'}
        }

    def _update_parameters_legacy(self, parsed_parameters: dict):
        """
        Update parameters using legacy methods as fallback.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            print("DEBUG: Using legacy parameter update methods")
            
            # Handle specific parameter types with legacy methods
            if 'apn_settings' in parsed_parameters:
                apn_data = parsed_parameters['apn_settings']
                self.update_apn_fields(
                    server=apn_data.get('apn', ''),
                    user=apn_data.get('user', ''),
                    password=apn_data.get('password', '')
                )
            
            # Add more legacy parameter updates as needed
            for param_name, values in parsed_parameters.items():
                if isinstance(values, dict):
                    for field_name, field_value in values.items():
                        full_param_name = f"{param_name}.{field_name}"
                        self.update_parameter_value(full_param_name, field_value)
                else:
                    self.update_parameter_value(param_name, values)
                    
        except Exception as e:
            print(f"ERROR: Failed to update parameters using legacy methods: {str(e)}")

    def get_parameter_update_summary(self) -> dict:
        """
        Get a summary of recent parameter updates.
        
        Returns:
            Dictionary with update summary information
        """
        try:
            # This would integrate with the configuration reader service
            # to get update statistics and information
            if hasattr(self.master, 'configuration_reader_service'):
                config_reader = self.master.configuration_reader_service
                if hasattr(config_reader, 'get_update_statistics'):
                    return config_reader.get_update_statistics()
            
            return {
                'total_updates': 0,
                'changed_updates': 0,
                'unchanged_updates': 0,
                'last_update': None,
                'error': 'Configuration reader service not available'
            }
            
        except Exception as e:
            return {'error': f'Failed to get update summary: {str(e)}'}

    def export_parameter_updates(self, file_path: str = None) -> str:
        """
        Export parameter update log.
        
        Args:
            file_path: Optional file path to save the log
            
        Returns:
            Log content as string or error message
        """
        try:
            if hasattr(self.master, 'configuration_reader_service'):
                config_reader = self.master.configuration_reader_service
                if hasattr(config_reader, 'export_parameter_update_log'):
                    return config_reader.export_parameter_update_log(file_path)
            
            return "ERROR: Configuration reader service not available for export"
            
        except Exception as e:
            return f"ERROR: Failed to export parameter updates: {str(e)}"
    
    def _setup_enhanced_apn_validation_with_mixin(self):
        """Set up enhanced APN validation using ValidationMixin with progressive feedback."""
        try:
            # Get APN settings parameter widget
            network_section = self.section_widgets.get('network_parameters')
            if not network_section:
                print("Warning: Network parameters section not found for APN validation setup")
                return
            
            apn_parameter = network_section.parameters.get('apn_settings')
            if not apn_parameter:
                print("Warning: APN settings parameter not found for validation setup")
                return
            
            # Store APN widgets for validation
            self.apn_widgets = apn_parameter.ui_elements
            
            # Set up enhanced real-time validation for APN fields using ValidationMixin
            if 'apn' in self.apn_widgets:
                apn_widget = self.apn_widgets['apn']
                self.setup_real_time_validation(
                    field_name='apn',
                    widget=apn_widget,
                    validation_callback=self._validate_apn_field_comprehensive,
                    debounce_ms=500,
                    enable_tooltips=True,
                    enable_message_display=True
                )
                
                user_widget = self.apn_widgets['user']
                self.setup_real_time_validation(
                    field_name='apn_user',
                    widget=user_widget,
                    validation_callback=self._validate_apn_user_field_comprehensive,
                    debounce_ms=300,
                    enable_tooltips=True,
                    enable_message_display=True
                )
            
            if 'password' in self.apn_widgets:
                password_widget = self.apn_widgets['password']
                self.setup_real_time_validation(
                    field_name='apn_password',
                    widget=password_widget,
                    validation_callback=self._validate_apn_password_field_comprehensive,
                    debounce_ms=300,
                    enable_tooltips=True,
                    enable_message_display=True
                )
            
            print("Enhanced APN validation with progressive feedback setup completed successfully")
            
        except Exception as e:
            print(f"Error setting up enhanced APN validation with mixin: {e}")
    
    def send_apn_command(self):
        """Validates and sends the complete APN configuration command with enhanced validation."""
        if not self.serial_service.is_connected:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("not_connected_error")
            )
            return

        # Check if form submission should be prevented due to validation errors
        if self.prevent_form_submission_on_validation_errors():
            validation_errors = self.get_validation_errors()
            error_messages = []
            
            for field_name, error_message in validation_errors.items():
                field_display = field_name.replace('_', ' ').title()
                error_messages.append(f"{field_display}: {error_message}")
            
            show_error(
                self,
                self.i18n.get("validation_errors", "Validation Errors"),
                "Please fix the following validation errors before sending:\n\n" + "\n".join(error_messages)
            )
            return

        # Get APN values from the network parameters section
        apn_values = self._get_apn_values_from_section()
        if not apn_values:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("apn_server_required")
            )
            return

        server = apn_values.get('apn', '').strip()
        user = apn_values.get('user', '').strip()
        password = apn_values.get('password', '').strip()

        # APN server is mandatory if any APN setting is being sent.
        if not server:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("apn_server_required")
            )
            return

        # Final comprehensive validation using the APN validation component
        validation_result = self.apn_validation_component.validate_apn_configuration(server, user, password)
        if not validation_result.is_valid:
            show_error(
                self,
                self.i18n.get("invalid_apn_server_title", "Invalid APN Configuration"),
                validation_result.error_message + 
                (f"\n\nSuggestions:\n• " + "\n• ".join(validation_result.suggestions) if validation_result.suggestions else "")
            )
            return

        # Construct the command. User and password can be empty.
        command = f"ATSMS:APN,{server},{user},{password}#"
        self.serial_service.send_command(command)
        
        # Show success feedback
        show_info(
            self,
            self.i18n.get("success", "Success"),
            f"APN configuration sent successfully:\nAPN: {server}\nUser: {user if user else '(none)'}"
        )

    def send_trans_mode_command(self):
        """Sends the Transmission Mode command to the device (always TCP)."""
        # Always use TCP (0) for transmission mode
        self._send_command_if_value("ATSMS:SZCS#PROTOCOL={value}#", "0")
    
    def update_language_display(self):
        """Updates all UI elements with the current language."""
        # Update frame label
        self.configure(label_text=self.i18n.get("parameters"))
        
        # Update all sections and parameters using the specification factory
        self.parameter_specification_factory.update_language_display(self.section_widgets)
    
    def update_apn_fields(self, server=None, user=None, password=None):
        """
        Update APN fields with values read from the device.
        
        Args:
            server: APN server value
            user: APN user value
            password: APN password value
        """
        print(f"DEBUG: update_apn_fields called with server={server}, user={user}, password={password}")
        
        # Build APN values dictionary
        apn_values = {}
        if server is not None:
            apn_values['apn'] = server
            print(f"Updated APN server to {server}")
        if user is not None:
            apn_values['user'] = user
            print(f"Updated APN user to {user}")
        if password is not None:
            apn_values['password'] = password
            print(f"Updated APN password to {password}")
        
        if apn_values:
            # Update APN settings in the network parameters section
            self.parameter_specification_factory.set_parameter_value(
                'network_parameters', 'apn_settings', apn_values, self.section_widgets
            )
            self.highlight_updated_parameter("network_parameters.apn_settings", True)
    
    def update_parameter_value(self, param_name, value):
        """
        Update a parameter value.
        
        Args:
            param_name: Name of the parameter to update (format: section_name.param_name)
            value: Value to set
        """
        print(f"DEBUG: update_parameter_value called with param_name={param_name}, value={value}")
        
        # Parse section and parameter name
        if '.' in param_name:
            section_name, param_name_only = param_name.split('.', 1)
            self.parameter_specification_factory.set_parameter_value(
                section_name, param_name_only, value, self.section_widgets
            )
            print(f"Updated parameter {param_name} to {value}")
            
            # Highlight the parameter to show it was updated
            self.highlight_updated_parameter(param_name, True)
        else:
            print(f"Invalid parameter name format: {param_name}")
    
    def get_section_names(self):
        """Get all section names in order."""
        return [section['config'].name for section in sorted(
            self.parameter_sections.values(), 
            key=lambda x: x['config'].order
        )]
    
    def get_parameter_names_in_section(self, section_name):
        """Get all parameter names in a specific section."""
        if section_name in self.parameter_sections:
            return list(self.parameter_sections[section_name]['parameters'].keys())
        return []
    
    def is_parameter_visible(self, param_name):
        """Check if a parameter is currently visible (for conditional parameters)."""
        if param_name in self.parameter_widgets:
            param_widget = self.parameter_widgets[param_name]
            return param_widget['frame'].winfo_viewable()
        return False

    def update_parameter_fields(self, parsed_parameters: dict):
        """
        Update parameter fields from parsed device responses.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            print(f"DEBUG: update_parameter_fields called with {len(parsed_parameters)} parameters")
            
            # Use the parameter specification factory to update fields
            if hasattr(self, 'parameter_specification_factory') and hasattr(self, 'section_widgets'):
                factory = self.parameter_specification_factory
                section_widgets = self.section_widgets
                
                # Map parameter names to section/parameter structure
                parameter_mapping = self._get_ui_parameter_mapping()
                
                for param_name, parsed_values in parsed_parameters.items():
                    try:
                        # Get section and parameter name from mapping
                        section_info = parameter_mapping.get(param_name)
                        if not section_info:
                            print(f"WARNING: No UI mapping found for parameter {param_name}")
                            continue
                        
                        section_name = section_info['section']
                        param_key = section_info['parameter']
                        
                        print(f"DEBUG: Updating {section_name}.{param_key} with values: {parsed_values}")
                        
                        # Update the parameter value using the factory
                        factory.set_parameter_value(section_name, param_key, parsed_values, section_widgets)
                        
                        # Highlight the updated parameter
                        full_param_name = f"{section_name}.{param_key}"
                        self.highlight_updated_parameter(full_param_name, True)
                        
                        print(f"DEBUG: Successfully updated {param_name}")
                        
                    except Exception as e:
                        print(f"ERROR: Failed to update parameter {param_name}: {str(e)}")
                
                print(f"DEBUG: Completed updating {len(parsed_parameters)} parameters")
            else:
                print("WARNING: Parameter specification factory or section widgets not available")
                # Fallback to legacy update methods
                self._update_parameters_legacy(parsed_parameters)
                
        except Exception as e:
            print(f"ERROR: Failed to update parameter fields: {str(e)}")

    def _get_ui_parameter_mapping(self) -> dict:
        """
        Get mapping of parameter names to their UI section and parameter keys.
        
        Returns:
            Dictionary mapping parameter names to section info
        """
        return {
            # Network Parameters
            'apn_settings': {'section': 'network_parameters', 'parameter': 'apn_settings'},
            'server_settings': {'section': 'network_parameters', 'parameter': 'server_settings'},
            
            # Time Parameters
            'report_intervals': {'section': 'time_parameters', 'parameter': 'report_intervals'},
            'heartbeat_intervals': {'section': 'time_parameters', 'parameter': 'heartbeat_intervals'},
            
            # Service Parameters
            'protocol': {'section': 'service_parameters', 'parameter': 'protocol'},
            'tcp_ack': {'section': 'service_parameters', 'parameter': 'tcp_ack'},
            
            # Ignition Parameters
            'ignition_type': {'section': 'ignition', 'parameter': 'ignition_type'},
            
            # Speed Parameters
            'speed_alert': {'section': 'speed', 'parameter': 'speed_alert'},
            'speed_buzzer': {'section': 'speed', 'parameter': 'speed_buzzer'},
            
            # Power Saving Parameters
            'sleep_mode': {'section': 'power_saving', 'parameter': 'sleep_mode'},
            'sleep_time': {'section': 'power_saving', 'parameter': 'sleep_time'},
            
            # Angle Parameters
            'angle_report': {'section': 'angle', 'parameter': 'angle_report'},
            
            # Battery Alert Parameters
            'backup_battery_alert': {'section': 'battery_alerts', 'parameter': 'backup_battery_alert'},
            'main_power_alert': {'section': 'battery_alerts', 'parameter': 'main_power_alert'},
            
            # Vibration Sensor Parameters
            'vibration_sensitivity': {'section': 'vibration_sensor', 'parameter': 'vibration_sensitivity'},
            
            # Jammer Detection Parameters
            'jammer_detection': {'section': 'jammer_detection', 'parameter': 'jammer_detection'},
            'jammer_relay_action': {'section': 'jammer_detection', 'parameter': 'jammer_relay_action'},
            
            # Miscellaneous Parameters
            'odometer': {'section': 'miscellaneous', 'parameter': 'odometer'},
            'hourmeter': {'section': 'miscellaneous', 'parameter': 'hourmeter'}
        }

    def _update_parameters_legacy(self, parsed_parameters: dict):
        """
        Update parameters using legacy methods as fallback.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            print("DEBUG: Using legacy parameter update methods")
            
            # Handle specific parameter types with legacy methods
            if 'apn_settings' in parsed_parameters:
                apn_data = parsed_parameters['apn_settings']
                self.update_apn_fields(
                    server=apn_data.get('apn', ''),
                    user=apn_data.get('user', ''),
                    password=apn_data.get('password', '')
                )
            
            # Add more legacy parameter updates as needed
            for param_name, values in parsed_parameters.items():
                if isinstance(values, dict):
                    for field_name, field_value in values.items():
                        full_param_name = f"{param_name}.{field_name}"
                        self.update_parameter_value(full_param_name, field_value)
                else:
                    self.update_parameter_value(param_name, values)
                    
        except Exception as e:
            print(f"ERROR: Failed to update parameters using legacy methods: {str(e)}")

    def get_parameter_update_summary(self) -> dict:
        """
        Get a summary of recent parameter updates.
        
        Returns:
            Dictionary with update summary information
        """
        try:
            # This would integrate with the configuration reader service
            # to get update statistics and information
            if hasattr(self.master, 'configuration_reader_service'):
                config_reader = self.master.configuration_reader_service
                if hasattr(config_reader, 'get_update_statistics'):
                    return config_reader.get_update_statistics()
            
            return {
                'total_updates': 0,
                'changed_updates': 0,
                'unchanged_updates': 0,
                'last_update': None,
                'error': 'Configuration reader service not available'
            }
            
        except Exception as e:
            return {'error': f'Failed to get update summary: {str(e)}'}

    def export_parameter_updates(self, file_path: str = None) -> str:
        """
        Export parameter update log.
        
        Args:
            file_path: Optional file path to save the log
            
        Returns:
            Log content as string or error message
        """
        try:
            if hasattr(self.master, 'configuration_reader_service'):
                config_reader = self.master.configuration_reader_service
                if hasattr(config_reader, 'export_parameter_update_log'):
                    return config_reader.export_parameter_update_log(file_path)
            
            return "ERROR: Configuration reader service not available for export"
            
        except Exception as e:
            return f"ERROR: Failed to export parameter updates: {str(e)}"
    
    def _setup_enhanced_apn_validation_with_mixin(self):
        """Set up enhanced APN validation using ValidationMixin with progressive feedback."""
        try:
            # Get APN settings parameter widget
            network_section = self.section_widgets.get('network_parameters')
            if not network_section:
                print("Warning: Network parameters section not found for APN validation setup")
                return
            
            apn_parameter = network_section.parameters.get('apn_settings')
            if not apn_parameter:
                print("Warning: APN settings parameter not found for validation setup")
                return
            
            # Store APN widgets for validation
            self.apn_widgets = apn_parameter.ui_elements
            
            # Set up enhanced real-time validation for APN fields using ValidationMixin
            if 'apn' in self.apn_widgets:
                apn_widget = self.apn_widgets['apn']
                self.setup_real_time_validation(
                    field_name='apn',
                    widget=apn_widget,
                    validation_callback=self._validate_apn_field_comprehensive,
                    debounce_ms=500,
                    enable_tooltips=True,
                    enable_message_display=True
                )
                
                user_widget = self.apn_widgets['user']
                self.setup_real_time_validation(
                    field_name='apn_user',
                    widget=user_widget,
                    validation_callback=self._validate_apn_user_field_comprehensive,
                    debounce_ms=300,
                    enable_tooltips=True,
                    enable_message_display=True
                )
            
            if 'password' in self.apn_widgets:
                password_widget = self.apn_widgets['password']
                self.setup_real_time_validation(
                    field_name='apn_password',
                    widget=password_widget,
                    validation_callback=self._validate_apn_password_field_comprehensive,
                    debounce_ms=300,
                    enable_tooltips=True,
                    enable_message_display=True
                )
            
            print("Enhanced APN validation with progressive feedback setup completed successfully")
            
        except Exception as e:
            print(f"Error setting up enhanced APN validation with mixin: {e}")
    
    def send_apn_command(self):
        """Validates and sends the complete APN configuration command with enhanced validation."""
        if not self.serial_service.is_connected:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("not_connected_error")
            )
            return

        # Check if form submission should be prevented due to validation errors
        if self.prevent_form_submission_on_validation_errors():
            validation_errors = self.get_validation_errors()
            error_messages = []
            
            for field_name, error_message in validation_errors.items():
                field_display = field_name.replace('_', ' ').title()
                error_messages.append(f"{field_display}: {error_message}")
            
            show_error(
                self,
                self.i18n.get("validation_errors", "Validation Errors"),
                "Please fix the following validation errors before sending:\n\n" + "\n".join(error_messages)
            )
            return

        # Get APN values from the network parameters section
        apn_values = self._get_apn_values_from_section()
        if not apn_values:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("apn_server_required")
            )
            return

        server = apn_values.get('apn', '').strip()
        user = apn_values.get('user', '').strip()
        password = apn_values.get('password', '').strip()

        # APN server is mandatory if any APN setting is being sent.
        if not server:
            show_error(
                self,
                self.i18n.get("error"),
                self.i18n.get("apn_server_required")
            )
            return

        # Final comprehensive validation using the APN validation component
        validation_result = self.apn_validation_component.validate_apn_configuration(server, user, password)
        if not validation_result.is_valid:
            show_error(
                self,
                self.i18n.get("invalid_apn_server_title", "Invalid APN Configuration"),
                validation_result.error_message + 
                (f"\n\nSuggestions:\n• " + "\n• ".join(validation_result.suggestions) if validation_result.suggestions else "")
            )
            return

        # Construct the command. User and password can be empty.
        command = f"ATSMS:APN,{server},{user},{password}#"
        self.serial_service.send_command(command)
        
        # Show success feedback
        show_info(
            self,
            self.i18n.get("success", "Success"),
            f"APN configuration sent successfully:\nAPN: {server}\nUser: {user if user else '(none)'}"
        )

    def send_trans_mode_command(self):
        """Sends the Transmission Mode command to the device (always TCP)."""
        # Always use TCP (0) for transmission mode
        self._send_command_if_value("ATSMS:SZCS#PROTOCOL={value}#", "0")
    
    def update_language_display(self):
        """Updates all UI elements with the current language."""
        # Update frame label
        self.configure(label_text=self.i18n.get("parameters"))
        
        # Update all sections and parameters using the specification factory
        self.parameter_specification_factory.update_language_display(self.section_widgets)
    
    def update_apn_fields(self, server=None, user=None, password=None):
        """
        Update APN fields with values read from the device.
        
        Args:
            server: APN server value
            user: APN user value
            password: APN password value
        """
        print(f"DEBUG: update_apn_fields called with server={server}, user={user}, password={password}")
        
        # Build APN values dictionary
        apn_values = {}
        if server is not None:
            apn_values['apn'] = server
            print(f"Updated APN server to {server}")
        if user is not None:
            apn_values['user'] = user
            print(f"Updated APN user to {user}")
        if password is not None:
            apn_values['password'] = password
            print(f"Updated APN password to {password}")
        
        if apn_values:
            # Update APN settings in the network parameters section
            self.parameter_specification_factory.set_parameter_value(
                'network_parameters', 'apn_settings', apn_values, self.section_widgets
            )
            self.highlight_updated_parameter("network_parameters.apn_settings", True)
    
    def update_parameter_value(self, param_name, value):
        """
        Update a parameter value.
        
        Args:
            param_name: Name of the parameter to update (format: section_name.param_name)
            value: Value to set
        """
        print(f"DEBUG: update_parameter_value called with param_name={param_name}, value={value}")
        
        # Parse section and parameter name
        if '.' in param_name:
            section_name, param_name_only = param_name.split('.', 1)
            self.parameter_specification_factory.set_parameter_value(
                section_name, param_name_only, value, self.section_widgets
            )
            print(f"Updated parameter {param_name} to {value}")
            
            # Highlight the parameter to show it was updated
            self.highlight_updated_parameter(param_name, True)
        else:
            print(f"Invalid parameter name format: {param_name}")
    
    def get_section_names(self):
        """Get all section names in order."""
        return [section['config'].name for section in sorted(
            self.parameter_sections.values(), 
            key=lambda x: x['config'].order
        )]
    
    def get_parameter_names_in_section(self, section_name):
        """Get all parameter names in a specific section."""
        if section_name in self.parameter_sections:
            return list(self.parameter_sections[section_name]['parameters'].keys())
        return []
    
    def is_parameter_visible(self, param_name):
        """Check if a parameter is currently visible (for conditional parameters)."""
        if param_name in self.parameter_widgets:
            param_widget = self.parameter_widgets[param_name]
            return param_widget['frame'].winfo_viewable()
        return False

    def update_parameter_fields(self, parsed_parameters: dict):
        """
        Update parameter fields from parsed device responses.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            print(f"DEBUG: update_parameter_fields called with {len(parsed_parameters)} parameters")
            
            # Use the parameter specification factory to update fields
            if hasattr(self, 'parameter_specification_factory') and hasattr(self, 'section_widgets'):
                factory = self.parameter_specification_factory
                section_widgets = self.section_widgets
                
                # Map parameter names to section/parameter structure
                parameter_mapping = self._get_ui_parameter_mapping()
                
                for param_name, parsed_values in parsed_parameters.items():
                    try:
                        # Get section and parameter name from mapping
                        section_info = parameter_mapping.get(param_name)
                        if not section_info:
                            print(f"WARNING: No UI mapping found for parameter {param_name}")
                            continue
                        
                        section_name = section_info['section']
                        param_key = section_info['parameter']
                        
                        print(f"DEBUG: Updating {section_name}.{param_key} with values: {parsed_values}")
                        
                        # Update the parameter value using the factory
                        factory.set_parameter_value(section_name, param_key, parsed_values, section_widgets)
                        
                        # Highlight the updated parameter
                        full_param_name = f"{section_name}.{param_key}"
                        self.highlight_updated_parameter(full_param_name, True)
                        
                        print(f"DEBUG: Successfully updated {param_name}")
                        
                    except Exception as e:
                        print(f"ERROR: Failed to update parameter {param_name}: {str(e)}")
                
                print(f"DEBUG: Completed updating {len(parsed_parameters)} parameters")
            else:
                print("WARNING: Parameter specification factory or section widgets not available")
                # Fallback to legacy update methods
                self._update_parameters_legacy(parsed_parameters)
                
        except Exception as e:
            print(f"ERROR: Failed to update parameter fields: {str(e)}")

    def _get_ui_parameter_mapping(self) -> dict:
        """
        Get mapping of parameter names to their UI section and parameter keys.
        
        Returns:
            Dictionary mapping parameter names to section info
        """
        return {
            # Network Parameters
            'apn_settings': {'section': 'network_parameters', 'parameter': 'apn_settings'},
            'server_settings': {'section': 'network_parameters', 'parameter': 'server_settings'},
            
            # Time Parameters
            'report_intervals': {'section': 'time_parameters', 'parameter': 'report_intervals'},
            'heartbeat_intervals': {'section': 'time_parameters', 'parameter': 'heartbeat_intervals'},
            
            # Service Parameters
            'protocol': {'section': 'service_parameters', 'parameter': 'protocol'},
            'tcp_ack': {'section': 'service_parameters', 'parameter': 'tcp_ack'},
            
            # Ignition Parameters
            'ignition_type': {'section': 'ignition', 'parameter': 'ignition_type'},
            
            # Speed Parameters
            'speed_alert': {'section': 'speed', 'parameter': 'speed_alert'},
            'speed_buzzer': {'section': 'speed', 'parameter': 'speed_buzzer'},
            
            # Power Saving Parameters
            'sleep_mode': {'section': 'power_saving', 'parameter': 'sleep_mode'},
            'sleep_time': {'section': 'power_saving', 'parameter': 'sleep_time'},
            
            # Angle Parameters
            'angle_report': {'section': 'angle', 'parameter': 'angle_report'},
            
            # Battery Alert Parameters
            'backup_battery_alert': {'section': 'battery_alerts', 'parameter': 'backup_battery_alert'},
            'main_power_alert': {'section': 'battery_alerts', 'parameter': 'main_power_alert'},
            
            # Vibration Sensor Parameters
            'vibration_sensitivity': {'section': 'vibration_sensor', 'parameter': 'vibration_sensitivity'},
            
            # Jammer Detection Parameters
            'jammer_detection': {'section': 'jammer_detection', 'parameter': 'jammer_detection'},
            'jammer_relay_action': {'section': 'jammer_detection', 'parameter': 'jammer_relay_action'},
            
            # Miscellaneous Parameters
            'odometer': {'section': 'miscellaneous', 'parameter': 'odometer'},
            'hourmeter': {'section': 'miscellaneous', 'parameter': 'hourmeter'}
        }

    def _update_parameters_legacy(self, parsed_parameters: dict):
        """
        Update parameters using legacy methods as fallback.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            print("DEBUG: Using legacy parameter update methods")
            
            # Handle specific parameter types with legacy methods
            if 'apn_settings' in parsed_parameters:
                apn_data = parsed_parameters['apn_settings']
                self.update_apn_fields(
                    server=apn_data.get('apn', ''),
                    user=apn_data.get('user', ''),
                    password=apn_data.get('password', '')
                )
            
            # Add more legacy parameter updates as needed
            for param_name, values in parsed_parameters.items():
                if isinstance(values, dict):
                    for field_name, field_value in values.items():
                        full_param_name = f"{param_name}.{field_name}"
                        self.update_parameter_value(full_param_name, field_value)
                else:
                    self.update_parameter_value(param_name, values)
                    
        except Exception as e:
            print(f"ERROR: Failed to update parameters using legacy methods: {str(e)}")

    def get_parameter_update_summary(self) -> dict:
        """
        Get a summary of recent parameter updates.
        
        Returns:
            Dictionary with update summary information
        """
        try:
            # This would integrate with the configuration reader service
            # to get update statistics and information
            if hasattr(self.master, 'configuration_reader_service'):
                config_reader = self.master.configuration_reader_service
                if hasattr(config_reader, 'get_update_statistics'):
                    return config_reader.get_update_statistics()
            
            return {
                'total_updates': 0,
                'changed_updates': 0,
                'unchanged_updates': 0,
                'last_update': None,
                'error': 'Configuration reader service not available'
            }
            
        except Exception as e:
            return {'error': f'Failed to get update summary: {str(e)}'}

    def export_parameter_updates(self, file_path: str = None) -> str:
        """
        Export parameter update log.
        
        Args:
            file_path: Optional file path to save the log
            
        Returns:
            Log content as string or error message
        """
        try:
            if hasattr(self.master, 'configuration_reader_service'):
                config_reader = self.master.configuration_reader_service
                if hasattr(config_reader, 'export_parameter_update_log'):
                    return config_reader.export_parameter_update_log(file_path)
            
            return "ERROR: Configuration reader service not available for export"
            
        except Exception as e:
            return f"ERROR: Failed to export parameter updates: {str(e)}"
    
    def update_parameters_with_batch_processing(self, parameters: dict):
        """
        Update parameters using batch processing for optimal responsiveness.
        
        Args:
            parameters: Dictionary of parameter names to values
            
        Requirements: 7.1, 7.2, 7.4, 7.5
        """
        try:
            print(f"DEBUG: Using batch processing for {len(parameters)} parameters")
            
            # Import here to avoid circular imports
            from services.ui_responsiveness_service import UIResponsivenessService, UpdatePriority
            
            # Create UI responsiveness service if not available
            if not hasattr(self, '_ui_responsiveness_service'):
                self._ui_responsiveness_service = UIResponsivenessService(self)
            
            # Process parameters in batches with visual feedback
            def progress_callback(current, total):
                print(f"DEBUG: Batch update progress: {current}/{total}")
            
            # Queue parameters for batch processing
            self._ui_responsiveness_service.queue_multiple_parameter_updates(
                parameters, UpdatePriority.NORMAL, True
            )
            
            # Process the queue
            result = self._ui_responsiveness_service.process_update_queue()
            
            # Log results
            print(f"DEBUG: Batch processing completed: {result.successful_updates}/{result.total_updates} successful in {result.update_duration_ms:.1f}ms")
            
            if result.update_duration_ms > 100:
                print(f"WARNING: Batch processing exceeded 100ms target: {result.update_duration_ms:.1f}ms")
            
            if result.errors:
                print(f"WARNING: Batch processing had {len(result.errors)} errors")
                for error in result.errors[:3]:  # Show first 3 errors
                    print(f"  - {error}")
                    
        except Exception as e:
            print(f"ERROR: Batch processing failed: {str(e)}")
            # Fallback to individual updates
            print("DEBUG: Falling back to individual parameter updates")
    
    def enable_ui_responsiveness_monitoring(self):
        """
        Enable UI responsiveness monitoring and optimization.
        
        This method sets up performance monitoring for UI updates to ensure
        they meet the 100ms responsiveness requirement.
        
        Requirements: 7.1, 7.5
        """
        try:
            from services.ui_responsiveness_service import UIResponsivenessService
            
            if not hasattr(self, '_ui_responsiveness_service'):
                self._ui_responsiveness_service = UIResponsivenessService(self)
                print("DEBUG: UI responsiveness monitoring enabled")
            
            # Set up periodic performance reporting
            def report_performance():
                if hasattr(self, '_ui_responsiveness_service'):
                    performance = self._ui_responsiveness_service.get_performance_summary()
                    if performance['total_batches'] > 0:
                        print(f"UI Performance: avg {performance['avg_duration_ms']:.1f}ms, "
                              f"{performance['avg_updates_per_second']:.1f} updates/sec")
                
                # Schedule next report
                self.after(30000, report_performance)  # Every 30 seconds
            
            # Start performance reporting
            self.after(30000, report_performance)
            
        except Exception as e:
            print(f"ERROR: Failed to enable UI responsiveness monitoring: {str(e)}")