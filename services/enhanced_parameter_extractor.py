"""
Enhanced Parameter Extractor for LT32Pro Device Responses

This module provides functionality to parse LT32Pro device responses and extract
individual parameters for profile file creation and validation.
"""

import re
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EnhancedParameterExtractor:
    """
    Extracts individual parameters from LT32Pro device responses.
    
    Converts device-specific response formats into standardized parameter
    dictionaries for profile file creation and validation.
    """
    
    # Protocol mapping for GT06SEL values
    PROTOCOL_MAPPING = {
        "0": "GT06",
        "1": "GT06N", 
        "2": "CRX",
        "3": "CONCOX",
        "4": "H02"
    }
    
    def __init__(self):
        """Initialize the parameter extractor."""
        self.logger = logging.getLogger(__name__)
    
    def extract_parameters_from_responses(self, device_responses: Dict[str, str]) -> Dict[str, str]:
        """
        Convert device responses to individual parameters.
        
        Args:
            device_responses: Dictionary of command -> response mappings
            
        Returns:
            Dictionary of extracted parameters
        """
        parameters = {}
        
        try:
            # Process each response type
            for command, response in device_responses.items():
                if not response:
                    continue
                    
                # Parse APN responses
                if command.upper() in ['APN', 'ATSMS:APN#']:
                    apn_params = self._parse_apn_response(response)
                    parameters.update(apn_params)
                
                # Parse SERVER responses
                elif command.upper() in ['SERVER', 'ATSMS:SERVER#']:
                    server_params = self._parse_server_response(response)
                    parameters.update(server_params)
                
                # Parse READOK responses (IMEI, ICCID, GT06SEL, POSBYACK)
                elif 'READOK' in response.upper():
                    readok_params = self._parse_readok_response(response)
                    parameters.update(readok_params)
                
                # Parse STATUS responses
                elif command.upper() in ['STATUS', 'ATSMS:STATUS#']:
                    status_params = self._parse_status_response(response)
                    parameters.update(status_params)
                
                # Parse VERSION responses
                elif command.upper() in ['VERSION', 'ATSMS:VERSION#']:
                    version_params = self._parse_version_response(response)
                    parameters.update(version_params)
            
            # Add default parameters
            parameters = self.add_default_parameters(parameters)
            
            self.logger.info(f"Extracted {len(parameters)} parameters from device responses")
            return parameters
            
        except Exception as e:
            self.logger.error(f"Error extracting parameters: {e}")
            return parameters
    
    def _parse_apn_response(self, response: str) -> Dict[str, str]:
        """
        Parse APN response format: APN:server,user,password
        
        Args:
            response: APN response string
            
        Returns:
            Dictionary with apn_server, apn_user, apn_password
        """
        parameters = {}
        
        try:
            # Match APN:server,user,password format
            apn_match = re.search(r'APN:([^,]*),([^,]*),([^,\r\n]*)', response, re.IGNORECASE)
            
            if apn_match:
                parameters['apn_server'] = apn_match.group(1).strip()
                parameters['apn_user'] = apn_match.group(2).strip()
                parameters['apn_password'] = apn_match.group(3).strip()
                
                self.logger.debug(f"Parsed APN: server={parameters['apn_server']}, "
                                f"user={parameters['apn_user']}, password=***")
            else:
                self.logger.warning(f"Could not parse APN response: {response}")
                
        except Exception as e:
            self.logger.error(f"Error parsing APN response '{response}': {e}")
            
        return parameters
    
    def _parse_server_response(self, response: str) -> Dict[str, str]:
        """
        Parse SERVER response format: SERVER:0,IP,PORT,0
        
        Args:
            response: SERVER response string
            
        Returns:
            Dictionary with server_ip, server_port, server_type
        """
        parameters = {}
        
        try:
            # Match SERVER:0,IP,PORT,0 format
            server_match = re.search(r'SERVER:(\d+),([^,]+),(\d+),(\d+)', response, re.IGNORECASE)
            
            if server_match:
                parameters['server_type'] = server_match.group(1).strip()
                parameters['server_ip'] = server_match.group(2).strip()
                parameters['server_port'] = server_match.group(3).strip()
                parameters['server_protocol'] = server_match.group(4).strip()
                
                self.logger.debug(f"Parsed SERVER: ip={parameters['server_ip']}, "
                                f"port={parameters['server_port']}, type={parameters['server_type']}")
            else:
                self.logger.warning(f"Could not parse SERVER response: {response}")
                
        except Exception as e:
            self.logger.error(f"Error parsing SERVER response '{response}': {e}")
            
        return parameters
    
    def _parse_readok_response(self, response: str) -> Dict[str, str]:
        """
        Parse READOK response formats:
        - READOK: IMEI=value
        - READOK: ICCID=value  
        - READOK: GT06SEL=value
        - READOK: POSBYACK=value
        
        Args:
            response: READOK response string
            
        Returns:
            Dictionary with extracted parameters
        """
        parameters = {}
        
        try:
            # Parse IMEI
            imei_match = re.search(r'READOK:\s*IMEI=([^\r\n]+)', response, re.IGNORECASE)
            if imei_match:
                imei_value = imei_match.group(1).strip()
                parameters['device_imei'] = imei_value
                parameters['device_id'] = imei_value
                parameters['imei'] = imei_value
                self.logger.debug(f"Parsed IMEI: {imei_value}")
            
            # Parse ICCID
            iccid_match = re.search(r'READOK:\s*ICCID=([^\r\n]+)', response, re.IGNORECASE)
            if iccid_match:
                iccid_value = iccid_match.group(1).strip()
                parameters['device_iccid'] = iccid_value
                parameters['iccid'] = iccid_value
                self.logger.debug(f"Parsed ICCID: {iccid_value}")
            
            # Parse GT06SEL (protocol)
            protocol_match = re.search(r'READOK:\s*GT06SEL=([^\r\n]+)', response, re.IGNORECASE)
            if protocol_match:
                protocol_value = protocol_match.group(1).strip()
                parameters['protocol'] = protocol_value
                parameters['protocol_name'] = self.PROTOCOL_MAPPING.get(protocol_value, f"Unknown({protocol_value})")
                self.logger.debug(f"Parsed Protocol: {protocol_value} -> {parameters['protocol_name']}")
            
            # Parse POSBYACK (TCP acknowledgment)
            posbyack_match = re.search(r'READOK:\s*POSBYACK=([^\r\n]+)', response, re.IGNORECASE)
            if posbyack_match:
                posbyack_value = posbyack_match.group(1).strip()
                parameters['tcp_ack'] = posbyack_value
                parameters['tcp_acknowledgment'] = posbyack_value
                self.logger.debug(f"Parsed POSBYACK: {posbyack_value}")
                
        except Exception as e:
            self.logger.error(f"Error parsing READOK response '{response}': {e}")
            
        return parameters
    
    def _parse_status_response(self, response: str) -> Dict[str, str]:
        """
        Parse STATUS response format: Battery:4.14V;GPRS:Online;GSM Signal Level:31;ACC:ON;GPS:Successful positioning
        
        Args:
            response: STATUS response string
            
        Returns:
            Dictionary with status parameters
        """
        parameters = {}
        
        try:
            # Parse battery voltage
            battery_match = re.search(r'Battery:([^;]+)', response, re.IGNORECASE)
            if battery_match:
                parameters['battery_voltage'] = battery_match.group(1).strip()
            
            # Parse GPRS status
            gprs_match = re.search(r'GPRS:([^;]+)', response, re.IGNORECASE)
            if gprs_match:
                parameters['gprs_status'] = gprs_match.group(1).strip()
            
            # Parse GSM signal level
            gsm_match = re.search(r'GSM Signal Level:([^;]+)', response, re.IGNORECASE)
            if gsm_match:
                parameters['gsm_signal_level'] = gsm_match.group(1).strip()
            
            # Parse ACC status
            acc_match = re.search(r'ACC:([^;]+)', response, re.IGNORECASE)
            if acc_match:
                parameters['acc_status'] = acc_match.group(1).strip()
            
            # Parse GPS status
            gps_match = re.search(r'GPS:([^;]+)', response, re.IGNORECASE)
            if gps_match:
                parameters['gps_status'] = gps_match.group(1).strip()
                
            self.logger.debug(f"Parsed STATUS response with {len(parameters)} status parameters")
            
        except Exception as e:
            self.logger.error(f"Error parsing STATUS response '{response}': {e}")
            
        return parameters
    
    def _parse_version_response(self, response: str) -> Dict[str, str]:
        """
        Parse VERSION response format: LT32Pro_10F8A_B53_V6.56 2025-06-26
        
        Args:
            response: VERSION response string
            
        Returns:
            Dictionary with version parameters
        """
        parameters = {}
        
        try:
            # Extract version information
            version_match = re.search(r'(LT32Pro[^\s]+)\s*([^\r\n]*)', response.strip(), re.IGNORECASE)
            if version_match:
                parameters['device_version'] = version_match.group(1).strip()
                if version_match.group(2).strip():
                    parameters['firmware_date'] = version_match.group(2).strip()
                
                self.logger.debug(f"Parsed VERSION: {parameters['device_version']}")
            else:
                # Fallback: use entire response as version
                parameters['device_version'] = response.strip()
                
        except Exception as e:
            self.logger.error(f"Error parsing VERSION response '{response}': {e}")
            
        return parameters
    
    def add_default_parameters(self, parameters: Dict[str, str]) -> Dict[str, str]:
        """
        Add default values for commonly required parameters.
        
        Args:
            parameters: Existing parameters dictionary
            
        Returns:
            Parameters dictionary with default values added
        """
        defaults = {
            'heartbeat_interval': '300',  # 5 minutes
            'report_interval': '60',      # 1 minute
            'timezone': '0',              # UTC
            'device_name': self._generate_device_name(parameters),
            'upload_interval': '30',      # 30 seconds
            'sleep_mode': '0',           # Disabled
            'power_save_mode': '0',      # Disabled
            'tracking_mode': '1',        # Normal tracking
        }
        
        # Only add defaults if they don't already exist
        for key, value in defaults.items():
            if key not in parameters:
                parameters[key] = value
        
        self.logger.debug(f"Added {len(defaults)} default parameters")
        return parameters
    
    def _generate_device_name(self, parameters: Dict[str, str]) -> str:
        """
        Generate a device name based on available parameters.
        
        Args:
            parameters: Current parameters dictionary
            
        Returns:
            Generated device name
        """
        # Use last 4 digits of IMEI if available
        if 'device_imei' in parameters and parameters['device_imei']:
            imei = parameters['device_imei']
            if len(imei) >= 4:
                return f"LT32Pro_{imei[-4:]}"
        
        # Use device version if available
        if 'device_version' in parameters and parameters['device_version']:
            version = parameters['device_version']
            if 'LT32Pro' in version:
                return version.split()[0]  # Take first part
        
        # Default name
        return "LT32Pro_Device"
    
    def validate_extracted_parameters(self, parameters: Dict[str, str]) -> Dict[str, str]:
        """
        Validate and clean extracted parameters.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            Validated parameters dictionary
        """
        validated = {}
        
        for key, value in parameters.items():
            if value is not None and str(value).strip():
                validated[key] = str(value).strip()
            else:
                self.logger.warning(f"Skipping empty parameter: {key}")
        
        return validated