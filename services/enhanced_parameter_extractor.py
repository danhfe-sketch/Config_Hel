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
        Convert device responses to individual parameters with comprehensive error handling.
        
        Args:
            device_responses: Dictionary of command -> response mappings
            
        Returns:
            Dictionary of extracted parameters
            
        Requirements: 5.1, 5.2 - Log errors and continue processing other parameters
        """
        parameters = {}
        extraction_errors = []
        successful_extractions = 0
        
        try:
            # Process each response type with individual error handling
            for command, response in device_responses.items():
                try:
                    if not response:
                        self.logger.debug(f"Skipping empty response for command: {command}")
                        continue
                    
                    extracted_params = {}
                    
                    # Parse APN responses
                    if command.upper() in ['APN', 'ATSMS:APN#']:
                        extracted_params = self._safe_parse_apn_response(response, command)
                    
                    # Parse SERVER responses
                    elif command.upper() in ['SERVER', 'ATSMS:SERVER#']:
                        extracted_params = self._safe_parse_server_response(response, command)
                    
                    # Parse READOK responses (IMEI, ICCID, GT06SEL, POSBYACK)
                    elif 'READOK' in response.upper():
                        extracted_params = self._safe_parse_readok_response(response, command)
                    
                    # Parse STATUS responses
                    elif command.upper() in ['STATUS', 'ATSMS:STATUS#']:
                        extracted_params = self._safe_parse_status_response(response, command)
                    
                    # Parse VERSION responses
                    elif command.upper() in ['VERSION', 'ATSMS:VERSION#']:
                        extracted_params = self._safe_parse_version_response(response, command)
                    
                    # Parse HOURMETER/ACCONT responses
                    elif command.upper() in ['HOURMETER', 'ACCONT', 'ATSMS:ACCONT#']:
                        extracted_params = self._safe_parse_hourmeter_response(response, command)
                    
                    # Parse ODOMETER/MILEAGE responses
                    elif command.upper() in ['ODOMETER', 'MILEAGE', 'ATSMS:MILEAGE#']:
                        extracted_params = self._safe_parse_odometer_response(response, command)
                    
                    else:
                        self.logger.debug(f"No parser available for command: {command}")
                        continue
                    
                    # Update parameters with extracted values
                    if extracted_params:
                        parameters.update(extracted_params)
                        successful_extractions += 1
                        self.logger.debug(f"Successfully extracted {len(extracted_params)} parameters from {command}")
                    else:
                        self.logger.warning(f"No parameters extracted from {command} response")
                        
                except Exception as e:
                    error_msg = f"Failed to process {command} response: {str(e)}"
                    extraction_errors.append(error_msg)
                    self.logger.error(error_msg)
                    # Continue processing other responses (Requirement 5.2)
                    continue
            
            # Add default parameters with error handling
            try:
                parameters = self.add_default_parameters(parameters)
            except Exception as e:
                error_msg = f"Failed to add default parameters: {str(e)}"
                extraction_errors.append(error_msg)
                self.logger.error(error_msg)
            
            # Log extraction summary
            total_responses = len(device_responses)
            if extraction_errors:
                self.logger.warning(f"Parameter extraction completed with {len(extraction_errors)} errors. "
                                  f"Successfully processed {successful_extractions}/{total_responses} responses. "
                                  f"Extracted {len(parameters)} total parameters.")
            else:
                self.logger.info(f"Successfully extracted {len(parameters)} parameters from {total_responses} device responses")
            
            return parameters
            
        except Exception as e:
            # Handle catastrophic failure
            error_msg = f"Critical error during parameter extraction: {str(e)}"
            self.logger.error(error_msg)
            extraction_errors.append(error_msg)
            
            # Return whatever parameters we managed to extract
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
            
            # Parse hourmeter from "Get ACC ON Time:value Minute" format in status
            acc_on_time_match = re.search(r'Get\s+ACC\s+ON\s+Time[=:](\d+)', response, re.IGNORECASE)
            if acc_on_time_match:
                parameters['acc_on_time'] = acc_on_time_match.group(1)
                self.logger.debug(f"Extracted acc_on_time from status: {acc_on_time_match.group(1)}")
            
            # Parse odometer from "Cur Mileage Value:valueKM" format in status
            cur_mileage_match = re.search(r'Cur\s+Mileage\s+Value[=:](\d+)', response, re.IGNORECASE)
            if cur_mileage_match:
                parameters['current_mileage'] = cur_mileage_match.group(1)
                self.logger.debug(f"Extracted current_mileage from status: {cur_mileage_match.group(1)}")
                
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
    
    def _safe_parse_apn_response(self, response: str, command: str) -> Dict[str, str]:
        """Safely parse APN response with error handling."""
        try:
            return self._parse_apn_response(response)
        except Exception as e:
            self.logger.error(f"Error parsing APN response for {command}: {e}")
            return {}
    
    def _safe_parse_server_response(self, response: str, command: str) -> Dict[str, str]:
        """Safely parse SERVER response with error handling."""
        try:
            return self._parse_server_response(response)
        except Exception as e:
            self.logger.error(f"Error parsing SERVER response for {command}: {e}")
            return {}
    
    def _safe_parse_readok_response(self, response: str, command: str) -> Dict[str, str]:
        """Safely parse READOK response with error handling."""
        try:
            return self._parse_readok_response(response)
        except Exception as e:
            self.logger.error(f"Error parsing READOK response for {command}: {e}")
            return {}
    
    def _safe_parse_status_response(self, response: str, command: str) -> Dict[str, str]:
        """Safely parse STATUS response with error handling."""
        try:
            return self._parse_status_response(response)
        except Exception as e:
            self.logger.error(f"Error parsing STATUS response for {command}: {e}")
            return {}
    
    def _safe_parse_version_response(self, response: str, command: str) -> Dict[str, str]:
        """Safely parse VERSION response with error handling."""
        try:
            return self._parse_version_response(response)
        except Exception as e:
            self.logger.error(f"Error parsing VERSION response for {command}: {e}")
            return {}
    
    def _safe_parse_hourmeter_response(self, response: str, command: str) -> Dict[str, str]:
        """Safely parse HOURMETER response with error handling."""
        try:
            return self._parse_hourmeter_response(response, command)
        except Exception as e:
            self.logger.error(f"Error parsing HOURMETER response for {command}: {e}")
            return {}
    
    def _safe_parse_odometer_response(self, response: str, command: str) -> Dict[str, str]:
        """Safely parse ODOMETER response with error handling."""
        try:
            return self._parse_odometer_response(response)
        except Exception as e:
            self.logger.error(f"Error parsing ODOMETER response for {command}: {e}")
            return {}
    
    def _parse_hourmeter_response(self, response: str, command: str = '') -> Dict[str, str]:
        """
        Parse HOURMETER/ACCONT response formats.
        
        Handles various formats:
        - "ACCONT=5678"
        - "Get ACC ON Time:5678 Minute"
        - "Engine Hours: 1234 hours"
        
        Args:
            response: Hourmeter response string
            command: Command that generated this response
            
        Returns:
            Dictionary with hourmeter parameters
        """
        parameters = {}
        
        try:
            # Pattern to match ACCONT=value format
            accont_match = re.search(r'ACCONT[=:](\d+)', response, re.IGNORECASE)
            if accont_match:
                # Use different parameter names based on the command to avoid conflicts
                if command.upper() == 'ACCONT':
                    param_name = 'accont'
                else:
                    param_name = 'hourmeter'
                
                parameters[param_name] = accont_match.group(1)
                self.logger.debug(f"Extracted {param_name} from ACCONT format: {accont_match.group(1)}")
                return parameters
            
            # Pattern to match "Get ACC ON Time:value Minute" format
            acc_on_time_match = re.search(r'Get\s+ACC\s+ON\s+Time[=:](\d+)', response, re.IGNORECASE)
            if acc_on_time_match:
                parameters['acc_on_time'] = acc_on_time_match.group(1)
                self.logger.debug(f"Extracted acc_on_time: {acc_on_time_match.group(1)}")
                return parameters
            
            # Pattern to match "Engine Hours: value hours" format
            engine_hours_match = re.search(r'Engine\s+Hours[=:]?\s*(\d+)', response, re.IGNORECASE)
            if engine_hours_match:
                parameters['engine_hours'] = engine_hours_match.group(1)
                self.logger.debug(f"Extracted engine_hours: {engine_hours_match.group(1)}")
                return parameters
            
            # Fallback: try to extract any numeric value
            numeric_match = re.search(r'(\d+)', response)
            if numeric_match:
                parameters['hourmeter'] = numeric_match.group(1)
                self.logger.debug(f"Extracted hourmeter (fallback): {numeric_match.group(1)}")
                return parameters
            
            self.logger.warning(f"Could not parse hourmeter response: {response}")
            
        except Exception as e:
            self.logger.error(f"Error parsing hourmeter response '{response}': {e}")
        
        return parameters
    
    def _parse_odometer_response(self, response: str) -> Dict[str, str]:
        """
        Parse ODOMETER/MILEAGE response formats.
        
        Handles various formats:
        - "MILEAGE=12345"
        - "Cur Mileage Value:12345KM"
        - "Odometer: 98765 km"
        
        Args:
            response: Odometer response string
            
        Returns:
            Dictionary with odometer parameters
        """
        parameters = {}
        
        try:
            # Pattern to match MILEAGE=value format
            mileage_match = re.search(r'MILEAGE[=:](\d+)', response, re.IGNORECASE)
            if mileage_match:
                parameters['odometer'] = mileage_match.group(1)
                self.logger.debug(f"Extracted odometer from MILEAGE format: {mileage_match.group(1)}")
                return parameters
            
            # Pattern to match "Cur Mileage Value:valueKM" format
            cur_mileage_match = re.search(r'Cur\s+Mileage\s+Value[=:](\d+)', response, re.IGNORECASE)
            if cur_mileage_match:
                parameters['current_mileage'] = cur_mileage_match.group(1)
                self.logger.debug(f"Extracted current_mileage: {cur_mileage_match.group(1)}")
                return parameters
            
            # Pattern to match "Odometer: value km" format
            odometer_match = re.search(r'Odometer[=:]?\s*(\d+)', response, re.IGNORECASE)
            if odometer_match:
                parameters['odometer'] = odometer_match.group(1)
                self.logger.debug(f"Extracted odometer: {odometer_match.group(1)}")
                return parameters
            
            # Fallback: try to extract any numeric value
            numeric_match = re.search(r'(\d+)', response)
            if numeric_match:
                parameters['odometer'] = numeric_match.group(1)
                self.logger.debug(f"Extracted odometer (fallback): {numeric_match.group(1)}")
                return parameters
            
            self.logger.warning(f"Could not parse odometer response: {response}")
            
        except Exception as e:
            self.logger.error(f"Error parsing odometer response '{response}': {e}")
        
        return parameters