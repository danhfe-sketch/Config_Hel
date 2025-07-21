#!/usr/bin/env python3
"""
Test script to verify the parameter groups reorganization.

This script tests that:
1. Main Server group only contains URL/IP and Port
2. Protocol group contains GT06 protocol and TCP+ACK configuration
3. All groups are properly created and accessible
"""

import sys
import os
from unittest.mock import Mock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.i18n_service import I18nService
from ui.parameter_factory import ParameterFactory
from services.validation_service import ValidationService


def test_parameter_groups_reorganization():
    """Test the parameter groups reorganization."""
    print("Testing parameter groups reorganization...")
    
    try:
        # Create services
        i18n_service = I18nService()
        i18n_service.set_language('en_US')
        validation_service = ValidationService(i18n_service)
        send_command_callback = Mock()
        
        # Create parameter factory
        parameter_factory = ParameterFactory(validation_service, i18n_service, send_command_callback)
        
        # Test get_all_groups includes the new protocol group
        all_groups = parameter_factory.get_all_groups()
        print(f"  ✓ All groups: {all_groups}")
        
        expected_groups = ['protocol', 'security', 'sensors', 'server', 'timers']
        for group in expected_groups:
            assert group in all_groups, f"Expected group '{group}' should be in groups list"
        
        print("  ✓ All expected groups found including new 'protocol' group")
        
        # Test server group parameters
        server_params = parameter_factory.get_parameters_by_group('server')
        print(f"  ✓ Server group parameters: {server_params}")
        
        expected_server_params = ['server_ip', 'server_port']
        assert set(server_params) == set(expected_server_params), f"Server group should only contain {expected_server_params}, got {server_params}"
        
        print("  ✓ Server group correctly contains only URL/IP and Port")
        
        # Test protocol group parameters
        protocol_params = parameter_factory.get_parameters_by_group('protocol')
        print(f"  ✓ Protocol group parameters: {protocol_params}")
        
        expected_protocol_params = ['gt06_protocol', 'tcp_ack_config']
        assert set(protocol_params) == set(expected_protocol_params), f"Protocol group should contain {expected_protocol_params}, got {protocol_params}"
        
        print("  ✓ Protocol group correctly contains GT06 protocol and TCP+ACK config")
        
        # Test parameter definitions
        gt06_param_def = parameter_factory.get_parameter_definition('gt06_protocol')
        assert gt06_param_def is not None, "GT06 protocol parameter definition should exist"
        assert gt06_param_def.group == 'protocol', f"GT06 protocol should be in 'protocol' group, got '{gt06_param_def.group}'"
        
        tcp_ack_param_def = parameter_factory.get_parameter_definition('tcp_ack_config')
        assert tcp_ack_param_def is not None, "TCP ACK parameter definition should exist"
        assert tcp_ack_param_def.group == 'protocol', f"TCP ACK should be in 'protocol' group, got '{tcp_ack_param_def.group}'"
        assert tcp_ack_param_def.param_type == 'radio', f"TCP ACK should be radio type, got '{tcp_ack_param_def.param_type}'"
        
        print("  ✓ Parameter definitions correctly configured")
        
        # Test creating actual parameter objects
        gt06_param = parameter_factory.create_parameter('gt06_protocol')
        tcp_ack_param = parameter_factory.create_parameter('tcp_ack_config')
        
        assert gt06_param is not None, "Should be able to create GT06 protocol parameter"
        assert tcp_ack_param is not None, "Should be able to create TCP ACK parameter"
        
        print("  ✓ Parameter objects created successfully")
        
        # Test creating protocol group
        protocol_group = parameter_factory.create_group('protocol', 'protocol_configuration')
        assert protocol_group is not None, "Should be able to create protocol group"
        
        protocol_group.add_parameter(gt06_param)
        protocol_group.add_parameter(tcp_ack_param)
        
        assert len(protocol_group.parameters) == 2, f"Protocol group should have 2 parameters, got {len(protocol_group.parameters)}"
        
        print("  ✓ Protocol group created and populated successfully")
        
        print("✓ Parameter groups reorganization test passed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation_rules():
    """Test that validation rules are properly configured for new parameters."""
    print("Testing validation rules for new parameters...")
    
    try:
        # Create services
        i18n_service = I18nService()
        i18n_service.set_language('en_US')
        validation_service = ValidationService(i18n_service)
        
        # Test TCP ACK validation rules
        tcp_ack_rules = validation_service.validation_rules.get('tcp_ack_config')
        assert tcp_ack_rules is not None, "TCP ACK validation rules should exist"
        assert tcp_ack_rules['type'] == 'radio', "TCP ACK should be radio type"
        assert 'allowed_values' in tcp_ack_rules, "TCP ACK should have allowed values"
        
        expected_values = ['Enabled', 'Disabled']
        assert tcp_ack_rules['allowed_values'] == expected_values, f"TCP ACK should allow {expected_values}, got {tcp_ack_rules['allowed_values']}"
        
        print(f"  ✓ TCP ACK validation rules: {tcp_ack_rules}")
        
        # Test validation
        valid_result = validation_service.validate_parameter('tcp_ack_config', 'Enabled')
        assert valid_result.is_valid, "Should validate 'Enabled' as valid"
        
        invalid_result = validation_service.validate_parameter('tcp_ack_config', 'Invalid')
        assert not invalid_result.is_valid, "Should validate 'Invalid' as invalid"
        
        print("  ✓ TCP ACK parameter validation working correctly")
        
        print("✓ Validation rules test passed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_language_support():
    """Test that language translations exist for new parameters."""
    print("Testing language support for new parameters...")
    
    try:
        languages = [
            ('en_US', 'Configure TCP+ACK Response:', 'Protocol Configuration'),
            ('pt_BR', 'Configurar Resposta TCP+ACK:', 'Configuração de Protocolo'),
            ('es_ES', 'Configurar Respuesta TCP+ACK:', 'Configuración de Protocolo')
        ]
        
        for lang_code, expected_tcp_ack, expected_protocol_config in languages:
            i18n_service = I18nService()
            i18n_service.set_language(lang_code)
            
            # Test TCP ACK translation
            tcp_ack_text = i18n_service.get('tcp_ack_config')
            assert tcp_ack_text == expected_tcp_ack, f"TCP ACK translation for {lang_code} should be '{expected_tcp_ack}', got '{tcp_ack_text}'"
            
            # Test protocol configuration translation
            protocol_config_text = i18n_service.get('protocol_configuration')
            assert protocol_config_text == expected_protocol_config, f"Protocol config translation for {lang_code} should be '{expected_protocol_config}', got '{protocol_config_text}'"
            
            print(f"  ✓ {lang_code}: TCP ACK = '{tcp_ack_text}', Protocol Config = '{protocol_config_text}'")
        
        print("✓ Language support test passed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all parameter groups reorganization tests."""
    print("=" * 70)
    print("Parameter Groups Reorganization Tests")
    print("=" * 70)
    
    success1 = test_parameter_groups_reorganization()
    print()
    success2 = test_validation_rules()
    print()
    success3 = test_language_support()
    
    success = success1 and success2 and success3
    
    if success:
        print("\n" + "=" * 70)
        print("✅ Parameter groups reorganization verified successfully!")
        print("=" * 70)
        
        print("\nReorganization Summary:")
        print("• Main Server group: URL/IP + Port only")
        print("• New Protocol group: GT06 Protocol + TCP+ACK Configuration")
        print("• TCP+ACK parameter: Radio buttons (Enabled/Disabled)")
        print("• Multi-language support: English, Portuguese, Spanish")
        
        print("\nGroup Structure:")
        print("1. APN Configuration (existing)")
        print("2. Main Server (URL/IP, Port)")
        print("3. Protocol Configuration (GT06 Protocol, TCP+ACK)")
        print("4. Sensor Configuration (existing)")
        print("5. Timer Configuration (existing)")
        print("6. Security Settings (existing)")
        
        print("\nImplementation Details:")
        print("• Added 'tcp_ack_config' parameter with radio button type")
        print("• Moved 'gt06_protocol' from server to protocol group")
        print("• Added validation rules for TCP+ACK parameter")
        print("• Added translations for all supported languages")
        print("• Updated parameters frame to create protocol group")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)