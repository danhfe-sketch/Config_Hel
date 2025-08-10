# Design Document

## Overview

This design document outlines the implementation of the complete Parameter UI specification as defined in the Parameter UI List document. The design focuses on updating the existing parameter system to match the exact specification including all parameter sections, UI element types, validation rules, command formats, and comprehensive configuration reading capabilities. The implementation will leverage the existing architecture while extending it to support the full parameter specification with proper RS232 communication for both reading and writing device parameters.

## Architecture

The design builds upon the existing LT32Pro configurator architecture and extends it with enhanced parameter management:

### Current Architecture Components to Extend
- **ParametersFrame**: Extend to implement all parameter sections with proper UI elements
- **DeviceCommandMapper**: Update with exact command formats from the specification
- **ConfigurationReaderService**: Enhance to handle all parameter read operations
- **ValidationService**: Update with all validation rules from the specification
- **SerialService**: Ensure proper RS232 communication for parameter operations

### New Components to Add
- **ParameterSpecificationFactory**: Factory to create parameters exactly as specified in the document
- **ConditionalFieldManager**: Handle visibility conditions for conditional parameters
- **ParameterResponseParser**: Parse device responses for all parameter types
- **ParameterUIElementFactory**: Create specific UI element types (text_input, number_input, dropdown, toggle_switch, slider, password_input)

## Components and Interfaces

### 1. Enhanced ParametersFrame

**Purpose**: Implement all parameter sections exactly as specified in the Parameter UI List document
**Design Changes**:
- Reorganize to match the exact section structure from the specification
- Implement all UI element types (text_input, number_input, dropdown, toggle_switch, slider, password_input for other fields)
- Add conditional field visibility management
- Integrate proper validation for each parameter type

**Parameter Section Structure**:
```python
PARAMETER_SECTIONS = {
    'network_parameters': {
        'apn_settings': {
            'name': 'apn_settings',
            'label': 'Configuração APN',
            'description': 'Configures the APN, username, and password for the mobile network.',
            'fields': {
                'apn': {'ui_element': 'text_input', 'validation': 'accepts APN name, IP, or URL'},
                'user': {'ui_element': 'text_input'},
                'password': {'ui_element': 'text_input'}
            },
            'commands': {'set': 'APN,<apn>,<user>,<password>#', 'read': 'APN#'}
        },
        'server_settings': {
            'name': 'server_settings',
            'label': 'Configuração de Servidor',
            'description': 'Configures the primary server IP/URL and port.',
            'fields': {
                'address': {'ui_element': 'text_input', 'validation': 'valid IP or URL'},
                'port': {'ui_element': 'number_input', 'validation': '1-65535'}
            },
            'commands': {'set': 'SERVER,<type>,<address>,<port>,0#', 'read': 'SERVER#'}
        }
    },
    'time_parameters': {
        'report_intervals': {
            'name': 'report_intervals',
            'label': 'Intervalos de Envio',
            'description': 'Defines the time intervals for sending position data based on ignition status.',
            'fields': {
                'moving_time': {'ui_element': 'number_input', 'unit': 'seconds'},
                'stopped_time': {'ui_element': 'number_input', 'unit': 'seconds'}
            },
            'commands': {'set': 'TIMER,<moving_time>,<stopped_time>#', 'read': 'TIMER#'}
        },
        'heartbeat_intervals': {
            'name': 'heartbeat_intervals',
            'label': 'Intervalos de Heartbeat',
            'description': 'Defines the keep-alive signal interval based on ignition status.',
            'fields': {
                'moving_heartbeat': {'ui_element': 'number_input', 'unit': 'seconds'},
                'stopped_heartbeat': {'ui_element': 'number_input', 'unit': 'seconds'}
            },
            'commands': {'set': 'HBT,<moving_heartbeat>,<stopped_heartbeat>#', 'read': 'HBT#'}
        }
    },
    'service_parameters': {
        'protocol': {
            'name': 'protocol',
            'label': 'Tipo de protocolo',
            'ui_element': 'dropdown',
            'options': ['GT06 (0x60)', 'CRX3 (0x22)', 'CRX (0x12)'],
            'commands': {'set': 'SZCS#GT06SEL=X', 'read': 'CXCS#GT06SEL'}
        },
        'tcp_ack': {
            'name': 'tcp_ack',
            'label': 'Habilitar confirmação TCP (ACK)',
            'ui_element': 'toggle_switch',
            'options': ['Enabled', 'Disabled'],
            'commands': {'set': 'SZCS#POSBYACK=A', 'read': 'CXCS#POSBYACK'}
        }
    },
    'ignition': {
        'ignition_type': {
            'name': 'ignition_type',
            'label': 'Tipo de ignição',
            'description': 'Configures the method for detecting ignition status.',
            'fields': {
                'ignition_mode': {
                    'ui_element': 'dropdown',
                    'options': ['Física (Physical)', 'Virtual por acelerômetro (Virtual by accelerometer)', 'Virtual por bateria (Virtual by battery)']
                },
                'on_voltage': {
                    'ui_element': 'number_input',
                    'unit': 'V',
                    'visibility_condition': "ignition_mode == 'Virtual por bateria (Virtual by battery)'"
                },
                'off_voltage': {
                    'ui_element': 'number_input',
                    'unit': 'V',
                    'visibility_condition': "ignition_mode == 'Virtual por bateria (Virtual by battery)'"
                }
            },
            'commands': {
                'set_physical': 'SZCS#ACCLINE=1#ACC_CFG=0-000-000',
                'set_accelerometer': 'SZCS#ACCLINE=0#ACC_CFG=0-000-000',
                'set_battery': 'SZCS#ACCLINE=1#ACC_CFG=1-<on_voltage>-<off_voltage>',
                'read': 'CXCS#ACCLINE#ACC_CFG'
            }
        }
    }
    # ... continue with all other sections from the specification
}
```

