# Requirements Document

## Introduction

The LT32Pro profile loading operations (load profile from device and send profile to device) are currently not working correctly. The main issues are: incorrect command format when communicating with the device (missing "ATSMS:" prefix), incomplete parameter extraction from device responses, and lack of proper error handling during profile operations. This feature will fix these core profile management operations to work reliably with real LT32Pro devices.

## Requirements

### Requirement 1

**User Story:** As a user, I want to load a profile from the connected LT32Pro device, so that I can save the current device configuration to a file for backup or transfer purposes.

#### Acceptance Criteria

1. WHEN I select "load profile from device" THEN the system SHALL connect to the device using the correct serial communication protocol
2. WHEN communicating with the device via USB THEN the system SHALL prefix all commands with "ATSMS:" as required for serial communication
3. WHEN reading device parameters THEN the system SHALL send the correct LT32Pro commands with ATSMS prefix (ATSMS:APN#, ATSMS:SERVER#, ATSMS:CXCS#IMEI, ATSMS:CXCS#ICCID, ATSMS:CXCS#GT06SEL, ATSMS:CXCS#POSBYACK, ATSMS:STATUS#, ATSMS:VERSION#)
4. WHEN device responds THEN the system SHALL parse responses correctly (APN:cmnet,,, SERVER:0,IP,PORT,0, READOK: IMEI=value, READOK: ICCID=value)
5. WHEN all parameters are read THEN the system SHALL create a profile file with individual parameters extracted from device responses
6. WHEN the operation completes THEN the system SHALL provide clear feedback about success or failure with specific error details

### Requirement 2

**User Story:** As a user, I want to send a profile to the connected LT32Pro device, so that I can configure the device with saved settings from a profile file.

#### Acceptance Criteria

1. WHEN I select "send profile to device" THEN the system SHALL read the profile file and validate its contents
2. WHEN sending configuration commands via USB THEN the system SHALL prefix all commands with "ATSMS:" as required for serial communication
3. WHEN configuring APN THEN the system SHALL send commands in the format "ATSMS:APN,server,user,password#"
4. WHEN configuring server THEN the system SHALL send commands in the format "ATSMS:SERVER,0,IP,PORT,0#"
5. WHEN configuring other parameters THEN the system SHALL use the correct LT32Pro command format with ATSMS prefix for USB communication
6. WHEN each command is sent THEN the system SHALL wait for and validate the device response before proceeding
7. WHEN the operation completes THEN the system SHALL provide clear feedback about which parameters were successfully configured

### Requirement 3

**User Story:** As a user, I want proper error handling during profile operations, so that I can understand what went wrong and take corrective action.

#### Acceptance Criteria

1. WHEN device connection fails THEN the system SHALL display a clear error message with connection details
2. WHEN device communication times out THEN the system SHALL retry the operation with exponential backoff
3. WHEN device returns error responses THEN the system SHALL log the specific error and continue with remaining parameters
4. WHEN profile file is invalid THEN the system SHALL validate the file format and show specific validation errors
5. WHEN partial operations succeed THEN the system SHALL report which parameters succeeded and which failed
6. WHEN critical errors occur THEN the system SHALL provide actionable troubleshooting guidance

### Requirement 4

**User Story:** As a user, I want the profile operations to work with the correct LT32Pro command protocol, so that the device communication is reliable and follows the manufacturer specifications.

#### Acceptance Criteria

1. WHEN sending commands via USB serial THEN the system SHALL prefix all commands with "ATSMS:" as required for serial communication
2. WHEN reading device status THEN the system SHALL use "ATSMS:STATUS#" command format
3. WHEN reading APN settings THEN the system SHALL use "ATSMS:APN#" command format
4. WHEN reading server settings THEN the system SHALL use "ATSMS:SERVER#" command format
5. WHEN reading device info THEN the system SHALL use "ATSMS:CXCS#IMEI", "ATSMS:CXCS#ICCID" command formats
6. WHEN reading protocol settings THEN the system SHALL use "ATSMS:CXCS#GT06SEL", "ATSMS:CXCS#POSBYACK" command formats
7. WHEN configuring parameters THEN the system SHALL use the correct command syntax as specified in the LT32Pro manual

### Requirement 5

**User Story:** As a user, I want enhanced parameter extraction from device responses, so that profile files contain all necessary individual parameters for validation and future use.

#### Acceptance Criteria

1. WHEN device responds with "APN:server,user,password" THEN the system SHALL extract apn_server, apn_user, apn_password parameters
2. WHEN device responds with "SERVER:0,IP,PORT,0" THEN the system SHALL extract server_ip, server_port, server_type parameters
3. WHEN device responds with "READOK: IMEI=value" THEN the system SHALL extract device_imei, device_id, imei parameters
4. WHEN device responds with "READOK: ICCID=value" THEN the system SHALL extract device_iccid, iccid parameters
5. WHEN device responds with "READOK: GT06SEL=value" THEN the system SHALL extract protocol, protocol_name parameters
6. WHEN device responds with "READOK: POSBYACK=value" THEN the system SHALL extract tcp_ack, tcp_acknowledgment parameters
7. WHEN creating profile files THEN the system SHALL include default values for commonly required parameters (heartbeat_interval, report_interval, timezone)

### Requirement 6

**User Story:** As a user, I want real-time progress feedback during profile operations, so that I understand what the system is doing and can monitor the operation progress.

#### Acceptance Criteria

1. WHEN profile operation starts THEN the system SHALL display a progress dialog with current operation status
2. WHEN reading each parameter THEN the system SHALL update progress with the specific parameter being read
3. WHEN sending each command THEN the system SHALL update progress with the specific command being sent
4. WHEN waiting for device response THEN the system SHALL show "waiting for response" status with timeout countdown
5. WHEN operation encounters errors THEN the system SHALL update progress with error details while continuing with remaining operations
6. WHEN operation completes THEN the system SHALL show final summary with success/failure counts and total time taken