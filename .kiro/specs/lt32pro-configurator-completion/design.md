# Design Document

## Overview

This design document outlines the completion of the LT32Pro Device Configurator v1 to fully implement the PRD requirements. The existing application provides a solid foundation with modular architecture, proper separation of concerns, and working serial communication. The design focuses on extending the current parameter system, implementing the missing toolbar functionality, adding theme support, and enhancing the overall user experience while maintaining the established architectural patterns.

## Architecture

The existing architecture will be preserved and extended:

### Current Architecture Strengths
- **Service Layer**: `SerialService`, `ConfigService`, `I18nService` provide clean separation
- **UI Components**: Modular frame-based UI with `ConnectionFrame`, `ParametersFrame`, `ActionsFrame`, `LogFrame`
- **Resource Management**: `resource_path` helper for PyInstaller compatibility
- **Threading**: Proper thread management for serial communication

### New Components to Add
- **ThemeService**: Manage light/dark/system theme switching with persistence
- **ToolbarFrame**: New UI component for top-level application functions with profile management, language switching, and help resources
- **ParameterFactory**: Factory pattern for creating different parameter input types (numeric, dropdown, radio button groups)
- **DeviceCommandMapper**: Map UI parameters to specific LT32Pro AT commands with proper device information retrieval
- **ValidationService**: Centralized input validation with localized error messages and range checking
- **LogExportService**: Handle log export functionality and enhanced logging capabilities
- **ProfileManager**: Manage configuration profile save/load operations

## Components and Interfaces

### 1. Enhanced ParametersFrame

**Current State**: Only implements APN configuration parameters
**Design Changes**:
- Extend to include all PRD-specified parameters using a factory pattern
- Group parameters into logical sections (Communication, Sensors, Timers, etc.)
- Implement parameter-specific validation rules
- Add visual feedback for validation states

**Parameter Categories to Add** (per Requirement 1):
```python
# Numeric Parameters with Validation
- Vibration (0-255) - Range validation with error feedback
- Timer settings (various ranges) - Context-specific validation
- Sensitivity levels (1-10) - Integer validation with bounds checking

# Dropdown Parameters with All Valid Options
- Heart Beat intervals (30s, 1min, 5min, 10min, 30min, 1hr, 2hr, 6hr, 12hr, 24hr)
- Curve Sensor options (Enabled/Disabled/Auto)
- Protocol types (TCP/UDP) - Network protocol selection

# Radio Button Groups with Exclusive Selection
- Lock Type (PIN/Card) - Security method selection
- Ignition Type (Digital/Analog) - Input type configuration
- Protocol options - Additional protocol-specific settings
```

**Design Rationale**: Factory pattern allows consistent parameter creation while maintaining type-specific validation and UI rendering. Each parameter type encapsulates its validation rules and AT command mapping, ensuring maintainable and extensible code.

### 2. New ToolbarFrame Component

**Purpose**: Implement the top toolbar required by Requirement 2
**Location**: Top of main window, spanning full width
**Components**:
- Configuration Profiles dropdown (Save current settings/Load .lt32config files)
- Language selector (Portuguese/English/Spanish with immediate application)
- Help menu (Driver installation guide, Equipment manuals)
- Restore Defaults button (Reset UI fields to defaults)
- Personalization button (Theme selection dialog)

**Design Rationale**: Centralized toolbar provides quick access to all major application functions while maintaining clean separation from parameter configuration area. Dropdown menus conserve space while providing comprehensive functionality.

**Interface**:
```python
class ToolbarFrame(ctk.CTkFrame):
    def __init__(self, master, i18n, config_service, theme_service, profile_manager):
        # Configuration profile dropdown with save/load options
        # Language selector with immediate application
        # Help menu with external resource links
        # Restore defaults with confirmation dialog
        # Personalization button opening theme dialog
    
    def on_save_profile(self) -> None
    def on_load_profile(self, file_path: str) -> None
    def on_language_change(self, language: str) -> None
    def on_restore_defaults(self) -> None
    def on_open_personalization(self) -> None
```

### 3. ThemeService

**Purpose**: Manage application themes with persistence
**Features**:
- Light/Dark/System theme options
- Immediate application without restart
- Persistent storage of user preference
- Integration with CustomTkinter theme system

**Interface**:
```python
class ThemeService:
    def set_theme(self, theme: str) -> None
    def get_current_theme(self) -> str
    def load_saved_theme(self) -> None
    def save_theme_preference(self, theme: str) -> None
```

### 4. Enhanced DeviceCommandMapper

**Purpose**: Map UI parameters to actual LT32Pro commands
**Current State**: Uses placeholder commands like "AT+APNSRV={value}"
**Design**: Create comprehensive mapping for all device parameters using actual LT32Pro command protocol

