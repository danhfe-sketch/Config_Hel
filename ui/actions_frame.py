import customtkinter as ctk
from tkinter.messagebox import askyesno, showwarning

class ActionsFrame(ctk.CTkFrame):
    def __init__(self, master, i18n, serial_service):
        super().__init__(master)
        self.i18n = i18n
        self.serial_service = serial_service

        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self, text=self.i18n.get("actions"), font=ctk.CTkFont(weight="bold"))
        self.title_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.send_all_button = ctk.CTkButton(
            self, text=self.i18n.get("send_all"), command=self.send_all_parameters
        )
        self.send_all_button.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.check_config_button = ctk.CTkButton(
            self, text=self.i18n.get("check_config"), command=self.check_configuration
        )
        self.check_config_button.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.reboot_button = ctk.CTkButton(
            self, text=self.i18n.get("reboot_device"), command=self.reboot_device
        )
        self.reboot_button.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        self.factory_reset_button = ctk.CTkButton(
            self,
            text=self.i18n.get("factory_reset"),
            command=self.confirm_factory_reset,
            fg_color="red",
            hover_color="darkred"
        )
        self.factory_reset_button.grid(row=4, column=0, padx=10, pady=(5, 10), sticky="ew")

    def send_all_parameters(self):
        """Sends all current UI parameters to the device in the correct sequence."""
        if not self.serial_service.is_connected:
            title = self.i18n.get("error")
            message = self.i18n.get("not_connected_error")
            showwarning(title=title, message=message)
            return
            
        # Use the new bulk command operation functionality
        self.serial_service.send_all_parameters()
        
    def check_configuration(self):
        """Retrieves and populates all device settings."""
        if not self.serial_service.is_connected:
            title = self.i18n.get("error")
            message = self.i18n.get("not_connected_error")
            showwarning(title=title, message=message)
            return
            
        # Use the new check device configuration functionality
        self.serial_service.check_device_configuration()

    def reboot_device(self):
        """Sends the command to reboot the device."""
        if not self.serial_service.is_connected:
            title = self.i18n.get("error")
            message = self.i18n.get("not_connected_error")
            showwarning(title=title, message=message)
            return
            
        # Get the actual reboot command from the device command mapper
        try:
            if hasattr(self.serial_service.app, 'device_command_mapper'):
                reboot_cmd = self.serial_service.app.device_command_mapper.get_command('reset_device', None)
                self.serial_service.send_command(reboot_cmd, 'reset_device')
                self.serial_service.app.log_frame.log_message("INFO: Reboot command sent to device\n")
            else:
                self.serial_service.send_command("ATSMS:RESET#")
                self.serial_service.app.log_frame.log_message("INFO: Reboot command sent using default command\n")
        except Exception as e:
            self.serial_service.app.log_frame.log_message(f"ERROR: Failed to send reboot command: {str(e)}\n")

    def confirm_factory_reset(self):
        """Shows a confirmation dialog before sending the factory reset command."""
        if not self.serial_service.is_connected:
            title = self.i18n.get("error")
            message = self.i18n.get("not_connected_error")
            showwarning(title=title, message=message)
            return
            
        title = self.i18n.get("factory_reset_confirm_title")
        message = self.i18n.get("factory_reset_confirm_message")
        if askyesno(title, message):
            # Get the actual factory reset command from the device command mapper
            try:
                if hasattr(self.serial_service.app, 'device_command_mapper'):
                    factory_cmd = self.serial_service.app.device_command_mapper.get_command('factory_reset', None)
                    self.serial_service.send_command(factory_cmd, 'factory_reset')
                    self.serial_service.app.log_frame.log_message("INFO: Factory reset command sent to device\n")
                else:
                    self.serial_service.send_command("ATSMS:FACTORY#")
                    self.serial_service.app.log_frame.log_message("INFO: Factory reset command sent using default command\n")
            except Exception as e:
                self.serial_service.app.log_frame.log_message(f"ERROR: Failed to send factory reset command: {str(e)}\n")
    
    def update_language_display(self):
        """Updates all UI elements with the current language."""
        # Update title
        self.title_label.configure(text=self.i18n.get("actions"))
        
        # Update buttons
        self.send_all_button.configure(text=self.i18n.get("send_all"))
        self.check_config_button.configure(text=self.i18n.get("check_config"))
        self.reboot_button.configure(text=self.i18n.get("reboot_device"))
        self.factory_reset_button.configure(text=self.i18n.get("factory_reset"))