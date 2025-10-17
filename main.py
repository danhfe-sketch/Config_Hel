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
        self.profile_operation_in_progress = False
        
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

        # Logo with improved error handling
        try:
            # Load logo image with proper error handling
            logo_path = resource_path("assets/images/logo.png")
            if os.path.exists(logo_path):
                logo_image = ctk.CTkImage(
                    light_image=Image.open(logo_path),
                    dark_image=Image.open(logo_path),
                    size=(160, 50),  # Slightly smaller to fit in narrower column
                )
                logo_label = ctk.CTkLabel(self.left_sidebar, image=logo_image, text="")
                # Keep a reference to prevent garbage collection
                self.logo_image = logo_image
            else:
                # Fallback to text if logo file doesn't exist
                logo_label = ctk.CTkLabel(
                    self.left_sidebar, text="Lumini Tracker", font=("Roboto", 24)
                )
        except Exception as e:
            print(f"Warning: Could not load logo image: {e}")
            # Fallback to text label
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

    def update_ui_with_parsed_data(self, parsed_data):
        """Update the UI with parsed data from a device response."""
        if not parsed_data or 'parameter' not in parsed_data or 'value' not in parsed_data:
            return

        param_name_from_response = parsed_data['parameter']
        param_value_from_response = parsed_data['value']

        # Find the parameter in the specification
        for section_name, section_data in self.params_frame.parameter_sections.items():
            section_config = section_data['config']
            for param_name, param_config in section_config.parameters.items():
                if param_name == param_name_from_response:
                    # Found the parameter
                    section_widget = self.params_frame.section_widgets.get(section_name)
                    if section_widget:
                        param_widget = section_widget.parameters.get(param_name)
                        if param_widget:
                            if param_widget.widget_type == 'simple':
                                ui_element = param_widget.ui_elements.get('main')
                                if ui_element:
                                    # Map the value back to the UI option
                                    if param_config.options:
                                        for option in param_config.options:
                                            if param_value_from_response in option:
                                                ui_element.set_value(option)
                                                return
                                    else:
                                        ui_element.set_value(param_value_from_response)
                                        return
                            else: # complex
                                self.params_frame.parameter_specification_factory.set_parameter_value(
                                    section_name, param_name, param_value_from_response, self.params_frame.section_widgets
                                )
                    return

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
    Enhanced function to initialize and start the main application with proper error handling.
    This is called after the splash screen is displayed.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting main application initialization")
        
        # Phase 1: Create the main application instance
        logger.debug("Creating main application instance")
        app = App()
        logger.info("Main application instance created successfully")
        
        # Phase 2: Ensure the window is properly configured for smooth transition
        logger.debug("Configuring main application window for smooth transition")
        app.update_idletasks()  # Process pending GUI updates
        app.lift()  # Bring window to front
        app.focus_force()  # Give focus to the window
        logger.debug("Main application window configured and focused")
        
        # Phase 3: Start the main event loop
        logger.info("Starting main application event loop")
        app.mainloop()
        logger.info("Main application event loop ended")
        
    except ImportError as e:
        logger.error(f"Import error during application startup: {e}")
        _show_startup_error("Import Error", f"Failed to import required modules:\n{e}")
        raise
    except tk.TclError as e:
        if "doesn't exist" in str(e) and "image" in str(e):
            logger.warning(f"Image loading error during startup (non-critical): {e}")
            # For image errors, don't show error dialog as the app can still function
            logger.info("Application started successfully despite image loading issues")
        else:
            logger.error(f"Tkinter error during application startup: {e}")
            _show_startup_error("Display Error", f"Failed to initialize display:\n{e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error during application startup: {e}")
        _show_startup_error("Startup Error", f"Failed to start application:\n{e}")
        raise

def _show_startup_error(title, message):
    """
    Show a simple error dialog for startup failures.
    
    Args:
        title: Error dialog title
        message: Error message to display
    """
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        # Create a temporary root window for the error dialog
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        
        # Show error dialog
        messagebox.showerror(title, message)
        root.destroy()
        
    except Exception:
        # Fallback to console output if GUI fails
        print(f"STARTUP ERROR - {title}: {message}")