### 2. ParameterSpecificationFactory

**Purpose**: Create parameter UI elements exactly as specified in the Parameter UI List document
**Features**:
- Generate UI elements based on specification (text_input, number_input, dropdown, toggle_switch, slider, password_input for other fields)
- Apply validation rules from specification
- Handle conditional field visibility
- Integrate with command mapping

**Interface**:
```python
class ParameterSpecificationFactory:
    def create_parameter_section(self, section_name: str, section_config: dict) -> ParameterSection
    def create_ui_element(self, element_type: str, config: dict) -> UIElement
    def apply_validation_rules(self, element: UIElement, validation_config: dict) -> None
    def setup_conditional_visibility(self, element: UIElement, condition: str) -> None
    def get_command_mapping(self, parameter_name: str) -> CommandMapping
```

### 3. Enhanced DeviceCommandMapper

**Purpose**: Map UI parameters to exact device commands as specified in the document
**Design Changes**:
- Update all command templates to match the exact specification
- Handle complex command formats with multiple parameters
- Support conditional command generation based on parameter values
- Implement proper command validation before sending

**Command Mapping Structure**:
```python
COMMAND_MAPPINGS = {
    'apn_settings': {
        'set_template': 'APN,{apn},{user},{password}#',
        'read_command': 'APN#',
        'response_pattern': r'APN:([^,]*),([^,]*),([^#]*)',
        'field_mapping': ['apn', 'user', 'password']
    },
    'server_settings': {
        'set_template': 'SERVER,{type},{address},{port},0#',
        'read_command': 'SERVER#',
        'response_pattern': r'SERVER:(\d+),([^,]*),(\d+),(\d+)',
        'field_mapping': ['type', 'address', 'port', 'protocol'],
        'type_logic': lambda address: 0 if is_ip_address(address) else 1
    },
    'report_intervals': {
        'set_template': 'TIMER,{moving_time},{stopped_time}#',
        'read_command': 'TIMER#',
        'response_pattern': r'TIMER:(\d+),(\d+)',
        'field_mapping': ['moving_time', 'stopped_time']
    },
    'heartbeat_intervals': {
        'set_template': 'HBT,{moving_heartbeat},{stopped_heartbeat}#',
        'read_command': 'HBT#',
        'response_pattern': r'HBT:(\d+),(\d+)',
        'field_mapping': ['moving_heartbeat', 'stopped_heartbeat']
    },
    'protocol': {
        'set_template': 'SZCS#GT06SEL={protocol_value}',
        'read_command': 'CXCS#GT06SEL',
        'response_pattern': r'GT06SEL=(\d+)',
        'field_mapping': ['protocol_value'],
        'value_mapping': {'GT06 (0x60)': 0, 'CRX3 (0x22)': 1, 'CRX (0x12)': 2}
    },
    'tcp_ack': {
        'set_template': 'SZCS#POSBYACK={ack_value}',
        'read_command': 'CXCS#POSBYACK',
        'response_pattern': r'POSBYACK=(\d+)',
        'field_mapping': ['ack_value'],
        'value_mapping': {'Enabled': 1, 'Disabled': 0}
    },
    'ignition_type': {
        'set_templates': {
            'physical': 'SZCS#ACCLINE=1#ACC_CFG=0-000-000',
            'accelerometer': 'SZCS#ACCLINE=0#ACC_CFG=0-000-000',
            'battery': 'SZCS#ACCLINE=1#ACC_CFG=1-{on_voltage}-{off_voltage}'
        },
        'read_commands': ['CXCS#ACCLINE', 'CXCS#ACC_CFG'],
        'response_patterns': {
            'accline': r'ACCLINE=(\d+)',
            'acc_cfg': r'ACC_CFG=(\d+)-(\d+)-(\d+)'
        },
        'field_mapping': ['accline', 'cfg_type', 'on_voltage', 'off_voltage']
    }
    # ... continue with all parameters from specification
}
```

