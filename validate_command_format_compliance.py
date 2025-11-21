#!/usr/bin/env python3
"""
Command Format Compliance Validator

This script validates that all command templates in DeviceCommandMapper comply
with the Parameter UI List specification. It cross-references command formats,
parameter order, and values to ensure exact compliance.

Task: 10. Validate command format compliance with Parameter UI List
Requirements: 1.4, 4.1, 4.2
"""

import json
import sys
import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from services.device_command_mapper import DeviceCommandMapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class CommandFormatValidator:
    """Validates command format compliance with Parameter UI List specification."""
    
    def __init__(self):
        """Initialize the validator with expected command formats from Parameter UI List."""
        self.mapper = DeviceCommandMapper()
        
        # Expected command formats from Parameter UI List specification
        self.expected_formats = {
            # Network Parameters
            'apn_settings': {
                'set': 'APN,{apn},{user},{password}#',
                'read': 'APN#'
            },
            'server_settings': {
                'set': 'SERVER,{type},{address},{port},0#',  # type: 0=IP, 1=domain
                'read': 'SERVER#'
            },
            
            # Time Parameters
            'report_intervals': {
                'set': 'TIMER,{moving_time},{stopped_time}#',
                'read': 'TIMER#'
            },
            'heartbeat_intervals': {
                'set': 'HBT,{moving_heartbeat},{stopped_heartbeat}#',
                'read': 'HBT#'
            },
            
            # Service Parameters
            'protocol': {
                'set': 'SZCS#GT06SEL={value}#',  # value: 0=GT06, 1=CRX3, 2=CRX
                'read': 'CXCS#GT06SEL'
            },
            'tcp_ack': {
                'set': 'SZCS#POSBYACK={value}#',  # value: 1=enabled, 0=disabled
                'read': 'CXCS#POSBYACK'
            },
            
            # Ignition
            'ignition_type': {
                'set_physical': 'SZCS#ACCLINE=1#ACC_CFG=0-000-000',
                'set_accelerometer': 'SZCS#ACCLINE=0#ACC_CFG=0-000-000',
                'set_battery': 'SZCS#ACCLINE=1#ACC_CFG=1-{on_voltage}-{off_voltage}',
                'read': 'CXCS#ACCLINE#ACC_CFG'
            },
            
            # Speed
            'speed_alert': {
                'set': 'SPEED,{enabled},{detection_time},{speed_limit},{alert_type}#',
                'read': 'SPEED#'
            },
            'speed_buzzer': {
                'set': 'SZCS#SPD_LED_SHOW={value}#',  # value: 1=enable, 0=disable
                'read': 'N/A'
            },
            
            # Power Saving
            'sleep_mode': {
                'set': 'SZCS#SLPDISCONNECT={value}#',  # value: 0=Disabled, 1=Sleep, 2=Deep Sleep
                'read': 'CXCS#SLPDISCONNECT'
            },
            'sleep_time': {
                'set': 'SZCS#SLEEPT={value}#',  # value: time in minutes
                'read': 'CXCS#SLEEPT'
            },
            
            # Angle
            'angle_report': {
                'set': 'SZCS#ANGLEVALUE={min_speed}-{angle_variation}',
                'read': 'CXCS#ANGLEVALUE'
            },
            
            # Battery Alerts
            'backup_battery_alert': {
                'set': 'BATALM,{state},{mode}#',  # state=ON/OFF, mode=0/1
                'read': 'BATALM#'
            },
            'main_power_alert': {
                'set': 'POWERALM,{enabled},{alert_type},{detection_time},{min_charge_time}#',
                'read': 'POWERALM#'
            },
            
            # Vibration Sensor
            'vibration_sensitivity': {
                'set': 'SZCS#VIBL={level}',  # level: 1-6
                'read': 'CXCS#VIBL'
            },
            
            # Jammer Detection
            'jammer_detection': {
                'set': 'JAMMER,{state},{mode}#',  # state=ON/OFF, mode=0/1
                'read': 'JAMMER#'
            },
            'jammer_relay_action': {
                'set': 'JAMRELAY,{op},{time},{speed},{d},{e},{f},{g}#',
                'read': 'JAMRELAY#'
            },
            
            # Miscellaneous
            'odometer': {
                'set': 'MILEAGE={value}#',  # value in km
                'read': 'MILEAGE#'
            },
            'hourmeter': {
                'set': 'ACCONT,{value}#',  # value in minutes
                'read': 'ACCONT#'
            }
        }
        
        # Expected value mappings from Parameter UI List
        self.expected_value_mappings = {
            'protocol': {
                'GT06 (0x60)': '0',
                'CRX3 (0x22)': '1',
                'GT06 (0x12)': '2'
            },
            'tcp_ack': {
                'Enabled': '1',
                'Disabled': '0'
            },
            'sleep_mode': {
                'Desabilitado (Disabled)': '0',
                'Sleep (Habilitado)': '1',
                'Deep Sleep (Ultra-baixo)': '2'
            },
            'speed_alert_enabled': {
                True: 'ON',
                False: 'OFF'
            },
            'alert_type': {
                'Apenas GPRS': '0',
                'GPRS+SMS': '1'
            },
            'jammer_output_operation': {
                'Sem Ação': '0',
                'Ativar e Manter': '1',
                'Ativar e Desativar com Jammer': '2'
            },
            'boolean_on_off': {
                True: 'ON',
                False: 'OFF'
            }
        }
    
    def validate_all_templates(self) -> Dict[str, Any]:
        """
        Validate all command templates against Parameter UI List specification.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'total_parameters': 0,
            'compliant_parameters': 0,
            'non_compliant_parameters': 0,
            'missing_parameters': [],
            'format_mismatches': [],
            'value_mapping_issues': [],
            'compliance_details': {}
        }
        
        logger.info("Starting command format compliance validation...")
        
        # Check each expected parameter
        for param_name, expected_formats in self.expected_formats.items():
            results['total_parameters'] += 1
            
            logger.info(f"Validating parameter: {param_name}")
            
            # Check if parameter exists in mapper
            param_result = self._validate_parameter(param_name, expected_formats)
            results['compliance_details'][param_name] = param_result
            
            if param_result['is_compliant']:
                results['compliant_parameters'] += 1
                logger.info(f"✓ {param_name} is compliant")
            else:
                results['non_compliant_parameters'] += 1
                logger.warning(f"✗ {param_name} has compliance issues")
                
                if param_result['missing']:
                    results['missing_parameters'].append(param_name)
                
                if param_result['format_issues']:
                    results['format_mismatches'].extend([
                        f"{param_name}: {issue}" for issue in param_result['format_issues']
                    ])
                
                if param_result['value_mapping_issues']:
                    results['value_mapping_issues'].extend([
                        f"{param_name}: {issue}" for issue in param_result['value_mapping_issues']
                    ])
        
        return results
    
    def _validate_parameter(self, param_name: str, expected_formats: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate a single parameter against its expected format.
        
        Args:
            param_name: Name of the parameter
            expected_formats: Expected command formats for the parameter
            
        Returns:
            Dictionary with validation results for the parameter
        """
        result = {
            'is_compliant': True,
            'missing': False,
            'format_issues': [],
            'value_mapping_issues': [],
            'tested_commands': []
        }
        
        # Check if parameter has a command template in the mapper
        mapper_template = self.mapper.command_templates.get(param_name)
        
        if not mapper_template:
            result['is_compliant'] = False
            result['missing'] = True
            result['format_issues'].append(f"No command template found for {param_name}")
            return result
        
        # For set commands, validate the template format
        if 'set' in expected_formats:
            expected_set = expected_formats['set']
            
            # Remove ATSMS: prefix for comparison
            actual_template = mapper_template
            
            # Compare template structure (ignoring parameter names)
            if not self._compare_template_structure(actual_template, expected_set):
                result['is_compliant'] = False
                result['format_issues'].append(
                    f"Template format mismatch. Expected: {expected_set}, Got: {actual_template}"
                )
        
        return result
    
    def _compare_template_structure(self, actual: str, expected: str) -> bool:
        """
        Compare the structure of two command templates.
        
        Args:
            actual: Actual template from mapper
            expected: Expected template from specification
            
        Returns:
            True if structures match, False otherwise
        """
        # Normalize templates by replacing parameter placeholders with X
        import re
        
        def normalize_template(template):
            # Replace {param} with X
            normalized = re.sub(r'\{[^}]+\}', 'X', template)
            # Remove extra spaces
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            return normalized
        
        actual_normalized = normalize_template(actual)
        expected_normalized = normalize_template(expected)
        
        return actual_normalized == expected_normalized
    
    def test_with_profile_data(self, profile_path: str) -> Dict[str, Any]:
        """
        Test command generation with actual profile data.
        
        Args:
            profile_path: Path to the profile JSON file
            
        Returns:
            Dictionary with test results
        """
        logger.info(f"Testing command generation with profile data: {profile_path}")
        
        # Load profile data
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load profile data: {e}")
            return {'error': f"Failed to load profile: {e}"}
        
        results = {
            'total_parameters': 0,
            'successful_commands': 0,
            'failed_commands': 0,
            'generated_commands': {},
            'errors': []
        }
        
        parameters = profile_data.get('parameters', {})
        
        for param_name, param_data in parameters.items():
            results['total_parameters'] += 1
            
            try:
                # Extract parameter value
                param_value = param_data.get('value')
                
                logger.info(f"Testing command generation for {param_name} with value: {param_value}")
                
                # Generate command using the mapper (disable validation to avoid SecurityContext issues)
                if param_name in ['apn_settings', 'server_settings', 'report_intervals', 
                                'heartbeat_intervals', 'speed_alert', 'main_power_alert',
                                'jammer_relay_action', 'angle_report']:
                    # Multi-field parameters
                    command = self.mapper.get_command(param_name, param_value, validate_command=False)
                else:
                    # Single-field parameters
                    command = self.mapper.get_command(param_name, param_value, validate_command=False)
                
                results['successful_commands'] += 1
                results['generated_commands'][param_name] = {
                    'value': param_value,
                    'command': command,
                    'status': 'success'
                }
                
                logger.info(f"✓ Generated command for {param_name}: {command}")
                
            except Exception as e:
                results['failed_commands'] += 1
                error_msg = f"Failed to generate command for {param_name}: {str(e)}"
                results['errors'].append(error_msg)
                results['generated_commands'][param_name] = {
                    'value': param_value,
                    'command': None,
                    'status': 'error',
                    'error': str(e)
                }
                
                logger.error(f"✗ {error_msg}")
        
        return results
    
    def validate_specific_commands(self) -> Dict[str, Any]:
        """
        Validate specific command examples with known parameter values.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating specific command examples...")
        
        test_cases = [
            # APN Settings - multi-field parameter
            {
                'param': 'apn_settings',
                'value': {'apn': 'allcom.br', 'user': 'allcom', 'password': 'allcom2'},
                'expected': 'ATSMS:APN,allcom.br,allcom,allcom2#'
            },
            
            # Server Settings - multi-field parameter  
            {
                'param': 'server_settings',
                'value': {'address': '3.216.82.119', 'port': 8841},
                'expected': 'ATSMS:SERVER,0,3.216.82.119,8841,0#'
            },
            
            # Protocol
            {
                'param': 'protocol',
                'value': 'GT06 (0x12)',
                'expected': 'ATSMS:SZCS#GT06SEL=2'
            },
            
            # Speed Alert
            {
                'param': 'speed_alert',
                'value': {'enabled': True, 'detection_time': 10, 'speed_limit': 80, 'alert_type': 'GPRS+SMS'},
                'expected': 'ATSMS:SPEED,ON,10,80,1#'
            },
            
            # Jammer Relay Action
            {
                'param': 'jammer_relay_action',
                'value': {'enabled': True, 'output_operation': 'Ativar e Desativar com Jammer', 
                         'confirmation_time': 80, 'speed_limit': 5},
                'expected': 'ATSMS:JAMRELAY,2,80,5,0,0,0,0#'
            },
            
            # Main Power Alert
            {
                'param': 'main_power_alert',
                'value': {'enabled': True, 'alert_type': 'GPRS+SMS', 'detection_time': 10, 'min_charge_time': 10},
                'expected': 'ATSMS:POWERALM,ON,1,10,10#'
            },
            
            # Sleep Mode
            {
                'param': 'sleep_mode',
                'value': 'Sleep (Habilitado)',
                'expected': 'ATSMS:SZCS#SLPDISCONNECT=1'
            }
        ]
        
        results = {
            'total_tests': len(test_cases),
            'passed_tests': 0,
            'failed_tests': 0,
            'test_results': []
        }
        
        for test_case in test_cases:
            param = test_case['param']
            value = test_case['value']
            expected = test_case['expected']
            
            try:
                # Generate command (disable validation to avoid SecurityContext issues)
                actual = self.mapper.get_command(param, value, validate_command=False)
                
                # Compare with expected
                if actual == expected:
                    results['passed_tests'] += 1
                    status = 'PASS'
                    logger.info(f"✓ {param}: Command matches expected format")
                else:
                    results['failed_tests'] += 1
                    status = 'FAIL'
                    logger.error(f"✗ {param}: Command format mismatch")
                    logger.error(f"  Expected: {expected}")
                    logger.error(f"  Actual:   {actual}")
                
                results['test_results'].append({
                    'parameter': param,
                    'value': value,
                    'expected': expected,
                    'actual': actual,
                    'status': status
                })
                
            except Exception as e:
                results['failed_tests'] += 1
                error_msg = f"Error generating command for {param}: {str(e)}"
                logger.error(f"✗ {error_msg}")
                
                results['test_results'].append({
                    'parameter': param,
                    'value': value,
                    'expected': expected,
                    'actual': None,
                    'status': 'ERROR',
                    'error': str(e)
                })
        
        return results
    
    def generate_compliance_report(self) -> str:
        """
        Generate a comprehensive compliance report.
        
        Returns:
            Formatted compliance report as string
        """
        logger.info("Generating comprehensive compliance report...")
        
        # Run all validations
        template_results = self.validate_all_templates()
        command_results = self.validate_specific_commands()
        
        # Try to test with profile data
        profile_results = None
        profile_path = "lt32pro_profile_20250810_083223.json"
        if Path(profile_path).exists():
            profile_results = self.test_with_profile_data(profile_path)
        
        # Generate report
        report = []
        report.append("=" * 80)
        report.append("COMMAND FORMAT COMPLIANCE VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Template validation results
        report.append("1. COMMAND TEMPLATE VALIDATION")
        report.append("-" * 40)
        report.append(f"Total parameters checked: {template_results['total_parameters']}")
        report.append(f"Compliant parameters: {template_results['compliant_parameters']}")
        report.append(f"Non-compliant parameters: {template_results['non_compliant_parameters']}")
        
        if template_results['missing_parameters']:
            report.append("")
            report.append("Missing parameters:")
            for param in template_results['missing_parameters']:
                report.append(f"  - {param}")
        
        if template_results['format_mismatches']:
            report.append("")
            report.append("Format mismatches:")
            for mismatch in template_results['format_mismatches']:
                report.append(f"  - {mismatch}")
        
        report.append("")
        
        # Command generation results
        report.append("2. COMMAND GENERATION VALIDATION")
        report.append("-" * 40)
        report.append(f"Total test cases: {command_results['total_tests']}")
        report.append(f"Passed tests: {command_results['passed_tests']}")
        report.append(f"Failed tests: {command_results['failed_tests']}")
        
        if command_results['failed_tests'] > 0:
            report.append("")
            report.append("Failed test cases:")
            for test in command_results['test_results']:
                if test['status'] in ['FAIL', 'ERROR']:
                    report.append(f"  - {test['parameter']}: {test.get('error', 'Format mismatch')}")
        
        report.append("")
        
        # Profile data results
        if profile_results:
            report.append("3. PROFILE DATA VALIDATION")
            report.append("-" * 40)
            report.append(f"Total parameters in profile: {profile_results['total_parameters']}")
            report.append(f"Successful command generation: {profile_results['successful_commands']}")
            report.append(f"Failed command generation: {profile_results['failed_commands']}")
            
            if profile_results['errors']:
                report.append("")
                report.append("Command generation errors:")
                for error in profile_results['errors'][:5]:  # Show first 5 errors
                    report.append(f"  - {error}")
                if len(profile_results['errors']) > 5:
                    report.append(f"  ... and {len(profile_results['errors']) - 5} more errors")
            
            report.append("")
        
        # Overall compliance status
        report.append("4. OVERALL COMPLIANCE STATUS")
        report.append("-" * 40)
        
        template_compliance = (template_results['compliant_parameters'] / 
                             template_results['total_parameters'] * 100) if template_results['total_parameters'] > 0 else 0
        
        command_compliance = (command_results['passed_tests'] / 
                            command_results['total_tests'] * 100) if command_results['total_tests'] > 0 else 0
        
        report.append(f"Template compliance: {template_compliance:.1f}%")
        report.append(f"Command generation compliance: {command_compliance:.1f}%")
        
        if profile_results:
            profile_compliance = (profile_results['successful_commands'] / 
                                profile_results['total_parameters'] * 100) if profile_results['total_parameters'] > 0 else 0
            report.append(f"Profile data compliance: {profile_compliance:.1f}%")
        
        overall_compliance = (template_compliance + command_compliance) / 2
        report.append(f"Overall compliance: {overall_compliance:.1f}%")
        
        report.append("")
        
        # Recommendations
        report.append("5. RECOMMENDATIONS")
        report.append("-" * 40)
        
        if template_results['missing_parameters']:
            report.append("- Add missing command templates for parameters listed above")
        
        if template_results['format_mismatches']:
            report.append("- Fix command template formats to match Parameter UI List specification")
        
        if command_results['failed_tests'] > 0:
            report.append("- Review and fix command generation logic for failed test cases")
        
        if profile_results and profile_results['failed_commands'] > 0:
            report.append("- Investigate command generation failures with actual profile data")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Main function to run the validation."""
    validator = CommandFormatValidator()
    
    # Generate and display the compliance report
    report = validator.generate_compliance_report()
    print(report)
    
    # Save report to file
    report_path = "command_format_compliance_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"Compliance report saved to: {report_path}")


if __name__ == "__main__":
    main()