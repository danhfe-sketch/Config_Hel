import tkinter as tk
import customtkinter as ctk
import os
import sys
import json
import serial
import time
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
from services.operation_confirmation_service import OperationConfirmationService
from services.universal_profile_manager import UniversalProfileManager
from ui.connection_frame import ConnectionFrame
from ui.parameters_frame import ParametersFrame
from ui.actions_frame import ActionsFrame
from ui.log_frame import LogFrame
from ui.toolbar_frame import ToolbarFrame
from ui.splash_screen import SplashScreen

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- App Setup ---
        self.i18n = I18nService() # Will load saved language preference or default to Portuguese
        self.title(self.i18n.get("app_title"))
        self.geometry("1200x700")
        ctk.set_default_color_theme("blue")
        
        # Set application icon
        try:
            # You can change this path to point to your custom icon
            icon_path = resource_path("assets/icons/my_custom_icon.ico")
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Failed to set application icon: {str(e)}")
            # Fallback to default icon if custom icon fails
            try:
                fallback_icon_path = resource_path("assets/icons/app_icon.ico")
                self.iconbitmap(fallback_icon_path)
            except:
                pass  # No icon if both fail

        # --- Services ---
        self.device_command_mapper = DeviceCommandMapper()  # Initialize device command mapper
        self.serial_service = SerialService(self)
        self.config_service = ConfigService(self)
        self.theme_service = ThemeService(self)  # Initialize theme service (loads saved theme)
        self.operation_confirmation_service = OperationConfirmationService(self)  # Initialize operation confirmation service
        self.profile_manager = UniversalProfileManager(self.serial_service, "Parameter UI List.md")  # Initialize profile manager
        
        # Initialize configuration reader service in serial service
        self.serial_service.initialize_configuration_reader()

        # --- Window Grid Layout ---
        # Configure the main grid - add row for toolbar
        self.grid_columnconfigure(0, weight=1, minsize=160) # Left column (reduced width)
        self.grid_columnconfigure(1, weight=5, minsize=550) # Center column
        self.grid_columnconfigure(2, weight=5, minsize=450) # Right column (increased width)
        self.grid_rowconfigure(0, weight=0)  # Toolbar row (fixed height)
        self.grid_rowconfigure(1, weight=1)  # Main content row (expandable)

        # --- Create UI Frames ---

        # Toolbar Frame (Top - spans all columns)
        self.toolbar_frame = ToolbarFrame(self, self.i18n, self.config_service, self.theme_service, self.profile_manager)
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
        
        # Add reference for ConfigurationReaderService
        self.parameters_frame = self.params_frame

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


def start_app():
    """
    Function to initialize and start the main application.
    This is called after the splash screen is displayed.
    """
    app = App()
    app.mainloop()

if __name__ == "__main__":
    # Use a simpler approach for the splash screen to avoid image issues
    try:
        # Create a simple splash window
        splash_root = tk.Tk()
        splash_root.overrideredirect(True)  # Remove window decorations
        splash_root.attributes('-topmost', True)  # Keep on top
        
        # Set a fixed size for the splash window
        width, height = 500, 300
        splash_root.geometry(f"{width}x{height}")
        
        # Center the window on the screen
        x = (splash_root.winfo_screenwidth() // 2) - (width // 2)
        y = (splash_root.winfo_screenheight() // 2) - (height // 2)
        splash_root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create a frame with a blue background
        splash_frame = tk.Frame(splash_root, bg="#0066cc", width=width, height=height)
        splash_frame.pack(fill="both", expand=True)
        
        # Add application name
        title_label = tk.Label(
            splash_frame,
            text="LT32Pro Configurator",
            font=("Arial", 24, "bold"),
            bg="#0066cc",
            fg="white"
        )
        title_label.pack(pady=(60, 5))
        
        # Add version number
        version_label = tk.Label(
            splash_frame,
            text="v1.0",
            font=("Arial", 12),
            bg="#0066cc",
            fg="#e0e0e0"
        )
        version_label.pack(pady=(0, 20))
        
        # Add loading text
        loading_label = tk.Label(
            splash_frame,
            text="Loading...",
            font=("Arial", 14),
            bg="#0066cc",
            fg="white"
        )
        loading_label.pack(pady=10)
        
        # Add company name at the bottom
        company_label = tk.Label(
            splash_frame,
            text="Lumini Tracker",
            font=("Arial", 10),
            bg="#0066cc",
            fg="#e0e0e0"
        )
        company_label.pack(side="bottom", pady=10)
        
        # Add a progress bar
        progress_bg = tk.Frame(splash_frame, bg="#003366", height=10)
        progress_bg.pack(fill="x", side="bottom", padx=20, pady=20)
        
        progress_bar = tk.Frame(progress_bg, bg="#00ccff", width=0, height=10)
        progress_bar.place(x=0, y=0, width=0)
        
        # Function to animate the progress bar
        def update_progress_bar(current=0):
            if current <= 100:
                # Calculate width based on percentage
                bar_width = int((width - 40) * (current / 100))
                progress_bar.place(width=bar_width)
                
                # Schedule next update with increasing speed
                delay = 30 if current > 80 else 40
                splash_root.after(delay, lambda: update_progress_bar(current + 2))
            else:
                # When progress reaches 100%, close splash and start app
                splash_root.after(200, finish_splash)
        
        # Function to close the splash screen and start the app
        def finish_splash():
            splash_root.destroy()
            start_app()
        
        # Start the progress animation
        update_progress_bar()
        
        # Start the splash screen
        splash_root.mainloop()
        
    except Exception as e:
        print(f"Error with splash screen: {e}")
        # If splash screen fails, start the main app directly
        start_app()