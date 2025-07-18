#!/usr/bin/env python3
"""
Debug version of main.py to catch any errors.
"""

import customtkinter as ctk
import traceback
from services.i18n_service import I18nService
from PIL import Image, ImageTk
from utils.helpers import resource_path

# --- Service and UI Frame Imports ---
from services.serial_service import SerialService
from services.config_service import ConfigService
from services.theme_service import ThemeService
from ui.connection_frame import ConnectionFrame
from ui.parameters_frame import ParametersFrame
from ui.actions_frame import ActionsFrame
from ui.log_frame import LogFrame

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        try:
            # --- App Setup ---
            self.i18n = I18nService(language='pt_BR') # Default to Portuguese
            self.title(self.i18n.get("app_title"))
            self.geometry("1200x700")
            ctk.set_default_color_theme("blue")

            # --- Services ---
            print("Initializing services...")
            self.serial_service = SerialService(self)
            self.config_service = ConfigService(self)
            self.theme_service = ThemeService(self)  # Initialize theme service (loads saved theme)

            # --- Window Grid Layout ---
            # Configure the main grid
            self.grid_columnconfigure(0, weight=1, minsize=280) # Left column
            self.grid_columnconfigure(1, weight=4, minsize=300) # Center column
            self.grid_columnconfigure(2, weight=4, minsize=400) # Right column
            self.grid_rowconfigure(0, weight=1)

            # --- Create UI Frames ---
            print("Creating UI frames...")

            # Left Sidebar (container for Logo, Connection and Actions)
            self.left_sidebar = ctk.CTkFrame(self, width=280, fg_color="transparent")
            self.left_sidebar.grid(row=0, column=0, sticky="ns", padx=(10, 0), pady=10)
            self.left_sidebar.grid_rowconfigure(1, weight=0)  # Connection frame (fixed size)
            self.left_sidebar.grid_rowconfigure(2, weight=0)  # Actions frame (fixed size)

            # Logo
            try:
                logo_image = ctk.CTkImage(
                    light_image=Image.open(resource_path("assets/images/logo.png")),
                    dark_image=Image.open(resource_path("assets/images/logo.png")),
                    size=(180, 60),
                )
                logo_label = ctk.CTkLabel(self.left_sidebar, image=logo_image, text="")
            except FileNotFoundError:
                print("Logo not found, using text label")
                logo_label = ctk.CTkLabel(
                    self.left_sidebar, text="Lumini Tracker", font=("Roboto", 24)
                )
            logo_label.grid(row=0, column=0, pady=(0, 20), padx=10)

            # Connection Frame
            print("Creating connection frame...")
            self.connection_frame = ConnectionFrame(self.left_sidebar, self.i18n, self.serial_service)
            self.connection_frame.grid(row=1, column=0, sticky="ew")

            # Actions Frame
            print("Creating actions frame...")
            self.actions_frame = ActionsFrame(
                self.left_sidebar, self.i18n, self.serial_service
            )
            self.actions_frame.grid(row=2, column=0, pady=(10, 0), sticky="ew")

            # Parameters Frame (Center)
            print("Creating parameters frame...")
            self.params_frame = ParametersFrame(self, self.i18n)
            self.params_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

            # Log Frame (Right)
            print("Creating log frame...")
            self.log_frame = LogFrame(self, self.i18n, self.serial_service)
            self.log_frame.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="nsew")

            # --- Protocol Handlers ---
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            print("App initialization complete!")

        except Exception as e:
            print(f"Error during initialization: {e}")
            traceback.print_exc()
            raise

    def on_closing(self):
        """
        Handles the window closing event gracefully.
        Ensures the serial port is disconnected before exiting.
        """
        try:
            if hasattr(self, 'serial_service') and self.serial_service.is_connected:
                self.serial_service.disconnect()
        except:
            pass
        self.destroy()


if __name__ == "__main__":
    try:
        print("Starting application...")
        app = App()
        print("Starting mainloop...")
        app.mainloop()
        print("Application closed normally")
    except Exception as e:
        print(f"Error running application: {e}")
        traceback.print_exc()