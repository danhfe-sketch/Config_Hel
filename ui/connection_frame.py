import customtkinter as ctk
import tkinter as tk
import time

class ConnectionFrame(ctk.CTkFrame):
    def __init__(self, master, i18n, serial_service):
        super().__init__(master)
        self.i18n = i18n
        self.serial_service = serial_service
        self.app = master # Reference to the main app
        self.connection_indicator = None
        self.activity_timer = None
        self.reconnect_timer = None
        self.auto_reconnect_enabled = True
        self.auto_reconnect_attempts = 0
        self.max_auto_reconnect_attempts = 3
        self.connection_quality = 100  # Connection quality percentage (100 = perfect)

        # Configure grid columns - give more space to the middle column and ensure the button column has enough space
        self.grid_columnconfigure(0, weight=0, minsize=80)  # Label column
        self.grid_columnconfigure(1, weight=1)              # Content column (expandable)
        self.grid_columnconfigure(2, weight=0, minsize=90)  # Button column

        # --- Connection Section ---
        self.conn_label = ctk.CTkLabel(self, text=self.i18n.get("connection"), font=ctk.CTkFont(weight="bold"))
        self.conn_label.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")

        self.com_label = ctk.CTkLabel(self, text=self.i18n.get("com_port"))
        self.com_label.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")

        self.com_port_combo = ctk.CTkComboBox(self, values=[""], command=self.refresh_ports)
        self.com_port_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.refresh_ports() # Initial population
        
        # INÍCIO DA ATUALIZAÇÃO AUTOMÁTICA
        self.after(1000, self._auto_refresh_ports)

        # Use a slightly smaller button with more compact text to ensure it fits on small screens
        self.connect_button = ctk.CTkButton(
            self, 
            text=self.i18n.get("connect"), 
            width=85,  # Slightly wider to accommodate text
            height=28, # Slightly shorter height
            command=self.toggle_connection
        )
        self.connect_button.grid(row=1, column=2, padx=(5, 10), pady=5, sticky="e")

        # Status row with indicator
        self.status_label = ctk.CTkLabel(self, text=self.i18n.get("status"))
        self.status_label.grid(row=2, column=0, padx=(10, 5), pady=5, sticky="w")

        # Create status frame to hold indicator and text
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        self.status_frame.grid_columnconfigure(1, weight=1)
        
        # Create connection indicator
        # Get the appropriate background color based on the current theme
        if ctk.get_appearance_mode() == "Dark":
            bg_color = "#2B2B2B"  # Dark gray for dark theme
        else:
            bg_color = "#F0F0F0"  # Light gray for light theme
            
        self.connection_indicator = tk.Canvas(
            self.status_frame, 
            width=15, 
            height=15, 
            bg=bg_color,
            highlightthickness=0
        )
        self.connection_indicator.grid(row=0, column=0, padx=(0, 5))
        
        # Draw initial indicator (red circle for disconnected)
        self.update_connection_indicator(False)
        
        # Status text
        self.status_value_label = ctk.CTkLabel(self.status_frame, text=self.i18n.get("disconnected"), text_color="red")
        self.status_value_label.grid(row=0, column=1, sticky="w")
        
        # Create reconnection status frame (hidden by default)
        self.reconnect_frame = ctk.CTkFrame(self)
        self.reconnect_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        self.reconnect_frame.grid_remove()  # Hide initially
        
        # Reconnection progress bar
        self.reconnect_progress = ctk.CTkProgressBar(self.reconnect_frame)
        self.reconnect_progress.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 0), sticky="ew")
        self.reconnect_progress.set(0)
        
        # Reconnection status label
        self.reconnect_label = ctk.CTkLabel(self.reconnect_frame, text=self.i18n.get("reconnecting"))
        self.reconnect_label.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")
        
        # Cancel reconnection button
        self.cancel_reconnect_button = ctk.CTkButton(
            self.reconnect_frame, 
            text=self.i18n.get("cancel"), 
            width=80, 
            command=self.cancel_reconnection
        )
        self.cancel_reconnect_button.grid(row=1, column=1, padx=10, pady=(0, 5), sticky="e")

        # --- Device Info Section ---
        self.info_label = ctk.CTkLabel(self, text=self.i18n.get("device_info"), font=ctk.CTkFont(weight="bold"))
        self.info_label.grid(row=4, column=0, columnspan=3, padx=10, pady=(15, 5), sticky="w")

        self.imei_label = ctk.CTkLabel(self, text=self.i18n.get("imei"))
        self.imei_label.grid(row=5, column=0, padx=(10, 5), pady=5, sticky="w")
        
        # Use Entry widget for IMEI to allow text selection and copying
        self.imei_value_var = tk.StringVar(value=self.i18n.get("not_available"))
        self.imei_value_entry = tk.Entry(
            self,
            textvariable=self.imei_value_var,
            state="readonly",
            readonlybackground=self._get_entry_bg_color(),
            highlightthickness=0,
            relief="flat",
            bd=0,
            font=("Arial", 12, "bold"),
            fg="#1F6AA5" if ctk.get_appearance_mode() == "Light" else "#78BDFF",
            width=25
        )
        self.imei_value_entry.grid(row=5, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        self.teriid_label = ctk.CTkLabel(self, text=self.i18n.get("teriid"))
        self.teriid_label.grid(row=6, column=0, padx=(10, 5), pady=5, sticky="w")
        
        self.teriid_value_var = tk.StringVar(value=self.i18n.get("not_available"))
        self.teriid_value_entry = tk.Entry(
            self,
            textvariable=self.teriid_value_var,
            state="readonly",
            readonlybackground=self._get_entry_bg_color(),
            highlightthickness=0,
            relief="flat",
            bd=0,
            font=("Arial", 12, "bold"),
            fg="#1F6AA5" if ctk.get_appearance_mode() == "Light" else "#78BDFF",
            width=25
        )
        self.teriid_value_entry.grid(row=6, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        self.iccid_label = ctk.CTkLabel(self, text=self.i18n.get("iccid"))
        self.iccid_label.grid(row=7, column=0, padx=(10, 5), pady=5, sticky="w")
        
        # Use Entry widget for ICCID to allow text selection and copying
        self.iccid_value_var = tk.StringVar(value=self.i18n.get("not_available"))
        self.iccid_value_entry = tk.Entry(
            self,
            textvariable=self.iccid_value_var,
            state="readonly",
            readonlybackground=self._get_entry_bg_color(),
            highlightthickness=0,
            relief="flat",
            bd=0,
            font=("Arial", 12, "bold"),
            fg="#1F6AA5" if ctk.get_appearance_mode() == "Light" else "#78BDFF",
            width=25
        )
        self.iccid_value_entry.grid(row=7, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        self.version_label = ctk.CTkLabel(self, text=self.i18n.get("version"))
        self.version_label.grid(row=8, column=0, padx=(10, 5), pady=5, sticky="w")
        
        # Use Entry widget for Version to allow text selection and copying
        self.version_value_var = tk.StringVar(value=self.i18n.get("not_available"))
        self.version_value_entry = tk.Entry(
            self,
            textvariable=self.version_value_var,
            state="readonly",
            readonlybackground=self._get_entry_bg_color(),
            highlightthickness=0,
            relief="flat",
            bd=0,
            font=("Arial", 12, "bold"),
            fg="#1F6AA5" if ctk.get_appearance_mode() == "Light" else "#78BDFF",
            width=25
        )
        self.version_value_entry.grid(row=8, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        
        # Connection quality indicator
        # self.quality_label = ctk.CTkLabel(self, text=self.i18n.get("connection_quality", "Connection Quality"))
        # self.quality_label.grid(row=8, column=0, padx=(10, 5), pady=5, sticky="w")
        
        # Quality frame with progress bar and percentage
        # self.quality_frame = ctk.CTkFrame(self, fg_color="transparent")
        # self.quality_frame.grid(row=8, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        # self.quality_frame.grid_columnconfigure(0, weight=1)
        
        # self.quality_bar = ctk.CTkProgressBar(self.quality_frame, width=80)  # Further reduced width
        # self.quality_bar.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="w")  # Changed from "ew" to "w"
        # self.quality_bar.set(1.0)  # Start at 100%
        
        # self.quality_value_label = ctk.CTkLabel(self.quality_frame, text="100%")
        # self.quality_value_label.grid(row=0, column=1, padx=(0, 5), pady=0, sticky="w")
        
        # Auto-reconnect toggle
        # self.auto_reconnect_var = tk.BooleanVar(value=True)
        # self.auto_reconnect_checkbox = ctk.CTkCheckBox(
        #     self, 
        #     text=self.i18n.get("auto_reconnect", "Auto-reconnect"), 
        #     variable=self.auto_reconnect_var,
        #     command=self.toggle_auto_reconnect
        # )
        # self.auto_reconnect_checkbox.grid(row=9, column=0, columnspan=3, padx=10, pady=(5, 10), sticky="w")

    def _get_entry_bg_color(self):
        """Get the appropriate background color for entry widgets based on the current theme."""
        if ctk.get_appearance_mode() == "Dark":
            return "#2B2B2B"  # Dark gray for dark theme
        else:
            return "#F0F0F0"  # Light gray for light theme

    def _auto_refresh_ports(self):
        """Silently monitors and updates the COM ports dropdown without user interaction."""
        try:
            # Pega as portas conectadas no momento no computador
            current_ports = self.serial_service.list_com_ports()
            # Pega as portas que estão sendo mostradas no Dropdown
            combo_ports = self.com_port_combo.cget("values")
            
            # Garante que a comparação seja feita em listas puras
            if isinstance(combo_ports, tuple):
                combo_ports = list(combo_ports)
                
            # Se ouve mudança nas portas (cabo plugado ou desplugado)
            if current_ports != combo_ports:
                # Atualiza a lista internamente sem recarregar a tela
                self.com_port_combo.configure(values=current_ports)
                
                # Se a porta que estava selecionada não existe mais e não estamos conectados, muda para a próxima
                selected_port = self.com_port_combo.get()
                if selected_port not in current_ports and not self.serial_service.is_connected:
                    if current_ports and current_ports[0] != "N/A":
                        self.com_port_combo.set(current_ports[0])
                    else:
                        self.com_port_combo.set("")
        except Exception:
            # Ignora falhas silenciosamente pois roda em background
            pass
            
        # Re-agendamento do monitor para rodar daqui a 1 segundo
        self.after(1000, self._auto_refresh_ports)

    def refresh_ports(self, _=None):
        """Refreshes the list of available COM ports."""
        ports = self.serial_service.list_com_ports()
        self.com_port_combo.configure(values=ports)
        # Set the first available port if a port hasn't been selected yet
        if ports and not self.com_port_combo.get():
            self.com_port_combo.set(ports[0]) 

    def toggle_connection(self):
        """Connects or disconnects from the selected serial port."""
        if self.serial_service.is_connected:
            self.serial_service.disconnect()
        else:
            port = self.com_port_combo.get()
            if port and port != "N/A":
                self.serial_service.connect(port)

    def update_status(self, is_connected):
        """Updates the UI to reflect the connection status."""
        if is_connected:
            # Get port name for status message
            port = self.com_port_combo.get() if self.com_port_combo.get() else "device"
            
            # Update status with quality indicator if available
            if hasattr(self.app, 'error_handler'):
                status_message = self.app.error_handler.get_connection_status_message(
                    True, port, self.connection_quality)
                self.status_value_label.configure(text=status_message, text_color="green")
            else:
                self.status_value_label.configure(text=self.i18n.get("connected"), text_color="green")
                
            self.connect_button.configure(text=self.i18n.get("disconnect"))
            self.com_port_combo.configure(state="disabled")
            
            # Update connection indicator
            self.update_connection_indicator(True)
            
            # Reset connection quality to good on new connection
            # self.update_connection_quality(100)
            
            # Hide reconnection frame if visible
            self.hide_reconnecting_status()
            
            # Retrieve device information after successful connection
            # Use after() to give the connection time to stabilize
            self.after(1000, self.retrieve_device_info)
            
            # Start connection monitoring if error handler is available
            if hasattr(self.app, 'error_handler'):
                self.app.error_handler.start_connection_monitoring()
        else:
            self.status_value_label.configure(text=self.i18n.get("disconnected"), text_color="red")
            self.connect_button.configure(text=self.i18n.get("connect"))
            self.com_port_combo.configure(state="normal")
            self.imei_value_var.set(self.i18n.get("not_available"))
            self.teriid_value_var.set(self.i18n.get("not_available"))
            self.iccid_value_var.set(self.i18n.get("not_available"))
            self.version_value_var.set(self.i18n.get("not_available"))
            
            # Update connection indicator
            self.update_connection_indicator(False)
            
            # Refresh available ports
            self.refresh_ports()
            
    def retrieve_device_info(self):
        """Triggers device information retrieval from the connected device."""
        if self.serial_service.is_connected:
            self.serial_service.retrieve_device_info()
    
    def update_language_display(self):
        """Updates all UI elements with the current language."""
        # Update section titles
        self.conn_label.configure(text=self.i18n.get("connection"))
        self.info_label.configure(text=self.i18n.get("device_info"))
        
        # Update labels
        self.com_label.configure(text=self.i18n.get("com_port"))
        self.status_label.configure(text=self.i18n.get("status"))
        self.imei_label.configure(text=self.i18n.get("imei"))
        self.teriid_label.configure(text=self.i18n.get("teriid"))
        self.iccid_label.configure(text=self.i18n.get("iccid"))
        self.version_label.configure(text=self.i18n.get("version"))
        # self.quality_label.configure(text=self.i18n.get("connection_quality", "Connection Quality"))
        self.reconnect_label.configure(text=self.i18n.get("reconnecting", "Reconnecting..."))
        self.cancel_reconnect_button.configure(text=self.i18n.get("cancel", "Cancel"))
        # self.auto_reconnect_checkbox.configure(text=self.i18n.get("auto_reconnect", "Auto-reconnect"))
        
        # Update button text based on connection state
        if self.serial_service.is_connected:
            self.connect_button.configure(text=self.i18n.get("disconnect"))
            self.status_value_label.configure(text=self.i18n.get("connected"))
        else:
            self.connect_button.configure(text=self.i18n.get("connect"))
            self.status_value_label.configure(text=self.i18n.get("disconnected"))
        
        # Update value labels if they show "not available"
        current_imei = self.imei_value_var.get()
        current_iccid = self.iccid_value_var.get()
        current_version = self.version_value_var.get()
        
        if current_imei in ["N/A", "not_available", "N/D"]:
            self.imei_value_var.set(self.i18n.get("not_available"))
        
        if current_iccid in ["N/A", "not_available", "N/D"]:
            self.iccid_value_var.set(self.i18n.get("not_available"))
            
        if current_version in ["N/A", "not_available", "N/D"]:
            self.version_value_var.set(self.i18n.get("not_available"))
            
    def update_connection_indicator(self, is_connected, is_active=False):
        """
        Update the connection status indicator.
        
        Args:
            is_connected: Whether the device is connected
            is_active: Whether there is active communication
        """
        if not self.connection_indicator:
            return
            
        # Clear previous indicator
        self.connection_indicator.delete("all")
        
        # Set color based on connection status
        if is_connected:
            if is_active:
                # Bright green for active communication
                color = "#00FF00"
            else:
                # Color based on connection quality
                if self.connection_quality >= 90:
                    color = "#00CC00"  # Good green
                elif self.connection_quality >= 70:
                    color = "#88CC00"  # Yellow-green
                elif self.connection_quality >= 40:
                    color = "#CCCC00"  # Yellow
                else:
                    color = "#CC8800"  # Orange
        else:
            # Red for disconnected
            color = "#FF0000"
            
        # Draw the indicator circle
        self.connection_indicator.create_oval(
            2, 2, 13, 13, 
            fill=color, 
            outline="#333333"
        )
        
        # Cancel any existing flash timer
        if self.activity_timer:
            self.connection_indicator.after_cancel(self.activity_timer)
            self.activity_timer = None
            
        # If active, schedule a return to normal state
        if is_active and is_connected:
            self.activity_timer = self.connection_indicator.after(
                300, lambda: self.update_connection_indicator(True, False)
            )
            
    def flash_activity_indicator(self):
        """Flash the connection indicator to show activity."""
        self.update_connection_indicator(True, True)
        
    # def update_connection_quality(self, quality):
    #     """
    #     Update the connection quality indicator.
        
    #     Args:
    #         quality: Connection quality percentage (0-100)
    #     """
    #     self.connection_quality = max(0, min(100, quality))
        
    #     # Update progress bar
    #     self.quality_bar.set(self.connection_quality / 100)
        
    #     # Update percentage label
    #     self.quality_value_label.configure(text=f"{self.connection_quality}%")
        
    #     # Update color based on quality
    #     if self.connection_quality >= 90:
    #         self.quality_bar.configure(progress_color="#00CC00")  # Green
    #     elif self.connection_quality >= 70:
    #         self.quality_bar.configure(progress_color="#88CC00")  # Yellow-green
    #     elif self.connection_quality >= 40:
    #         self.quality_bar.configure(progress_color="#CCCC00")  # Yellow
    #     else:
    #         self.quality_bar.configure(progress_color="#CC8800")  # Orange
            
    #     # Update connection indicator
    #     if self.serial_service.is_connected:
    #         self.update_connection_indicator(True)
            
    def show_reconnecting_status(self):
        """Show the reconnection status UI."""
        # Show reconnection frame
        self.reconnect_frame.grid()
        
        # Reset progress bar
        self.reconnect_progress.set(0)
        
        # Update label
        self.reconnect_label.configure(text=self.i18n.get("reconnecting", "Reconnecting..."))
        
    def hide_reconnecting_status(self):
        """Hide the reconnection status UI."""
        self.reconnect_frame.grid_remove()
        
    def update_reconnection_status(self, current, total):
        """
        Update the reconnection progress.
        
        Args:
            current: Current attempt number
            total: Total number of attempts
        """
        # Update progress bar
        progress = current / total
        self.reconnect_progress.set(progress)
        
        # Update label
        self.reconnect_label.configure(
            text=f"{self.i18n.get('reconnecting', 'Reconnecting...')} ({current}/{total})"
        )
        
    def update_reconnection_countdown(self, seconds):
        """
        Update the reconnection countdown timer.
        
        Args:
            seconds: Seconds remaining until next attempt
        """
        self.reconnect_label.configure(
            text=f"{self.i18n.get('next_attempt', 'Next attempt in')} {seconds}s"
        )
        
    def show_reconnection_failed(self):
        """Show reconnection failure message."""
        self.reconnect_label.configure(
            text=self.i18n.get("reconnection_failed", "Reconnection failed"),
            text_color="red"
        )
        
        # Hide the reconnection UI after a delay
        self.after(5000, self.hide_reconnecting_status)
        
    def cancel_reconnection(self):
        """Cancel any ongoing reconnection attempts."""
        if hasattr(self.app, 'error_handler'):
            self.app.error_handler.stop_reconnection()
        self.hide_reconnecting_status()
        
    def toggle_auto_reconnect(self):
        """Toggle automatic reconnection setting."""
        enabled = self.auto_reconnect_var.get()
        
        # Update error handler if available
        if hasattr(self.app, 'error_handler'):
            self.app.error_handler.set_auto_reconnect(enabled)