### 4. Enhanced ConfigurationReaderService

**Purpose**: Read all device parameters and populate UI fields as specified
**Design Changes**:
- Implement reading for all parameter types from the specification
- Handle complex response parsing for different parameter formats
- Provide progress indication during bulk reading operations
- Support partial reading with error handling for failed parameters

**Interface**:
```python
class ConfigurationReaderService:
    def read_all_parameters(self) -> ConfigurationReadResult
    def read_parameter_section(self, section_name: str) -> SectionReadResult
    def read_single_parameter(self, parameter_name: str) -> ParameterReadResult
    def parse_parameter_response(self, parameter_name: str, response: str) -> ParsedParameterData
    def update_ui_from_parameter_data(self, parameter_name: str, data: ParsedParameterData) -> None
    def handle_conditional_parameters(self, parameter_name: str, data: ParsedParameterData) -> None
    def show_read_progress(self, current_param: str, progress: float) -> None
    def handle_read_errors(self, failed_params: List[str]) -> None
```

### 5. ParameterResponseParser

**Purpose**: Parse device responses for all parameter types according to specification
**Features**:
- Handle different response formats for each parameter type
- Extract multiple values from complex responses
- Validate response format before parsing
- Provide detailed error information for parsing failures

**Interface**:
```python
class ParameterResponseParser:
    def parse_response(self, parameter_name: str, raw_response: str) -> ParsedResponse
    def validate_response_format(self, parameter_name: str, response: str) -> bool
    def extract_parameter_values(self, parameter_name: str, response: str) -> dict
    def handle_parsing_error(self, parameter_name: str, response: str, error: Exception) -> ParseError
    def get_response_pattern(self, parameter_name: str) -> str
```

### 6. ConditionalFieldManager

**Purpose**: Handle conditional field visibility as specified in the document
**Features**:
- Monitor parameter value changes that trigger visibility conditions
- Show/hide fields based on visibility conditions
- Update field states when conditions change
- Maintain proper UI layout when fields are hidden/shown

**Interface**:
```python
class ConditionalFieldManager:
    def register_conditional_field(self, field_name: str, condition: str, trigger_field: str) -> None
    def evaluate_condition(self, condition: str, current_values: dict) -> bool
    def update_field_visibility(self, field_name: str, visible: bool) -> None
    def handle_trigger_change(self, trigger_field: str, new_value: any) -> None
    def get_visible_fields(self, section_name: str) -> List[str]
```

### 7. Enhanced ValidationService

**Purpose**: Implement all validation rules from the Parameter UI List specification
**Design Changes**:
- Add validation rules for all parameter types
- Implement range validation for numeric parameters
- Add format validation for text parameters
- Support conditional validation based on other parameter values

**Validation Rules Implementation**:
```python
VALIDATION_RULES = {
    'port': {
        'type': 'numeric_range',
        'min': 1,
        'max': 65535,
        'error_message': 'Port must be between 1 and 65535'
    },
    'apn': {
        'type': 'format_validation',
        'patterns': [r'^[\w\.-]+$', r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', r'^https?://[\w\.-]+'],
        'error_message': 'APN must be a valid name, IP address, or URL'
    },
    'speed_detection_time': {
        'type': 'numeric_range',
        'min': 5,
        'max': 600,
        'error_message': 'Detection time must be between 5 and 600 seconds'
    },
    'speed_limit': {
        'type': 'numeric_range',
        'min': 1,
        'max': 255,
        'error_message': 'Speed limit must be between 1 and 255 km/h'
    },
    'angle_min_speed': {
        'type': 'numeric_range',
        'min': 1,
        'max': 20,
        'error_message': 'Minimum speed must be between 1 and 20 km/h'
    },
    'angle_variation': {
        'type': 'numeric_range',
        'min': 5,
        'max': 90,
        'error_message': 'Angle variation must be between 5 and 90 degrees'
    },
    'vibration_level': {
        'type': 'numeric_range',
        'min': 1,
        'max': 6,
        'error_message': 'Vibration level must be between 1 (low) and 6 (high)'
    }
    # ... continue with all validation rules from specification
}
```

## Data Models

