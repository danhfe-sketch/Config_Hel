# Requirements Document

## Introduction

The LT32 PRO configurator has an issue where parameters are not being written correctly to the device. The problem stems from an incomplete DeviceCommandMapper that lacks proper command templates for all parameters defined in the Parameter UI List, and incorrect method calls in the test file. This affects the ability to write profile parameters like jammer_relay_action back to the device correctly.

## Requirements

### Requirement 1

**User Story:** As a developer running the profile test cycle, I want all parameters to be written correctly to the device, so that the device configuration matches the loaded profile.

#### Acceptance Criteria

1. WHEN the test file attempts to write parameters to the device THEN all parameters defined in the Parameter UI List SHALL have corresponding command templates in DeviceCommandMapper
2. WHEN a parameter has multiple fields THEN the command template SHALL correctly map all field values to the appropriate command parameters
3. WHEN the jammer_relay_action parameter is written THEN it SHALL generate the correct JAMRELAY command with all required parameters
4. WHEN any parameter from the Parameter UI List is written THEN it SHALL use the exact command format specified in the Parameter UI List

### Requirement 2

**User Story:** As a developer using the DeviceCommandMapper, I want a consistent API for generating commands, so that I can reliably generate commands for any parameter.

#### Acceptance Criteria

1. WHEN calling methods on DeviceCommandMapper THEN all method calls SHALL use existing methods in the class
2. WHEN the test file calls get_parameter_command_variations THEN it SHALL either use an existing method or the method SHALL be implemented
3. WHEN generating commands for multi-field parameters THEN the mapper SHALL handle the field-to-parameter mapping correctly
4. WHEN an unknown parameter is requested THEN the mapper SHALL provide a clear error message

### Requirement 3

**User Story:** As a system administrator, I want the parameter writing to be reliable and complete, so that device configurations are applied correctly.

#### Acceptance Criteria

1. WHEN all parameters from a profile are written THEN each parameter SHALL generate exactly one valid command
2. WHEN complex parameters like jammer_relay_action are processed THEN all field values SHALL be correctly mapped to command parameters
3. WHEN the command generation fails THEN the system SHALL provide detailed error information about which parameter failed and why
4. WHEN commands are generated THEN they SHALL follow the exact format specified in the Parameter UI List documentation

### Requirement 4

**User Story:** As a developer maintaining the codebase, I want the DeviceCommandMapper to be complete and consistent with the Parameter UI List, so that adding new parameters is straightforward.

#### Acceptance Criteria

1. WHEN comparing DeviceCommandMapper templates with Parameter UI List THEN every parameter SHALL have a corresponding command template
2. WHEN a parameter has set and read commands in Parameter UI List THEN both commands SHALL be supported in DeviceCommandMapper
3. WHEN parameter value mappings are needed THEN they SHALL be defined in the value_mappings dictionary
4. WHEN new parameters are added to Parameter UI List THEN the DeviceCommandMapper SHALL be easily extensible to support them