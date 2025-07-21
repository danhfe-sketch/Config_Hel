import customtkinter as ctk
import re
from ipaddress import ip_address
from tkinter import messagebox
from ui.parameter_factory import ParameterFactory
from services.validation_service import ValidationService

class ParametersFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, i18n):
        super().__init__(master, label_text=i18n.get("parameters"))
        self.i18n = i18n
        self.serial_service = master.serial_service  # Get serial service from master
        
        # Initialize validation service and parameter factory
        self.validation_service = ValidationService(i18n)
        self.parameter_factory = ParameterFactory(
            self.validation_service, 
            i18n, 
            self._send_command_callback
        )
        
        # Store parameter widgets for value retrieval
        self.parameter_widgets = {}
        # Store parameter groups for language updates
        self.parameter_groups = {}

        self.grid_columnconfigure(0, weight=1)
        
        # Create APN configuration first
        self._create_apn_configuration()
        
        # Create parameter groups and widgets
        self._create_parameter_groups()

    def _create_apn_configuration(self):
        """Create the APN configuration section."""
        # --- APN Configuration ---
        self.apn_frame = ctk.CTkFrame(self)
        self.apn_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.apn_frame.grid_columnconfigure(1, weight=1)

        self.apn_title = ctk.CTkLabel(self.apn_frame, text=self.i18n.get("apn_config", "APN Configuration"), font=ctk.CTkFont(weight="bold"))
        self.apn_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="w")

        # APN Server
        self.apn_server_label = ctk.CTkLabel(self.apn_frame, text=self.i18n.get("apn_server"))
        self.apn_server_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.apn_server_entry = ctk.CTkEntry(self.apn_frame)
        self.apn_server_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # APN User
        self.apn_user_label = ctk.CTkLabel(self.apn_frame, text=self.i18n.get("apn_user"))
        self.apn_user_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.apn_user_entry = ctk.CTkEntry(self.apn_frame)
        self.apn_user_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # APN Password
        self.apn_password_label = ctk.CTkLabel(self.apn_frame, text=self.i18n.get("apn_password"))
        self.apn_password_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.apn_password_entry = ctk.CTkEntry(self.apn_frame)
        self.apn_password_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Single Send Button for APN
        self.apn_send_button = ctk.CTkButton(
            self.apn_frame, text=self.i18n.get("send_apn_config"), command=self.send_apn_command
        )
        self.apn_send_button.grid(row=4, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")

        # Transmission Mode is always TCP (removed from UI)

    def _create_parameter_groups(self):
        """Create parameter groups and their widgets using the factory pattern."""
        # Define the groups and their parameters in the required sequence
        
        # First, create the server configuration group (to be placed after APN)
        server_group = self.parameter_factory.create_group('server', 'main_server')
        
        # Create server parameters (only URL/IP and Port)
        server_ip_param = self.parameter_factory.create_parameter('server_ip')
        server_port_param = self.parameter_factory.create_parameter('server_port')
        
        if server_ip_param:
            server_group.add_parameter(server_ip_param)
            self.parameter_widgets['server_ip'] = server_ip_param
            
        if server_port_param:
            server_group.add_parameter(server_port_param)
            self.parameter_widgets['server_port'] = server_port_param
        
        # Store the server group for language updates
        self.parameter_groups['server'] = server_group
        
        # Place the server configuration group right after APN
        if server_group.parameters:
            server_widget = server_group.create_widget(self)
            server_widget.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        # Create the protocol configuration group
        protocol_group = self.parameter_factory.create_group('protocol', 'protocol_configuration')
        
        # Create protocol parameters
        protocol_param = self.parameter_factory.create_parameter('gt06_protocol')
        tcp_ack_param = self.parameter_factory.create_parameter('tcp_ack_config')
        
        if protocol_param:
            protocol_group.add_parameter(protocol_param)
            self.parameter_widgets['gt06_protocol'] = protocol_param
            
        if tcp_ack_param:
            protocol_group.add_parameter(tcp_ack_param)
            self.parameter_widgets['tcp_ack_config'] = tcp_ack_param
        
        # Store the protocol group for language updates
        self.parameter_groups['protocol'] = protocol_group
        
        # Place the protocol configuration group after server
        if protocol_group.parameters:
            protocol_widget = protocol_group.create_widget(self)
            protocol_widget.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        # Define the remaining groups and their parameters
        group_configs = {
            'sensors': {
                'display_label': 'sensor_configuration',
                'parameters': ['vibration', 'sensitivity', 'curve_sensor', 'ignition_type']
            },
            'timers': {
                'display_label': 'timer_configuration', 
                'parameters': ['timer_ign_on', 'timer_ign_off', 'heartbeat_ign_on', 'heartbeat_ign_off', 'heartbeat_interval']
            },
            'security': {
                'display_label': 'security_settings',
                'parameters': ['lock_type']
            }
        }
        
        row_index = 3  # Start after APN, Server, and Protocol configuration
        
        for group_name, config in group_configs.items():
            # Create parameter group
            group = self.parameter_factory.create_group(group_name, config['display_label'])
            
            # Add parameters to group
            for param_name in config['parameters']:
                parameter = self.parameter_factory.create_parameter(param_name)
                if parameter:
                    group.add_parameter(parameter)
                    self.parameter_widgets[param_name] = parameter
            
            # Store the group for language updates
            self.parameter_groups[group_name] = group
            
            # Create and place group widget
            if group.parameters:  # Only create if group has parameters
                group_widget = group.create_widget(self)
                group_widget.grid(row=row_index, column=0, padx=10, pady=10, sticky="ew")
                row_index += 1
    
    def _send_command_callback(self, command: str):
        """Callback for parameter factory to send commands."""
        if self.serial_service:
            self.serial_service.send_command(command)
    
    def get_all_parameter_values(self):
        """Get all parameter values from the factory-created widgets."""
        values = {}
        for param_name, parameter in self.parameter_widgets.items():
            values[param_name] = parameter.get_value()
        return values
    
    def set_all_parameter_values(self, values):
        """Set parameter values in the factory-created widgets."""
        for param_name, value in values.items():
            if param_name in self.parameter_widgets:
                self.parameter_widgets[param_name].set_value(value)
    
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
                ui_widget = getattr(parameter_widget, 'widget', None)
                
                if ui_widget:
                    if value_changed:
                        # Green border for changed values
                        original_border_color = ui_widget.cget("border_color")
                        ui_widget.configure(border_color="#00ff00", border_width=2)
                        
                        # Schedule removal after 3 seconds
                        self.after(3000, lambda: self._remove_parameter_highlight(ui_widget, original_border_color))
                    else:
                        # Blue border for unchanged values
                        original_border_color = ui_widget.cget("border_color")
                        ui_widget.configure(border_color="#0066cc", border_width=1)
                        
                        # Schedule removal after 2 seconds
                        self.after(2000, lambda: self._remove_parameter_highlight(ui_widget, original_border_color))
                        
        except Exception as e:
            print(f"WARNING: Failed to highlight parameter {param_name}: {str(e)}")
    
    def _remove_parameter_highlight(self, widget, original_border_color):
        """Remove the highlight from a parameter widget."""
        try:
            widget.configure(border_color=original_border_color, border_width=0)
        except Exception as e:
            print(f"WARNING: Failed to remove parameter highlight: {str(e)}")
    
    def get_parameter_widget(self, param_name: str):
        """Get a specific parameter widget by name."""
        return self.parameter_widgets.get(param_name)

    def _send_command_if_value(self, command_template: str, value: str):
        """Helper to send a command if the value is not empty."""
        if value:
            self.serial_service.send_command(command_template.format(value=value))
    
    def send_apn_command(self):
        """Validates and sends the complete APN configuration command."""
        if not self.serial_service.is_connected:
            messagebox.showerror(
                self.i18n.get("error"),
                self.i18n.get("not_connected_error")
            )
            return

        server = self.apn_server_entry.get().strip()
        user = self.apn_user_entry.get().strip()
        password = self.apn_password_entry.get().strip()

        # APN server is mandatory if any APN setting is being sent.
        if not server:
            messagebox.showerror(
                self.i18n.get("error"),
                self.i18n.get("apn_server_required")
            )
            return

        # Validate the APN server format (domain or IP)
        validation_result = self.validation_service.validate_parameter('apn_server', server)
        if not validation_result.is_valid:
            messagebox.showerror(
                self.i18n.get("invalid_apn_server_title", "Invalid APN Server"),
                validation_result.error_message,
            )
            return

        # Construct the command. User and password can be empty.
        command = f"ATSMS:APN,{server},{user},{password}#"
        self.serial_service.send_command(command)

    def send_trans_mode_command(self):
        """Sends the Transmission Mode command to the device (always TCP)."""
        # Always use TCP (0) for transmission mode
        self._send_command_if_value("ATSMS:SZCS#PROTOCOL={value}#", "0")
    
    def update_language_display(self):
        """Updates all UI elements with the current language."""
        # Update frame label
        self.configure(label_text=self.i18n.get("parameters"))
        
        # Update APN configuration section
        self.apn_title.configure(text=self.i18n.get("apn_config"))
        
        # Update APN labels
        self.apn_server_label.configure(text=self.i18n.get("apn_server"))
        self.apn_user_label.configure(text=self.i18n.get("apn_user"))
        self.apn_password_label.configure(text=self.i18n.get("apn_password"))
        
        # Update APN button
        self.apn_send_button.configure(text=self.i18n.get("send_apn_config"))
        
        # Update parameter factory widgets
        for param_name, parameter in self.parameter_widgets.items():
            if hasattr(parameter, 'update_language_display'):
                parameter.update_language_display(self.i18n)
        
        # Update parameter groups
        for group_name, group in self.parameter_groups.items():
            if hasattr(group, 'update_language_display'):
                group.update_language_display(self.i18n)
    
    def update_apn_fields(self, server=None, user=None, password=None):
        """
        Update APN fields with values read from the device.
        
        Args:
            server: APN server value
            user: APN user value
            password: APN password value
        """
        print(f"DEBUG: update_apn_fields called with server={server}, user={user}, password={password}")
        if server is not None:
            self.apn_server_entry.delete(0, 'end')
            self.apn_server_entry.insert(0, server)
            print(f"Updated APN server to {server}")
        
        if user is not None:
            self.apn_user_entry.delete(0, 'end')
            self.apn_user_entry.insert(0, user)
            print(f"Updated APN user to {user}")
        
        if password is not None:
            self.apn_password_entry.delete(0, 'end')
            self.apn_password_entry.insert(0, password)
            print(f"Updated APN password to {password}")
    
    def update_parameter_value(self, param_name, value):
        """
        Update a parameter value.
        
        Args:
            param_name: Name of the parameter to update
            value: Value to set
        """
        print(f"DEBUG: update_parameter_value called with param_name={param_name}, value={value}")
        if param_name in self.parameter_widgets:
            parameter_widget = self.parameter_widgets[param_name]
            if hasattr(parameter_widget, 'set_value'):
                parameter_widget.set_value(value)
                print(f"Updated parameter {param_name} to {value}")
                
                # Highlight the parameter to show it was updated
                self.highlight_updated_parameter(param_name, True)
            else:
                print(f"Parameter widget {param_name} does not have a set_value method")
        else:
            print(f"Parameter widget {param_name} not found")