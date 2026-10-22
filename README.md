# LT32Pro Device Configurator v1

This is a desktop application for Windows 11 to configure, monitor, and manage LT32Pro tracking hardware, as specified in the Product Requirements Document.

## Setup

1.  Ensure you have Python 3.8+ installed.
2.  Create a virtual environment:
    ```sh
    python -m venv venv
    .\venv\Scripts\activate
    .\venv\Scripts\activate.bat
    ```
3.  Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```
4.  Run the application:
    ```sh
    python main.py
    ```

## Running Tests

The application includes comprehensive integration tests to verify all functionality:

1. Make sure you have completed the **Setup** steps above.
2. Run specific test files that don't involve GUI components:
   ```sh
   python -m unittest test_app_config_service.py test_language_persistence.py test_theme_persistence.py
   ```
3. Run a specific test method:
   ```sh
   python -m unittest test_integration.IntegrationTest.test_language_switching_integration
   ```

### Available Tests

- `test_integration.py`: Comprehensive integration tests for the entire application
- `test_theme_persistence.py`: Tests theme switching persistence across application restarts
- `test_language_persistence.py`: Tests language switching persistence across application restarts
- `test_app_config_service.py`: Tests the centralized configuration service
- `test_all_radio_parameters.py`: Tests radio button parameters functionality
- `test_dropdown_ui.py`: Tests dropdown parameters functionality
- `test_numeric_parameters.py`: Tests numeric parameters functionality
- `test_operation_confirmation.py`: Tests operation confirmation dialogs and progress indicators
- `test_connection_error_handling.py`: Tests connection error handling and recovery
- `test_build_configuration.py`: Tests PyInstaller build configuration

## Building a Standalone Application

To create a single executable file for distribution on Windows 11 (as per PRD section 8), follow these steps:

1. Make sure you have completed the **Setup** steps above, which includes installing `pyinstaller`.
2. Run the build script from the project's root directory:

   ```sh
   # Activate the virtual environment first
   .\venv\Scripts\activate
   
   # Install PyInstaller if not already installed
   pip install pyinstaller
   
   # Run PyInstaller
   python -m PyInstaller --name="LT32Pro_Configurator_v1" --windowed --onefile --add-data "assets;assets" main.py
   ```

   python build_with_icon.py

   Command options explained:
   * `--name`: Sets the name of the executable.
   * `--windowed`: Prevents a console window from appearing when the application is run.
   * `--onefile`: Packages everything into a single executable.
   * `--add-data "assets;assets"`: Bundles the `assets` directory (containing locales and images) into the application.

3. Alternatively, you can use the provided batch file:

   ```sh
   # Edit build_app.bat to ensure it has the correct Python path
   # Then run:
   .\build_app.bat
   ```

4. The standalone application will be located in the `dist` directory.

### Troubleshooting Build Issues

If you encounter issues with PyInstaller:

1. Make sure you're running the command from the activated virtual environment
2. Try using the full Python module path: `python -m PyInstaller` instead of just `pyinstaller`
3. Check that all required modules are listed in the `hiddenimports` section of the spec file
4. If using a spec file, ensure it includes the new `app_config_service` module
5. For permission issues, try running the command prompt or PowerShell as administrator

### Known Issues with the Packaged Application

#### Language Setting Not Persisting

If the packaged application defaults to Spanish and doesn't save the language setting:

1. Use the fixed spec file: `LT32Pro_Configurator_v1_fixed.spec`
2. Build with console mode enabled for debugging: 
   ```
   python -m PyInstaller LT32Pro_Configurator_v1_fixed.spec
   ```
3. Check the console output for any errors related to configuration file access
4. If the issue persists, try running the executable as administrator once to create the configuration directory
5. Alternatively, manually create the `.lt32pro_config` directory in your user home folder and ensure it has write permissions

#### Configuration File Location

The application tries to save configuration in the following locations (in order):

1. `~/.lt32pro_config/app_config.json` (User's home directory)
2. In the same directory as the executable (fallback if home directory is not writable)

If you're experiencing issues with settings not being saved, check these locations for the configuration file and ensure the application has write permissions.

## Features

### Complete Parameter Configuration
- **Numeric Parameters**: Configure vibration levels (0-255), timer settings (1-65500s), and sensitivity ranges (1-10)
- **Dropdown Parameters**: Set Heart Beat intervals (30s to 24hr), Curve Sensor options (Enabled/Disabled/Auto), and Protocol types
- **Radio Button Groups**: Select Lock Type (PIN/Card), Ignition Type (Digital/Analog), and Protocol (TCP/UDP)
- **Comprehensive Validation**: Range checking for numeric inputs and format validation for all parameters

### User Interface
- **Toolbar**: Access configuration profiles, language selection, help resources, and personalization options
- **Connection Management**: Connect to devices via serial port with automatic device information retrieval
- **Parameter Organization**: Logically grouped parameters with clear labeling and validation feedback
- **Log Display**: Detailed communication log with message categorization and export functionality
- **Optimized Layout**: Adjustable column widths for better use of screen space

### Customization and Profiles
- **Theme Switching**: Choose between Light, Dark, and System themes with immediate application
- **Theme Persistence**: Remember theme selection across application restarts
- **Configuration Profiles**: Save and load device configurations as .lt32config files
- **Language Selection**: Switch between Portuguese, English, and Spanish with immediate UI updates
- **Centralized Configuration**: All user preferences stored in a single configuration file

### Device Communication
- **AT Command Mapping**: Proper command syntax for all LT32Pro device parameters
- **Bulk Operations**: Send all parameters at once or retrieve current device configuration
- **Device Information**: Display IMEI and ICCID information upon connection
- **Command Validation**: Ensure commands are properly formatted before sending

### Error Handling and User Feedback
- **Connection Error Handling**: Detailed error messages for different connection failure scenarios
- **Automatic Reconnection**: Attempt to reconnect with user feedback on progress
- **Operation Confirmation**: Confirmation dialogs for destructive operations like factory reset
- **Progress Indicators**: Visual feedback for long-running operations
- **Validation Messages**: Localized error messages for invalid parameter values

### Logging and Export
- **Enhanced Logging**: Clear distinction between app commands, device responses, and system messages
- **Log Export**: Save communication logs as text files for troubleshooting and record-keeping
- **Log Performance**: Optimized handling of lengthy logs with easy navigation
- **Message Categorization**: Color coding or prefixes for different message types

### Internationalization
- **Multiple Languages**: Full support for Portuguese, English, and Spanish
- **Localized Validation**: Error messages in the user's selected language
- **Immediate Switching**: Change language without application restart
- **Complete Coverage**: All UI elements and messages available in all supported languages
- **Language Persistence**: Remember language selection across application restarts

## Recent Updates

### Version 1.1.0 (July 2025)
- **Centralized Configuration System**: Implemented a unified configuration system that stores all user preferences (theme, language, etc.) in a single file
- **Optimized UI Layout**: Adjusted column widths for better use of screen space, with narrower left sidebar and wider center/right columns
- **Improved Theme Persistence**: Fixed issues with theme settings not being properly saved and restored
- **Enhanced Language Persistence**: Fixed issues with language settings not being properly saved and restored
- **Updated Test Suite**: Improved unit and integration tests for better coverage and reliability
- **Bug Fixes**: Fixed various minor bugs and improved error handling

## Configuration

User preferences are stored in the following location:
- `~/.lt32pro_config/app_config.json`: Contains theme and language preferences

The configuration file is automatically created when the application is first run and updated whenever settings are changed.# Config_Hel
