"""
Parameter Specification Data Structure for LT32 PRO Configurator

This module contains the comprehensive parameter specification dictionary that matches
the Parameter UI List document exactly. It defines all parameter sections, UI element
types, validation rules, command mappings, and conditional visibility rules.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass


@dataclass
class FieldConfig:
    """Configuration for a parameter field"""
    name: str
    label: str
    ui_element: str
    validation: Optional[str] = None
    unit: Optional[str] = None
    options: Optional[List[str]] = None
    visibility_condition: Optional[str] = None


@dataclass
class ParameterConfig:
    """Configuration for a parameter"""
    name: str
    label: str
    description: Optional[str] = None
    ui_element: Optional[str] = None
    fields: Optional[Dict[str, FieldConfig]] = None
    options: Optional[List[str]] = None
    validation: Optional[str] = None
    unit: Optional[str] = None
    commands: Optional[Dict[str, str]] = None


@dataclass
class SectionConfig:
    """Configuration for a parameter section"""
    name: str
    label: str
    parameters: Dict[str, ParameterConfig]
    order: int


# Complete Parameter Specification matching the Parameter UI List document
PARAMETER_SPECIFICATION: Dict[str, SectionConfig] = {
    'network_parameters': SectionConfig(
        name='network_parameters',
        label='Parâmetros de Rede',
        order=1,
        parameters={
            'apn_settings': ParameterConfig(
                name='apn_settings',
                label='Configuração APN',
                description='Configures the APN, username, and password for the mobile network.',
                fields={
                    'apn': FieldConfig(
                        name='apn',
                        label='APN',
                        ui_element='text_input',
                        validation='Accepts a standard APN name, an IP address, or a URL.'
                    ),
                    'user': FieldConfig(
                        name='user',
                        label='Usuário',
                        ui_element='text_input'
                    ),
                    'password': FieldConfig(
                        name='password',
                        label='Senha',
                        ui_element='text_input'
                    )
                },
                commands={
                    'set': 'APN,<apn>,<user>,<password>#',
                    'read': 'APN#'
                }
            ),
            'server_settings': ParameterConfig(
                name='server_settings',
                label='Configuração de Servidor',
                description='Configures the primary server IP/URL and port.',
                fields={
                    'address': FieldConfig(
                        name='address',
                        label='IP / URL',
                        ui_element='text_input',
                        validation='Should accept a valid IP address or a valid URL.'
                    ),
                    'port': FieldConfig(
                        name='port',
                        label='PORTA',
                        ui_element='number_input',
                        validation='1-65535',
                    )
                },
                commands={
                    'set': 'SERVER,<type>,<address>,<port>,0#',
                    'read': 'SERVER#'
                }
            ),
            'network_settings': ParameterConfig(
                name='network_settings',
                label='Seleção de Rede',
                ui_element='dropdown',
                options=['AUTO', '4G', '2G'],
                commands={
                    'set': 'NETSELECT,<value>#',
                    'read': 'NETSELECT#'
                }
            )
        }
    ),
    
    'time_parameters': SectionConfig(
        name='time_parameters',
        label='Parâmetros de Tempo',
        order=2,
        parameters={
            'report_intervals': ParameterConfig(
                name='report_intervals',
                label='Intervalos de Envio',
                description='Defines the time intervals for sending position data based on ignition status.',
                fields={
                    'moving_time': FieldConfig(
                        name='moving_time',
                        label='Tempo em movimento (Ignição ligada)',
                        ui_element='number_input',
                        unit='segundos'
                    ),
                    'stopped_time': FieldConfig(
                        name='stopped_time',
                        label='Tempo parado (Ignição desligada)',
                        ui_element='number_input',
                        unit='segundos'
                    )
                },
                commands={
                    'set': 'TIMER,<moving_time>,<stopped_time>#',
                    'read': 'TIMER#'
                }
            ),
            'heartbeat_intervals': ParameterConfig(
                name='heartbeat_intervals',
                label='Intervalos de Heartbeat',
                description='Defines the keep-alive signal interval based on ignition status.',
                fields={
                    'moving_heartbeat': FieldConfig(
                        name='moving_heartbeat',
                        label='Intervalo (Heartbeat) em movimento',
                        ui_element='number_input',
                        unit='segundos'
                    ),
                    'stopped_heartbeat': FieldConfig(
                        name='stopped_heartbeat',
                        label='Intervalo (Heartbeat) parado',
                        ui_element='number_input',
                        unit='segundos'
                    )
                },
                commands={
                    'set': 'HBT,<moving_heartbeat>,<stopped_heartbeat>#',
                    'read': 'HBT#'
                }
            )
        }
    ),
    
    'service_parameters': SectionConfig(
        name='service_parameters',
        label='Parâmetros de Serviço',
        order=3,
        parameters={
            'protocol': ParameterConfig(
                name='protocol',
                label='Tipo de protocolo',
                ui_element='dropdown',
                options=['GT06 (0x60)', 'CRX3 (0x22)', 'CRX (0x12)'],
                commands={
                    'set': 'SZCS#GT06SEL=X',
                    'read': 'CXCS#GT06SEL'
                }
            ),
            'tcp_ack': ParameterConfig(
                name='tcp_ack',
                label='Habilitar confirmação TCP (ACK)',
                ui_element='toggle_switch',
                options=['Enabled', 'Disabled'],
                commands={
                    'set': 'SZCS#POSBYACK=A',
                    'read': 'CXCS#POSBYACK'
                }
            )
        }
    ),
    
    'ignition': SectionConfig(
        name='ignition',
        label='Ignição',
        order=4,
        parameters={
            'ignition_type': ParameterConfig(
                name='ignition_type',
                label='Tipo de ignição',
                description='Configures the method for detecting ignition status.',
                fields={
                    'ignition_mode': FieldConfig(
                        name='ignition_mode',
                        label='Modo de Ignição',
                        ui_element='dropdown',
                        options=['Física (Physical)', 'Virtual por acelerômetro (Virtual by accelerometer)', 'Virtual por bateria (Virtual by battery)']
                    ),
                    'on_voltage': FieldConfig(
                        name='on_voltage',
                        label='Tensão para Ligar (ON)',
                        ui_element='number_input',
                        unit='volts',
                        visibility_condition="ignition_mode == 'Virtual por bateria (Virtual by battery)'"
                    ),
                    'off_voltage': FieldConfig(
                        name='off_voltage',
                        label='Tensão para Desligar (OFF)',
                        ui_element='number_input',
                        unit='volts',
                        visibility_condition="ignition_mode == 'Virtual por bateria (Virtual by battery)'"
                    )
                },
                commands={
                    'set_physical': 'SZCS#ACCLINE=1#ACC_CFG=0-000-000',
                    'set_accelerometer': 'SZCS#ACCLINE=0#ACC_CFG=0-000-000',
                    'set_battery': 'SZCS#ACCLINE=1#ACC_CFG=1-<on_voltage>-<off_voltage>',
                    'read': 'CXCS#ACCLINE#ACC_CFG'
                }
            )
        }
    ),
    
    'speed': SectionConfig(
        name='speed',
        label='Velocidade',
        order=5,
        parameters={
            'speed_alert': ParameterConfig(
                name='speed_alert',
                label='Alerta de Velocidade',
                description='Configures the over-speed alert.',
                fields={
                    'enabled': FieldConfig(
                        name='enabled',
                        label='Habilitar Alerta de limite de velocidade',
                        ui_element='toggle_switch'
                    ),
                    'detection_time': FieldConfig(
                        name='detection_time',
                        label='Tempo para detectar (s)',
                        ui_element='number_input'
                    ),
                    'speed_limit': FieldConfig(
                        name='speed_limit',
                        label='Velocidade (km/h)',
                        ui_element='number_input'
                    ),
                    'alert_type': FieldConfig(
                        name='alert_type',
                        label='Tipo de Alerta',
                        ui_element='dropdown',
                        options=['Apenas GPRS', 'GPRS+SMS']
                    )
                },
                commands={
                    'set': 'SPEED,<enabled>,<detection_time>,<speed_limit>,<alert_type>#',
                    'read': 'SPEED#'
                }
            ),
            'speed_buzzer': ParameterConfig(
                name='speed_buzzer',
                label='Ativar o buzzer no alerta de limite de velocidade',
                ui_element='toggle_switch',
                commands={
                    'set': 'SZCS#SPD_LED_SHOW=A',
                    'read': 'N/A'
                }
            )
        }
    ),
    
    'power_saving': SectionConfig(
        name='power_saving',
        label='Economia de Energia',
        order=6,
        parameters={
            'sleep_mode': ParameterConfig(
                name='sleep_mode',
                label='Modo Sleep',
                ui_element='dropdown',
                options=['Desabilitado (Disabled)', 'Sleep (Habilitado)', 'Deep Sleep (Ultra-baixo)'],
                commands={
                    'set': 'SZCS#SLPDISCONNECT=A',
                    'read': 'CXCS#SLPDISCONNECT'
                }
            ),
            'sleep_time': ParameterConfig(
                name='sleep_time',
                label='Tempo para entrar em Sleep (minutos)',
                ui_element='number_input',
                unit='minutos',
                commands={
                    'set': 'SZCS#SLEEPT=X',
                    'read': 'CXCS#SLEEPT'
                }
            )
        }
    ),
    
    'angle': SectionConfig(
        name='angle',
        label='Ângulo',
        order=7,
        parameters={
            'angle_report': ParameterConfig(
                name='angle_report',
                label='Envio por Ângulo',
                description='Configures position reporting based on angle changes.',
                fields={
                    'enabled': FieldConfig(
                        name='enabled',
                        label='Habilitar envio por ângulo',
                        ui_element='toggle_switch'
                    ),
                    'min_speed': FieldConfig(
                        name='min_speed',
                        label='Velocidade mínima (km/h)',
                        ui_element='number_input',
                        validation='1-20',
                        visibility_condition='enabled == true'
                    ),
                    'angle_variation': FieldConfig(
                        name='angle_variation',
                        label='Variação do Ângulo (°)',
                        ui_element='number_input',
                        validation='5-90',
                        visibility_condition='enabled == true'
                    )
                },
                commands={
                    'set': 'SZCS#ANGLEVALUE=<min_speed>-<angle_variation>',
                    'read': 'CXCS#ANGLEVALUE'
                }
            )
        }
    ),
    
    'battery_alerts': SectionConfig(
        name='battery_alerts',
        label='Alertas de Bateria',
        order=8,
        parameters={
            'backup_battery_alert': ParameterConfig(
                name='backup_battery_alert',
                label='Alerta de bateria backup baixa',
                ui_element='toggle_switch',
                commands={
                    'set': 'BATALM,<state>,<mode>#',
                    'read': 'BATALM#'
                }
            ),
            'main_power_alert': ParameterConfig(
                name='main_power_alert',
                label='Alerta de Remoção de Bateria Principal',
                description='Configures the main power removal alert.',
                fields={
                    'enabled': FieldConfig(
                        name='enabled',
                        label='Habilitar alerta',
                        ui_element='toggle_switch'
                    ),
                    'alert_type': FieldConfig(
                        name='alert_type',
                        label='Tipo de Alerta',
                        ui_element='dropdown',
                        options=['Apenas GPRS', 'GPRS+SMS']
                    ),
                    'detection_time': FieldConfig(
                        name='detection_time',
                        label='Tempo de detecção (s)',
                        ui_element='number_input'
                    ),
                    'min_charge_time': FieldConfig(
                        name='min_charge_time',
                        label='Tempo mínimo de carga (s)',
                        ui_element='number_input'
                    )
                },
                commands={
                    'set': 'POWERALM,<enabled>,<alert_type>,<detection_time>,<min_charge_time>#',
                    'read': 'POWERALM#'
                }
            )
        }
    ),
    
    'vibration_sensor': SectionConfig(
        name='vibration_sensor',
        label='Sensor de Vibração',
        order=9,
        parameters={
            'vibration_sensitivity': ParameterConfig(
                name='vibration_sensitivity',
                label='Sensibilidade à Vibração',
                fields={
                    'level': FieldConfig(
                        name='level',
                        label='Nível da sensibilidade (1=Baixa, 6=Alta)',
                        ui_element='slider',
                        validation='1-6'
                    )
                },
                commands={
                    'set_level': 'SZCS#VIBL=<level>',
                    'read': 'CXCS#VIBL'
                }
            ),
            'vibration_window': ParameterConfig(
                name='vibration_window',
                label='Janela de Vibração',
                fields={
                    'window': FieldConfig(
                        name='window',
                        label='Janela de tempo (s)',
                        ui_element='number_input',
                        validation='1-60'
                    ),
                    'threshold': FieldConfig(
                        name='threshold',
                        label='Threshold',
                        ui_element='number_input',
                        validation='1-10'
                    )
                },
                commands={
                    'set': 'VIBCHK,<window>,<threshold>#',
                    'read': 'VIBCHK#'
                }
            )
        }
    ),
    
    'jammer_detection': SectionConfig(
        name='jammer_detection',
        label='Detecção de Jammer',
        order=10,
        parameters={
            'jammer_detection': ParameterConfig(
                name='jammer_detection',
                label='Detecção de Jammer',
                ui_element='toggle_switch',
                commands={
                    'set': 'JAMMER,<state>,<mode>#',
                    'read': 'JAMMER#'
                }
            ),
            'jammer_relay_action': ParameterConfig(
                name='jammer_relay_action',
                label='Ação da Saída por Jammer',
                description='Configures the relay (output) behavior upon jammer detection.',
                fields={
                    'output_operation': FieldConfig(
                        name='output_operation',
                        label='Operação da Saída',
                        ui_element='dropdown',
                        options=['Sem Ação', 'Ativar e Manter', 'Ativar e Desativar com Jammer']
                    ),
                    'confirmation_time': FieldConfig(
                        name='confirmation_time',
                        label='Tempo para confirmação (s)',
                        ui_element='number_input',
                        validation='0-1800'
                    ),
                    'speed_limit': FieldConfig(
                        name='speed_limit',
                        label='Velocidade limite (km/h)',
                        ui_element='number_input',
                        validation='0-255'
                    )
                },
                commands={
                    'set': 'JAMRELAY,<op>,<time>,<speed>,<D>,<E>,<F>,<G>#',
                    'read': 'JAMRELAY#'
                }
            )
        }
    ),
    
    'security': SectionConfig(
        name='security',
        label='Segurança',
        order=11,
        parameters={
            'defense_settings': ParameterConfig(
                name='defense_settings',
                label='Defense Time (min):',
                ui_element='number_input',
                validation='1-60',
                commands={
                    'set': 'DEFENSE,<value>#',
                    'read': 'DEFENSE#'
                }
            )
        }
    ),

    'miscellaneous': SectionConfig(
        name='miscellaneous',
        label='Diversos',
        order=12,
        parameters={
            'odometer': ParameterConfig(
                name='odometer',
                label='Ajustar Odômetro',
                ui_element='number_input',
                unit='metros',
                commands={
                    'set': 'MILEAGE=A#',
                    'read': 'MILEAGE#'
                }
            ),
            'hourmeter': ParameterConfig(
                name='hourmeter',
                label='Ajustar Horímetro',
                ui_element='number_input',
                unit='minutos',
                commands={
                    'set': 'ACCONT,A#',
                    'read': 'ACCONT#'
                }
            )
        }
    )
}


# Validation rules mapping for all parameters
VALIDATION_RULES = {
    'port': {
        'type': 'numeric_range',
        'min': 1,
        'max': 65535,
        'error_message': 'Port must be between 1 and 65535'
    },
    'apn': {
        'type': 'format_validation',
        'patterns': [
            r'^[\w\.-]+$',  # Standard APN name
            r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',  # IP address
            r'^https?://[\w\.-]+.*$'  # URL
        ],
        'error_message': 'APN must be a valid name, IP address, or URL'
    },
    'ip_url': {
        'type': 'format_validation',
        'patterns': [
            r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',  # IP address
            r'^[\w\.-]+\.[a-zA-Z]{2,}$',  # Domain
            r'^https?://[\w\.-]+.*$'  # URL
        ],
        'error_message': 'Must be a valid IP address or URL'
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
    'power_detection_time': {
        'type': 'numeric_range',
        'min': 2,
        'max': 60,
        'error_message': 'Detection time must be between 2 and 60 seconds'
    },
    'min_charge_time': {
        'type': 'numeric_range',
        'min': 1,
        'max': 3600,
        'error_message': 'Minimum charge time must be between 1 and 3600 seconds'
    },
    'vibration_level': {
        'type': 'numeric_range',
        'min': 1,
        'max': 6,
        'error_message': 'Vibration level must be between 1 (low) and 6 (high)'
    },
    'jammer_confirmation_time': {
        'type': 'numeric_range',
        'min': 0,
        'max': 1800,
        'error_message': 'Confirmation time must be between 0 and 1800 seconds'
    },
    'jammer_speed_limit': {
        'type': 'numeric_range',
        'min': 0,
        'max': 255,
        'error_message': 'Speed limit must be between 0 and 255 km/h'
    }
}


# Command value mappings for dropdown and toggle options
COMMAND_VALUE_MAPPINGS = {
    'protocol': {
        'GT06 (0x60)': 0,
        'CRX3 (0x22)': 1,
        'CRX (0x12)': 2
    },
    'tcp_ack': {
        'Enabled': 1,
        'Disabled': 0
    },
    'sleep_mode': {
        'Desabilitado (Disabled)': 0,
        'Sleep (Habilitado)': 1,
        'Deep Sleep (Ultra-baixo)': 2
    },
    'alert_type': {
        'Apenas GPRS': 0,
        'GPRS+SMS': 1
    },
    'jammer_output_operation': {
        'Sem Ação': 0,
        'Ativar e Manter': 1,
        'Ativar e Desativar com Jammer': 2
    },
    'boolean_on_off': {
        True: 'ON',
        False: 'OFF'
    },
    'boolean_1_0': {
        True: 1,
        False: 0
    }
}


# Conditional visibility rules
CONDITIONAL_VISIBILITY_RULES = {
    'ignition_type.on_voltage': {
        'condition': "ignition_mode == 'Virtual por bateria (Virtual by battery)'",
        'trigger_field': 'ignition_type.ignition_mode'
    },
    'ignition_type.off_voltage': {
        'condition': "ignition_mode == 'Virtual por bateria (Virtual by battery)'",
        'trigger_field': 'ignition_type.ignition_mode'
    },
    'angle_report.min_speed': {
        'condition': 'enabled == true',
        'trigger_field': 'angle_report.enabled'
    },
    'angle_report.angle_variation': {
        'condition': 'enabled == true',
        'trigger_field': 'angle_report.enabled'
    }
}


def get_parameter_specification() -> Dict[str, SectionConfig]:
    """
    Returns the complete parameter specification dictionary.
    
    Returns:
        Dict[str, SectionConfig]: The parameter specification
    """
    return PARAMETER_SPECIFICATION


def get_section_by_name(section_name: str) -> Optional[SectionConfig]:
    """
    Get a specific section configuration by name.
    
    Args:
        section_name: Name of the section to retrieve
        
    Returns:
        SectionConfig or None if not found
    """
    return PARAMETER_SPECIFICATION.get(section_name)


def get_parameter_by_name(section_name: str, parameter_name: str) -> Optional[ParameterConfig]:
    """
    Get a specific parameter configuration by section and parameter name.
    
    Args:
        section_name: Name of the section
        parameter_name: Name of the parameter
        
    Returns:
        ParameterConfig or None if not found
    """
    section = get_section_by_name(section_name)
    if section:
        return section.parameters.get(parameter_name)
    return None


def get_validation_rule(rule_name: str) -> Optional[Dict[str, Any]]:
    """
    Get validation rule by name.
    
    Args:
        rule_name: Name of the validation rule
        
    Returns:
        Dict with validation rule or None if not found
    """
    return VALIDATION_RULES.get(rule_name)


def get_command_value_mapping(mapping_name: str) -> Optional[Dict[str, Any]]:
    """
    Get command value mapping by name.
    
    Args:
        mapping_name: Name of the mapping
        
    Returns:
        Dict with value mappings or None if not found
    """
    return COMMAND_VALUE_MAPPINGS.get(mapping_name)


def get_conditional_visibility_rule(field_name: str) -> Optional[Dict[str, str]]:
    """
    Get conditional visibility rule for a field.
    
    Args:
        field_name: Full field name (section.parameter.field)
        
    Returns:
        Dict with visibility rule or None if not found
    """
    return CONDITIONAL_VISIBILITY_RULES.get(field_name)


def get_all_sections_ordered() -> List[SectionConfig]:
    """
    Get all sections ordered by their order attribute.
    
    Returns:
        List of SectionConfig objects ordered by order attribute
    """
    return sorted(PARAMETER_SPECIFICATION.values(), key=lambda x: x.order)


def get_all_ui_element_types() -> List[str]:
    """
    Get all unique UI element types used in the specification.
    
    Returns:
        List of unique UI element type strings
    """
    element_types = set()
    
    for section in PARAMETER_SPECIFICATION.values():
        for param in section.parameters.values():
            if param.ui_element:
                element_types.add(param.ui_element)
            if param.fields:
                for field in param.fields.values():
                    element_types.add(field.ui_element)
    
    return sorted(list(element_types))


def validate_specification_completeness() -> Dict[str, List[str]]:
    """
    Validate that the specification is complete and consistent.
    
    Returns:
        Dict with validation results and any issues found
    """
    issues = {
        'missing_commands': [],
        'missing_labels': [],
        'invalid_ui_elements': [],
        'missing_validation': []
    }
    
    valid_ui_elements = {
        'text_input', 'number_input', 'dropdown', 'toggle_switch', 
        'slider', 'password_input'
    }
    
    for section_name, section in PARAMETER_SPECIFICATION.items():
        for param_name, param in section.parameters.items():
            # Check for missing commands
            if not param.commands:
                issues['missing_commands'].append(f"{section_name}.{param_name}")
            
            # Check for missing labels
            if not param.label:
                issues['missing_labels'].append(f"{section_name}.{param_name}")
            
            # Check UI elements
            if param.ui_element and param.ui_element not in valid_ui_elements:
                issues['invalid_ui_elements'].append(f"{section_name}.{param_name}")
            
            # Check fields if they exist
            if param.fields:
                for field_name, field in param.fields.items():
                    if field.ui_element not in valid_ui_elements:
                        issues['invalid_ui_elements'].append(f"{section_name}.{param_name}.{field_name}")
                    
                    if not field.label:
                        issues['missing_labels'].append(f"{section_name}.{param_name}.{field_name}")
    
    return issues