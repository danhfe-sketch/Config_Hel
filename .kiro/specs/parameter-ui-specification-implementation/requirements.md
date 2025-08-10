# Requirements Document

## Introduction

This feature spec addresses the implementation of the complete Parameter UI specification as defined in the Parameter UI List document. The current LT32Pro configurator has basic parameter functionality, but needs to be updated to match the exact specification including all parameter sections, UI element types, validation rules, command formats, and configuration reading capabilities. This ensures the application provides comprehensive device configuration management with proper RS232 communication for both reading and writing device parameters.

## Requirements

### Requirement 1

**User Story:** As a technician, I want to configure all device parameters exactly as specified in the Parameter UI List document, so that I can access every configuration option available on the LT32Pro device through the proper UI elements.

#### Acceptance Criteria

1. WHEN I open the parameters section THEN the system SHALL display all parameter sections in the correct order: Network Parameters, Time Parameters, Service Parameters, Ignition, Speed, Power Saving, Angle, Battery Alerts, Vibration Sensor, Jammer Detection, and Miscellaneous
2. WHEN I view Network Parameters THEN the system SHALL display APN Settings (text inputs for APN, user, password) and Server Settings (text input for IP/URL, number input for port) with proper validation
3. WHEN I view Time Parameters THEN the system SHALL display Report Intervals (number inputs for moving/stopped time in seconds) and Heartbeat Intervals (number inputs for moving/stopped heartbeat in seconds)
4. WHEN I view Service Parameters THEN the system SHALL display Protocol dropdown with options ["GT06 (0x60)", "CRX3 (0x22)", "CRX (0x12)"] and TCP ACK toggle switch
5. WHEN I view Ignition section THEN the system SHALL display Ignition Type dropdown with conditional voltage fields that appear only when "Virtual por bateria" is selected

### Requirement 2

**User Story:** As a technician, I want proper UI element types for each parameter as specified in the document, so that I can interact with parameters using the most appropriate input method for each configuration type.

#### Acceptance Criteria

1. WHEN I interact with text parameters THEN the system SHALL provide text_input elements for APN server, user, and server address fields
2. WHEN I interact with APN password parameters THEN the system SHALL provide text_input elements for better visibility and configuration usability
3. WHEN I interact with numeric parameters THEN the system SHALL provide number_input elements with proper validation ranges for ports, times, speeds, and voltages
4. WHEN I interact with selection parameters THEN the system SHALL provide dropdown elements for protocol types, ignition modes, and alert types
5. WHEN I interact with boolean parameters THEN the system SHALL provide toggle_switch elements for enable/disable options
6. WHEN I interact with range parameters THEN the system SHALL provide slider elements for vibration sensitivity levels (1-6 range)

### Requirement 3

**User Story:** As a technician, I want proper validation for all parameter inputs as specified in the document, so that I can only enter valid values and receive clear feedback for invalid inputs.

#### Acceptance Criteria

1. WHEN I enter port numbers THEN the system SHALL validate the range is between 1 and 65535 and display error messages for invalid values
2. WHEN I enter APN values THEN the system SHALL accept standard APN names, IP addresses, or URLs and validate the format
3. WHEN I enter speed values THEN the system SHALL validate detection time is 5-600 seconds and speed limit is 1-255 km/h
4. WHEN I enter angle report values THEN the system SHALL validate minimum speed is 1-20 km/h and angle variation is 5-90 degrees
5. WHEN I enter power alert values THEN the system SHALL validate detection time is 2-60 seconds and minimum charge time is 1-3600 seconds
6. WHEN I enter vibration sensitivity THEN the system SHALL validate the level is between 1-6 with proper slider constraints

### Requirement 4

**User Story:** As a technician, I want conditional field visibility as specified in the document, so that I only see relevant configuration options based on my current selections.

#### Acceptance Criteria

1. WHEN I select "Virtual por bateria" for ignition mode THEN the system SHALL show the "Tensão para Ligar (ON)" and "Tensão para Desligar (OFF)" voltage fields
2. WHEN I select other ignition modes THEN the system SHALL hide the voltage configuration fields
3. WHEN I enable speed alert THEN the system SHALL show all speed alert configuration fields (detection time, speed limit, alert type)
4. WHEN I disable speed alert THEN the system SHALL hide the speed alert configuration fields
5. WHEN I enable angle report THEN the system SHALL show minimum speed and angle variation fields
6. WHEN I disable angle report THEN the system SHALL hide the angle report configuration fields

### Requirement 5

**User Story:** As a technician, I want proper device command mapping for all parameters as specified in the document, so that the application sends the correct AT commands to configure each device parameter.

#### Acceptance Criteria

