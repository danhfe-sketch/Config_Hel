# Design Document

## Overview

This design addresses the parameter command generation issues in the LT32 PRO configurator by completing the DeviceCommandMapper implementation and fixing the test file's method calls. The solution ensures that all parameters defined in the Parameter UI List have proper command templates and can be written correctly to the device.

## Architecture

The fix involves three main components:

1. **DeviceCommandMapper Enhancement**: Complete the command templates and add missing methods
2. **Parameter Value Mapping**: Ensure proper mapping between UI parameter values and command values
3. **Test File Correction**: Fix method calls and parameter handling in the test file

## Components and Interfaces

### DeviceCommandMapper Updates

**Missing Command Templates to Add:**
- `jammer_relay_action`: Maps to `JAMRELAY,<op>,<time>,<speed>,<D>,<E>,<F>,<G>#`
- `backup_battery_alert`: Maps to `BATALM,<state>,<mode>#`
- `main_power_alert`: Maps to `POWERALM,<enabled>,<alert_type>,<detection_time>,<min_charge_time>#`
- `vibration_sensitivity`: Maps to `SZCS#VIBL=<level>`
- `angle_report`: Maps to `SZCS#ANGLEVALUE=<min_speed>-<angle_variation>`
- `speed_buzzer`: Maps to `SZCS#SPD_LED_SHOW=<value>`

**New Method to Add:**
```python
def get_parameter_command_variations(self, section: str, param_name: str, values: Dict[str, Any]) -> List[str]:
    """Generate command variations for a parameter with multiple fields."""
```

**Enhanced Value Mappings:**
- Jammer output operation mappings
- Boolean to ON/OFF mappings for various parameters
- Multi-field parameter handling

### Parameter Field Mapping Strategy

For complex parameters like `jammer_relay_action`, the design uses a field mapping approach:

```python
# Input from profile
{
    "enabled": false,
    "output_operation": "Ativar e Desativar com Jammer", 
    "confirmation_time": 80,
    "speed_limit": 5
}

# Mapped to command parameters
JAMRELAY,2,80,5,0,0,0,0#
```

The mapping logic:
- `enabled` → determines if command should be sent
- `output_operation` → maps to operation code (0=Sem Ação, 1=Ativar e Manter, 2=Ativar e Desativar com Jammer)
- `confirmation_time` → direct value
- `speed_limit` → direct value
- Additional parameters (D,E,F,G) → default to 0 unless specified

### Test File Corrections

**Current Issue:**
```python
per_param_cmds = mapper.get_parameter_command_variations(section, param_name, values)
```

**Fixed Approach:**
```python
# Use existing get_command method with proper context
command = mapper.get_command(param_name, values, context={'section': section})
```

## Data Models

### Command Template Structure
```python
command_templates = {
    'jammer_relay_action': "JAMRELAY,{op},{time},{speed},{d},{e},{f},{g}#",
    'main_power_alert': "POWERALM,{enabled},{alert_type},{detection_time},{min_charge_time}#",
    # ... other templates
}
```

### Value Mapping Structure
```python
value_mappings = {
    'jammer_output_operation': {
        'Sem Ação': '0',
        'Ativar e Manter': '1', 
        'Ativar e Desativar com Jammer': '2'
    },
    'boolean_on_off': {
        True: 'ON',
        False: 'OFF'
    },
    # ... other mappings
}
```

### Multi-Field Parameter Handler
```python
def _handle_multi_field_parameter(self, param_name: str, values: Dict[str, Any]) -> Dict[str, Any]:
    """Convert multi-field parameter values to command format."""
    if param_name == 'jammer_relay_action':
        return {
            'op': self._map_value('jammer_output_operation', values.get('output_operation', 'Sem Ação')),
            'time': values.get('confirmation_time', 0),
            'speed': values.get('speed_limit', 0),
            'd': 0, 'e': 0, 'f': 0, 'g': 0  # Default values
        }
    # Handle other multi-field parameters...
```

## Error Handling

### Command Generation Errors
- **Missing Template**: Provide clear error message with parameter name
- **Invalid Field Values**: Validate field values before command generation
- **Mapping Failures**: Handle cases where value mappings are not found

### Test File Error Handling
- **Method Not Found**: Use try-catch blocks around mapper method calls
- **Command Generation Failure**: Log detailed error information
- **Parameter Processing**: Continue processing other parameters if one fails

## Testing Strategy

### Unit Tests for DeviceCommandMapper
1. Test each new command template with sample parameter values
2. Test value mappings for all parameter types
3. Test multi-field parameter handling
4. Test error conditions (missing templates, invalid values)

### Integration Tests
1. Test complete parameter writing cycle with updated mapper
2. Test all parameters from Parameter UI List
3. Test error handling in realistic scenarios

### Test File Validation
1. Verify all method calls use existing DeviceCommandMapper methods
2. Test command generation for all profile parameters
3. Validate generated commands match expected format

## Implementation Notes

### Command Format Compliance
All command templates must exactly match the Parameter UI List specification:
- Use exact parameter order as specified
- Include all required parameters even if optional
- Use correct command prefixes (SZCS vs CXCS for write vs read)

### Backward Compatibility
- Existing command templates remain unchanged
- New methods are additive, not replacing existing functionality
- Value mappings are extended, not replaced

### Performance Considerations
- Command generation should be fast for bulk operations
- Value mapping lookups should be O(1)
- Error handling should not significantly impact performance