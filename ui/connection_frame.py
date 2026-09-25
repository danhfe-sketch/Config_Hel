import customtkinter as ctk
import tkinter as tk
import time
import re
from tkinter import messagebox

# ============================================================================
# BANCO DE DADOS DE FIRMWARES OTA (UPGRADE E DOWNGRADE)
# ============================================================================
OTA_FIRMWARES = {
    "LT32Pro B53 - V6.60 (Mais Recente)": "ATSMS:YCSJ,http://139.9.60.174/update/LT32Pro_10F8A_B53_V660.bin,AF#",
    "LT32Pro B53 - V6.59": "ATSMS:YCSJ,http://139.9.60.174/update/LT32Pro_10F8A_B53_V659.bin,93#",
    "LT32Pro B53 - V6.58": "ATSMS:YCSJ,http://139.9.60.174/update/LT32Pro_10F8A_B53_V658.bin,9E#",
    "LT32Pro B53 - V6.57": "ATSMS:YCSJ,http://139.9.60.174/update/LT32Pro_10F8A_B53_V657.bin,FE#",
    "LT32Pro B53 - V6.56": "ATSMS:YCSJ,http://139.9.60.174/update/LT32Pro_10F8A_B53_V656.bin,D0#",
    "LT32Pro B53 - V6.55": "ATSMS:YCSJ,http://139.9.60.174/update/LT32Pro_10F8A_B53_V655.bin,A8#",
    "LT32Pro B53 - V6.54": "ATSMS:YCSJ,http://139.9.60.174/update/LT32Pro_10F8A_B53_V654.bin,66#",
    "LT32Pro B53 - V6.53": "ATSMS:YCSJ,http://139.9.60.174/update/LT32Pro_10F8A_B53_V653.bin,E0#",
    "LT32Pro B52 - V6.47 (Máximo OTA)": "ATSMS:YCSJ,http://139.9.60.174/update/LT32Pro_10F8A_B52_V647.bin,35#"
}

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
        
        # --- NOVO: GESTOR OTA DE FIRMWARE (Oculto por padrão) ---
        self.frm_ota = ctk.CTkFrame(self, fg_color="transparent")
        self.frm_ota.grid(row=10, column=0, columnspan=3, padx=10, pady=(5, 10), sticky="ew")
        self.frm_ota.grid_remove() # Oculta por padrão

        ctk.CTkLabel(self.frm_ota, text="Gestor de Versão (OTA):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#F39C12", anchor="w").pack(fill="x", padx=0)
        self.cmb_ota = ctk.CTkComboBox(self.frm_ota, values=[])
        self.cmb_ota.pack(fill="x", pady=(5, 5))
        
        self.btn_ota = ctk.CTkButton(
            self.frm_ota, text="🚀 Aplicar Versão Selecionada", 
            fg_color="#F39C12", text_color="black", hover_color="#D68910",
            font=ctk.CTkFont(weight="bold"),
            command=self.disparar_atualizacao_ota
        )
        self.btn_ota.pack(fill="x")
        # --------------------------------------------------------

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
            
            # --- NOVO: Oculta o Gestor OTA se desconectar ---
            if hasattr(self, 'frm_ota'):
                self.frm_ota.grid_remove()
            
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
        
        # --- NOVO: LÓGICA DO GESTOR OTA ---
    def verificar_atualizacao_firmware(self, versao_aparelho):
        """Avalia a versão conectada e exibe as OTAs compatíveis limitando downgrades ilógicos."""
        if not versao_aparelho or versao_aparelho == "N/A":
            if hasattr(self, 'frm_ota'): self.frm_ota.grid_remove()
            return
            
        versao_limpa = versao_aparelho.upper()
        opcoes_disponiveis = []
        
        # BLINDAGEM 1: Identifica se é o modelo PRO W
        if "PRO W" in versao_limpa or "PROW" in versao_limpa or "LT32PRO_W" in versao_limpa or "_W_" in versao_limpa:
            opcoes_disponiveis = ["LT32 PRO W - Sem atualizações via cabo disponíveis"]
            self.btn_ota.configure(state="disabled", text="OTA Indisponível para PRO W")
            
        # BLINDAGEM 2: Lógica progressiva para versão B53
        elif "B53" in versao_limpa:
            self.btn_ota.configure(state="normal", text="🚀 Aplicar Versão Selecionada")
            current_num = 0
            match = re.search(r'V6\.?(\d+)', versao_limpa)
            if match:
                current_num = int(match.group(1))
            
            for nome, _ in OTA_FIRMWARES.items():
                if "B53" in nome:
                    m = re.search(r'V6\.?(\d+)', nome)
                    if m:
                        fw_num = int(m.group(1))
                        # Só adiciona se for estritamente MAIOR que a versão atual
                        if current_num == 0 or fw_num > current_num:
                            opcoes_disponiveis.append(nome)
            
            # Se não sobrou nenhuma opção para atualizar, o aparelho já está no topo
            if not opcoes_disponiveis and current_num > 0:
                self.btn_ota.configure(state="disabled", text="Última Versão Instalada")
                opcoes_disponiveis = ["Equipamento Atualizado"]
        
        # BLINDAGEM 3: Lógica para B52
        elif "B52" in versao_limpa:
            self.btn_ota.configure(state="normal", text="🚀 Aplicar Versão Selecionada")
            opcoes_disponiveis = [k for k in OTA_FIRMWARES.keys() if "B52" in k]
        
        # Fallback
        else:
            self.btn_ota.configure(state="disabled", text="Versão incompatível")
            opcoes_disponiveis = ["Sem OTAs para esta arquitetura"]
            
        if opcoes_disponiveis:
            self.cmb_ota.configure(values=opcoes_disponiveis)
            self.cmb_ota.set(opcoes_disponiveis[0])
            self.frm_ota.grid()
        else:
            self.frm_ota.grid_remove()

    def disparar_atualizacao_ota(self):
        """Dispara o processo de checagem e envio."""
        fw_selecionado = self.cmb_ota.get()
        cmd_ota = OTA_FIRMWARES.get(fw_selecionado)
        
        if not cmd_ota: return
        
        confirmar = messagebox.askyesno(
            "Atenção - Mudança de Firmware via OTA",
            f"Você está prestes a enviar o firmware:\n{fw_selecionado}\n\n"
            "O aparelho irá se conectar ao servidor da Lumini, baixar o arquivo e reiniciar.\n"
            "⚠️ O rastreador OBRIGATORIAMENTE precisa de um Chip GPRS/Internet ativo para isso funcionar.\n\n"
            "Deseja checar a configuração do APN e enviar o comando agora?"
        )
        
        if not confirmar: return
        
        if hasattr(self.app, 'log_frame') and self.app.log_frame:
            self.app.log_frame.log_message(f"INFO: Solicitada atualização OTA para {fw_selecionado}\n")
            
        self.btn_ota.configure(state="disabled", text="⏳ Checando APN...")
        
        import threading
        threading.Thread(target=self._validar_rede_e_aplicar, args=(cmd_ota,), daemon=True).start()
        
    def _validar_rede_e_aplicar(self, cmd_ota):
        """Verifica ativamente se o APN está configurado antes de liberar o OTA."""
        import time
        apn_lido = ""
        
        # 1. Envia o comando APN# diretamente para o aparelho em background
        if hasattr(self, 'serial_service') and self.serial_service.is_connected:
            self.app.after(0, lambda: self.app.log_frame.log_message("INFO: Checando APN do aparelho para OTA...\n"))
            self.serial_service.send_command("ATSMS:APN#")
        else:
            self.app.after(0, self.btn_ota.configure, {"state": "normal", "text": "🚀 Aplicar Versão Selecionada"})
            return

        # 2. Aguarda até 4 segundos lendo o buffer de respostas em busca do APN
        for _ in range(40): # 40 * 0.1s = 4 segundos
            time.sleep(0.1)
            # Procura de trás pra frente no buffer do serial_service
            if hasattr(self.serial_service, 'response_buffer'):
                for res in reversed(self.serial_service.response_buffer[-15:]):
                    if res.startswith("APN:"):
                        partes = res[4:].split(',')
                        if partes and partes[0].strip():
                            apn_lido = partes[0].strip()
                        break
            if apn_lido:
                break
                
        if not apn_lido:
            self.app.after(0, self.btn_ota.configure, {"state": "normal", "text": "🚀 Aplicar Versão Selecionada"})
            self.app.after(0, lambda: messagebox.showerror(
                "Falha na Leitura", 
                "O aparelho não respondeu com a APN ou a APN está em branco.\n\nPor favor, configure uma APN válida antes de tentar atualizar o firmware OTA."
            ))
            return
            
        # 3. Base de dados de APNs
        apn_db = {
            "zap.vivo.com.br": "Vivo (Padrão/M2M)",
            "claro.com.br": "Claro (Padrão/Dados)",
            "bandalarga.claro.com.br": "Claro (Banda Larga)",
            "generica.claro.com.br": "Claro (M2M Genérica)",
            "timbrasil.br": "TIM (Connect)",
            "tim.br": "TIM (Connect Alt)",
            "algar.br": "Algar Telecom",
            "gprs.oi.com.br": "Oi Internet",
            "allcom.arquia.com.br": "Allcom (Arqia)",
            "allcom.claro.com.br": "Allcom (Claro)",
            "allcom.vivo.com.br": "Allcom (Vivo)",
            "allcom.br": "Allcom (Algar)",
            "m2data.arqia.br": "M2Data (Arqia)",
            "m2data.claro.com.br": "M2Data (Claro)",
            "m2data.vivo.com.br": "M2Data (Vivo)",
            "arqia.br": "Arqia M2M",
            "nlt.com.br": "NLT Telecom",
            "virtueyes.com.br": "Virtueyes M2M",
            "tmdata.vivo.com.br": "Tmdata (Vivo)",
            "tmdata.claro.com.br": "Tmdata (Claro)",
            "tmdata.tim.br": "Tmdata (TIM)",
            "telecall.br": "Telecall",
            "surf.br": "Surf Telecom"
        }
        
        operadora = apn_db.get(apn_lido.lower(), "Desconhecida / Personalizada")
        
        def _pergunta_final():
            # Força o botão a restaurar o visual antes de abrir o pop-up
            self.btn_ota.configure(state="normal", text="🚀 Aplicar Versão Selecionada")
            
            prosseguir = messagebox.askyesno(
                "Verificação de Rede Concluída", 
                f"O APN atual configurado no aparelho é:\n\n"
                f"👉 {apn_lido}\n"
                f"🏢 Operadora Identificada: {operadora}\n\n"
                f"Tem certeza que este chip possui pacote de dados ativo para concluir o download?\n"
                f"(Se o chip estiver sem dados, o aparelho apenas piscará o led mas não atualizará!)"
            )
            
            if prosseguir:
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message(f"INFO: Enviando comando OTA (YCSJ)...\n")
                self.serial_service.send_command(cmd_ota)
                messagebox.showinfo("Comando Enviado", "Comando de atualização enviado!\n\nO aparelho baixará o arquivo, as luzes apagarão e ele reiniciará em alguns minutos.")
            else:
                # O usuário clicou em "Não", avisa como configurar a APN
                messagebox.showinfo(
                    "Configuração de APN", 
                    "Para configurar a APN corretamente:\n\n"
                    "1. Vá na aba 'Parâmetros' -> 'Parâmetros de Rede'.\n"
                    "2. Preencha os dados da sua APN e clique no botão 'Enviar'.\n\n"
                    "⚠️ Aviso: Ao enviar o comando de APN, o aparelho será reiniciado automaticamente para aplicar as configurações de rede."
                )
                
            # Força a remoção de foco para desativar o hover do botão que estava pressionado
            self.focus_set()
        
        self.app.after(0, _pergunta_final)