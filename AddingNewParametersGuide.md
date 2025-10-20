# Guide to Implementing New Parameters

This guide provides a step-by-step process for adding new parameters to the LT32Pro Configurator application. Following these steps will ensure that the new parameter is correctly integrated into the UI, the bulk read/write operations, and the individual command sending.

## 1. Update `Parameter UI List.md`

The `Parameter UI List.md` file is the source of truth for the UI generation. It defines the structure of the parameters, their UI elements, and their commands.

To add a new parameter, you need to add a new `### Config` section to this file. The section should contain the following information:

- `name`: The name of the parameter.
- `label`: The label that will be displayed in the UI.
- `ui_element`: The type of UI element to use (e.g., `dropdown`, `text_input`, `toggle_switch`).
- `options`: A list of options for dropdowns and toggle switches.
- `commands`: The `set` and `read` commands for the parameter.

**Example:**

```markdown
### Config: Distance Movement Action

*   **name:** distance_movement_action
*   **label:** "Configurar ação para movimento por distância"
*   **ui_element:** "dropdown"
*   **options:** ["Automaticamente ativado após entrar no modo DEFENSE (quando a ignição é desligada)", "Envia um alerta - Apenas uma vez independente da IGN on ou off", "Envia um alerta uma vez e bloqueia o veículo - Apenas uma vez independente da IGN on ou off"]
*   **commands:**
    *   **set:** `SZCS#MOVEALMFUN=X` (Note: X=0 for the first option, 1 for the second, 2 for the third)
    *   **read:** `CXCS#MOVEALMFUN`
```

## 2. Update `services/parameter_specification.py`

The `services/parameter_specification.py` file contains the hardcoded representation of the `Parameter UI List.md` file. You need to add the new parameter to the `PARAMETER_SPECIFICATION` and `COMMAND_VALUE_MAPPINGS` dictionaries in this file.

### `PARAMETER_SPECIFICATION`

Add the new parameter to the appropriate section in the `PARAMETER_SPECIFICATION` dictionary. The structure of the parameter should match the one in the `Parameter UI List.md` file.

**Example:**

```python
'distance_movement_action': ParameterConfig(
    name='distance_movement_action',
    label='Configurar ação para movimento por distância',
    ui_element='dropdown',
    options=['Automaticamente ativado após entrar no modo DEFENSE (quando a ignição é desligada)', 'Envia um alerta - Apenas uma vez independente da IGN on ou off', 'Envia um alerta uma vez e bloqueia o veículo - Apenas uma vez independente da IGN on ou off'],
    commands={
        'set': 'SZCS#MOVEALMFUN=X',
        'read': 'CXCS#MOVEALMFUN'
    }
)
```

### `COMMAND_VALUE_MAPPINGS`

If the parameter uses a dropdown or a toggle switch, you need to add a mapping from the UI options to the command values in the `COMMAND_VALUE_MAPPINGS` dictionary.

**Example:**

```python
'distance_movement_action': {
    'Automaticamente ativado após entrar no modo DEFENSE (quando a ignição é desligada)': 0,
    'Envia um alerta - Apenas uma vez independente da IGN on ou off': 1,
    'Envia um alerta uma vez e bloqueia o veículo - Apenas uma vez independente da IGN on ou off': 2
},
```

## 3. Update `services/configuration_reader_service.py`

The `services/configuration_reader_service.py` file is responsible for reading the device configuration. You need to update this file to include the new parameter in the bulk read operation.

### `_init_parameter_query_commands`

Add the new parameter to the `parameter_query_commands` dictionary. This will include the parameter in the list of commands to be executed during a bulk read.

**Example:**

```python
'distance_movement_action': ('MOVEALMFUN', 'get_distance_movement_action'),
```

### `_init_response_patterns`

Add a new regex pattern to the `response_patterns` dictionary to parse the response for the new parameter.

**Example:**

```python
'get_distance_movement_action': r'READOK:\s*MOVEALMFUN=(\d+)',
```

### `_get_command_type_for_parameter`

Add a new entry to the `command_type_mapping` dictionary to map the parameter name to the command type.

**Example:**

```python
'distance_movement_action': 'get_distance_movement_action',
```

### `parse_device_response`

Add a new `elif` block to the `parse_device_response` method to handle the parsing of the new parameter's response. This block will map the numeric value from the response to the corresponding UI option.

**Example:**

```python
elif command_type == 'get_distance_movement_action':
    action_map = {'0': 'Automaticamente ativado após entrar no modo DEFENSE (quando a ignição é desligada)', 
               '1': 'Envia um alerta - Apenas uma vez independente da IGN on ou off', 
               '2': 'Envia um alerta uma vez e bloqueia o veículo - Apenas uma vez independente da IGN on ou off'}
    action_value = match.group(1)
    parsed_values['distance_movement_action'] = action_map.get(action_value, action_value)