def run_with_image_splash():
    """
    Run the application with splash screen using the actual splash.png image.
    """
    import logging
    import time
    
    logger = logging.getLogger(__name__)
    
    try:
        # Create splash screen with the actual splash image
        logger.debug("Creating image-based splash screen")
        
        splash_root = None
        splash_image = None
        try:
            # Create splash window
            splash_root = tk.Tk()
            splash_root.overrideredirect(True)
            splash_root.attributes('-topmost', True)
            
            # Try to load the splash image
            splash_image_path = resource_path("assets/images/splash.png")
            if os.path.exists(splash_image_path):
                try:
                    # Load and display the splash image
                    from PIL import Image, ImageTk
                    pil_image = Image.open(splash_image_path)
                    
                    # Get image dimensions
                    img_width, img_height = pil_image.size
                    
                    # Resize if too large (max 600x400)
                    max_width, max_height = 600, 400
                    if img_width > max_width or img_height > max_height:
                        ratio = min(max_width / img_width, max_height / img_height)
                        new_width = int(img_width * ratio)
                        new_height = int(img_height * ratio)
                        pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                        img_width, img_height = new_width, new_height
                    
                    # Convert to PhotoImage
                    splash_image = ImageTk.PhotoImage(pil_image)
                    
                    # Center the splash screen
                    screen_width = splash_root.winfo_screenwidth()
                    screen_height = splash_root.winfo_screenheight()
                    x = (screen_width // 2) - (img_width // 2)
                    y = (screen_height // 2) - (img_height // 2)
                    splash_root.geometry(f"{img_width}x{img_height}+{x}+{y}")
                    
                    # Create label with image
                    image_label = tk.Label(splash_root, image=splash_image, bd=0)
                    image_label.pack()
                    
                    logger.info(f"Splash image loaded successfully: {splash_image_path}")
                    
                except Exception as img_error:
                    logger.warning(f"Failed to load splash image: {img_error}")
                    # Fallback to text-based splash
                    splash_root.geometry("400x200")
                    splash_frame = tk.Frame(splash_root, bg="#0066cc")
                    splash_frame.pack(fill="both", expand=True)
                    
                    title_label = tk.Label(
                        splash_frame,
                        text="LT32Pro Configurator",
                        font=("Arial", 18, "bold"),
                        bg="#0066cc",
                        fg="white"
                    )
                    title_label.pack(expand=True)
            else:
                logger.warning(f"Splash image not found: {splash_image_path}")
                # Fallback to text-based splash
                splash_root.geometry("400x200")
                screen_width = splash_root.winfo_screenwidth()
                screen_height = splash_root.winfo_screenheight()
                x = (screen_width // 2) - 200
                y = (screen_height // 2) - 100
                splash_root.geometry(f"400x200+{x}+{y}")
                
                splash_frame = tk.Frame(splash_root, bg="#0066cc")
                splash_frame.pack(fill="both", expand=True)
                
                title_label = tk.Label(
                    splash_frame,
                    text="LT32Pro Configurator",
                    font=("Arial", 18, "bold"),
                    bg="#0066cc",
                    fg="white"
                )
                title_label.pack(expand=True)
            
            # Show splash for a brief moment
            splash_root.update()
            time.sleep(1.2)  # Brief display time
            
            # Close splash screen
            splash_root.destroy()
            splash_root = None
            splash_image = None  # Clear image reference
            
            logger.info("Image splash screen completed")
            
        except Exception as e:
            logger.warning(f"Image splash screen failed: {e}")
            if splash_root:
                try:
                    splash_root.destroy()
                except:
                    pass
        
        # Give a moment for cleanup
        time.sleep(0.1)
        
        logger.info("Starting main application")
        
        # Start the main application
        start_app()
        
    except Exception as e:
        logger.error(f"Error in run_with_image_splash: {e}")
        raise

if __name__ == "__main__":
    import logging
    import sys
    
    # Configure logging for startup process
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info("LT32Pro Configurator starting up")
    
    # Check if splash screen should be disabled
    disable_splash = (
        os.environ.get('DISABLE_SPLASH', '').lower() in ('1', 'true', 'yes') or
        '--no-splash' in sys.argv
    )
    
    if disable_splash:
        logger.info("Splash screen disabled by user preference")
        splash_success = False
    else:
        # Use a conservative approach to preserve existing functionality
        # Try splash screen first, but fallback quickly if there are any issues
        splash_success = False
        
        try:
            # Try to run with image splash screen approach
            logger.debug("Attempting to run with splash screen")
            run_with_image_splash()
            splash_success = True
            logger.info("Application completed successfully with splash screen")
            
        except Exception as e:
            logger.warning(f"Splash screen approach failed: {e}")
            splash_success = False
    
    # If splash screen failed or wasn't attempted, use direct startup
    if not splash_success:
        logger.info("Using direct application startup (no splash screen)")
        
        try:
            # Direct startup to preserve all existing functionality
            start_app()
            logger.info("Application started successfully without splash screen")
            
        except Exception as fallback_error:
            logger.critical(f"Failed to start application: {fallback_error}")
            
            # Show critical error dialog and exit
            _show_startup_error(
                "Critical Startup Failure", 
                f"The application failed to start:\n\n{fallback_error}\n\nPlease check the logs for more details."
            )
            
            logger.critical("Application startup failed completely, exiting")
            sys.exit(1)