1. WHEN I configure APN settings THEN the system SHALL send `APN,<apn>,<user>,<password>#` command with the entered values
2. WHEN I configure server settings THEN the system SHALL send `SERVER,<type>,<address>,<port>,0#` command with type 0 for IP and 1 for domain
3. WHEN I configure timer settings THEN the system SHALL send `TIMER,<moving_time>,<stopped_time>#` command with the specified intervals
4. WHEN I configure heartbeat settings THEN the system SHALL send `HBT,<moving_heartbeat>,<stopped_heartbeat>#` command with the specified intervals
5. WHEN I configure protocol settings THEN the system SHALL send `SZCS#GT06SEL=X` command where X=0 for GT06, 1 for CRX3, 2 for CRX
6. WHEN I configure ignition settings THEN the system SHALL send appropriate commands for physical (`SZCS#ACCLINE=1#ACC_CFG=0-000-000`), accelerometer (`SZCS#ACCLINE=0#ACC_CFG=0-000-000`), or battery (`SZCS#ACCLINE=1#ACC_CFG=1-<on_voltage>-<off_voltage>`) modes

### Requirement 6

**User Story:** As a technician, I want comprehensive configuration reading from the device via RS232, so that I can retrieve all current device settings and see them populated in the UI for verification and modification.

#### Acceptance Criteria

1. WHEN I click "Checar configuração" THEN the system SHALL send all parameter read commands (`APN#`, `SERVER#`, `TIMER#`, `HBT#`, `CXCS#GT06SEL`, `CXCS#ACCLINE#ACC_CFG`, etc.) to query current device configuration
2. WHEN the device responds to read commands THEN the system SHALL parse each response and populate the corresponding UI fields with the current device values
3. WHEN configuration reading is in progress THEN the system SHALL display a progress indicator showing which parameters are being read and disable parameter modification until complete
4. WHEN some parameters fail to read THEN the system SHALL continue reading other parameters and report which specific parameters could not be retrieved
5. WHEN all readable parameters are retrieved THEN the system SHALL log the operation with timestamps and update the UI to show which values were updated from the device
6. WHEN device responses are invalid or unexpected THEN the system SHALL handle errors gracefully and provide meaningful feedback about parsing failures

### Requirement 7

**User Story:** As a technician, I want proper response parsing for all parameter types as specified in the document, so that device responses are correctly interpreted and displayed in the UI.

#### Acceptance Criteria

1. WHEN the device responds to `APN#` command THEN the system SHALL parse the response format and populate APN, user, and password fields in the UI
2. WHEN the device responds to `SERVER#` command THEN the system SHALL parse the response and populate server address and port fields
3. WHEN the device responds to `TIMER#` command THEN the system SHALL parse the response and populate moving time and stopped time fields
4. WHEN the device responds to `HBT#` command THEN the system SHALL parse the response and populate heartbeat interval fields
5. WHEN the device responds to protocol queries THEN the system SHALL parse the response and select the correct protocol option in the dropdown
6. WHEN the device responds to ignition queries THEN the system SHALL parse the response and set the correct ignition mode and voltage values if applicable

### Requirement 8

**User Story:** As a technician, I want comprehensive error handling for parameter operations, so that I receive clear feedback when configuration reading or writing fails and can take appropriate corrective action.

#### Acceptance Criteria

1. WHEN parameter reading fails due to communication timeout THEN the system SHALL display specific error messages indicating which parameters could not be read and suggest checking device connection
2. WHEN parameter writing fails due to invalid responses THEN the system SHALL display error messages with the specific parameter that failed and the device response received
3. WHEN device connection is lost during parameter operations THEN the system SHALL detect the disconnection and provide clear feedback about the connection status
4. WHEN parameter validation fails before sending commands THEN the system SHALL prevent command transmission and highlight the invalid fields with specific error messages
5. WHEN device returns error responses to parameter commands THEN the system SHALL parse error codes and provide user-friendly explanations of the errors
6. WHEN partial parameter reading succeeds THEN the system SHALL update successfully read parameters in the UI and clearly indicate which parameters could not be retrieved

### Requirement 9

**User Story:** As a technician, I want proper logging and feedback for all parameter operations, so that I can track configuration changes and troubleshoot issues effectively.

#### Acceptance Criteria

1. WHEN I perform parameter reading operations THEN the system SHALL log all sent commands, received responses, and parsing results with timestamps
2. WHEN I perform parameter writing operations THEN the system SHALL log the commands sent, device responses, and success/failure status for each parameter
3. WHEN parameter operations complete THEN the system SHALL provide summary feedback showing how many parameters were successfully processed and how many failed
4. WHEN errors occur during parameter operations THEN the system SHALL log detailed error information including command sent, response received, and error interpretation
5. WHEN configuration reading updates UI fields THEN the system SHALL log which specific fields were updated and their new values
6. WHEN I export logs THEN the system SHALL include all parameter operation details in a readable format for troubleshooting and record-keeping