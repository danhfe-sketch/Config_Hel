"""
Profile Parameter Filter for LT32Pro Devices

This module provides filtering functionality to identify which parameters
can be written back to LT32Pro devices, separating read-only parameters
from writable configuration parameters.
"""

from typing import Dict, Set, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ProfileParameterFilter:
    """
    Filters profile parameters to identify writable vs read-only parameters.
    
    This class helps ensure that only appropriate parameters are sent back
    to the device during profile operations, improving success rates and
    avoiding unnecessary errors.
    """
    
    # Parameters that are typically writable to LT32Pro devices
    WRITABLE_PARAMETERS = {
        'apn_server',
        'apn_user', 
        'apn_password',
        'server_ip',
        'server_port',
        'server_type',
        'protocol',
        'tcp_ack',
        'tcp_acknowledgment'
    }
    
    # Parameters that are read-only (device status/info)
    READ_ONLY_PARAMETERS = {
        'battery_voltage',
        'gprs_status',
        'gsm_signal_level',
        'acc_status',
        'gps_status',
        'device_imei',
        'device_id',
        'imei',
        'device_iccid',
        'iccid',
        'device_version',
        'firmware_date'
    }
    
    # Parameters that may not be supported by all device versions
    UNSUPPORTED_PARAMETERS = {
        'heartbeat_interval',  # Use different command format
        'report_interval',     # Use different command format
        'timezone',           # May not be supported
        'device_name',        # May not be writable
        'upload_interval',    # May not be supported
        'sleep_mode',         # May not be supported
        'power_save_mode',    # May not be supported
        'tracking_mode',      # May not be supported
        'server_protocol',    # Derived parameter
        'protocol_name'       # Derived parameter
    }
    
    def __init__(self):
        """Initialize the parameter filter."""
        self.logger = logging.getLogger(__name__)
    
    def filter_writable_parameters(self, parameters: Dict[str, str]) -> Dict[str, str]:
        """
        Filter parameters to only include those that can be written to the device.
        
        Args:
            parameters: Dictionary of all parameters
            
        Returns:
            Dictionary containing only writable parameters
        """
        if not parameters:
            return {}
        
        writable_params = {}
        filtered_count = 0
        
        for param_name, param_value in parameters.items():
            if self._is_writable_parameter(param_name):
                writable_params[param_name] = param_value
            else:
                filtered_count += 1
                self.logger.debug(f"Filtered out parameter: {param_name} (not writable)")
        
        self.logger.info(f"Parameter filtering: {len(writable_params)} writable, {filtered_count} filtered out")
        
        return writable_params
    
    def _is_writable_parameter(self, param_name: str) -> bool:
        """
        Check if a parameter is writable to the device.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            True if parameter is writable, False otherwise
        """
        param_lower = param_name.lower()
        
        # Check if it's explicitly writable
        if any(writable in param_lower for writable in self.WRITABLE_PARAMETERS):
            return True
        
        # Check if it's explicitly read-only
        if any(readonly in param_lower for readonly in self.READ_ONLY_PARAMETERS):
            return False
        
        # Check if it's unsupported
        if any(unsupported in param_lower for unsupported in self.UNSUPPORTED_PARAMETERS):
            return False
        
        # Default to not writable for unknown parameters (conservative approach)
        return False
    
    def categorize_parameters(self, parameters: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """
        Categorize parameters into writable, read-only, and unsupported.
        
        Args:
            parameters: Dictionary of all parameters
            
        Returns:
            Dictionary with categories: 'writable', 'read_only', 'unsupported'
        """
        categories = {
            'writable': {},
            'read_only': {},
            'unsupported': {}
        }
        
        for param_name, param_value in parameters.items():
            param_lower = param_name.lower()
            
            if any(writable in param_lower for writable in self.WRITABLE_PARAMETERS):
                categories['writable'][param_name] = param_value
            elif any(readonly in param_lower for readonly in self.READ_ONLY_PARAMETERS):
                categories['read_only'][param_name] = param_value
            elif any(unsupported in param_lower for unsupported in self.UNSUPPORTED_PARAMETERS):
                categories['unsupported'][param_name] = param_value
            else:
                # Unknown parameters go to unsupported for safety
                categories['unsupported'][param_name] = param_value
        
        return categories
    
    def get_filtering_report(self, parameters: Dict[str, str]) -> Dict[str, any]:
        """
        Generate a detailed filtering report.
        
        Args:
            parameters: Dictionary of all parameters
            
        Returns:
            Dictionary with filtering statistics and recommendations
        """
        categories = self.categorize_parameters(parameters)
        
        total_params = len(parameters)
        writable_count = len(categories['writable'])
        readonly_count = len(categories['read_only'])
        unsupported_count = len(categories['unsupported'])
        
        report = {
            'total_parameters': total_params,
            'writable_parameters': writable_count,
            'read_only_parameters': readonly_count,
            'unsupported_parameters': unsupported_count,
            'writable_percentage': (writable_count / total_params * 100) if total_params > 0 else 0,
            'categories': categories,
            'recommendations': self._generate_recommendations(categories)
        }
        
        return report
    
    def _generate_recommendations(self, categories: Dict[str, Dict[str, str]]) -> List[str]:
        """Generate recommendations based on parameter categorization."""
        recommendations = []
        
        writable_count = len(categories['writable'])
        readonly_count = len(categories['read_only'])
        unsupported_count = len(categories['unsupported'])
        
        if writable_count == 0:
            recommendations.append("No writable parameters found - check parameter extraction")
        elif writable_count < 5:
            recommendations.append("Few writable parameters found - verify device compatibility")
        
        if readonly_count > writable_count:
            recommendations.append("Many read-only parameters detected - consider filtering before send operations")
        
        if unsupported_count > 0:
            recommendations.append(f"{unsupported_count} unsupported parameters found - update parameter mapping if needed")
        
        if writable_count > 0:
            recommendations.append(f"Recommend sending only {writable_count} writable parameters to device")
        
        return recommendations


def filter_parameters_for_device_write(parameters: Dict[str, str]) -> Dict[str, str]:
    """
    Convenience function to filter parameters for device writing.
    
    Args:
        parameters: Dictionary of all parameters
        
    Returns:
        Dictionary containing only writable parameters
    """
    filter_instance = ProfileParameterFilter()
    return filter_instance.filter_writable_parameters(parameters)


def get_parameter_filtering_report(parameters: Dict[str, str]) -> Dict[str, any]:
    """
    Convenience function to get a parameter filtering report.
    
    Args:
        parameters: Dictionary of all parameters
        
    Returns:
        Dictionary with filtering statistics and recommendations
    """
    filter_instance = ProfileParameterFilter()
    return filter_instance.get_filtering_report(parameters)