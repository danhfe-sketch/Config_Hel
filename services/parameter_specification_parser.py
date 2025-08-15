"""
Parameter Specification Parser for the LT32 PRO Universal Profile System.

This module provides functionality to parse the Parameter UI List markdown file
and extract parameter specifications, commands, and validation rules.
"""

import re
from typing import Dict, List, Optional, Any
from pathlib import Path

from models.parameter_spec import ParameterSpec, ParameterField, ParameterCommands, UIElementType
from models.validation_result import ValidationResult
from utils.helpers import resource_path


class ParameterSpecificationParser:
    """
    Parser for the Parameter UI List markdown file.
    
    This class parses the structured markdown format and extracts parameter
    specifications including fields, commands, and validation rules.
    """
    
    def __init__(self, parameter_ui_list_path: str):
        """
        Initialize the parser with the path to the Parameter UI List file.
        
        Args:
            parameter_ui_list_path: Path to the Parameter UI List markdown file
        """
        # Use resource_path to handle PyInstaller bundled resources
        resolved_path = resource_path(parameter_ui_list_path)
        self.parameter_ui_list_path = Path(resolved_path)
        self._specifications: Optional[Dict[str, ParameterSpec]] = None
        self._sections: Optional[Dict[str, List[str]]] = None
    
    def parse_specifications(self) -> Dict[str, ParameterSpec]:
        """
        Parse all parameter specifications from the markdown file.
        
        Returns:
            Dict[str, ParameterSpec]: Dictionary mapping parameter names to specifications
            
        Raises:
            FileNotFoundError: If the parameter UI list file doesn't exist
            ValueError: If the file format is invalid
        """
        if self._specifications is not None:
            return self._specifications
        
        if not self.parameter_ui_list_path.exists():
            raise FileNotFoundError(f"Parameter UI List file not found: {self.parameter_ui_list_path}")
        
        try:
            with open(self.parameter_ui_list_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except Exception as e:
            raise ValueError(f"Failed to read Parameter UI List file: {e}")
        
        self._specifications = {}
        self._sections = {}
        
        # Parse sections and configurations
        current_section = None
        current_config = None
        current_config_data = {}
        
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments
            if not line:
                i += 1
                continue
                
            if line.startswith('## Section:'):
                # Save current config before switching sections
                if current_config and current_config_data:
                    spec = self._parse_config_data(current_config_data, current_section or "Unknown")
                    if spec:
                        self._specifications[spec.name] = spec
                        if current_section:
                            self._sections[current_section].append(spec.name)
                    current_config = None
                    current_config_data = {}
                
                current_section = line.replace('## Section:', '').strip()
                if current_section not in self._sections:
                    self._sections[current_section] = []
                i += 1
                continue
            
            # Parse configuration blocks
            if line.startswith('### Config:'):
                # Save previous config if exists
                if current_config and current_config_data:
                    spec = self._parse_config_data(current_config_data, current_section or "Unknown")
                    if spec:
                        self._specifications[spec.name] = spec
                        if current_section:
                            self._sections[current_section].append(spec.name)
                
                # Start new config
                current_config = line.replace('### Config:', '').strip()
                current_config_data = {'title': current_config}
                i += 1
                continue
            
            # Parse config content
            if current_config:
                i = self._parse_config_content(lines, i, current_config_data)
            else:
                i += 1
        
        # Don't forget the last config
        if current_config and current_config_data:
            spec = self._parse_config_data(current_config_data, current_section or "Unknown")
            if spec:
                self._specifications[spec.name] = spec
                if current_section:
                    self._sections[current_section].append(spec.name)
        
        return self._specifications
    
    def _parse_config_content(self, lines: List[str], start_index: int, config_data: Dict[str, Any]) -> int:
        """
        Parse the content of a configuration block.
        
        Args:
            lines: All lines from the file
            start_index: Starting index for parsing
            config_data: Dictionary to store parsed data
            
        Returns:
            int: Next index to continue parsing from
        """
        i = start_index
        current_field = None
        current_field_data = {}
        in_fields_section = False
        in_commands_section = False
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Stop at next section or config
            if line.startswith('##') or line.startswith('### Config:'):
                break
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Parse bullet points (handle both * and indented content)
            if line.startswith('*') or (in_fields_section and line.startswith('    *')) or (in_commands_section and line.startswith('    *')):
                # Check for main sections
                if '**fields:**' in line:
                    in_fields_section = True
                    in_commands_section = False
                    config_data['fields'] = []
                    current_field = None
                    current_field_data = {}
                elif '**commands:**' in line:
                    in_commands_section = True
                    in_fields_section = False
                    config_data['commands'] = {}
                    # Save any pending field
                    if current_field and current_field_data:
                        config_data['fields'].append(current_field_data.copy())
                        current_field = None
                        current_field_data = {}
                elif '**field_' in line and line.strip().endswith(':**') and in_fields_section:
                    # Save previous field if exists
                    if current_field and current_field_data:
                        config_data['fields'].append(current_field_data.copy())
                    
                    # Start new field
                    current_field = self._extract_field_number(line)
                    current_field_data = {}
                elif ('**set' in line or '**read' in line) and in_commands_section:
                    # Parse command
                    command_type, command_value = self._parse_command(line)
                    if command_type and command_value:
                        config_data['commands'][command_type] = command_value
                elif in_fields_section and current_field is not None:
                    # Parse field properties (handle indented content)
                    if '**name:**' in line:
                        current_field_data['name'] = self._extract_value(line)
                    elif '**label:**' in line:
                        current_field_data['label'] = self._extract_value(line)
                    elif '**ui_element:**' in line:
                        current_field_data['ui_element'] = self._extract_value(line)
                    elif '**validation:**' in line:
                        current_field_data['validation'] = self._extract_value(line)
                    elif '**unit:**' in line:
                        current_field_data['unit'] = self._extract_value(line)
                    elif '**options:**' in line:
                        current_field_data['options'] = self._parse_options(line)
                    elif '**visibility_condition:**' in line:
                        current_field_data['visibility_condition'] = self._extract_value(line)
                elif not in_fields_section and not in_commands_section:
                    # Handle main config properties (not in fields or commands section)
                    if '**name:**' in line:
                        config_data['name'] = self._extract_value(line)
                    elif '**label:**' in line:
                        config_data['label'] = self._extract_value(line)
                    elif '**description:**' in line:
                        config_data['description'] = self._extract_value(line)
                    elif '**ui_element:**' in line:
                        config_data['ui_element'] = self._extract_value(line)
                    elif '**validation:**' in line:
                        config_data['validation'] = self._extract_value(line)
                    elif '**unit:**' in line:
                        config_data['unit'] = self._extract_value(line)
                    elif '**options:**' in line:
                        config_data['options'] = self._parse_options(line)
                    elif '**visibility_condition:**' in line:
                        config_data['visibility_condition'] = self._extract_value(line)
            
            i += 1
        
        # Don't forget the last field
        if current_field and current_field_data and in_fields_section:
            if 'fields' not in config_data:
                config_data['fields'] = []
            config_data['fields'].append(current_field_data)
        
        return i
    
    def _extract_value(self, line: str) -> str:
        """Extract value from a markdown line."""
        # Remove markdown formatting and extract the value
        line = re.sub(r'\*\*[^*]+:\*\*', '', line)  # Remove **key:** part
        line = line.strip('* ').strip()
        # Remove quotes if present
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        return line
    
    def _parse_options(self, line: str) -> List[str]:
        """Parse options from a markdown line."""
        # Extract the array part
        match = re.search(r'\[(.*?)\]', line)
        if match:
            options_str = match.group(1)
            # Split by comma and clean up
            options = [opt.strip().strip('"') for opt in options_str.split(',')]
            return options
        return []
    
    def _extract_field_number(self, line: str) -> str:
        """Extract field number from field definition line."""
        match = re.search(r'\*\*field_(\d+):\*\*', line)
        return match.group(1) if match else None
    
    def _parse_command(self, line: str) -> tuple[Optional[str], Optional[str]]:
        """Parse command from a markdown line."""
        # Extract command type and value
        match = re.search(r'\*\*([^*]+):\*\*\s*`([^`]+)`', line)
        if match:
            command_type = match.group(1).strip()
            command_value = match.group(2).strip()
            return command_type, command_value
        return None, None
    
    def _parse_config_data(self, config_data: Dict[str, Any], section: str) -> Optional[ParameterSpec]:
        """
        Convert parsed config data into a ParameterSpec object.
        
        Args:
            config_data: Raw parsed configuration data
            section: Section name this config belongs to
            
        Returns:
            Optional[ParameterSpec]: Created parameter specification or None if invalid
        """
        if 'name' not in config_data:
            return None
        
        # Parse UI element type
        ui_element = None
        if 'ui_element' in config_data:
            try:
                ui_element = UIElementType(config_data['ui_element'])
            except ValueError:
                # Unknown UI element type, keep as None
                pass
        
        # Parse fields
        fields = None
        if 'fields' in config_data and config_data['fields']:
            fields = []
            for field_data in config_data['fields']:
                field = self._create_parameter_field(field_data)
                if field:
                    fields.append(field)
        
        # Parse commands
        commands = ParameterCommands()
        if 'commands' in config_data:
            cmd_data = config_data['commands']
            commands.set_command = cmd_data.get('set')
            commands.read_command = cmd_data.get('read')
            commands.set_physical = cmd_data.get('set_physical')
            commands.set_accelerometer = cmd_data.get('set_accelerometer')
            commands.set_battery = cmd_data.get('set_battery')
            commands.set_level = cmd_data.get('set_level')
            commands.read_level = cmd_data.get('read_level')
        
        return ParameterSpec(
            name=config_data['name'],
            label=config_data.get('label', config_data['name']),
            section=section,
            description=config_data.get('description'),
            ui_element=ui_element,
            validation=config_data.get('validation'),
            unit=config_data.get('unit'),
            options=config_data.get('options'),
            visibility_condition=config_data.get('visibility_condition'),
            commands=commands,
            fields=fields
        )
    
    def _create_parameter_field(self, field_data: Dict[str, Any]) -> Optional[ParameterField]:
        """
        Create a ParameterField from parsed field data.
        
        Args:
            field_data: Raw parsed field data
            
        Returns:
            Optional[ParameterField]: Created field or None if invalid
        """
        if 'name' not in field_data or 'label' not in field_data:
            return None
        
        # Parse UI element type
        ui_element = UIElementType.TEXT_INPUT  # Default
        if 'ui_element' in field_data:
            try:
                ui_element = UIElementType(field_data['ui_element'])
            except ValueError:
                # Keep default if unknown type
                pass
        
        return ParameterField(
            name=field_data['name'],
            label=field_data['label'],
            ui_element=ui_element,
            validation=field_data.get('validation'),
            unit=field_data.get('unit'),
            options=field_data.get('options'),
            visibility_condition=field_data.get('visibility_condition')
        )
    
    def get_parameter_spec(self, parameter_name: str) -> Optional[ParameterSpec]:
        """
        Get a specific parameter specification by name.
        
        Args:
            parameter_name: Name of the parameter to retrieve
            
        Returns:
            Optional[ParameterSpec]: Parameter specification or None if not found
        """
        specs = self.parse_specifications()
        return specs.get(parameter_name)
    
    def get_all_parameters(self) -> List[str]:
        """
        Get a list of all parameter names.
        
        Returns:
            List[str]: List of all parameter names
        """
        specs = self.parse_specifications()
        return list(specs.keys())
    
    def get_parameters_by_section(self, section: str) -> List[ParameterSpec]:
        """
        Get all parameters in a specific section.
        
        Args:
            section: Section name to filter by
            
        Returns:
            List[ParameterSpec]: List of parameter specifications in the section
        """
        specs = self.parse_specifications()
        return [spec for spec in specs.values() if spec.section == section]
    
    def get_all_sections(self) -> List[str]:
        """
        Get a list of all section names.
        
        Returns:
            List[str]: List of all section names
        """
        self.parse_specifications()  # Ensure sections are parsed
        return list(self._sections.keys()) if self._sections else []
    
    def validate_parameter_value(self, param_name: str, value: Any) -> ValidationResult:
        """
        Validate a parameter value against its specification.
        
        Args:
            param_name: Name of the parameter
            value: Value to validate
            
        Returns:
            ValidationResult: Result of the validation
        """
        spec = self.get_parameter_spec(param_name)
        if not spec:
            return ValidationResult(
                is_valid=False,
                errors=[f"Parameter '{param_name}' not found in specifications"]
            )
        
        return spec.validate_value(value)
    
    def get_parameter_default_value(self, param_name: str) -> Any:
        """
        Get the default value for a parameter.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            Any: Default value or None if parameter not found
        """
        spec = self.get_parameter_spec(param_name)
        return spec.get_default_value() if spec else None
    
    def is_parameter_visible(self, param_name: str, context: Dict[str, Any]) -> bool:
        """
        Check if a parameter should be visible given the current context.
        
        Args:
            param_name: Name of the parameter
            context: Dictionary of current parameter values
            
        Returns:
            bool: True if parameter should be visible
        """
        spec = self.get_parameter_spec(param_name)
        return spec.is_visible(context) if spec else True
    
    def get_visible_fields(self, param_name: str, context: Dict[str, Any]) -> List[ParameterField]:
        """
        Get the visible fields for a parameter given the current context.
        
        Args:
            param_name: Name of the parameter
            context: Dictionary of current field values
            
        Returns:
            List[ParameterField]: List of visible fields
        """
        spec = self.get_parameter_spec(param_name)
        return spec.get_visible_fields(context) if spec else []