### Parameter Configuration Model
```python
@dataclass
class ParameterConfig:
    name: str
    label: str
    description: Optional[str]
    ui_element: str
    validation: Optional[dict]
    unit: Optional[str]
    options: Optional[List[str]]
    visibility_condition: Optional[str]
    commands: dict
    field_mapping: Optional[List[str]]

@dataclass
class ParameterSection:
    name: str
    label: str
    description: str
    parameters: List[ParameterConfig]
    order: int
```

### UI Element Models
```python
@dataclass
class UIElementConfig:
    element_type: str  # text_input, number_input, dropdown, toggle_switch, slider, password_input
    validation_rules: dict
    default_value: Optional[any]
    options: Optional[List[str]]
    range_config: Optional[dict]  # For sliders and number inputs
    visibility: bool

@dataclass
class ConditionalField:
    field_name: str
    condition: str
    trigger_fields: List[str]
    visible: bool
```

### Response Parsing Models
```python
@dataclass
class ParsedParameterData:
    parameter_name: str
    success: bool
    values: dict
    raw_response: str
    parsing_errors: List[str]
    timestamp: datetime

@dataclass
class ParameterReadResult:
    parameter_name: str
    success: bool
    parsed_data: Optional[ParsedParameterData]
    error_message: Optional[str]
    command_sent: str
    response_received: str
    read_duration: float

@dataclass
class SectionReadResult:
    section_name: str
    parameters_read: List[ParameterReadResult]
    success_count: int
    failure_count: int
    total_duration: float
```

### Command Generation Models
```python
@dataclass
class CommandMapping:
    parameter_name: str
    set_template: str
    read_command: str
    response_pattern: str
    field_mapping: List[str]
    value_mapping: Optional[dict]
    conditional_logic: Optional[callable]

@dataclass
class GeneratedCommand:
    command_string: str
    parameter_name: str
    values_used: dict
    validation_passed: bool
    error_message: Optional[str]
```

## Error Handling

### Parameter-Specific Error Categories
1. **Validation Errors**: Invalid parameter values, format errors, range violations
2. **Command Generation Errors**: Template formatting failures, missing required values
3. **Communication Errors**: Device timeout, invalid responses, connection failures
4. **Parsing Errors**: Unexpected response format, missing response data
5. **Conditional Logic Errors**: Visibility condition evaluation failures

### Error Display Strategy
- **Inline Validation**: Real-time feedback for parameter input validation
- **Progress Errors**: Error reporting during bulk configuration reading
- **Command Errors**: Detailed feedback for failed command execution
- **Parsing Errors**: Clear indication of response parsing failures with raw response data

## Testing Strategy

### Unit Testing Focus Areas
1. **Parameter Factory**: Test creation of all UI element types with proper configuration
2. **Command Mapping**: Verify correct command generation for all parameter types
3. **Response Parsing**: Test parsing of all expected response formats
4. **Validation Rules**: Test all validation scenarios including edge cases
5. **Conditional Logic**: Test field visibility conditions and trigger mechanisms

### Integration Testing
1. **Full Parameter Reading**: Test reading all parameters from mock device responses
2. **UI Population**: Test UI field updates from parsed parameter data
3. **Conditional Fields**: Test visibility changes based on parameter interactions
4. **Error Handling**: Test error scenarios for each parameter type

### User Acceptance Testing Scenarios
1. **Complete Parameter Configuration**: Configure all parameter types and verify proper command generation
2. **Configuration Reading**: Read device configuration and verify UI population
3. **Conditional Parameter Interaction**: Test ignition type with voltage field visibility
4. **Validation Feedback**: Test all validation rules with invalid inputs
5. **Error Recovery**: Test partial reading scenarios with some failed parameters

## Implementation Approach

### Phase 1: Parameter Specification Implementation
- Implement ParameterSpecificationFactory with all parameter definitions from the document
- Create UI element factory for all element types (text_input, number_input, dropdown, toggle_switch, slider, password_input for other fields)
- Update ParametersFrame to use the specification-based parameter creation
- Implement conditional field visibility management

### Phase 2: Command Mapping Update
- Update DeviceCommandMapper with exact command formats from specification
- Implement complex command generation logic for parameters with multiple values
- Add command validation before transmission
- Test command generation for all parameter types

### Phase 3: Configuration Reading Enhancement
- Enhance ConfigurationReaderService to handle all parameter read commands
- Implement ParameterResponseParser for all response formats
- Add progress indication for bulk reading operations
- Implement UI field population from parsed responses

### Phase 4: Validation and Error Handling
- Implement all validation rules from the specification
- Add proper error handling for all parameter operations
- Implement conditional validation based on parameter interactions
- Add comprehensive error reporting and user feedback

### Phase 5: Integration and Testing
- Integrate all components with existing application architecture
- Test complete parameter workflows (read/write/validate)
- Test conditional field interactions and visibility
- Verify proper error handling and recovery scenarios
- Test with various device response scenarios