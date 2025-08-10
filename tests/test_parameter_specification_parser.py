"""
Unit tests for the Parameter Specification Parser.

This module contains comprehensive tests for parsing the Parameter UI List
markdown file and extracting parameter specifications.
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Dict, Any

from services.parameter_specification_parser import ParameterSpecificationParser
from models.parameter_spec import ParameterSpec, ParameterField, UIElementType
from models.validation_result import ValidationResult


class TestParameterSpecificationParser:
    """Test cases for the ParameterSpecificationParser class."""
    
    @pytest.fixture
    def sample_markdown_content(self) -> str:
        """Sample markdown content for testing."""
        return """# AI Input: UI and Command Specification for LT32 PRO

## Section: Network Parameters

### Config: APN Settings

*   **name:** apn_settings
*   **label:** "Configuração APN"
*   **description:** "Configures the APN, username, and password for the mobile network."
*   **fields:**
    *   **field_1:**
        *   **name:** apn
        *   **label:** "APN"
        *   **ui_element:** "text_input"
        *   **validation:** "Accepts a standard APN name, an IP address, or a URL."
    *   **field_2:**
        *   **name:** user
        *   **label:** "Usuário"
        *   **ui_element:** "text_input"
    *   **field_3:**
        *   **name:** password
        *   **label:** "Senha"
        *   **ui_element:** "text_input"
*   **commands:**
    *   **set:** `APN,<apn>,<user>,<password>#`
    *   **read:** `APN#`

### Config: Protocol

*   **name:** protocol
*   **label:** "Tipo de protocolo"
*   **ui_element:** "dropdown"
*   **options:** ["GT06 (0x60)", "CRX3 (0x22)", "CRX (0x12)"]
*   **commands:**
    *   **set:** `SZCS#GT06SEL=X`
    *   **read:** `CXCS#GT06SEL`

## Section: Time Parameters

### Config: Report Intervals

*   **name:** report_intervals
*   **label:** "Intervalos de Envio"
*   **description:** "Defines the time intervals for sending position data based on ignition status."
*   **fields:**
    *   **field_1:**
        *   **name:** moving_time
        *   **label:** "Tempo em movimento (Ignição ligada)"
        *   **ui_element:** "number_input"
        *   **unit:** "seconds"
    *   **field_2:**
        *   **name:** stopped_time
        *   **label:** "Tempo parado (Ignição desligada)"
        *   **ui_element:** "number_input"
        *   **unit:** "seconds"
*   **commands:**
    *   **set:** `TIMER,<moving_time>,<stopped_time>#`
    *   **read:** `TIMER#`

## Section: Ignition

### Config: Ignition Type

*   **name:** ignition_type
*   **label:** "Tipo de ignição"
*   **description:** "Configures the method for detecting ignition status."
*   **fields:**
    *   **field_1:**
        *   **name:** ignition_mode
        *   **label:** "Modo de Ignição"
        *   **ui_element:** "dropdown"
        *   **options:** ["Física (Physical)", "Virtual por acelerômetro (Virtual by accelerometer)", "Virtual por bateria (Virtual by battery)"]
    *   **field_2:**
        *   **name:** on_voltage
        *   **label:** "Tensão para Ligar (ON)"
        *   **ui_element:** "number_input"
        *   **unit:** "V"
        *   **visibility_condition:** "ignition_mode == 'Virtual por bateria (Virtual by battery)'"
    *   **field_3:**
        *   **name:** off_voltage
        *   **label:** "Tensão para Desligar (OFF)"
        *   **ui_element:** "number_input"
        *   **unit:** "V"
        *   **visibility_condition:** "ignition_mode == 'Virtual por bateria (Virtual by battery)'"
*   **commands:**
    *   **set_physical:** `SZCS#ACCLINE=1#ACC_CFG=0-000-000`
    *   **set_accelerometer:** `SZCS#ACCLINE=0#ACC_CFG=0-000-000`
    *   **set_battery:** `SZCS#ACCLINE=1#ACC_CFG=1-<on_voltage>-<off_voltage>`
    *   **read:** `CXCS#ACCLINE#ACC_CFG`

## Section: Speed

### Config: Speed Alert

*   **name:** speed_alert
*   **label:** "Alerta de Velocidade"
*   **description:** "Configures the over-speed alert."
*   **fields:**
    *   **field_1:**
        *   **name:** enabled
        *   **label:** "Habilitar Alerta de limite de velocidade"
        *   **ui_element:** "toggle_switch"
    *   **field_2:**
        *   **name:** detection_time
        *   **label:** "Tempo para detectar (s)"
        *   **ui_element:** "number_input"
        *   **validation:** "5-600"
    *   **field_3:**
        *   **name:** speed_limit
        *   **label:** "Velocidade (km/h)"
        *   **ui_element:** "number_input"
        *   **validation:** "1-255"
    *   **field_4:**
        *   **name:** alert_type
        *   **label:** "Tipo de Alerta"
        *   **ui_element:** "dropdown"
        *   **options:** ["Apenas GPRS", "GPRS+SMS"]
