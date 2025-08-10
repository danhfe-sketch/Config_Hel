# Implementation Plan

- [x] 1. Add missing command templates to DeviceCommandMapper





  - Add command templates for all parameters from Parameter UI List that are currently missing
  - Implement jammer_relay_action, main_power_alert, backup_battery_alert, vibration_sensitivity, angle_report, and speed_buzzer templates
  - Ensure templates match exact format specified in Parameter UI List
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Implement multi-field parameter handling in DeviceCommandMapper





  - Create _handle_multi_field_parameter method to process complex parameters
  - Add logic to map parameter fields to command parameters for jammer_relay_action
  - Handle default values for undefined command parameters (D, E, F, G in JAMRELAY)
  - _Requirements: 1.2, 2.3_

- [x] 3. Add missing value mappings for parameter options





  - Add jammer_output_operation mapping (Sem Ação → 0, Ativar e Manter → 1, etc.)
  - Add boolean_on_off mapping for parameters that need ON/OFF values
  - Add alert_type mapping for GPRS/SMS options
  - Update existing mappings to be complete and consistent
  - _Requirements: 1.4, 4.3_

- [x] 4. Implement get_parameter_command_variations method





  - Add the missing method that the test file is trying to call
  - Make it handle both single-field and multi-field parameters
  - Return list of commands for the given parameter
  - Include proper error handling for unknown parameters
  - _Requirements: 2.1, 2.2, 2.4_

- [x] 5. Update get_command method to handle multi-field parameters





  - Modify existing get_command method to detect multi-field parameters
  - Use _handle_multi_field_parameter for complex parameters
  - Maintain backward compatibility with existing single-field parameters
  - _Requirements: 2.3, 4.4_

- [x] 6. Fix test file method calls and parameter handling





  - Replace get_parameter_command_variations calls with correct method calls
  - Update parameter processing logic to handle the corrected DeviceCommandMapper API
  - Add proper error handling for command generation failures
  - _Requirements: 2.1, 3.3_

- [x] 7. Add comprehensive error handling and validation





  - Add validation for parameter values before command generation
  - Provide detailed error messages for missing templates or invalid values
  - Add logging for command generation process
  - _Requirements: 2.4, 3.3_

- [ ] 8. Create unit tests for new DeviceCommandMapper functionality
  - Write tests for each new command template with sample parameter values
  - Test multi-field parameter handling with jammer_relay_action
  - Test value mappings for all new parameter types
  - Test error conditions and edge cases
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 9. Update integration test to verify complete parameter writing





  - Modify test_com14_profile_cycle.py to use corrected DeviceCommandMapper
  - Test all parameters from the profile can generate valid commands
  - Verify generated commands match expected format from Parameter UI List
  - _Requirements: 3.1, 3.2, 4.1_

- [x] 10. Validate command format compliance with Parameter UI List









  - Cross-reference all command templates with Parameter UI List specification
  - Ensure parameter order, format, and values match exactly
  - Test with actual parameter values from profile data
  - _Requirements: 1.4, 4.1, 4.2_