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

        self.apn_title = ctk.CTkLabel(self.apn_frame, text=self.i18n.get("apn_config"), font=ctk.CTkFont(weight="bold"))
        self.apn_title.grid(row=0, column=0, columnspan=3, padx=10, pady=(5, 10), sticky="w")

        # APN Server
        self.apn_server_label = ctk.CTkLabel(self.apn_frame, text=self.i18n.get("apn_server"))
        self.apn_server_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.apn_server_entry = ctk.CTkEntry(self.apn_frame)
        self.apn_server_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.apn_send_button = ctk.CTkButton(
            self.apn_frame, text=self.i18n.get("send"), width=60, command=self.send_apn_server_command
        )
        self.apn_send_button.grid(row=1, column=2, padx=(5, 10), pady=5)

        # APN User
        self.apn_user_label = ctk.CTkLabel(self.apn_frame, text=self.i18n.get("apn_user"))
        self.apn_user_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.apn_user_entry = ctk.CTkEntry(self.apn_frame)
        self.apn_user_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.apn_user_send_button = ctk.CTkButton(
            self.apn_frame, text=self.i18n.get("send"), width=60, command=self.send_apn_user_command
        )
        self.apn_user_send_button.grid(row=2, column=2, padx=(5, 10), pady=5)

        # APN Password
        self.apn_password_label = ctk.CTkLabel(self.apn_frame, text=self.i18n.get("apn_password"))
        self.apn_password_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.apn_password_entry = ctk.CTkEntry(self.apn_frame, show="*")
        self.apn_password_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.apn_password_send_button = ctk.CTkButton(
            self.apn_frame, text=self.i18n.get("send"), width=60, command=self.send_apn_password_command
        )
        self.apn_password_send_button.grid(row=3, column=2, padx=(5, 10), pady=5)

        # Transmission Mode
        self.trans_mode_label = ctk.CTkLabel(self.apn_frame, text=self.i18n.get("transmission_mode"))
        self.trans_mode_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")

        self.trans_mode_var = ctk.StringVar(value="TCP")
        self.tcp_radio = ctk.CTkRadioButton(self.apn_frame, text=self.i18n.get("tcp"), variable=self.trans_mode_var, value="TCP")
        self.tcp_radio.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        self.udp_radio = ctk.CTkRadioButton(self.apn_frame, text=self.i18n.get("udp"), variable=self.trans_mode_var, value="UDP")
        self.udp_radio.grid(row=4, column=1, padx=(80, 5), pady=5, sticky="w")

        self.trans_mode_send_button = ctk.CTkButton(
            self.apn_frame,
            text=self.i18n.get("send"),
            width=60,
            command=self.send_trans_mode_command,
        )
        self.trans_mode_send_button.grid(row=4, column=2, padx=(5, 10), pady=5)

    def _create_parameter_groups(self):
        """Create parameter groups and their widgets using the factory pattern."""
        # Define the groups and their parameters
        group_configs = {
            'sensors': {
                'display_label': 'sensor_configuration',
                'parameters': ['vibration', 'sensitivity', 'curve_sensor', 'ignition_type']
            },
            'timers': {
                'display_label': 'timer_configuration', 
                'parameters': ['timer_ign_on', 'timer_ign_off', 'heartbeat_ign_on', 'heartbeat_ign_off', 'heartbeat_interval']
            },
            'communication': {
                'display_label': 'communication_settings',
                'parameters': ['transmission_mode']
            },
            'security': {
                'display_label': 'security_settings',
                'parameters': ['lock_type']
            }
        }
        
        row_index = 1  # Start after APN configuration
        
        for group_name, config in group_configs.items():
            # Create parameter group
            group = self.parameter_factory.create_group(group_name, config['display_label'])
            
            # Add parameters to group
            for param_name in config['parameters']:
                parameter = self.parameter_factory.create_parameter(param_name)
                if parameter:
                    group.add_parameter(parameter)
                    self.parameter_widgets[param_name] = parameter
            
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

    def _send_command_if_value(self, command_template: str, value: str):
        """Helper to send a command if the value is not empty."""
        if value:
            self.serial_service.send_command(command_template.format(value=value))

    def send_apn_server_command(self):
        """Sends the APN Server command to the device after validation."""
        value = self.apn_server_entry.get()
        if value:
            # Use validation service for proper APN server validation
            validation_result = self.validation_service.validate_parameter('apn_server', value)
            if not validation_result.is_valid:
                messagebox.showerror(
                    self.i18n.get("invalid_apn_server_title"),
                    validation_result.error_message,
                )
                return
        self._send_command_if_value("ATSMS:APN,{value},,#", value)

    def send_apn_user_command(self):
        """Sends the APN User command to the device."""
        server = self.apn_server_entry.get()
        user = self.apn_user_entry.get()
        if server and user:
            self.serial_service.send_command(f"ATSMS:APN,{server},{user},#")
        elif user:
            messagebox.showerror(
                self.i18n.get("error"),
                self.i18n.get("apn_server_required")
            )

    def send_apn_password_command(self):
        """Sends the APN Password command to the device."""
        server = self.apn_server_entry.get()
        user = self.apn_user_entry.get()
        password = self.apn_password_entry.get()
        
        if server and user and password:
            self.serial_service.send_command(f"ATSMS:APN,{server},{user},{password}#")
        elif password:
            missing = []
            if not server:
                missing.append(self.i18n.get("apn_server"))
            if not user:
                missing.append(self.i18n.get("apn_user"))
            
            messagebox.showerror(
                self.i18n.get("error"),
                self.i18n.get("missing_fields") + ": " + ", ".join(missing)
            )

    def send_trans_mode_command(self):
        """Sends the Transmission Mode command to the device."""
        # Map TCP/UDP to the correct values according to LT32Pro documentation
        mode_map = {"TCP": "0", "UDP": "1"}
        value = self.trans_mode_var.get()
        mapped_value = mode_map.get(value, "0")  # Default to TCP (0) if not found
        self._send_command_if_value("ATSMS:SZCS#PROTOCOL={value}#", mapped_value)
    
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
        self.trans_mode_label.configure(text=self.i18n.get("transmission_mode"))
        
        # Update APN buttons
        self.apn_send_button.configure(text=self.i18n.get("send"))
        self.apn_user_send_button.configure(text=self.i18n.get("send"))
        self.apn_password_send_button.configure(text=self.i18n.get("send"))
        self.trans_mode_send_button.configure(text=self.i18n.get("send"))
        
        # Update radio buttons
        self.tcp_radio.configure(text=self.i18n.get("tcp"))
        self.udp_radio.configure(text=self.i18n.get("udp"))
        
        # Update parameter factory widgets
        for param_name, parameter in self.parameter_widgets.items():
            if hasattr(parameter, 'update_language_display'):
                parameter.update_language_display(self.i18n)
        
        # Update parameter groups
        for group_name, group in self.parameter_factory.get_all_groups().items():
            if hasattr(group, 'update_language_display'):
                group.update_language_display(self.i18n)