*   **commands:**
    *   **set:** `SPEED,<enabled>,<detection_time>,<speed_limit>,<alert_type>#`
    *   **read:** `SPEED#`

### Config: Sleep Mode

*   **name:** sleep_mode
*   **label:** "Modo Sleep"
*   **ui_element:** "dropdown"
*   **options:** ["Desabilitado (Disabled)", "Sleep (Habilitado)", "Deep Sleep (Ultra-baixo)"]
*   **commands:**
    *   **set:** `SZCS#SLPDISCONNECT=A`
    *   **read:** `CXCS#SLPDISCONNECT`
"""
    
    @pytest.fixture
    def temp_markdown_file(self, sample_markdown_content: str) -> str:
        """Create a temporary markdown file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(sample_markdown_content)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def parser(self, temp_markdown_file: str) -> ParameterSpecificationParser:
        """Create a parser instance with the temporary file."""
        return ParameterSpecificationParser(temp_markdown_file)
    
    def test_parser_initialization(self, temp_markdown_file: str):
        """Test parser initialization."""
        parser = ParameterSpecificationParser(temp_markdown_file)
        assert parser.parameter_ui_list_path == Path(temp_markdown_file)
        assert parser._specifications is None
        assert parser._sections is None
    
    def test_file_not_found_error(self):
        """Test error handling when file doesn't exist."""
        parser = ParameterSpecificationParser("nonexistent_file.md")
        
        with pytest.raises(FileNotFoundError):
            parser.parse_specifications()
    
    def test_parse_specifications_basic(self, parser: ParameterSpecificationParser):
        """Test basic parsing of specifications."""
        specs = parser.parse_specifications()
        
        # Should have parsed all configurations
        expected_params = [
            'apn_settings', 'protocol', 'report_intervals', 
            'ignition_type', 'speed_alert', 'sleep_mode'
        ]
        
        assert len(specs) == len(expected_params)
        for param_name in expected_params:
            assert param_name in specs
            assert isinstance(specs[param_name], ParameterSpec)
    
    def test_parse_simple_parameter(self, parser: ParameterSpecificationParser):
        """Test parsing of simple parameters (no fields)."""
        specs = parser.parse_specifications()
        
        # Test protocol parameter
        protocol_spec = specs['protocol']
        assert protocol_spec.name == 'protocol'
        assert protocol_spec.label == 'Tipo de protocolo'
        assert protocol_spec.ui_element == UIElementType.DROPDOWN
        assert protocol_spec.options == ["GT06 (0x60)", "CRX3 (0x22)", "CRX (0x12)"]
        assert protocol_spec.fields is None
        assert protocol_spec.commands.set_command == 'SZCS#GT06SEL=X'
        assert protocol_spec.commands.read_command == 'CXCS#GT06SEL'
    
    def test_parse_complex_parameter_with_fields(self, parser: ParameterSpecificationParser):
        """Test parsing of complex parameters with multiple fields."""
        specs = parser.parse_specifications()
        
        # Test APN settings parameter
        apn_spec = specs['apn_settings']
        assert apn_spec.name == 'apn_settings'
        assert apn_spec.label == 'Configuração APN'
        assert apn_spec.description == 'Configures the APN, username, and password for the mobile network.'
        assert apn_spec.fields is not None
        assert len(apn_spec.fields) == 3
        
        # Check individual fields
        apn_field = apn_spec.fields[0]
        assert apn_field.name == 'apn'
        assert apn_field.label == 'APN'
        assert apn_field.ui_element == UIElementType.TEXT_INPUT
        assert apn_field.validation == 'Accepts a standard APN name, an IP address, or a URL.'
        
        user_field = apn_spec.fields[1]
        assert user_field.name == 'user'
        assert user_field.label == 'Usuário'
        assert user_field.ui_element == UIElementType.TEXT_INPUT
        
        password_field = apn_spec.fields[2]
        assert password_field.name == 'password'
        assert password_field.label == 'Senha'
        assert password_field.ui_element == UIElementType.TEXT_INPUT
    
    def test_parse_parameter_with_validation(self, parser: ParameterSpecificationParser):
        """Test parsing of parameters with validation rules."""
        specs = parser.parse_specifications()
        
        # Test speed alert parameter
        speed_spec = specs['speed_alert']
        assert speed_spec.fields is not None
        
        # Find detection_time field
        detection_field = next(f for f in speed_spec.fields if f.name == 'detection_time')
        assert detection_field.validation == '5-600'
        
        # Find speed_limit field
        speed_field = next(f for f in speed_spec.fields if f.name == 'speed_limit')
        assert speed_field.validation == '1-255'
    
    def test_parse_parameter_with_visibility_conditions(self, parser: ParameterSpecificationParser):
        """Test parsing of parameters with visibility conditions."""
        specs = parser.parse_specifications()
        
        # Test ignition type parameter
        ignition_spec = specs['ignition_type']
        assert ignition_spec.fields is not None
        
        # Find voltage fields with visibility conditions
        on_voltage_field = next(f for f in ignition_spec.fields if f.name == 'on_voltage')
        assert on_voltage_field.visibility_condition == "ignition_mode == 'Virtual por bateria (Virtual by battery)'"
        
        off_voltage_field = next(f for f in ignition_spec.fields if f.name == 'off_voltage')
        assert off_voltage_field.visibility_condition == "ignition_mode == 'Virtual por bateria (Virtual by battery)'"
    
    def test_parse_parameter_with_multiple_commands(self, parser: ParameterSpecificationParser):
        """Test parsing of parameters with multiple command types."""
        specs = parser.parse_specifications()
        
        # Test ignition type parameter
        ignition_spec = specs['ignition_type']
        commands = ignition_spec.commands
        
        assert commands.set_physical == 'SZCS#ACCLINE=1#ACC_CFG=0-000-000'
        assert commands.set_accelerometer == 'SZCS#ACCLINE=0#ACC_CFG=0-000-000'
        assert commands.set_battery == 'SZCS#ACCLINE=1#ACC_CFG=1-<on_voltage>-<off_voltage>'
        assert commands.read_command == 'CXCS#ACCLINE#ACC_CFG'
    
    def test_parse_parameter_with_units(self, parser: ParameterSpecificationParser):
        """Test parsing of parameters with units."""
        specs = parser.parse_specifications()
        
        # Test report intervals parameter
        report_spec = specs['report_intervals']
        assert report_spec.fields is not None
        
        for field in report_spec.fields:
            assert field.unit == 'seconds'
    
    def test_get_parameter_spec(self, parser: ParameterSpecificationParser):
        """Test getting a specific parameter specification."""
        # Test existing parameter
        spec = parser.get_parameter_spec('protocol')
        assert spec is not None
        assert spec.name == 'protocol'
        
        # Test non-existing parameter
        spec = parser.get_parameter_spec('nonexistent')
        assert spec is None
    
    def test_get_all_parameters(self, parser: ParameterSpecificationParser):
        """Test getting all parameter names."""
        params = parser.get_all_parameters()
        
        expected_params = [
            'apn_settings', 'protocol', 'report_intervals', 
            'ignition_type', 'speed_alert', 'sleep_mode'
        ]
        
        assert len(params) == len(expected_params)
        for param in expected_params:
            assert param in params
    
    def test_get_parameters_by_section(self, parser: ParameterSpecificationParser):
        """Test getting parameters by section."""
        network_params = parser.get_parameters_by_section('Network Parameters')
        assert len(network_params) == 2
        
        param_names = [p.name for p in network_params]
        assert 'apn_settings' in param_names
        assert 'protocol' in param_names
        
        time_params = parser.get_parameters_by_section('Time Parameters')
        assert len(time_params) == 1
        assert time_params[0].name == 'report_intervals'
    
    def test_get_all_sections(self, parser: ParameterSpecificationParser):
        """Test getting all section names."""
        sections = parser.get_all_sections()
        
        expected_sections = [
            'Network Parameters', 'Time Parameters', 
            'Ignition', 'Speed'
        ]
        
        for section in expected_sections:
            assert section in sections
    
    def test_validate_parameter_value_simple(self, parser: ParameterSpecificationParser):
        """Test parameter value validation for simple parameters."""
        # Test valid dropdown value
        result = parser.validate_parameter_value('protocol', 'GT06 (0x60)')
        assert result.is_valid
        assert len(result.errors) == 0
        
        # Test invalid dropdown value
        result = parser.validate_parameter_value('protocol', 'Invalid Protocol')
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_validate_parameter_value_complex(self, parser: ParameterSpecificationParser):
        """Test parameter value validation for complex parameters."""
        # Test valid complex parameter
        apn_value = {
            'apn': 'internet.provider.com',
            'user': 'testuser',
            'password': 'testpass'
        }
        result = parser.validate_parameter_value('apn_settings', apn_value)
        assert result.is_valid
        
        # Test invalid complex parameter (not a dict)
        result = parser.validate_parameter_value('apn_settings', 'invalid_value')
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_validate_parameter_value_with_numeric_validation(self, parser: ParameterSpecificationParser):
        """Test parameter value validation with numeric ranges."""
        # Test valid numeric value within range
        speed_value = {
            'enabled': True,
            'detection_time': 30,  # Should be valid (5-600)
            'speed_limit': 100,    # Should be valid (1-255)
            'alert_type': 'Apenas GPRS'
        }
        result = parser.validate_parameter_value('speed_alert', speed_value)
        assert result.is_valid
        
        # Test invalid numeric value outside range
        speed_value_invalid = {
            'enabled': True,
            'detection_time': 1000,  # Should be invalid (5-600)
            'speed_limit': 300,      # Should be invalid (1-255)
            'alert_type': 'Apenas GPRS'
        }
        result = parser.validate_parameter_value('speed_alert', speed_value_invalid)
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_validate_nonexistent_parameter(self, parser: ParameterSpecificationParser):
        """Test validation of non-existent parameter."""
        result = parser.validate_parameter_value('nonexistent_param', 'value')
        assert not result.is_valid
        assert 'not found in specifications' in result.errors[0]
    
    def test_get_parameter_default_value(self, parser: ParameterSpecificationParser):
        """Test getting default values for parameters."""
        # Test simple parameter default
        default = parser.get_parameter_default_value('protocol')
        assert default == 'GT06 (0x60)'  # First option in dropdown
        
        # Test complex parameter default
        default = parser.get_parameter_default_value('apn_settings')
        assert isinstance(default, dict)
        assert 'apn' in default
        assert 'user' in default
        assert 'password' in default
        
        # Test non-existent parameter
        default = parser.get_parameter_default_value('nonexistent')
        assert default is None
    
    def test_is_parameter_visible(self, parser: ParameterSpecificationParser):
        """Test parameter visibility checking."""
        # Test parameter without visibility condition
        visible = parser.is_parameter_visible('protocol', {})
        assert visible
        
        # Test parameter with visibility condition (ignition voltage fields)
        context = {'ignition_mode': 'Virtual por bateria (Virtual by battery)'}
        visible = parser.is_parameter_visible('ignition_type', context)
        assert visible  # The parameter itself should be visible
    
    def test_get_visible_fields(self, parser: ParameterSpecificationParser):
        """Test getting visible fields based on context."""
        # Test with context that makes voltage fields visible
        context = {'ignition_mode': 'Virtual por bateria (Virtual by battery)'}
        visible_fields = parser.get_visible_fields('ignition_type', context)
        
        field_names = [f.name for f in visible_fields]
        assert 'ignition_mode' in field_names
        assert 'on_voltage' in field_names
        assert 'off_voltage' in field_names
        
        # Test with context that hides voltage fields
        context = {'ignition_mode': 'Física (Physical)'}
        visible_fields = parser.get_visible_fields('ignition_type', context)
        
        field_names = [f.name for f in visible_fields]
        assert 'ignition_mode' in field_names
        assert 'on_voltage' not in field_names
        assert 'off_voltage' not in field_names
    
    def test_caching_behavior(self, parser: ParameterSpecificationParser):
        """Test that specifications are cached after first parse."""
        # First call should parse the file
        specs1 = parser.parse_specifications()
        
        # Second call should return cached results
        specs2 = parser.parse_specifications()
        
        # Should be the same object (cached)
        assert specs1 is specs2
    
    def test_malformed_markdown_handling(self):
        """Test handling of malformed markdown content."""
        malformed_content = """# Malformed Content
        
## Section: Test

### Config: Broken Config
* **name:** broken_config
* **label:** "Broken Config"
* **fields:**
    * **field_1:**
        * **name:** field1
        # Missing closing field definition
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(malformed_content)
            temp_path = f.name
        
        try:
            parser = ParameterSpecificationParser(temp_path)
            specs = parser.parse_specifications()
            
            # Should still parse what it can
            assert 'broken_config' in specs
            spec = specs['broken_config']
            assert spec.name == 'broken_config'
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_empty_file_handling(self):
        """Test handling of empty markdown file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("")
            temp_path = f.name
        
        try:
            parser = ParameterSpecificationParser(temp_path)
            specs = parser.parse_specifications()
            
            # Should return empty dict for empty file
            assert len(specs) == 0
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_ui_element_type_conversion(self, parser: ParameterSpecificationParser):
        """Test conversion of UI element type strings to enums."""
        specs = parser.parse_specifications()
        
        # Test various UI element types
        protocol_spec = specs['protocol']
        assert protocol_spec.ui_element == UIElementType.DROPDOWN
        
        apn_spec = specs['apn_settings']
        apn_field = apn_spec.fields[0]
        assert apn_field.ui_element == UIElementType.TEXT_INPUT
        
        speed_spec = specs['speed_alert']
        enabled_field = next(f for f in speed_spec.fields if f.name == 'enabled')
        assert enabled_field.ui_element == UIElementType.TOGGLE_SWITCH
        
        detection_field = next(f for f in speed_spec.fields if f.name == 'detection_time')
        assert detection_field.ui_element == UIElementType.NUMBER_INPUT


if __name__ == '__main__':
    pytest.main([__file__])