"""
LT32Pro Command Formatter

This module provides command formatting functionality for LT32Pro device communication
via USB serial interface. All commands must be prefixed with "ATSMS:" for USB communication.
"""

import re
from typing import Dict, List, Optional


class LT32ProCommandFormatter:
    """
    Formats commands for LT32Pro device communication via USB serial interface.
    
    All commands sent via USB must be prefixed with "ATSMS:" and properly formatted
    according to the LT32Pro protocol specification.
    """
    
    # Command mappings for read operations
    READ_COMMAND_MAPPINGS = {
        'APN': 'APN#',
        'SERVER': 'SERVER#',
        'STATUS': 'STATUS#',
        'VERSION': 'VERSION#',
        'IMEI': 'CXCS#IMEI',
        'ICCID': 'CXCS#ICCID',
        'IMSI': 'CXCS#IMSI',
        'GT06SEL': 'CXCS#GT06SEL',
        'POSBYACK': 'CXCS#POSBYACK',
        'NETSELECT': 'CXCS#NETSELECT',
        'TERIID': 'CXCS#TERIID',
        'TIMER': 'TIMER#',
        'HBT': 'HBT#',
        'ACCLINE': 'CXCS#ACCLINE#ACC_CFG',
        'ACC_CFG': 'CXCS#ACCLINE#ACC_CFG',
        'SPEED': 'SPEED#',
        'SPD_LED_SHOW': 'CXCS#SPD_LED_SHOW',
        'SLPDISCONNECT': 'CXCS#SLPDISCONNECT',
        'SLEEPT': 'CXCS#SLEEPT',
        'ANGLEVALUE': 'CXCS#ANGLEVALUE',
        'BATALM': 'BATALM#',
        'POWERALM': 'POWERALM#',
        'VIBL': 'CXCS#VIBL',
        'VIBCHK': 'CXCS#VIBCHK',
        'JAMMER': 'JAMMER#',
        'JAMRELAY': 'JAMRELAY#',
        'JAMCFG': 'JAMCFG#',
        'MILEAGE': 'MILEAGE#',
        'ACCONT': 'ACCONT#',
        'DEFENSE': 'DEFENSE#',
        'SOURCE_OFF_TYPE': 'CXCS#SOURCE_OFF_TYPE',
        'RELAY': 'RELAY#',
        'SENDS': 'SENDS#',
        'SENALM': 'SENALM#',
        'MOVEALMFUN': 'CXCS#MOVEALMFUN',
        'BATSLPVALUE': 'CXCS#BATSLPVALUE',
        'PARAM': 'PARAM#',
    }
    
    # Alternative command mappings for devices that don't support CXCS# commands
    ALTERNATIVE_READ_COMMANDS = {
        'SLPDISCONNECT': ['CXCS#SLPDISCONNECT', 'STATUS#'],  # Fallback to STATUS for sleep info
        'SLEEPT': ['CXCS#SLEEPT', 'STATUS#'],  # Fallback to STATUS for sleep time info
        'ANGLEVALUE': ['CXCS#ANGLEVALUE'],
        'VIBL': ['CXCS#VIBL'],
        'VIBCHK': ['CXCS#VIBCHK'],
        'GT06SEL': ['CXCS#GT06SEL'],
        'POSBYACK': ['CXCS#POSBYACK'],
        'NETSELECT': ['CXCS#NETSELECT'],
        'SPD_LED_SHOW': ['CXCS#SPD_LED_SHOW'],
        'IMEI': ['CXCS#IMEI', 'STATUS#'],
        'ICCID': ['CXCS#ICCID', 'STATUS#'],
        'IMSI': ['CXCS#IMSI', 'STATUS#'],
        'ACCLINE': ['CXCS#ACCLINE#ACC_CFG'],
        'ACC_CFG': ['CXCS#ACCLINE#ACC_CFG'],
        'JAMCFG': ['JAMCFG#']
    }
    
    # Commands that are known to work on most LT32Pro devices
    RELIABLE_COMMANDS = [
        'STATUS', 'VERSION', 'APN', 'SERVER', 'TIMER', 'HBT',
        'SPEED', 'BATALM', 'POWERALM', 'JAMMER', 'JAMRELAY',
        'MILEAGE', 'ACCONT'
    ]
    
    # Command mappings for write operations
    WRITE_COMMAND_MAPPINGS = {
        'APN': 'APN,{value}#',
        'SERVER': 'SERVER,{value}#',
        'GT06SEL': 'SZCS#GT06SEL={value}',
        'POSBYACK': 'SZCS#POSBYACK={value}',
        'TIMER': 'TIMER,{value}#',
        'HBT': 'HBT,{value}#',
        'ACCLINE': 'SZCS#ACCLINE={value}#ACC_CFG={value2}',
        'SPEED': 'SPEED,{value}#',
        'SLPDISCONNECT': 'SZCS#SLPDISCONNECT={value}',
        'SLEEPT': 'SZCS#SLEEPT={value}',
        'ANGLEVALUE': 'SZCS#ANGLEVALUE={value}',
        'BATALM': 'BATALM,{value}#',
        'POWERALM': 'POWERALM,{value}#',
        'VIBL': 'SZCS#VIBL={value}',
        'JAMMER': 'JAMMER,{value}#',
        'JAMRELAY': 'JAMRELAY,{value}#',
        'MILEAGE': 'MILEAGE={value}#',
        'ACCONT': 'ACCONT,{value}#',
        'SOURCE_OFF_TYPE': 'SZCS#SOURCE_OFF_TYPE={value}',
        'RELAY': 'RELAY,{value}#',
        'SENDS': 'SENDS,{value}#',
        'SENALM': 'SENALM,{value}#',
        'BATSLPVALUE': 'SZCS#BATSLPVALUE={value}',
    }
    
    # Valid protocol values for GT06SEL
    VALID_PROTOCOLS = {'0', '1', '2'}
    
    # Valid TCP ACK values for POSBYACK
    VALID_TCP_ACK = {'0', '1'}
    
    def __init__(self):
        """Initialize the command formatter."""
        pass
    
    def format_read_command(self, command: str) -> str:
        """
        Format read commands with ATSMS prefix for USB communication.
        """
        if not command:
            raise ValueError("Command cannot be empty")
            
        command = command.upper().strip()
        
        if command not in self.READ_COMMAND_MAPPINGS:
            raise ValueError(f"Unsupported read command: {command}")
        
        base_command = self.READ_COMMAND_MAPPINGS[command]
        formatted_command = f"ATSMS:{base_command}"
        
        return formatted_command
    
    def format_write_command(self, command: str, value: str) -> str:
        """
        Format write commands with ATSMS prefix for USB communication.
        """
        if not command:
            raise ValueError("Command cannot be empty")
        if not value:
            raise ValueError("Value cannot be empty")
            
        command = command.upper().strip()
        value = value.strip()
        
        if command not in self.WRITE_COMMAND_MAPPINGS:
            raise ValueError(f"Unsupported write command: {command}")

        # Special handling for JAMMER: when state is OFF, do not include the extra mode/field
        if command == 'JAMMER':
            # Accept values like 'OFF', 'OFF,0', 'ON,1' etc.
            parts = [p.strip() for p in value.split(',') if p is not None]
            if len(parts) == 0:
                raise ValueError("JAMMER command requires at least a state value")
            state = parts[0].upper()
            if state == 'OFF':
                return f"ATSMS:JAMMER,OFF#"
            # For non-OFF states, preserve original formatting (include remaining parts if any)
            rest = ','.join(parts[1:]) if len(parts) > 1 else ''
            base = f"JAMMER,{state}"
            if rest:
                base = f"{base},{rest}"
            base = f"{base}#"
            return f"ATSMS:{base}"

        # Special handling for SPEED: when state is OFF, do not include trailing numeric fields
        if command == 'SPEED':
            # Accept values like 'OFF', 'OFF,15,0,0', 'ON,80,1,0' etc.
            parts = [p.strip() for p in value.split(',') if p is not None]
            if len(parts) == 0:
                raise ValueError("SPEED command requires at least a state value")
            state = parts[0].upper()
            if state == 'OFF':
                return f"ATSMS:SPEED,OFF#"
            # For non-OFF states, preserve original formatting and append '#'
            rest = ','.join(parts[1:]) if len(parts) > 1 else ''
            base = f"SPEED,{state}"
            if rest:
                base = f"{base},{rest}"
            base = f"{base}#"
            return f"ATSMS:{base}"

        self._validate_write_command_value(command, value)

        base_command = self.WRITE_COMMAND_MAPPINGS[command].format(value=value)
        return f"ATSMS:{base_command}"
    
    def _validate_write_command_value(self, command: str, value: str) -> None:
        """
        Validate command values according to LT32Pro specifications.
        """
        if command == 'GT06SEL':
            if value not in self.VALID_PROTOCOLS:
                raise ValueError(f"Invalid protocol value: {value}. Must be one of {self.VALID_PROTOCOLS}")
                
        elif command == 'POSBYACK':
            if value not in self.VALID_TCP_ACK:
                raise ValueError(f"Invalid TCP ACK value: {value}. Must be one of {self.VALID_TCP_ACK}")
                
        elif command == 'APN':
            parts = value.split(',')
            if len(parts) != 3:
                raise ValueError("APN value must be in format: server,user,password")
            if not parts[0]:
                raise ValueError("APN server cannot be empty")
                
        elif command == 'SERVER':
            parts = value.split(',')
            if len(parts) != 4:
                raise ValueError("SERVER value must be in format: type,ip,port,protocol")
            
            try:
                server_type = int(parts[0])
                if server_type not in [0, 1]:
                    raise ValueError("Server type must be 0 (IP) or 1 (domain)")
                
                port = int(parts[2])
                if not (1 <= port <= 65535):
                    raise ValueError("Port must be between 1 and 65535")
                
                protocol = int(parts[3])
                if protocol != 0:
                    raise ValueError("Protocol must be 0 (TCP)")
                    
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError("SERVER numeric values must be valid integers")
                raise
    
    def validate_command_syntax(self, formatted_command: str) -> bool:
        """
        Validate that a formatted command follows proper LT32Pro syntax.
        """
        if not formatted_command:
            raise ValueError("Command cannot be empty")
            
        if not formatted_command.startswith("ATSMS:"):
            raise ValueError("USB commands must start with 'ATSMS:' prefix")
            
        command_body = formatted_command[6:]
        
        valid_patterns = [
            r'^[A-Z]+#$',                    # Simple commands like APN#, STATUS#
            r'^[A-Z]+,.+#$',                 # Commands with values like APN,value#
            r'^SZCS#[A-Z0-9]+$',            # Read commands like SZCS#IMEI, SZCS#GT06SEL
            r'^SZCS#[A-Z0-9]+=.+$',         # Set commands like SZCS#GT06SEL=2
            r'^CXCS#[A-Z0-9_]+$',           # Legacy read commands like CXCS#IMEI, CXCS#GT06SEL, CXCS#SPD_LED_SHOW
            r'^CXCS#[A-Z0-9_]+#[A-Z0-9_]+$' # Multi-part legacy commands like CXCS#ACCLINE#ACC_CFG
        ]
        
        for pattern in valid_patterns:
            if re.match(pattern, command_body):
                return True
                
        raise ValueError(f"Invalid command syntax: {formatted_command}")
    
    def get_supported_read_commands(self) -> List[str]:
        """
        Get list of supported read commands.
        """
        return list(self.READ_COMMAND_MAPPINGS.keys())
    
    def get_supported_write_commands(self) -> List[str]:
        """
        Get list of supported write commands.
        """
        return list(self.WRITE_COMMAND_MAPPINGS.keys())
    
    def is_read_command_supported(self, command: str) -> bool:
        """
        Check if a read command is supported.
        """
        return command.upper().strip() in self.READ_COMMAND_MAPPINGS
    
    def is_write_command_supported(self, command: str) -> bool:
        """
        Check if a write command is supported.
        """
        return command.upper().strip() in self.WRITE_COMMAND_MAPPINGS
    
    def get_alternative_read_commands(self, command: str) -> List[str]:
        """
        Get alternative read commands for devices that don't support CXCS# commands.
        """
        command = command.upper().strip()
        return self.ALTERNATIVE_READ_COMMANDS.get(command, [])
    
    def has_alternative_commands(self, command: str) -> bool:
        """
        Check if a command has alternative formats available.
        """
        command = command.upper().strip()
        return command in self.ALTERNATIVE_READ_COMMANDS
