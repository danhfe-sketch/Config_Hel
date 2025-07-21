"""
Device Command Mapper - Maps UI parameters to LT32Pro AT commands.

This module provides a centralized mapping between UI parameters and the actual
AT commands required by the LT32Pro device. It handles command formatting,
validation, and error handling for malformed commands.
"""

from typing import Dict, Any, Optional, Tuple, List
import re


class DeviceCommandMapper:
    """Maps UI parameters to LT32Pro AT commands with validation."""

    def __init__(self):
        """Initialize the command mapper with LT32Pro command definitions."""
        # Command prefix required for all LT32Pro commands via serial port
        self.command_prefix = "ATSMS:"

        # Define command templates for all parameters
        self._init_command_templates()

        # Define parameter value mappings (e.g., TCP -> 0)
        self._init_value_mappings()

    def _init_command_templates(self) -> None:
        """Initialize command templates for all parameters based on LT32Pro documentation."""
        self.command_templates = {
            # APN Configuration
            'apn_server': "APN,{value},,#",
            'apn_user': "APN,{server},{value},#",
            'apn_password': "APN,{server},{user},{value}#",
            'apn_full': "APN,{server},{user},{password}#",
            
            # Parameter Query Commands
            'query_apn': "APN#",
            'query_server': "SERVER#",
            'query_timer': "TIMER#",
            'query_heartbeat': "HBT#",
            'query_vibration': "CXCS#VIBL",
            'query_defense': "DEFENSE#",
            'query_protocol': "CXCS#GT06SEL",
            'query_network': "CXCS#NETSELECT",
            'query_volte': "CXCS#VOLTESWITCH",
            'query_sleep_mode': "CXCS#SLPDISCONNECT",
            'query_sleep_time': "CXCS#SLEEPT",
            'query_ignition': "CXCS#ACCLINE#ACC_CFG",
            'query_vibration_window': "CXCS#VIBCHK",
            'query_blind_speed': "CXCS#BLINDSPD",
            'query_angle_reporting': "CXCS#ANGLEVALUE",
            'query_relay_gps': "CXCS#SOURCE_OFF_TYPE",
            'query_curve_sensor': "CXCS#CURVE",
            'query_lock_type': "CXCS#LOCKTYPE",
            'query_sensitivity': "CXCS#SENSITIVITY",

            # Server Configuration
            'server_ip': "SERVER,0,{value},{port},0#",
            'server_domain': "SERVER,1,{value},{port},0#",
            'server_port': "SERVER,0,{ip},{value},0#",
            'backup_server_ip': "CXCS#SERV2_ADDR={value}#",
            'backup_server_port': "CXCS#SERV2_PORT={value}#",

            # Communication Intervals
            'timer_ign_on': "TIMER,{value},{timer_ign_off}#",
            'timer_ign_off': "TIMER,{timer_ign_on},{value}#",
            'heartbeat_ign_on': "HBT,{value},{heartbeat_ign_off}#",
            'heartbeat_ign_off': "HBT,{heartbeat_ign_on},{value}#",
            'heartbeat_interval': "HBT,{value}#",

            # Device Information Retrieval
            'get_imei': "CXCS#IMEI",
            'get_iccid': "CXCS#ICCID",
            'get_imsi': "CXCS#IMSI",
            'get_status': "STATUS#",
            'get_version': "VERSION#",
            'get_all_params': "PARAM#",

            # Movement and Vibration Settings
            'vibration': "CXCS#VIBL={value}#",
            'vibration_window': "CXCS#VIBCHK={window}:{value}#",
            'defense_time': "DEFENSE,{value}#",

            # Speed and Angle Reporting
            'speed_alert': "SPEED,ON,{time},{value},{alert_type}#",
            'angle_reporting': "CXCS#ANGLEVALUE={speed}-{value}#",
            'blind_speed': "CXCS#BLINDSPD={value}#",

            # Ignition Configuration
            'ignition_type': "CXCS#ACCLINE={value}#ACC_CFG=0-000-000",
            'ignition_config': "CXCS#ACC_CFG={value}#",

            # Alerts Configuration
            'movement_alert': "SENALM,ON,{value}#",
            'power_alert': "POWERALM,ON,{value},{t1},{t2}#",
            'battery_alert': "BATALM,ON,{value}#",
            'moving_alert': "MOVING,ON,{value},{type}#",
            'acc_on_alert': "ACCALM,ON,{value}#",
            'acc_off_alert': "ACCOFFALM,ON,{value}#",

            # Network and Protocol Settings
            'gt06_protocol': "CXCS#GT06SEL={value}#",
            'network_select': "CXCS#NETSELECT={value}#",
            'volte_switch': "CXCS#VOLTESWITCH={value}#",
            'transmission_mode': "CXCS#PROTOCOL={value}#",

            # Sleep Mode Configuration
            'sleep_mode': "CXCS#SLPDISCONNECT={value}#",
            'sleep_time': "CXCS#SLEEPT={value}#",

            # Relay/Output Control
            'relay_control': "RELAY,{value}#",
            'relay_gps_check': "CXCS#SOURCE_OFF_TYPE={value}#",

            # Phone Numbers Configuration
            'center_number1': "CENTER,A,{value}#",
            'center_number2': "CENTER,A2,{value}#",
            'center_number3': "CENTER,A3,{value}#",
            'sos_numbers': "SOS,A,{phone1},{phone2},{phone3}#",

            # System Commands
            'reset_device': "RESET#",
            'factory_reset': "FACTORY#",
            'format_device': "FORMAT#",
            'clear_memory': "BLINDINIT#",

            # Advanced Features
            'jammer_detection': "JAMMER,ON,{value}#",
            'jammer_config': "JAMCFG,{time},{signal},{value}#",
            'parameter_lock': "PRLOCK,{password},{value}#",

            # Curve Sensor - Corrected from CURVE to proper command
            'curve_sensor': "CXCS#CURVE={value}#",

            # Lock Type - This is a placeholder as the actual command isn't in the documentation
            'lock_type': "CXCS#LOCKTYPE={value}#",

            # Sensitivity - This is a placeholder as the actual command isn't in the documentation
            'sensitivity': "CXCS#SENSITIVITY={value}#",
        }

    def _init_value_mappings(self) -> None:
        """Initialize value mappings for parameters that need translation based on LT32Pro documentation."""
        self.value_mappings = {
            # Network and Protocol Settings
            'transmission_mode': {
                'TCP': '0',
                'UDP': '1'
            },
            'gt06_protocol': {
                'GT06-0x60': '0',  # GT06 (0x60)
                'GT06-0x12': '2',  # GT06 (0x12)
                'CRX3': '1'        # CRX3 (0x22)
            },
            'network_select': {
                'AUTO': '0',  # Auto-select between 2G and 4G
                '4G': '1',    # 4G only
                '2G': '2'     # 2G only
            },
            'volte_switch': {
                '2G': '0',    # Use 2G for SMS
                '4G': '1'     # Use 4G for SMS
            },

            # Sleep Mode Configuration
            'sleep_mode': {
                'Disabled': '0',    # Sleep mode disabled
                'Sleep': '1',       # Sleep mode (can receive SMS)
                'Deep Sleep': '2'   # Deep sleep mode (cannot receive SMS)
            },

            # Relay/Output Control
            'relay_control': {
                'OFF': '0',   # Disable output
                'ON': '1'     # Enable output
            },
            'relay_gps_check': {
                'Check GPS': '0',   # Check GPS fix before activating output
                'Immediate': '1'    # Activate output immediately without checking GPS
            },

            # Ignition Configuration
            'ignition_type': {
                'Digital': '0',   # Virtual ignition (based on movement)
                'Analog': '1'     # Physical ignition (based on voltage)
            },

            # Alert Types
            'alert_type': {
                'GPRS': '0',      # Send alerts via GPRS only
                'SMS+GPRS': '1'   # Send alerts via SMS and GPRS
            },

            # Custom Parameters
            'lock_type': {
                'PIN': '0',     # PIN-based security
                'Card': '1'     # Card-based security
            },
            'curve_sensor': {
                'Disabled': '0',  # Curve sensor disabled
                'Enabled': '1',   # Curve sensor enabled
                'Auto': '2'       # Curve sensor in auto mode
            },

            # Heartbeat Intervals (converted to seconds)
            'heartbeat_interval': {
                '30s': '30',
                '1min': '60',
                '5min': '300',
                '10min': '600',
                '30min': '1800',
                '1hr': '3600',
                '2hr': '7200',
                '6hr': '21600',
                '12hr': '43200',
                '24hr': '86400'
            }
        }

    def get_command(self, param_name: str, value: Any, context: Dict[str, Any] = None,
                   confirm_destructive: bool = True) -> str:
        """
        Get the formatted AT command for a parameter.

        Args:
            param_name: The parameter name
            value: The parameter value
            context: Optional context with additional parameter values needed for the command
            confirm_destructive: Whether to confirm destructive operations

        Returns:
            The formatted AT command string
        """
        # Check if this is a destructive operation that requires confirmation
        if confirm_destructive and param_name in [
            'factory_reset', 'reset_device', 'format_device', 'clear_memory'
        ]:
            # Map param_name to operation type
            operation_type_map = {
                'factory_reset': 'OPERATION_FACTORY_RESET',
                'reset_device': 'OPERATION_DEVICE_RESET',
                'format_device': 'OPERATION_FORMAT_DEVICE',
                'clear_memory': 'OPERATION_CLEAR_MEMORY'
            }

            # Get the app instance if available in context
            app = context.get('app') if context else None

            # If we have the app and operation confirmation service, confirm the operation
            if app and hasattr(app, 'operation_confirmation_service'):
                operation_type = getattr(app.operation_confirmation_service, operation_type_map[param_name])
                if not app.operation_confirmation_service.confirm_operation(operation_type):
                    raise ValueError(f"Operation {param_name} was canceled by user")

        # Apply value mapping if needed
        mapped_value = self._map_value(param_name, value)

        # Get the command template
        template = self.command_templates.get(param_name)
        if not template:
            raise ValueError(f"Unknown parameter: {param_name}")

        # Prepare format arguments
        format_args = {'value': mapped_value}
        if context:
            format_args.update(context)

        # Format the command
        try:
            command = template.format(**format_args)
            # Add the command prefix
            return f"{self.command_prefix}{command}"
        except KeyError as e:
            missing_key = str(e).strip("'")
            raise ValueError(f"Missing required context parameter: {missing_key} for {param_name}")
        except Exception as e:
            raise ValueError(f"Error formatting command for {param_name}: {str(e)}")

    def _map_value(self, param_name: str, value: Any) -> str:
        """Map parameter values to their command equivalents if needed."""
        # Always use TCP (0) for transmission_mode regardless of the input value
        if param_name == 'transmission_mode':
            return '0'  # TCP

        if param_name in self.value_mappings and value in self.value_mappings[param_name]:
            return self.value_mappings[param_name][value]
        return str(value)

    def validate_command(self, command: str) -> Tuple[bool, str]:
        """
        Validate a command string for proper format.

        Args:
            command: The command string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if command starts with prefix
        if not command.startswith(self.command_prefix):
            return False, f"Command must start with {self.command_prefix}"

        # Check for common format issues
        if not re.match(r'^ATSMS:[A-Z0-9#,_=:]+.*', command):
            return False, "Command format is invalid"

        # Check for specific command patterns
        command_body = command[len(self.command_prefix):]

        # Check APN command format
        if command_body.startswith("APN,"):
            parts = command_body.split(',')
            if len(parts) < 2 or not command_body.endswith('#'):
                return False, "Invalid APN command format. Should be APN,server,user,password#"

        # Check SERVER command format
        elif command_body.startswith("SERVER,"):
            parts = command_body.split(',')
            if len(parts) < 5 or not command_body.endswith('#'):
                return False, "Invalid SERVER command format. Should be SERVER,type,address,port,protocol#"

        # Check TIMER command format
        elif command_body.startswith("TIMER,"):
            parts = command_body.split(',')
            if len(parts) < 3 or not command_body.endswith('#'):
                return False, "Invalid TIMER command format. Should be TIMER,ign_on,ign_off#"

        # Check HBT command format
        elif command_body.startswith("HBT,"):
            parts = command_body.split(',')
            if len(parts) < 2 or not command_body.endswith('#'):
                return False, "Invalid HBT command format. Should be HBT,ign_on,ign_off#"

        # Check SZCS command format
        elif command_body.startswith("SZCS#"):
            if not re.match(r'^SZCS#[A-Z0-9_]+=.+#', command_body):
                return False, "Invalid SZCS command format. Should be SZCS#PARAM=value#"

        # All checks passed
        return True, ""

    def parse_device_response(self, response: str, command_type: str) -> Dict[str, Any]:
        """
        Parse device response based on the command type.

        Args:
            response: The device response string
            command_type: The type of command that was sent

        Returns:
            Dictionary with parsed information
        """
        result = {}

        # Handle different response types based on LT32Pro documentation
        if command_type == 'get_imei' or 'IMEI' in response:
            # Example responses:
            # "READOK: IMEI=868022038821794"
            # "IMEI: 868022038821794"
            # "IMEI:868022038821794"
            match = re.search(r'IMEI[=:]\s*(\d+)', response)
            if match:
                result['imei'] = match.group(1)

        elif command_type == 'get_iccid' or 'ICCID' in response:
            # Example responses:
            # "READOK: ICCID=89860000192397786063"
            # "ICCID: 89860000192397786063"
            # "ICCID:89860000192397786063"
            match = re.search(r'ICCID[=:]\s*(\d+)', response)
            if match:
                result['iccid'] = match.group(1)

        elif command_type == 'get_imsi':
            # Example response: "READOK: IMSI=234588563274918"
            match = re.search(r'IMSI=(\d+)', response)
            if match:
                result['imsi'] = match.group(1)

        elif command_type == 'get_status':
            # Example response: "Battery:4.23V;GPRS:Offline;GSMSignalLevel:25;ACC:OFF;GPS:OFF;Defense:ON;"
            # Parse each section separated by semicolons
            for section in response.split(';'):
                if ':' in section:
                    key, value = section.split(':', 1)
                    result[key.strip()] = value.strip()

        elif command_type == 'get_version':
            # Example response: "W16A_10D6K_B44_V6.21 2024 11 15"
            result['version'] = response.strip()

        elif command_type == 'get_all_params':
            # Example response: "IMEI:357457040000821;TIMER:20,300;SEMDS:3;HBT:180Sec;Defense:3;"
            # Parse each section separated by semicolons
            for section in response.split(';'):
                if ':' in section:
                    key, value = section.split(':', 1)
                    result[key.strip()] = value.strip()

        # Handle command responses with SETOK prefix
        elif response.startswith('SETOK:'):
            # Example: "SETOK: VIBL=3"
            # Extract the parameter name and value
            match = re.search(r'SETOK:\s+([A-Z0-9_]+)=(.+)', response)
            if match:
                param_name = match.group(1)
                param_value = match.group(2)
                result['parameter'] = param_name
                result['value'] = param_value
                result['status'] = 'success'

        # Handle APN responses
        elif response.startswith('APN:'):
            # Example: "APN:cmnet,,"
            parts = response[4:].split(',')
            if len(parts) >= 1:
                result['apn_server'] = parts[0]
            if len(parts) >= 2:
                result['apn_user'] = parts[1]
            if len(parts) >= 3:
                result['apn_password'] = parts[2].rstrip('#')

        # Handle SERVER responses
        elif response.startswith('SERVER:'):
            # Example: "SERVER:0,58.61.154.247,7018,0"
            parts = response[7:].split(',')
            if len(parts) >= 4:
                result['server_type'] = parts[0]  # 0 for IP, 1 for domain
                result['server_address'] = parts[1]
                result['server_port'] = parts[2]
                result['server_protocol'] = parts[3]  # 0 for TCP

        # Handle TIMER responses
        elif response.startswith('TIMER ACC ON:'):
            # Example: "TIMER ACC ON:30s,ACC OFF:300s"
            match = re.search(r'TIMER ACC ON:(\d+)s,ACC OFF:(\d+)s', response)
            if match:
                result['timer_ign_on'] = match.group(1)
                result['timer_ign_off'] = match.group(2)

        # Handle HBT (Heartbeat) responses
        elif response.startswith('HBT ACC ON:'):
            # Example: "HBT ACC ON:180s,ACC OFF:180s"
            match = re.search(r'HBT ACC ON:(\d+)s,ACC OFF:(\d+)s', response)
            if match:
                result['heartbeat_ign_on'] = match.group(1)
                result['heartbeat_ign_off'] = match.group(2)

        # Handle DEFENSE responses
        elif response.startswith('DEFENSE:'):
            # Example: "DEFENSE:3"
            match = re.search(r'DEFENSE:(\d+)', response)
            if match:
                result['defense_time'] = match.group(1)

        # Handle RELAY responses
        elif response.startswith('RELAY ') and response.endswith(' OK'):
            # Example: "RELAY 1 OK"
            match = re.search(r'RELAY (\d) OK', response)
            if match:
                result['relay_state'] = match.group(1)
                result['status'] = 'success'

        # Handle generic OK responses
        elif ' OK' in response:
            result['status'] = 'success'
            result['message'] = response

        return result

    def get_bulk_commands(self, parameters: Dict[str, Any]) -> List[str]:
        """
        Generate a list of commands for bulk sending based on LT32Pro documentation.

        Args:
            parameters: Dictionary of parameter names and values

        Returns:
            List of formatted commands in the correct sequence
        """
        commands = []

        # Always add TCP transmission mode command first
        tcp_command = self.get_command('transmission_mode', 'TCP')
        commands.append(tcp_command)

        # Define command sequence for proper device configuration according to LT32Pro documentation
        sequence = [
            # First configure network settings
            'apn_server', 'apn_user', 'apn_password',
            # Then configure server settings
            'server_ip', 'server_port', 'backup_server_ip', 'backup_server_port',
            # Configure reporting intervals
            'timer_ign_on', 'timer_ign_off', 'heartbeat_ign_on', 'heartbeat_ign_off',
            # Configure device behavior
            'ignition_type', 'lock_type', 'curve_sensor',
            # Configure sensitivity settings
            'vibration', 'sensitivity',
            # Configure other settings
            'gt06_protocol', 'network_select', 'sleep_mode',
            # Configure sleep time
            'sleep_time',
            # Configure movement detection
            'defense_time', 'vibration_window', 'blind_speed',
            # Configure relay settings
            'relay_gps_check'
        ]

        # Generate commands in the defined sequence
        for param in sequence:
            if param in parameters and parameters[param] is not None:
                try:
                    # Some parameters need context from other parameters
                    context = {}

                    # Handle timer parameters that need both values
                    if param == 'timer_ign_off' and 'timer_ign_on' in parameters:
                        context['timer_ign_on'] = parameters['timer_ign_on']
                    elif param == 'timer_ign_on' and 'timer_ign_off' in parameters:
                        context['timer_ign_off'] = parameters['timer_ign_off']

                    # Handle heartbeat parameters that need both values
                    elif param == 'heartbeat_ign_off' and 'heartbeat_ign_on' in parameters:
                        context['heartbeat_ign_on'] = parameters['heartbeat_ign_on']
                    elif param == 'heartbeat_ign_on' and 'heartbeat_ign_off' in parameters:
                        context['heartbeat_ign_off'] = parameters['heartbeat_ign_off']

                    # Handle APN parameters that need server, user, and password
                    elif param == 'apn_user' and 'apn_server' in parameters:
                        context['server'] = parameters['apn_server']
                    elif param == 'apn_password' and 'apn_server' in parameters and 'apn_user' in parameters:
                        context['server'] = parameters['apn_server']
                        context['user'] = parameters['apn_user']

                    # Handle server parameters that need IP and port
                    elif param == 'server_port' and 'server_ip' in parameters:
                        context['ip'] = parameters['server_ip']

                    # Handle vibration window parameters
                    elif param == 'vibration_window' and 'vibration' in parameters:
                        context['window'] = parameters['vibration']

                    command = self.get_command(param, parameters[param], context)
                    commands.append(command)
                except ValueError as e:
                    # Log error and skip parameters that can't be formatted
                    print(f"Error formatting command for {param}: {str(e)}")
                    continue

        return commands

    def get_device_info_commands(self) -> List[str]:
        """
        Get commands to retrieve device information based on LT32Pro documentation.

        Returns:
            List of commands to retrieve device information
        """
        return [
            self.get_command('get_imei', None),
            self.get_command('get_iccid', None),
            self.get_command('get_status', None),
            self.get_command('get_version', None)
        ]

    def get_check_config_commands(self) -> List[Tuple[str, str]]:
        """
        Get commands to check current device configuration based on LT32Pro documentation.

        Returns:
            List of tuples containing commands and their types
        """
        # Create a comprehensive list of commands to check all device settings
        return [
            # Basic device information
            (self.get_command('get_all_params', None), 'get_all_params'),

            # APN and server settings
            (self.get_command('query_apn', None), 'query_apn'),
            (self.get_command('query_server', None), 'query_server'),

            # Timer and heartbeat settings
            (self.get_command('query_timer', None), 'query_timer'),
            (self.get_command('query_heartbeat', None), 'query_heartbeat'),

            # Vibration and sensitivity settings
            (self.get_command('query_vibration', None), 'query_vibration'),
            (self.get_command('query_vibration_window', None), 'query_vibration_window'),
            (self.get_command('query_defense', None), 'query_defense'),

            # Network and protocol settings
            (self.get_command('query_protocol', None), 'query_protocol'),
            (self.get_command('query_network', None), 'query_network'),
            (self.get_command('query_volte', None), 'query_volte'),

            # Sleep mode settings
            (self.get_command('query_sleep_mode', None), 'query_sleep_mode'),
            (self.get_command('query_sleep_time', None), 'query_sleep_time'),

            # Ignition settings
            (self.get_command('query_ignition', None), 'query_ignition'),
            
            # Additional parameter queries
            (self.get_command('query_blind_speed', None), 'query_blind_speed'),
            (self.get_command('query_angle_reporting', None), 'query_angle_reporting'),
            (self.get_command('query_relay_gps', None), 'query_relay_gps'),
            (self.get_command('query_curve_sensor', None), 'query_curve_sensor'),
            (self.get_command('query_lock_type', None), 'query_lock_type'),
            (self.get_command('query_sensitivity', None), 'query_sensitivity')
        ]

    def get_parameter_query_commands(self) -> Dict[str, str]:
        """
        Get mapping of parameter names to their query commands.
        
        Returns:
            Dictionary mapping parameter names to query command types
        """
        return {
            'apn_server': 'query_apn',
            'apn_user': 'query_apn', 
            'apn_password': 'query_apn',
            'server_ip': 'query_server',
            'server_domain': 'query_server',
            'server_port': 'query_server',
            'server_protocol': 'query_server',
            'timer_ign_on': 'query_timer',
            'timer_ign_off': 'query_timer',
            'heartbeat_ign_on': 'query_heartbeat',
            'heartbeat_ign_off': 'query_heartbeat',
            'heartbeat_interval': 'query_heartbeat',
            'vibration': 'query_vibration',
            'defense_time': 'query_defense',
            'gt06_protocol': 'query_protocol',
            'network_select': 'query_network',
            'volte_switch': 'query_volte',
            'sleep_mode': 'query_sleep_mode',
            'sleep_time': 'query_sleep_time',
            'ignition_type': 'query_ignition',
            'vibration_window': 'query_vibration_window',
            'blind_speed': 'query_blind_speed',
            'angle_reporting': 'query_angle_reporting',
            'relay_gps_check': 'query_relay_gps',
            'curve_sensor': 'query_curve_sensor',
            'lock_type': 'query_lock_type',
            'sensitivity': 'query_sensitivity',
            'imsi': 'get_imsi',
            'device_status': 'get_status'
        }

    def get_response_patterns(self) -> Dict[str, str]:
        """
        Get regex patterns for parsing device responses.
        
        Returns:
            Dictionary mapping command types to their response patterns
        """
        return {
            # APN response pattern: "APN:server,user,password"
            'query_apn': r'APN:([^,]*),([^,]*),([^#\r\n]*)',
            
            # SERVER response pattern: "SERVER:type,address,port,protocol"
            'query_server': r'SERVER:(\d+),([^,]*),(\d+),(\d+)',
            
            # TIMER response pattern: "TIMER ACC ON:30s,ACC OFF:300s"
            'query_timer': r'TIMER ACC ON:(\d+)s,ACC OFF:(\d+)s',
            
            # HBT response pattern: "HBT ACC ON:180s,ACC OFF:180s"
            'query_heartbeat': r'HBT ACC ON:(\d+)s,ACC OFF:(\d+)s',
            
            # VIBL response pattern: "READOK: VIBL=3"
            'query_vibration': r'(?:READOK:\s*)?VIBL=(\d+)',
            
            # DEFENSE response pattern: "DEFENSE:3"
            'query_defense': r'DEFENSE:(\d+)',
            
            # GT06SEL response pattern: "READOK: GT06SEL=0"
            'query_protocol': r'(?:READOK:\s*)?GT06SEL=(\d+)',
            
            # NETSELECT response pattern: "READOK: NETSELECT=0"
            'query_network': r'(?:READOK:\s*)?NETSELECT=(\d+)',
            
            # VOLTESWITCH response pattern: "READOK: VOLTESWITCH=0"
            'query_volte': r'(?:READOK:\s*)?VOLTESWITCH=(\d+)',
            
            # SLPDISCONNECT response pattern: "READOK: SLPDISCONNECT=0"
            'query_sleep_mode': r'(?:READOK:\s*)?SLPDISCONNECT=(\d+)',
            
            # SLEEPT response pattern: "READOK: SLEEPT=60"
            'query_sleep_time': r'(?:READOK:\s*)?SLEEPT=(\d+)',
            
            # ACCLINE response pattern: "READOK: ACCLINE=0#ACC_CFG=0-000-000"
            'query_ignition': r'(?:READOK:\s*)?ACCLINE=(\d+)(?:#ACC_CFG=([^#\r\n]*))?',
            
            # VIBCHK response pattern: "READOK: VIBCHK=3:5"
            'query_vibration_window': r'(?:READOK:\s*)?VIBCHK=(\d+):(\d+)',
            
            # BLINDSPD response pattern: "READOK: BLINDSPD=5"
            'query_blind_speed': r'(?:READOK:\s*)?BLINDSPD=(\d+)',
            
            # ANGLEVALUE response pattern: "READOK: ANGLEVALUE=10-30"
            'query_angle_reporting': r'(?:READOK:\s*)?ANGLEVALUE=(\d+)-(\d+)',
            
            # SOURCE_OFF_TYPE response pattern: "READOK: SOURCE_OFF_TYPE=0"
            'query_relay_gps': r'(?:READOK:\s*)?SOURCE_OFF_TYPE=(\d+)',
            
            # CURVE response pattern: "READOK: CURVE=1"
            'query_curve_sensor': r'(?:READOK:\s*)?CURVE=(\d+)',
            
            # LOCKTYPE response pattern: "READOK: LOCKTYPE=0"
            'query_lock_type': r'(?:READOK:\s*)?LOCKTYPE=(\d+)',
            
            # SENSITIVITY response pattern: "READOK: SENSITIVITY=5"
            'query_sensitivity': r'(?:READOK:\s*)?SENSITIVITY=(\d+)',
            
            # Device info patterns
            'get_imei': r'(?:READOK:\s*)?IMEI[=:]?\s*(\d+)',
            'get_iccid': r'(?:READOK:\s*)?ICCID[=:]?\s*(\d+)',
            'get_imsi': r'(?:READOK:\s*)?IMSI[=:]?\s*(\d+)',
            'get_version': r'([A-Z0-9_]+\s+\d{4}\s+\d{1,2}\s+\d{1,2})',
            
            # Generic success pattern
            'success': r'(?:SETOK|READOK|OK)',
            
            # Error patterns
            'error': r'(?:ERROR|FAIL|INVALID)',
            
            # Missing patterns for comprehensive coverage
            'get_status': r'Battery:([^;]+);GPRS:([^;]+);GSMSignalLevel:([^;]+);ACC:([^;]+);GPS:([^;]+);Defense:([^;]+);',
            'get_all_params': r'IMEI:([^;]+);TIMER:([^;]+);SEMDS:([^;]+);HBT:([^;]+);Defense:([^;]+);'
        }

    def parse_query_response(self, response: str, command_type: str) -> Dict[str, Any]:
        """
        Parse device response for query commands with enhanced pattern matching.
        
        Args:
            response: The device response string
            command_type: The type of query command that was sent
            
        Returns:
            Dictionary with parsed parameter values and metadata
        """
        result = {
            'success': False,
            'command_type': command_type,
            'raw_response': response.strip(),
            'parameters': {},
            'error_message': None
        }
        
        patterns = self.get_response_patterns()
        
        # Check for error responses first
        if re.search(patterns.get('error', ''), response, re.IGNORECASE):
            result['error_message'] = f"Device returned error for {command_type}"
            return result
            
        # Check for success indicators
        if re.search(patterns.get('success', ''), response, re.IGNORECASE):
            result['success'] = True
        
        # Parse specific command responses
        if command_type in patterns:
            pattern = patterns[command_type]
            match = re.search(pattern, response, re.IGNORECASE)
            
            if match:
                result['success'] = True
                
                # Parse based on command type
                if command_type == 'query_apn':
                    result['parameters'] = {
                        'apn_server': match.group(1).strip(),
                        'apn_user': match.group(2).strip(),
                        'apn_password': match.group(3).strip()
                    }
                    
                elif command_type == 'query_server':
                    server_type = match.group(1)
                    result['parameters'] = {
                        'server_type': server_type,
                        'server_address': match.group(2).strip(),
                        'server_port': match.group(3).strip(),
                        'server_protocol': match.group(4).strip()
                    }
                    # Map to UI field names
                    if server_type == '0':  # IP address
                        result['parameters']['server_ip'] = result['parameters']['server_address']
                    else:  # Domain name
                        result['parameters']['server_domain'] = result['parameters']['server_address']
                        
                elif command_type == 'query_timer':
                    result['parameters'] = {
                        'timer_ign_on': match.group(1),
                        'timer_ign_off': match.group(2)
                    }
                    
                elif command_type == 'query_heartbeat':
                    result['parameters'] = {
                        'heartbeat_ign_on': match.group(1),
                        'heartbeat_ign_off': match.group(2)
                    }
                    
                elif command_type == 'query_vibration':
                    result['parameters'] = {
                        'vibration': match.group(1)
                    }
                    
                elif command_type == 'query_defense':
                    result['parameters'] = {
                        'defense_time': match.group(1)
                    }
                    
                elif command_type == 'query_protocol':
                    protocol_value = match.group(1)
                    # Map numeric value back to string
                    protocol_map = {'0': 'GT06-0x60', '1': 'CRX3', '2': 'GT06-0x12'}
                    result['parameters'] = {
                        'protocol': protocol_map.get(protocol_value, protocol_value)
                    }
                    
                elif command_type == 'query_network':
                    network_value = match.group(1)
                    # Map numeric value back to string
                    network_map = {'0': 'AUTO', '1': '4G', '2': '2G'}
                    result['parameters'] = {
                        'network_select': network_map.get(network_value, network_value)
                    }
                    
                elif command_type == 'query_volte':
                    volte_value = match.group(1)
                    # Map numeric value back to string
                    volte_map = {'0': '2G', '1': '4G'}
                    result['parameters'] = {
                        'volte_switch': volte_map.get(volte_value, volte_value)
                    }
                    
                elif command_type == 'query_sleep_mode':
                    sleep_value = match.group(1)
                    # Map numeric value back to string
                    sleep_map = {'0': 'Disabled', '1': 'Sleep', '2': 'Deep Sleep'}
                    result['parameters'] = {
                        'sleep_mode': sleep_map.get(sleep_value, sleep_value)
                    }
                    
                elif command_type == 'query_sleep_time':
                    result['parameters'] = {
                        'sleep_time': match.group(1)
                    }
                    
                elif command_type == 'query_ignition':
                    ignition_value = match.group(1)
                    # Map numeric value back to string
                    ignition_map = {'0': 'Digital', '1': 'Analog'}
                    result['parameters'] = {
                        'ignition_type': ignition_map.get(ignition_value, ignition_value)
                    }
                    if len(match.groups()) > 1 and match.group(2):
                        result['parameters']['ignition_config'] = match.group(2)
                        
                elif command_type == 'query_vibration_window':
                    result['parameters'] = {
                        'vibration_window': match.group(2),
                        'vibration_window_base': match.group(1)
                    }
                    
                elif command_type == 'query_blind_speed':
                    result['parameters'] = {
                        'blind_speed': match.group(1)
                    }
                    
                elif command_type == 'query_angle_reporting':
                    result['parameters'] = {
                        'angle_speed': match.group(1),
                        'angle_value': match.group(2)
                    }
                    
                elif command_type == 'query_relay_gps':
                    relay_value = match.group(1)
                    # Map numeric value back to string
                    relay_map = {'0': 'Check GPS', '1': 'Immediate'}
                    result['parameters'] = {
                        'relay_gps_check': relay_map.get(relay_value, relay_value)
                    }
                    
                elif command_type == 'query_curve_sensor':
                    curve_value = match.group(1)
                    # Map numeric value back to string
                    curve_map = {'0': 'Disabled', '1': 'Enabled', '2': 'Auto'}
                    result['parameters'] = {
                        'curve_sensor': curve_map.get(curve_value, curve_value)
                    }
                    
                elif command_type == 'query_lock_type':
                    lock_value = match.group(1)
                    # Map numeric value back to string
                    lock_map = {'0': 'PIN', '1': 'Card'}
                    result['parameters'] = {
                        'lock_type': lock_map.get(lock_value, lock_value)
                    }
                    
                elif command_type == 'query_sensitivity':
                    result['parameters'] = {
                        'sensitivity': match.group(1)
                    }
                    
                # Handle device info queries
                elif command_type == 'get_imei':
                    result['parameters'] = {
                        'imei': match.group(1)
                    }
                    
                elif command_type == 'get_iccid':
                    result['parameters'] = {
                        'iccid': match.group(1)
                    }
                    
                elif command_type == 'get_imsi':
                    result['parameters'] = {
                        'imsi': match.group(1)
                    }
                    
                elif command_type == 'get_version':
                    result['parameters'] = {
                        'version': match.group(1).strip()
                    }
                    
                elif command_type == 'get_status':
                    result['parameters'] = {
                        'battery': match.group(1).strip(),
                        'gprs_status': match.group(2).strip(),
                        'signal_level': match.group(3).strip(),
                        'acc_status': match.group(4).strip(),
                        'gps_status': match.group(5).strip(),
                        'defense_status': match.group(6).strip()
                    }
                    
                elif command_type == 'get_all_params':
                    result['parameters'] = {
                        'imei': match.group(1).strip(),
                        'timer_settings': match.group(2).strip(),
                        'semds': match.group(3).strip(),
                        'heartbeat_settings': match.group(4).strip(),
                        'defense_settings': match.group(5).strip()
                    }
            else:
                result['error_message'] = f"Could not parse response for {command_type}: {response}"
                
        else:
            result['error_message'] = f"No pattern defined for command type: {command_type}"
            
        return result

    def get_query_timeout_settings(self) -> Dict[str, float]:
        """
        Get timeout settings for different types of query commands.
        
        Returns:
            Dictionary mapping command types to timeout values in seconds
        """
        return {
            # Basic parameter queries - shorter timeout
            'query_apn': 5.0,
            'query_server': 5.0,
            'query_timer': 5.0,
            'query_heartbeat': 5.0,
            'query_vibration': 3.0,
            'query_defense': 3.0,
            'query_protocol': 3.0,
            'query_network': 3.0,
            'query_volte': 3.0,
            'query_sleep_mode': 3.0,
            'query_sleep_time': 3.0,
            'query_ignition': 5.0,
            'query_vibration_window': 3.0,
            'query_blind_speed': 3.0,
            'query_angle_reporting': 3.0,
            'query_relay_gps': 3.0,
            'query_curve_sensor': 3.0,
            'query_lock_type': 3.0,
            'query_sensitivity': 3.0,
            
            # Device info queries - longer timeout as they may take more time
            'get_imei': 10.0,
            'get_iccid': 10.0,
            'get_imsi': 10.0,
            'get_status': 8.0,
            'get_version': 8.0,
            'get_all_params': 15.0,  # Longest timeout for comprehensive query
            
            # Default timeout for unknown commands
            'default': 5.0
        }

    def get_command_timeout(self, command_type: str) -> float:
        """
        Get timeout value for a specific command type.
        
        Args:
            command_type: The type of command
            
        Returns:
            Timeout value in seconds
        """
        timeouts = self.get_query_timeout_settings()
        return timeouts.get(command_type, timeouts['default'])

    def create_parameter_mapping(self) -> Dict[str, List[str]]:
        """
        Create mapping from UI parameter names to the query commands needed to retrieve them.
        
        Returns:
            Dictionary mapping UI parameter names to list of required query command types
        """
        return {
            # APN parameters - all retrieved with single APN query
            'apn_server': ['query_apn'],
            'apn_user': ['query_apn'],
            'apn_password': ['query_apn'],
            
            # Server parameters - all retrieved with single SERVER query
            'server_ip': ['query_server'],
            'server_domain': ['query_server'],
            'server_port': ['query_server'],
            'server_protocol': ['query_server'],
            
            # Timer parameters - all retrieved with single TIMER query
            'timer_ign_on': ['query_timer'],
            'timer_ign_off': ['query_timer'],
            
            # Heartbeat parameters - all retrieved with single HBT query
            'heartbeat_ign_on': ['query_heartbeat'],
            'heartbeat_ign_off': ['query_heartbeat'],
            'heartbeat_interval': ['query_heartbeat'],
            
            # Individual parameter queries
            'vibration': ['query_vibration'],
            'defense_time': ['query_defense'],
            'protocol': ['query_protocol'],
            'network_select': ['query_network'],
            'volte_switch': ['query_volte'],
            'sleep_mode': ['query_sleep_mode'],
            'sleep_time': ['query_sleep_time'],
            'ignition_type': ['query_ignition'],
            'vibration_window': ['query_vibration_window'],
            'blind_speed': ['query_blind_speed'],
            'angle_reporting': ['query_angle_reporting'],
            'relay_gps_check': ['query_relay_gps'],
            'curve_sensor': ['query_curve_sensor'],
            'lock_type': ['query_lock_type'],
            'sensitivity': ['query_sensitivity'],
            
            # Device information
            'imei': ['get_imei'],
            'iccid': ['get_iccid'],
            'imsi': ['get_imsi'],
            'version': ['get_version'],
            'device_status': ['get_status']
        }