**Serial Communication Protocol**: All commands must be prefixed with "ATSMS:" when sent via serial port
- Example: `ATSMS:APN,cmnet,,#` instead of just `APN,cmnet,,#`
- This prefix is required for proper serial communication with the LT32Pro device

**Command Categories**:
```python
# APN Configuration
APN,{server},{user},{password}#    # Configure APN
APN#                               # Request current APN

# Server Configuration  
SERVER,0,{ip},{port},0#           # Configure main server (TCP)
SERVER,1,{domain},{port},0#       # Configure main server (domain)
SERVER#                          # Request current server
SZCS#SERV2_ADDR={ip}#SERV2_PORT={port}  # Configure backup server

# Communication Intervals
TIMER,{ign_on},{ign_off}#         # Set reporting intervals (1-65500s)
HBT,{ign_on},{ign_off}#          # Set heartbeat intervals (60-300s)

# Device Information Retrieval
CXCS#IMEI                        # Request IMEI
CXCS#ICCID                       # Request ICCID  
CXCS#IMSI                        # Request IMSI
STATUS#                          # Request device status
VERSION#                         # Request firmware version
PARAM#                           # Request all parameters

# Movement and Vibration Settings
SZCS#VIBL={level}                # Set vibration sensitivity (1-6)
SZCS#VIBCHK={window}:{threshold} # Set vibration detection window
DEFENSE,{minutes}#               # Set movement sensor activation time (1-60min)

# Speed and Angle Reporting
SPEED,ON,{time},{limit},{alert_type}#  # Configure speed alert (5-600s, 1-255km/h)
SZCS#ANGLEVALUE={speed}-{angle}  # Configure angle reporting (1-20km/h, 5-90°)
SZCS#BLINDSPD={threshold}        # Set speed threshold for position logging (0-20km/h)

# Ignition Configuration
SZCS#ACCLINE={type}#ACC_CFG={config}  # Configure ignition type
# type: 0=Virtual, 1=Physical
# Physical voltage: ACC_CFG=1-{on_voltage}-{off_voltage}

# Alerts Configuration
SENALM,ON,{alert_type}#          # Enable movement alert (0=GPRS, 1=SMS+GPRS)
POWERALM,ON,{type},{t1},{t2}#    # Configure power disconnection alert
BATALM,ON,{type}#                # Configure low battery alert
MOVING,ON,{radius},{type}#       # Configure movement by distance alert (100-1000m)
ACCALM,ON,{type}#                # Configure ignition ON alert
ACCOFFALM,ON,{type}#             # Configure ignition OFF alert

# Network and Protocol Settings
SZCS#GT06SEL={protocol}          # Select protocol (0=GT06, 1=CRX3, 2=CRX)
SZCS#NETSELECT={network}         # Select network (0=AUTO, 1=4G, 2=2G)
SZCS#VOLTESWITCH={network}       # Set SMS network (0=2G, 1=4G)

# Sleep Mode Configuration
SZCS#SLPDISCONNECT={mode}        # Set sleep mode (0=Disabled, 1=Sleep, 2=Deep Sleep)
SZCS#SLEEPT={minutes}            # Set sleep activation time

# Relay/Output Control
RELAY,{state}#                   # Control output (0=OFF, 1=ON)
SZCS#SOURCE_OFF_TYPE={type}      # Set GPS check before relay activation

# Phone Numbers Configuration
CENTER,A,{phone}#                # Add center phone number 1
CENTER,A2,{phone}#               # Add center phone number 2  
CENTER,A3,{phone}#               # Add center phone number 3
SOS,A,{phone1},{phone2},{phone3}# # Add SOS numbers

# System Commands
RESET#                           # Restart device
FACTORY#                         # Factory reset
FORMAT#                          # Format device
BLINDINIT#                       # Clear memory messages

# Advanced Features
JAMMER,ON,{alert_type}#          # Enable jammer detection
JAMCFG,{time},{signal},{freq}#   # Configure jammer parameters
PRLOCK,{password},{state}#       # Lock/unlock parameters (state: 0=unlock, 1=lock)
```

### 5. Enhanced ValidationService

**Purpose**: Centralized validation with localized error messages (per Requirement 6)
**Features**:
- Parameter-specific validation rules with detailed error messages
- Range checking for numeric inputs with specific valid ranges
- Format validation for text inputs
- Connection state validation before command execution
- Localized error messages through I18nService
- Prevention of actions when device not connected

**Interface**:
```python
class ValidationService:
    def validate_parameter(self, param_name: str, value: any) -> ValidationResult
    def validate_connection_required(self) -> bool
    def get_validation_message(self, error_type: str, param_name: str) -> str
    def validate_profile_data(self, profile_data: dict) -> ValidationResult
```