```

## 4. Update `services/lt32pro_command_formatter.py`

The `services/lt32pro_command_formatter.py` file is responsible for formatting the commands before they are sent to the device. If the new parameter uses a `CXCS` read command, you need to add it to the `READ_COMMAND_MAPPINGS` dictionary.

**Example:**

```python
'MOVEALMFUN': 'CXCS#MOVEALMFUN',
```

## 5. Update `ui/parameters_frame.py`

The `ui/parameters_frame.py` file is responsible for creating and managing the UI elements for the parameters. You need to add the new parameter to the `_get_ui_parameter_mapping` method to map the parameter to the UI.

**Example:**

```python
'distance_movement_action': {'section': 'movement_alerts', 'parameter': 'distance_movement_action'},
```

## 6. Update `services/device_command_mapper.py`

The `services/device_command_mapper.py` file is responsible for generating the bulk write commands. You need to add the new parameter to the `individual_params` list in the `get_bulk_commands` method.

**Example:**

```python
'distance_movement_action'
```

You also need to add a new method to format the command and add it to the `individual_mapping` dictionary in the `_generate_individual_command` method.

**Example:**

```python
def format_distance_movement_action_command(self, value: str) -> str:
    """Format distance movement action configuration command."""
    # Map distance movement action to command value
    distance_movement_action_mapping = {
        'Automaticamente ativado após entrar no modo DEFENSE (quando a ignição é desligada)': '0',
        'Envia um alerta - Apenas uma vez independente da IGN on ou off': '1',
        'Envia um alerta uma vez e bloqueia o veículo - Apenas uma vez independente da IGN on ou off': '2'
    }
    
    value_code = distance_movement_action_mapping.get(value, '0')
    command = f"ATSMS:SZCS#MOVEALMFUN={value_code}"
    
    if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
        try:
            self.command_validation_gateway.validate_command(command, source="bulk_commands")
        except ValueError as e:
            raise ValueError(f"Distance movement action command validation failed: {str(e)}")
    return command

'distance_movement_action': lambda v: self.format_distance_movement_action_command(v)
```

## 7. Update `services/parameter_specification_factory.py`

The `services/parameter_specification_factory.py` file is responsible for creating the UI elements and handling the individual send button actions. You need to add a new `_send_*_command` method and call it from `_send_parameter_command`.

**Example:**

```python
def _send_distance_movement_action_command(self, values: dict):
    """Send distance movement action configuration command"""
    distance_movement_action = str(values.get('distance_movement_action', '')).strip()
    
    # Map distance movement action to command value
    distance_movement_action_mapping = {
        'Automaticamente ativado após entrar no modo DEFENSE (quando a ignição é desligada)': '0',
        'Envia um alerta - Apenas uma vez independente da IGN on ou off': '1',
        'Envia um alerta uma vez e bloqueia o veículo - Apenas uma vez independente da IGN on ou off': '2'
    }
    
    value = distance_movement_action_mapping.get(distance_movement_action, '0')
    command = f"ATSMS:SZCS#MOVEALMFUN={value}"
    
    self.serial_service.send_command(command, command_type='distance_movement_action')
    messagebox.showinfo(
        self.i18n_service.get("success", "Success"),
        self.i18n_service.get("distance_movement_action_sent", "Distance movement action configuration sent to device")
    )

elif param_name == 'distance_movement_action':
    self._send_distance_movement_action_command(param_values)
```

## Conclusion

By following these steps, you can successfully add a new parameter to the LT32Pro Configurator application. It is important to pay attention to the details and ensure that the new parameter is correctly integrated into all the relevant files.
