import tkinter as tk
import customtkinter as ctk
import os
import sys
import json
import serial
from services.i18n_service import I18nService
from PIL import Image, ImageTk
# Import the new helper function
from utils.helpers import resource_path

# --- Service and UI Frame Imports ---
# (Assuming these files exist in the specified paths)
from services.serial_service import SerialService
from services.config_service import ConfigService
from services.theme_service import ThemeService
from services.device_command_mapper import DeviceCommandMapper
from ui.connection_frame import ConnectionFrame
from ui.parameters_frame import ParametersFrame
from ui.actions_frame import ActionsFrame
from ui.log_frame import LogFrame
from ui.toolbar_frame import ToolbarFrame

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- App Setup ---
        self.i18n = I18nService() # Will load saved language preference or default to Portuguese
        self.title(self.i18n.get("app_title"))
        self.geometry("1200x700")
        ctk.set_default_color_theme("blue")

        # --- Services ---
        self.device_command_mapper = DeviceCommandMapper()  # Initialize device command mapper
        self.serial_service = SerialService(self)
        self.config_service = ConfigService(self)
        self.theme_service = ThemeService(self)  # Initialize theme service (loads saved theme)

        # --- Window Grid Layout ---
        # Configure the main grid - add row for toolbar
        self.grid_columnconfigure(0, weight=1, minsize=160) # Left column (reduced width)
        self.grid_columnconfigure(1, weight=5, minsize=550) # Center column
        self.grid_columnconfigure(2, weight=5, minsize=450) # Right column (increased width)
        self.grid_rowconfigure(0, weight=0)  # Toolbar row (fixed height)
        self.grid_rowconfigure(1, weight=1)  # Main content row (expandable)

        # --- Create UI Frames ---

        # Toolbar Frame (Top - spans all columns)
        self.toolbar_frame = ToolbarFrame(self, self.i18n, self.config_service, self.theme_service)
        self.toolbar_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 0))

        # Left Sidebar (container for Logo, Connection and Actions)
        self.left_sidebar = ctk.CTkFrame(self, width=180, fg_color="transparent")
        self.left_sidebar.grid(row=1, column=0, sticky="ns", padx=(10, 0), pady=10)
        self.left_sidebar.grid_rowconfigure(1, weight=0)  # Connection frame (fixed size)
        self.left_sidebar.grid_rowconfigure(2, weight=0)  # Actions frame (fixed size)

        # Logo
        try:
            logo_image = ctk.CTkImage(
                light_image=Image.open(resource_path("assets/images/logo.png")),
                dark_image=Image.open(resource_path("assets/images/logo.png")),
                size=(160, 50),  # Slightly smaller to fit in narrower column
            )
            logo_label = ctk.CTkLabel(self.left_sidebar, image=logo_image, text="")
        except FileNotFoundError:
            logo_label = ctk.CTkLabel(
                self.left_sidebar, text="Lumini Tracker", font=("Roboto", 24)
            )
        logo_label.grid(row=0, column=0, pady=(0, 20), padx=5)

        # Connection Frame
        self.connection_frame = ConnectionFrame(self.left_sidebar, self.i18n, self.serial_service)
        self.connection_frame.grid(row=1, column=0, sticky="ew")

        # Actions Frame
        self.actions_frame = ActionsFrame(
            self.left_sidebar, self.i18n, self.serial_service
        )
        self.actions_frame.grid(row=2, column=0, pady=(10, 0), sticky="ew")

        # Parameters Frame (Center)
        self.params_frame = ParametersFrame(self, self.i18n)
        self.params_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        # Log Frame (Right)
        self.log_frame = LogFrame(self, self.i18n, self.serial_service)
        self.log_frame.grid(row=1, column=2, padx=(0, 10), pady=10, sticky="nsew")

        # --- Protocol Handlers ---
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """
        Handles the window closing event gracefully.
        Ensures the serial port is disconnected before exiting.
        """
        if self.serial_service.is_connected:
            self.serial_service.disconnect()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()