### 6. LogExportService

**Purpose**: Handle enhanced logging and export functionality (per Requirement 5)
**Features**:
- Export communication log as text file
- Clear distinction between command types, device responses, and system messages
- Performance optimization for lengthy logs
- Copy log content to clipboard
- Timestamped entries with proper formatting

**Interface**:
```python
class LogExportService:
    def export_log_to_file(self, file_path: str) -> bool
    def copy_log_to_clipboard(self) -> bool
    def format_log_entry(self, entry_type: str, message: str) -> str
    def clear_old_entries(self, max_entries: int) -> None
```

### 7. DeviceInfoService

**Purpose**: Retrieve and display device information (per Requirement 4)
**Features**:
- IMEI and ICCID retrieval on connection
- Device status verification
- Current configuration retrieval
- Device information display in UI

**Interface**:
```python
class DeviceInfoService:
    def retrieve_device_info(self) -> DeviceInfo
    def get_current_device_config(self) -> dict
    def verify_device_connection(self) -> bool
    def format_device_info_display(self, info: DeviceInfo) -> str
```

## Data Models

### Configuration Profile Structure
Extend the existing `.lt32config` format to include all parameters:

```json
{
  "version": "1.0",
  "apn_config": {
    "server": "internet.provider.com",
    "user": "username", 
    "password": "password",
    "transmission_mode": "TCP"
  },
  "device_parameters": {
    "vibration": 128,
    "heartbeat_interval": "1min",
    "sensitivity": 5,
    "lock_type": "PIN",
    "ignition_type": "Digital"
  },
  "sensor_config": {
    "curve_sensor": "Auto"
  }
}
```

### Theme Configuration
```json
{
  "theme": "System",
  "last_updated": "2025-01-16T10:30:00Z"
}
```

### Device Information Model
```python
@dataclass
class DeviceInfo:
    imei: str
    iccid: str
    firmware_version: str
    signal_strength: int
    connection_status: str
    last_communication: datetime
```

### Validation Result Model
```python
@dataclass
class ValidationResult:
    is_valid: bool
    error_message: str
    error_code: str
    suggested_value: Optional[str] = None
```

### Parameter Definition Model
```python
@dataclass
class ParameterDefinition:
    name: str
    param_type: str  # 'numeric', 'dropdown', 'radio'
    validation_rules: dict
    at_command_template: str
    display_label: str
    help_text: str
```

## Error Handling

### Enhanced Error Categories
1. **Connection Errors**: Device disconnection, COM port issues
2. **Validation Errors**: Invalid parameter values, format errors
3. **Configuration Errors**: Profile loading/saving failures
4. **Device Communication Errors**: AT command failures, timeout issues

### Error Display Strategy
- **Validation Errors**: Inline feedback near input fields
- **Connection Errors**: Status updates in connection frame
- **System Errors**: Modal dialogs with detailed information
- **Log Errors**: Timestamped entries in serial log

## Testing Strategy

### Unit Testing Focus Areas
1. **Parameter Validation**: Test all validation rules with edge cases
2. **Theme Switching**: Verify theme persistence and application
3. **Configuration Profiles**: Test save/load with various parameter combinations
4. **AT Command Mapping**: Verify correct command generation for all parameters

### Integration Testing
1. **UI Component Integration**: Test toolbar interactions with main application
2. **Service Integration**: Test theme service with UI updates
3. **Serial Communication**: Test enhanced command mapping with mock device
4. **Internationalization**: Test all new UI elements in multiple languages

### User Acceptance Testing Scenarios
1. **Complete Configuration Workflow**: Connect device, configure all parameters, save profile
2. **Theme Switching**: Change themes and verify persistence across restarts
3. **Error Handling**: Test various error conditions and recovery
4. **Internationalization**: Test application in all supported languages

## Implementation Approach

### Phase 1: Core Parameter Extension
- Implement parameter factory pattern
- Add all missing parameter types to ParametersFrame
- Implement validation for new parameters
- Update ConfigService to handle extended configuration format

### Phase 2: Toolbar Implementation  
- Create ToolbarFrame component
- Implement profile management UI
- Add language switching functionality
- Create help menu with driver/manual links

### Phase 3: Theme System
- Implement ThemeService
- Add personalization dialog
- Integrate theme switching with CustomTkinter
- Add theme persistence

### Phase 4: Enhanced Device Communication
- Replace placeholder AT commands with actual device commands
- Implement device information retrieval (IMEI/ICCID)
- Add comprehensive error handling for device communication
- Implement log export functionality

### Phase 5: Polish and Testing
- Add comprehensive input validation
- Implement remaining UI enhancements
- Conduct thorough testing
- Update documentation and build process