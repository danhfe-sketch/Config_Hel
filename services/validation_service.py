"""
ValidationService - Comprehensive parameter validation with localized error messages.

This service provides centralized validation for all LT32Pro device parameters,
including range checking for numeric inputs, format validation for text inputs,
and connection state validation.
"""

import re
import logging
import json
import threading
import asyncio
import hashlib
import time
from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict, List, Callable, Union
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import lru_cache, wraps
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from services.i18n_service import I18nService
from services.apn_security_service import APNSecurityService, SecurityContext, SecurityLevel, AuditAction


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    error_message: str = ""
    error_code: str = ""
    suggested_value: Optional[str] = None
    warning_message: str = ""
    validation_level: str = "error"  # "error", "warning", "info"


@dataclass
class ValidationAttempt:
    """Detailed information about a validation attempt."""
    timestamp: datetime
    parameter_name: str
    value: str  # Masked for sensitive data
    validation_type: str
    source: str  # 'ui', 'command', 'api', 'profile'
    result: ValidationResult
    execution_time_ms: float
    context: Optional[Dict[str, Any]] = None


@dataclass
class ValidationMetrics:
    """Aggregated validation metrics for monitoring."""
    total_attempts: int = 0
    successful_validations: int = 0
    failed_validations: int = 0
    success_rate: float = 0.0
    average_execution_time_ms: float = 0.0
    common_errors: Dict[str, int] = None
    parameter_failure_rates: Dict[str, float] = None
    cache_hit_rate: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    async_validations: int = 0
    timeout_validations: int = 0
    
    def __post_init__(self):
        if self.common_errors is None:
            self.common_errors = {}
        if self.parameter_failure_rates is None:
            self.parameter_failure_rates = {}


@dataclass
class ValidationCacheEntry:
    """Cache entry for validation results."""
    result: ValidationResult
    timestamp: datetime
    access_count: int = 0
    last_accessed: datetime = None
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.timestamp


@dataclass
class PerformanceConfig:
    """Configuration for validation performance optimizations."""
    cache_enabled: bool = True
    cache_max_size: int = 1000
    cache_ttl_seconds: int = 300  # 5 minutes
    async_enabled: bool = True
    async_threshold_ms: int = 50
    timeout_seconds: int = 5
    regex_optimization: bool = True
    batch_validation: bool = True
    performance_monitoring: bool = True


class ValidationService:
    """Handles comprehensive parameter validation with localized error messages and performance optimizations."""
    
    def __init__(self, i18n_service: I18nService, performance_config: Optional[PerformanceConfig] = None):
        self.i18n = i18n_service
        self.logger = logging.getLogger(__name__)
        
        # Performance configuration
        self._perf_config = performance_config or PerformanceConfig()
        
        # Security service integration
        self.security_service = APNSecurityService()
        self._security_enabled = True
        
        # Enhanced logging and debugging
        self._debug_mode = False
        self._validation_attempts = deque(maxlen=1000)  # Store last 1000 attempts
        self._metrics = ValidationMetrics()
        self._error_patterns = defaultdict(int)
        self._parameter_stats = defaultdict(lambda: {'attempts': 0, 'failures': 0})
        self._lock = threading.Lock()
        
        # Performance monitoring
        self._performance_thresholds = {
            'slow_validation_ms': 100,
            'very_slow_validation_ms': 500
        }
        
        # Performance optimizations
        self._validation_cache: Dict[str, ValidationCacheEntry] = {}
        self._cache_lock = threading.RLock()
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        self._pattern_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="validation")
        self._async_loop = None
        
        # Performance monitoring dashboard data
        self._performance_dashboard = {
            'cache_stats': defaultdict(int),
            'async_stats': defaultdict(int),
            'timeout_stats': defaultdict(int),
            'pattern_performance': defaultdict(list),
            'validation_timeline': deque(maxlen=1000)
        }
        
        # Initialize validation components
        self._init_validation_rules()
        self._init_apn_validation_patterns()
        self._init_debug_logging()
        self._init_performance_optimizations()
    
    def _init_validation_rules(self):
        """Initialize validation rules for all parameter types from the specification."""
        self.validation_rules = {
            # Network Parameters
            'apn': {
                'type': 'apn',
                'max_length': 50,
                'required': True,
                'pattern': r'^(?!.*\.\.+)(?!^\.)(?!.*\.$)(?:(?!.*\.([a-zA-Z])\.\1\.)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z]{2,}|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|https?://(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:/.*)?|[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)$'
            },
            'apn_user': {
                'type': 'apn_credential',
                'max_length': 30,
                'min_length': 0,
                'required': False
            },
            'apn_password': {
                'type': 'apn_credential',
                'max_length': 30,
                'min_length': 0,
                'required': False
            },
            'server_address': {
                'type': 'text',
                'max_length': 100,
                'required': True,
                'pattern': r'^(?!.*\.\.)((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|[\w\.-]+\.[a-zA-Z]{2,}|https?://[\w\.-]+.*)$'
            },
            'server_port': {
                'type': 'numeric',
                'min': 1,
                'max': 65535,
                'integer': True
            },
            
            # Time Parameters
            'moving_time': {
                'type': 'numeric',
                'min': 1,
                'max': 65535,
                'integer': True
            },
            'stopped_time': {
                'type': 'numeric',
                'min': 1,
                'max': 65535,
                'integer': True
            },
            'moving_heartbeat': {
                'type': 'numeric',
                'min': 30,
                'max': 86400,
                'integer': True
            },
            'stopped_heartbeat': {
                'type': 'numeric',
                'min': 30,
                'max': 86400,
                'integer': True
            },
            
            # Service Parameters
            'protocol': {
                'type': 'dropdown',
                'allowed_values': ['GT06 (0x60)', 'CRX3 (0x22)', 'CRX (0x12)']
            },
            'tcp_ack': {
                'type': 'dropdown',
                'allowed_values': ['Enabled', 'Disabled']
            },
            
            # Ignition Parameters
            'ignition_mode': {
                'type': 'dropdown',
                'allowed_values': ['Física (Physical)', 'Virtual por acelerômetro (Virtual by accelerometer)', 'Virtual por bateria (Virtual by battery)']
            },
            'on_voltage': {
                'type': 'numeric',
                'min': 6,
                'max': 60,
                'integer': True
            },
            'off_voltage': {
                'type': 'numeric',
                'min': 6,
                'max': 60,
                'integer': True
            },
            
            # Speed Parameters
            'speed_detection_time': {
                'type': 'numeric',
                'min': 5,
                'max': 600,
                'integer': True
            },
            'speed_limit': {
                'type': 'numeric',
                'min': 1,
                'max': 255,
                'integer': True
            },
            'speed_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['Apenas GPRS', 'GPRS+SMS']
            },
            
            # Power Saving Parameters
            'sleep_mode': {
                'type': 'dropdown',
                'allowed_values': ['Desabilitado (Disabled)', 'Sleep (Habilitado)', 'Deep Sleep (Ultra-baixo)']
            },
            'sleep_time': {
                'type': 'numeric',
                'min': 1,
                'max': 1440,
                'integer': True
            },
            
            # Angle Parameters
            'angle_min_speed': {
                'type': 'numeric',
                'min': 1,
                'max': 20,
                'integer': True
            },
            'angle_variation': {
                'type': 'numeric',
                'min': 5,
                'max': 90,
                'integer': True
            },
            
            # Battery Alert Parameters
            'power_detection_time': {
                'type': 'numeric',
                'min': 2,
                'max': 60,
                'integer': True
            },
            'min_charge_time': {
                'type': 'numeric',
                'min': 1,
                'max': 3600,
                'integer': True
            },
            'battery_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['Apenas GPRS', 'GPRS+SMS']
            },
            
            # Vibration Sensor Parameters
            'vibration_level': {
                'type': 'numeric',
                'min': 1,
                'max': 6,
                'integer': True
            },
            
            # Jammer Detection Parameters
            'jammer_confirmation_time': {
                'type': 'numeric',
                'min': 0,
                'max': 1800,
                'integer': True
            },
            'jammer_speed_limit': {
                'type': 'numeric',
                'min': 0,
                'max': 255,
                'integer': True
            },
            'jammer_output_operation': {
                'type': 'dropdown',
                'allowed_values': ['Sem Ação', 'Ativar e Manter', 'Ativar e Desativar com Jammer']
            },
            
            # Miscellaneous Parameters
            'odometer': {
                'type': 'numeric',
                'min': 0,
                'max': 999999999,
                'integer': True
            },
            'hourmeter': {
                'type': 'numeric',
                'min': 0,
                'max': 999999999,
                'integer': True
            },
            
            # Legacy parameters for backward compatibility
            'vibration': {
                'type': 'numeric',
                'min': 0,
                'max': 255,
                'integer': True
            },
            'sensitivity': {
                'type': 'numeric',
                'min': 1,
                'max': 10,
                'integer': True
            },
            'timer_ign_on': {
                'type': 'numeric',
                'min': 1,
                'max': 65500,
                'integer': True
            },
            'timer_ign_off': {
                'type': 'numeric',
                'min': 1,
                'max': 65500,
                'integer': True
            },
            'heartbeat_ign_on': {
                'type': 'numeric',
                'min': 60,
                'max': 300,
                'integer': True
            },
            'heartbeat_ign_off': {
                'type': 'numeric',
                'min': 60,
                'max': 300,
                'integer': True
            },
            'speed_time': {
                'type': 'numeric',
                'min': 5,
                'max': 600,
                'integer': True
            },
            'angle_speed': {
                'type': 'numeric',
                'min': 1,
                'max': 20,
                'integer': True
            },
            'angle_value': {
                'type': 'numeric',
                'min': 5,
                'max': 90,
                'integer': True
            },
            'blind_speed': {
                'type': 'numeric',
                'min': 0,
                'max': 20,
                'integer': True
            },
            'defense_time': {
                'type': 'numeric',
                'min': 1,
                'max': 60,
                'integer': True
            },
            'moving_radius': {
                'type': 'numeric',
                'min': 100,
                'max': 1000,
                'integer': True
            },
            'jammer_time': {
                'type': 'numeric',
                'min': 1,
                'max': 60,
                'integer': True
            },
            'jammer_signal': {
                'type': 'numeric',
                'min': 1,
                'max': 100,
                'integer': True
            },
            'jammer_freq': {
                'type': 'numeric',
                'min': 1,
                'max': 10,
                'integer': True
            },
            'acc_on_voltage': {
                'type': 'numeric',
                'min': 6,
                'max': 60,
                'integer': True
            },
            'acc_off_voltage': {
                'type': 'numeric',
                'min': 6,
                'max': 60,
                'integer': True
            },
            'timezone_hours': {
                'type': 'numeric',
                'min': 0,
                'max': 12,
                'integer': True
            },
            'timezone_minutes': {
                'type': 'numeric',
                'min': 0,
                'max': 59,
                'integer': True
            },
            
            # Text parameters with format validation
            'apn_server': {
                'type': 'text',
                'max_length': 50,
                'required': True,
                'pattern': r'^((?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))$'
            },
            'server_ip': {
                'type': 'text',
                'max_length': 100,
                'required': True,
                'pattern': r'^((?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))$'
            },
            'server_domain': {
                'type': 'domain',
                'max_length': 50,
                'required': True
            },
            'phone_number': {
                'type': 'phone',
                'max_length': 15,
                'required': True
            },
            
            # Dropdown parameters with allowed values
            'heartbeat_interval': {
                'type': 'dropdown',
                'allowed_values': ['30s', '1min', '5min', '10min', '30min', '1hr', '2hr', '6hr', '12hr', '24hr']
            },
            'curve_sensor': {
                'type': 'dropdown',
                'allowed_values': ['Enabled', 'Disabled', 'Auto']
            },
            'protocol_type': {
                'type': 'dropdown',
                'allowed_values': ['TCP', 'UDP']
            },
            'network_type': {
                'type': 'dropdown',
                'allowed_values': ['AUTO', '4G', '2G']
            },
            'sleep_mode': {
                'type': 'dropdown',
                'allowed_values': ['Disabled', 'Sleep', 'Deep Sleep']
            },
            'alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'gt06_protocol': {
                'type': 'dropdown',
                'allowed_values': ['GT06-0x60', 'GT06-0x12', 'CRX3']
            },
            'volte_switch': {
                'type': 'dropdown',
                'allowed_values': ['2G', '4G']
            },
            'relay_state': {
                'type': 'dropdown',
                'allowed_values': ['OFF', 'ON']
            },
            
            # Radio button parameters
            'lock_type': {
                'type': 'radio',
                'allowed_values': ['PIN', 'Card']
            },
            'ignition_type': {
                'type': 'radio',
                'allowed_values': ['Digital', 'Analog']
            },
            'transmission_mode': {
                'type': 'radio',
                'allowed_values': ['TCP', 'UDP']
            },
            'timezone_direction': {
                'type': 'radio',
                'allowed_values': ['E', 'W']
            },
            'tcp_ack_config': {
                'type': 'radio',
                'allowed_values': ['Enabled', 'Disabled']
            },
            
            # Additional numeric parameters for comprehensive coverage
            'vibration_window': {
                'type': 'numeric',
                'min': 1,
                'max': 60,
                'integer': True
            },
            'vibration_threshold': {
                'type': 'numeric',
                'min': 1,
                'max': 100,
                'integer': True
            },
            'power_alert_t1': {
                'type': 'numeric',
                'min': 1,
                'max': 60,
                'integer': True
            },
            'power_alert_t2': {
                'type': 'numeric',
                'min': 1,
                'max': 60,
                'integer': True
            },
            'sos_phone1': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'sos_phone2': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'sos_phone3': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'center_phone1': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'center_phone2': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'center_phone3': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'password': {
                'type': 'text',
                'min_length': 4,
                'max_length': 20,
                'required': False
            },
            
            # Additional dropdown parameters
            'power_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'battery_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'movement_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'acc_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'acc_off_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'jammer_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'speed_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'gps_source_type': {
                'type': 'dropdown',
                'allowed_values': ['Disabled', 'Enabled']
            },
            'parameter_lock_state': {
                'type': 'dropdown',
                'allowed_values': ['Unlock', 'Lock']
            },
            
            # Additional parameters from design document
            'firmware_version': {
                'type': 'text',
                'max_length': 20,
                'required': False
            },
            'signal_strength': {
                'type': 'numeric',
                'min': 0,
                'max': 100,
                'integer': True
            },
            'device_status': {
                'type': 'text',
                'max_length': 50,
                'required': False
            },
            'imei': {
                'type': 'text',
                'min_length': 15,
                'max_length': 15,
                'required': False,
                'pattern': r'^\d{15}$'
            },
            'iccid': {
                'type': 'text',
                'min_length': 19,
                'max_length': 20,
                'required': False,
                'pattern': r'^\d{19,20}$'
            },
            'imsi': {
                'type': 'text',
                'min_length': 15,
                'max_length': 15,
                'required': False,
                'pattern': r'^\d{15}$'
            }
        }
    
    def _init_apn_validation_patterns(self):
        """Initialize enhanced APN validation patterns."""
        # Domain name pattern - prevents consecutive dots and malformed domains
        self.apn_domain_pattern = r'^(?!.*\.\.+)(?!^\.)(?!.*\.$)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
        
        # IP address pattern - validates IPv4 addresses
        self.apn_ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        
        # URL pattern - validates HTTP/HTTPS URLs
        self.apn_url_pattern = r'^https?://(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:/.*)?$'
        
        # Simple APN name pattern - for carrier-specific APNs without dots
        self.apn_simple_pattern = r'^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        
        # Combined pattern for all APN formats
        self.apn_combined_pattern = f'({self.apn_domain_pattern[1:-1]}|{self.apn_ip_pattern[1:-1]}|{self.apn_url_pattern[1:-1]}|{self.apn_simple_pattern[1:-1]})'
        
        # APN credential pattern - allows alphanumeric, special chars commonly used in credentials
        self.apn_credential_pattern = r'^[a-zA-Z0-9@._-]*$'
        
        # Common carrier APN patterns for suggestions
        self.common_carrier_apns = {
            'vivo': ['zap.vivo.com.br', 'vivo.br'],
            'claro': ['claro.com.br', 'bandalarga.claro.com.br'],
            'tim': ['tim.br', 'timbrasil.br'],
            'oi': ['gprs.oi.com.br', 'oi.com.br'],
            'allcom': ['allcom.br']
        }
    
    def validate_parameter(self, param_name: str, value: Any, context: Optional[Dict[str, Any]] = None, 
                         source: str = 'unknown', security_context: Optional[SecurityContext] = None) -> ValidationResult:
        """
        Validate a parameter value according to its defined rules with security enhancements.
        
        Args:
            param_name: Name of the parameter to validate
            value: Value to validate
            context: Optional context with other parameter values for conditional validation
            source: Source of the validation request ('ui', 'command', 'api', 'profile')
            security_context: Security context for audit logging and rate limiting
            
        Returns:
            ValidationResult with validation status and error details
        """
        start_time = datetime.now()
        result = None
        param_type = 'unknown'

        # Short-circuit: if speed alert is disabled, skip validation for speed fields
        try:
            if param_name in ('speed_detection_time', 'speed_limit') and context:
                # Context may include either a flattened flag or a grouped dict
                enabled = None
                if isinstance(context, dict):
                    if 'speed_alert_enabled' in context:
                        enabled = context.get('speed_alert_enabled')
                    elif 'speed_alert' in context and isinstance(context.get('speed_alert'), dict):
                        enabled = context.get('speed_alert', {}).get('enabled')
                # Treat common false-ish values
                if enabled is False or (isinstance(enabled, str) and enabled.lower() in ('false', 'off', '0', 'no')):
                    return ValidationResult(is_valid=True)
        except Exception:
            # If any error occurs while checking context, fall back to normal validation
            pass
        
        # Create default security context if not provided
        if security_context is None:
            security_context = SecurityContext(
                user_id="system",
                session_id="default",
                ip_address="127.0.0.1",
                user_agent="ValidationService",
                timestamp=start_time,
                security_level=SecurityLevel.MEDIUM,
                permissions=[]
            )
        
        # Security enhancements
        if self._security_enabled:
            # 1. Rate limiting check
            rate_limit_id = f"{security_context.ip_address}:{security_context.user_id}"
            rate_allowed, rate_error = self.security_service.check_rate_limit(
                rate_limit_id, "validation", security_context
            )
            if not rate_allowed:
                return ValidationResult(
                    is_valid=False,
                    error_message=rate_error,
                    error_code='RATE_LIMITED'
                )
            
            # 2. Input sanitization for APN-related fields
            if param_name in ['apn', 'apn_user', 'apn_password'] and isinstance(value, str):
                field_type = 'apn' if param_name == 'apn' else 'username' if param_name == 'apn_user' else 'password'
                sanitized_value, sanitization_issues = self.security_service.sanitize_apn_input(value, field_type)
                
                if sanitization_issues:
                    # Log sanitization issues
                    self.security_service.audit_log(
                        AuditAction.SECURITY_VIOLATION,
                        security_context,
                        "input_sanitization",
                        param_name,
                        {"original_value_length": len(value), "issues": sanitization_issues},
                        True,
                        f"Input sanitization applied: {', '.join(sanitization_issues)}"
                    )
                
                # Use sanitized value for validation
                value = sanitized_value
            
            # 3. Validation integrity check
            integrity_ok, integrity_issues = self.security_service.verify_validation_integrity(self.validation_rules)
            if not integrity_ok:
                self.security_service.audit_log(
                    AuditAction.SECURITY_VIOLATION,
                    security_context,
                    "validation_integrity",
                    "validation_rules",
                    {"integrity_issues": integrity_issues},
                    False,
                    f"Validation integrity compromised: {', '.join(integrity_issues)}"
                )
                # Continue with validation but log the issue
        
        # Check cache first for performance optimization
        cache_key = self._generate_cache_key(param_name, value, context)
        cached_result = self._get_cached_validation_result(cache_key)
        if cached_result:
            # Update metrics for cached result
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.log_validation_attempt(param_name, str(value), 'cached', source, cached_result, execution_time, context)
            return cached_result
        
        try:
            if param_name not in self.validation_rules:
                result = ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_unknown_parameter', 'Unknown parameter: {param_name}').format(param_name=param_name),
                    error_code='UNKNOWN_PARAMETER'
                )
                param_type = 'unknown_parameter'
                return result
            
            rules = self.validation_rules[param_name]
            param_type = rules['type']
            
            # Get the translated display name for the parameter
            display_name = self.i18n.get(param_name, param_name)
            
            # For server_ip, use the server_url_ip translation
            if param_name == 'server_ip':
                display_name = self.i18n.get('server_url_ip', 'URL/IP')
            elif param_name == 'server_address':
                display_name = self.i18n.get('server_url_ip', 'URL/IP')
            
            # Handle empty values
            if value is None or (isinstance(value, str) and value.strip() == ''):
                if rules.get('required', False):
                    result = ValidationResult(
                        is_valid=False,
                        error_message=self.i18n.get('validation_required_field', '{param_name} is required and cannot be empty').format(param_name=display_name),
                        error_code='REQUIRED_FIELD'
                    )
                else:
                    result = ValidationResult(is_valid=True)
                return result
            
            # Check conditional validation rules
            conditional_result = self._validate_conditional_rules(param_name, value, context)
            if conditional_result is not None:
                result = conditional_result
                return result
            
            # Type-specific validation
            if param_type == 'numeric':
                result = self._validate_numeric(param_name, value, rules)
            elif param_type == 'text':
                result = self._validate_text(param_name, value, rules)
            elif param_type == 'apn':
                result = self._validate_apn(param_name, value, rules, context)
            elif param_type == 'apn_credential':
                result = self._validate_apn_credential(param_name, value, rules)
            elif param_type == 'ip_address':
                result = self._validate_ip_address(param_name, value)
            elif param_type == 'domain':
                result = self._validate_domain(param_name, value, rules)
            elif param_type == 'phone':
                result = self._validate_phone(param_name, value, rules)
            elif param_type == 'dropdown':
                result = self._validate_dropdown(param_name, value, rules)
            elif param_type == 'radio':
                result = self._validate_radio(param_name, value, rules)
            else:
                result = ValidationResult(is_valid=True)
            
            # Cache the result for future use
            if result is not None:
                self._cache_validation_result(cache_key, result)
            
            return result
            
        finally:
            # Always log the validation attempt, regardless of the path taken
            if result is not None:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                self.log_validation_attempt(
                    param_name, str(value), param_type, source, result, execution_time, context
                )
                
                # Security audit logging
                if self._security_enabled and security_context:
                    self.security_service.audit_log(
                        AuditAction.VALIDATION_ATTEMPT,
                        security_context,
                        "parameter_validation",
                        param_name,
                        {
                            "param_type": param_type,
                            "validation_source": source,
                            "execution_time_ms": execution_time,
                            "has_context": context is not None
                        },
                        result.is_valid,
                        result.error_message if not result.is_valid else ""
                    )
    
    def validate_parameter_realtime(self, param_name: str, value: Any, context: Optional[Dict[str, Any]] = None, 
                                  source: str = 'ui', security_context: Optional[SecurityContext] = None) -> ValidationResult:
        """
        Validate a parameter value with real-time feedback optimizations and security enhancements.
        
        This method provides immediate validation feedback suitable for real-time UI updates.
        It includes progressive validation levels and user-friendly error messages.
        
        Args:
            param_name: Name of the parameter to validate
            value: Value to validate
            context: Optional context with other parameter values for conditional validation
            security_context: Security context for audit logging and rate limiting
            
        Returns:
            ValidationResult with validation status and detailed feedback
        """
        # Delegate to main validation method with security context
        return self.validate_parameter(param_name, value, context, source, security_context)
        # Use the standard validation but with enhanced feedback
        result = self.validate_parameter(param_name, value, context, source)
        
        # Add progressive validation feedback
        if not result.is_valid and result.error_code:
            result = self._enhance_validation_feedback(param_name, value, result)
        
        return result
    
    def _enhance_validation_feedback(self, param_name: str, value: Any, result: ValidationResult) -> ValidationResult:
        """
        Enhance validation result with more detailed feedback for real-time validation.
        
        Args:
            param_name: Name of the parameter
            value: Value being validated
            result: Original validation result
            
        Returns:
            Enhanced validation result
        """
        rules = self.validation_rules.get(param_name, {})
        param_type = rules.get('type', 'text')
        display_name = self.i18n.get(param_name, param_name)
        
        # Enhance numeric validation feedback
        if param_type == 'numeric' and result.error_code in ['RANGE_ERROR', 'MIN_VALUE', 'MAX_VALUE']:
            min_val = rules.get('min')
            max_val = rules.get('max')
            
            try:
                num_value = float(value) if value else 0
                
                if min_val is not None and max_val is not None:
                    # Provide contextual feedback based on how far off the value is
                    if num_value < min_val:
                        diff = min_val - num_value
                        if diff <= (max_val - min_val) * 0.1:  # Within 10% of range
                            result.validation_level = "warning"
                            result.warning_message = self.i18n.get(
                                'validation_close_to_range', 
                                '{param_name} is close to valid range. Minimum is {min_val}'
                            ).format(param_name=display_name, constraint=f"Minimum is {min_val}")
                    elif num_value > max_val:
                        diff = num_value - max_val
                        if diff <= (max_val - min_val) * 0.1:  # Within 10% of range
                            result.validation_level = "warning"
                            result.warning_message = self.i18n.get(
                                'validation_close_to_range', 
                                '{param_name} is close to valid range. Maximum is {max_val}'
                            ).format(param_name=display_name, constraint=f"Maximum is {max_val}")
                            
            except (ValueError, TypeError):
                pass
        
        # Enhance text validation feedback
        elif param_type == 'text' and result.error_code in ['MIN_LENGTH', 'MAX_LENGTH']:
            text_value = str(value) if value else ""
            min_length = rules.get('min_length')
            max_length = rules.get('max_length')
            
            if min_length and len(text_value) < min_length:
                remaining = min_length - len(text_value)
                if remaining <= 3:  # Close to minimum length
                    result.validation_level = "warning"
                    result.warning_message = self.i18n.get(
                        'validation_characters_remaining',
                        '{remaining} more characters needed for {param_name}'
                    ).format(remaining=remaining, param_name=display_name)
        
        return result
    
    def validate_parameter_group(self, parameters: Dict[str, Any]) -> Dict[str, ValidationResult]:
        """
        Validate a group of parameters with conditional validation support.
        
        Args:
            parameters: Dictionary of parameter names and values
            
        Returns:
            Dictionary of parameter names and their validation results
        """
        results = {}
        
        for param_name, value in parameters.items():
            results[param_name] = self.validate_parameter(param_name, value, parameters)
        
        return results
    
    def _validate_conditional_rules(self, param_name: str, value: Any, context: Optional[Dict[str, Any]]) -> Optional[ValidationResult]:
        """
        Validate conditional rules based on other parameter values.
        
        Args:
            param_name: Name of the parameter being validated
            value: Value being validated
            context: Context with other parameter values
            
        Returns:
            ValidationResult for conditional validation, or None to continue with normal validation
        """
        if not context:
            return None
        
        # Conditional validation for voltage fields based on ignition mode
        if param_name in ['on_voltage', 'off_voltage']:
            ignition_mode = context.get('ignition_mode')
            if ignition_mode and ignition_mode != 'Virtual por bateria (Virtual by battery)':
                # These fields should not be validated if ignition mode is not battery
                return ValidationResult(is_valid=True)
        
        # Conditional validation for angle parameters based on angle report enabled
        if param_name in ['angle_min_speed', 'angle_variation']:
            angle_enabled = context.get('angle_enabled')
            if angle_enabled is False:  # Explicitly check for False
                # These fields should not be validated if angle report is disabled
                return ValidationResult(is_valid=True)
        
        # Conditional validation for speed alert parameters
        if param_name in ['speed_detection_time', 'speed_limit', 'speed_alert_type']:
            speed_enabled = context.get('speed_enabled')
            if speed_enabled is False:  # Explicitly check for False
                # These fields should not be validated if speed alert is disabled
                return ValidationResult(is_valid=True)
        
        # Conditional validation for power alert parameters
        if param_name in ['power_detection_time', 'min_charge_time', 'battery_alert_type']:
            power_enabled = context.get('power_enabled')
            if power_enabled is False:  # Explicitly check for False
                # These fields should not be validated if power alert is disabled
                return ValidationResult(is_valid=True)
        
        # Conditional validation for jammer parameters
        if param_name in ['jammer_confirmation_time', 'jammer_speed_limit', 'jammer_output_operation']:
            jammer_enabled = context.get('jammer_enabled')
            if jammer_enabled is False:  # Explicitly check for False
                # These fields should not be validated if jammer detection is disabled
                return ValidationResult(is_valid=True)
        
        return None  # Continue with normal validation
    
    def _validate_numeric(self, param_name: str, value: Any, rules: Dict) -> ValidationResult:
        # Get the translated display name for the parameter
        display_name = self.i18n.get(param_name, param_name)
        
        # For server_port, use the server_port translation
        if param_name == 'server_port':
            display_name = self.i18n.get('server_port', 'Porta do Servidor')
        """Validate numeric parameters with range checking."""
        try:
            if isinstance(value, str):
                if rules.get('integer', False):
                    num_value = int(value)
                else:
                    num_value = float(value)
            else:
                num_value = value
                
            # Check if integer is required
            if rules.get('integer', False) and not isinstance(num_value, int):
                if isinstance(num_value, float) and not num_value.is_integer():
                    return ValidationResult(
                        is_valid=False,
                        error_message=self.i18n.get('validation_integer_required', '{param_name} must be an integer value').format(param_name=display_name),
                        error_code='INTEGER_REQUIRED'
                    )
                num_value = int(num_value)
            
            # Check range
            min_val = rules.get('min')
            max_val = rules.get('max')
            
            if min_val is not None and num_value < min_val:
                # Use more specific range error message if both min and max are specified
                if max_val is not None:
                    return ValidationResult(
                        is_valid=False,
                        error_message=self.i18n.get('validation_range_error', '{param_name} must be between {min_val} and {max_val}').format(
                            param_name=display_name, min_val=min_val, max_val=max_val
                        ),
                        error_code='RANGE_ERROR',
                        suggested_value=str(min_val)
                    )
                else:
                    return ValidationResult(
                        is_valid=False,
                        error_message=self.i18n.get('validation_min_value', '{param_name} must be at least {min_val}').format(
                            param_name=display_name, min_val=min_val
                        ),
                        error_code='MIN_VALUE',
                        suggested_value=str(min_val)
                    )
            
            if max_val is not None and num_value > max_val:
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_max_value', '{param_name} must be at most {max_val}').format(
                        param_name=display_name, max_val=max_val
                    ),
                    error_code='MAX_VALUE',
                    suggested_value=str(max_val)
                )
            
            # Check allowed values (for specific numeric constraints)
            allowed_values = rules.get('allowed_values')
            if allowed_values and num_value not in allowed_values:
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_not_in_allowed_values', '{param_name} must be one of: {allowed_values}').format(
                        param_name=display_name, 
                        allowed_values=", ".join(map(str, allowed_values))
                    ),
                    error_code='NOT_IN_ALLOWED_VALUES'
                )
            
            return ValidationResult(is_valid=True)
            
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_numeric_required', '{param_name} must be a numeric value').format(param_name=display_name),
                error_code='NUMERIC_REQUIRED'
            )
    
    def _validate_text(self, param_name: str, value: Any, rules: Dict) -> ValidationResult:
        # Get the translated display name for the parameter
        display_name = self.i18n.get(param_name, param_name)
        
        # For server_ip, use the server_url_ip translation
        if param_name == 'server_ip':
            display_name = self.i18n.get('server_url_ip', 'URL/IP')
        """Validate text parameters with length and pattern checking."""
        if not isinstance(value, str):
            value = str(value)
        
        # Check minimum length
        min_length = rules.get('min_length')
        if min_length and len(value) < min_length:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_min_length', '{param_name} must be at least {min_length} characters').format(
                    param_name=display_name, 
                    min_length=min_length
                ),
                error_code='MIN_LENGTH'
            )
        
        # Check maximum length
        max_length = rules.get('max_length')
        if max_length and len(value) > max_length:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_max_length', '{param_name} must be at most {max_length} characters').format(
                    param_name=param_name, 
                    max_length=max_length
                ),
                error_code='MAX_LENGTH'
            )
        
        # Check pattern
        pattern = rules.get('pattern')
        if pattern and not re.match(pattern, value):
            # Use specific error messages for known patterns
            if param_name == 'imei':
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_invalid_imei', '{param_name} must be exactly 15 digits').format(param_name=display_name),
                    error_code='INVALID_IMEI'
                )
            elif param_name == 'iccid':
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_invalid_iccid', '{param_name} must be 19-20 digits').format(param_name=display_name),
                    error_code='INVALID_ICCID'
                )
            elif param_name == 'imsi':
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_invalid_imsi', '{param_name} must be exactly 15 digits').format(param_name=display_name),
                    error_code='INVALID_IMSI'
                )
            elif param_name in ['apn', 'apn_server']:
                # Use enhanced APN validation
                apn_result = self._validate_apn_format(value)
                if not apn_result.is_valid:
                    suggestions = self._get_apn_suggestions(value)
                    error_message = self.i18n.get('validation_invalid_apn', '{param_name} deve ser um nome de host ou endereço IP válido').format(param_name=display_name)
                    if suggestions:
                        error_message += f". Sugestões: {', '.join(suggestions[:3])}"
                    
                    return ValidationResult(
                        is_valid=False,
                        error_message=error_message,
                        error_code='INVALID_APN'
                    )
            elif param_name in ['server_ip', 'server_address']:
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_invalid_server_url_ip', '{param_name} deve ser uma URL ou endereço IP válido').format(param_name=display_name),
                    error_code='INVALID_SERVER_URL_IP'
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_invalid_format', '{param_name} has an invalid format').format(param_name=display_name),
                    error_code='INVALID_FORMAT'
                )
        
        return ValidationResult(is_valid=True)
    
    def _validate_ip_address(self, param_name: str, value: str) -> ValidationResult:
        """Validate IP address format using optimized compiled pattern."""
        ip_pattern = self._get_compiled_pattern('ip_address')
        
        # Use compiled pattern if available, otherwise fall back to regex
        if ip_pattern:
            is_valid = bool(ip_pattern.match(value))
        else:
            ip_pattern_str = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            is_valid = bool(re.match(ip_pattern_str, value))
        
        if not is_valid:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_invalid_ip', '{param_name} must be a valid IP address (e.g. 192.168.1.1)').format(param_name=param_name),
                error_code='INVALID_IP'
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_domain(self, param_name: str, value: str, rules: Dict) -> ValidationResult:
        """Validate domain name format using optimized compiled pattern."""
        domain_pattern = self._get_compiled_pattern('domain')
        
        # Use compiled pattern if available, otherwise fall back to regex
        if domain_pattern:
            is_valid = bool(domain_pattern.match(value))
        else:
            domain_pattern_str = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
            is_valid = bool(re.match(domain_pattern_str, value))
        
        if not is_valid:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_invalid_domain', '{param_name} must be a valid domain name (e.g. example.com)').format(param_name=param_name),
                error_code='INVALID_DOMAIN'
            )
        
        max_length = rules.get('max_length', 253)
        if len(value) > max_length:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_max_length', '{param_name} must be at most {max_length} characters').format(
                    param_name=param_name, 
                    max_length=max_length
                ),
                error_code='MAX_LENGTH'
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_phone(self, param_name: str, value: str, rules: Dict) -> ValidationResult:
        """Validate phone number format using optimized pattern matching."""
        # First check if the format looks like a phone number using compiled pattern
        phone_pattern = self._get_compiled_pattern('phone')
        if phone_pattern and not phone_pattern.match(value):
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_invalid_phone', '{param_name} must contain only digits and common separators').format(param_name=param_name),
                error_code='INVALID_PHONE'
            )
        
        # Remove common phone number separators
        clean_phone = re.sub(r'[\s\-\(\)\+]', '', value)
        
        # Check if it contains only digits
        if not clean_phone.isdigit():
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_invalid_phone', '{param_name} must contain only digits').format(param_name=param_name),
                error_code='INVALID_PHONE'
            )
        
        # Check length
        max_length = rules.get('max_length', 15)
        if len(clean_phone) > max_length:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_phone_too_long', '{param_name} must be at most {max_length} digits').format(
                    param_name=param_name,
                    max_length=max_length
                ),
                error_code='PHONE_TOO_LONG'
            )
        
        if len(clean_phone) < 7:  # Minimum reasonable phone number length
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_phone_too_short', '{param_name} must be at least 7 digits').format(param_name=param_name),
                error_code='PHONE_TOO_SHORT'
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_dropdown(self, param_name: str, value: str, rules: Dict) -> ValidationResult:
        """Validate dropdown selection."""
        allowed_values = rules.get('allowed_values', [])
        
        if value not in allowed_values:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_invalid_selection', '{param_name} must be one of: {allowed_values}').format(
                    param_name=param_name,
                    allowed_values=", ".join(allowed_values)
                ),
                error_code='INVALID_SELECTION'
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_radio(self, param_name: str, value: str, rules: Dict) -> ValidationResult:
        """Validate radio button selection."""
        return self._validate_dropdown(param_name, value, rules)
    
    def _validate_apn(self, param_name: str, value: Any, rules: Dict, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Enhanced APN validation with support for domain names, IP addresses, and URLs.
        
        Args:
            param_name: Name of the parameter being validated
            value: APN value to validate
            rules: Validation rules for the parameter
            context: Optional context with other parameter values
            
        Returns:
            ValidationResult with detailed validation feedback
        """
        display_name = self.i18n.get(param_name, param_name)
        
        if not isinstance(value, str):
            value = str(value)
        
        # Log validation attempt
        self._log_validation_attempt(param_name, value, 'apn_validation')
        
        # Check length constraints
        max_length = rules.get('max_length', 50)
        if len(value) > max_length:
            result = ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_max_length', '{param_name} must be at most {max_length} characters').format(
                    param_name=display_name, 
                    max_length=max_length
                ),
                error_code='MAX_LENGTH'
            )
            self._log_validation_result(param_name, value, result)
            return result
        
        # Check for empty value
        if not value.strip():
            if rules.get('required', False):
                result = ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_required_field', '{param_name} is required and cannot be empty').format(param_name=display_name),
                    error_code='REQUIRED_FIELD'
                )
                self._log_validation_result(param_name, value, result)
                return result
            else:
                result = ValidationResult(is_valid=True)
                self._log_validation_result(param_name, value, result)
                return result
        
        # Enhanced APN format validation
        validation_result = self._validate_apn_format(value)
        if not validation_result.is_valid:
            # Add suggestions for common errors
            suggestions = self._get_apn_suggestions(value)
            validation_result.error_message = self.i18n.get('validation_invalid_apn', '{param_name} deve ser um nome de host ou endereço IP válido').format(param_name=display_name)
            if suggestions:
                validation_result.error_message += f". Sugestões: {', '.join(suggestions[:3])}"
            
            self._log_validation_result(param_name, value, validation_result)
            return validation_result
        
        # Log successful validation
        result = ValidationResult(is_valid=True)
        self._log_validation_result(param_name, value, result)
        return result
    
    def _validate_apn_credential(self, param_name: str, value: Any, rules: Dict) -> ValidationResult:
        """
        Validate APN credentials (username/password) with proper length and character checks.
        
        Args:
            param_name: Name of the parameter being validated
            value: Credential value to validate
            rules: Validation rules for the parameter
            
        Returns:
            ValidationResult with validation status
        """
        display_name = self.i18n.get(param_name, param_name)
        
        if not isinstance(value, str):
            value = str(value)
        
        # Log validation attempt
        self._log_validation_attempt(param_name, value, 'apn_credential_validation')
        
        # Check length constraints
        min_length = rules.get('min_length', 0)
        max_length = rules.get('max_length', 30)
        
        if len(value) < min_length:
            result = ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_min_length', '{param_name} must be at least {min_length} characters').format(
                    param_name=display_name, 
                    min_length=min_length
                ),
                error_code='MIN_LENGTH'
            )
            self._log_validation_result(param_name, value, result)
            return result
        
        if len(value) > max_length:
            result = ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_max_length', '{param_name} must be at most {max_length} characters').format(
                    param_name=display_name, 
                    max_length=max_length
                ),
                error_code='MAX_LENGTH'
            )
            self._log_validation_result(param_name, value, result)
            return result
        
        # Check for valid characters in credentials using compiled pattern
        if value:
            credential_pattern = self._get_compiled_pattern('apn_credential')
            if credential_pattern:
                is_valid = bool(credential_pattern.match(value))
            else:
                is_valid = bool(re.match(self.apn_credential_pattern, value))
            
            if not is_valid:
                result = ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_invalid_apn_credential', '{param_name} contains invalid characters. Only letters, numbers, @, ., _, - are allowed').format(param_name=display_name),
                    error_code='INVALID_APN_CREDENTIAL'
                )
                self._log_validation_result(param_name, value, result)
                return result
        
        # Log successful validation
        result = ValidationResult(is_valid=True)
        self._log_validation_result(param_name, value, result)
        return result
    
    def _validate_apn_format(self, apn_value: str) -> ValidationResult:
        """
        Validate APN format against multiple patterns (domain, IP, URL, simple name).
        
        Args:
            apn_value: APN value to validate
            
        Returns:
            ValidationResult with specific error details
        """
        # Check for consecutive dots (main issue from the bug report)
        if '..' in apn_value:
            return ValidationResult(
                is_valid=False,
                error_message="APN cannot contain consecutive dots",
                error_code='CONSECUTIVE_DOTS'
            )
        
        # Check for leading or trailing dots
        if apn_value.startswith('.') or apn_value.endswith('.'):
            return ValidationResult(
                is_valid=False,
                error_message="APN cannot start or end with a dot",
                error_code='INVALID_DOT_POSITION'
            )
        
        # Try to match against different APN format patterns using compiled patterns for performance
        domain_pattern = self._get_compiled_pattern('apn_domain')
        if domain_pattern and domain_pattern.match(apn_value):
            return ValidationResult(is_valid=True)
        
        ip_pattern = self._get_compiled_pattern('apn_ip')
        if ip_pattern and ip_pattern.match(apn_value):
            return ValidationResult(is_valid=True)
        
        url_pattern = self._get_compiled_pattern('apn_url')
        if url_pattern and url_pattern.match(apn_value):
            return ValidationResult(is_valid=True)
        
        simple_pattern = self._get_compiled_pattern('apn_simple')
        if simple_pattern and simple_pattern.match(apn_value):
            return ValidationResult(is_valid=True)
        
        # Fallback to original patterns if compiled patterns are not available
        if not domain_pattern:
            if re.match(self.apn_domain_pattern, apn_value):
                return ValidationResult(is_valid=True)
            if re.match(self.apn_ip_pattern, apn_value):
                return ValidationResult(is_valid=True)
            if re.match(self.apn_url_pattern, apn_value):
                return ValidationResult(is_valid=True)
            if re.match(self.apn_simple_pattern, apn_value):
                return ValidationResult(is_valid=True)
        
        # If none of the patterns match, return detailed error
        return ValidationResult(
            is_valid=False,
            error_message="APN format is invalid. Must be a valid domain name, IP address, URL, or simple name",
            error_code='INVALID_APN_FORMAT'
        )
    
    def _get_apn_suggestions(self, invalid_apn: str) -> List[str]:
        """
        Get APN suggestions based on invalid input.
        
        Args:
            invalid_apn: The invalid APN value
            
        Returns:
            List of suggested APN values
        """
        suggestions = []
        
        # Fix consecutive dots
        if '..' in invalid_apn:
            fixed_apn = re.sub(r'\.+', '.', invalid_apn)
            suggestions.append(fixed_apn)
        
        # Remove leading/trailing dots
        cleaned_apn = invalid_apn.strip('.')
        if cleaned_apn != invalid_apn and cleaned_apn:
            suggestions.append(cleaned_apn)
        
        # Check for partial matches with common carriers
        lower_apn = invalid_apn.lower()
        for carrier, apns in self.common_carrier_apns.items():
            if carrier in lower_apn:
                suggestions.extend(apns)
        
        return list(set(suggestions))  # Remove duplicates
    
    def _log_validation_attempt(self, param_name: str, value: str, validation_type: str):
        """
        Log validation attempt for debugging and monitoring.
        
        Args:
            param_name: Name of the parameter being validated
            value: Value being validated (masked for sensitive data)
            validation_type: Type of validation being performed
        """
        # Mask sensitive credential values
        masked_value = value
        if param_name in ['apn_password', 'password']:
            masked_value = '*' * len(value) if value else ''
        elif param_name == 'apn_user' and value:
            masked_value = value[:2] + '*' * (len(value) - 2) if len(value) > 2 else '*' * len(value)
        
        self.logger.info(f"Validation attempt - Parameter: {param_name}, Type: {validation_type}, Value: {masked_value}, Timestamp: {datetime.now().isoformat()}")
    
    def _log_validation_result(self, param_name: str, value: str, result: ValidationResult):
        """
        Log validation result for debugging and monitoring.
        
        Args:
            param_name: Name of the parameter that was validated
            value: Value that was validated (masked for sensitive data)
            result: ValidationResult object
        """
        # Mask sensitive credential values
        masked_value = value
        if param_name in ['apn_password', 'password']:
            masked_value = '*' * len(value) if value else ''
        elif param_name == 'apn_user' and value:
            masked_value = value[:2] + '*' * (len(value) - 2) if len(value) > 2 else '*' * len(value)
        
        log_data = {
            'parameter': param_name,
            'value': masked_value,
            'is_valid': result.is_valid,
            'error_code': result.error_code,
            'error_message': result.error_message,
            'timestamp': datetime.now().isoformat()
        }
        
        if result.is_valid:
            self.logger.info(f"Validation success - {log_data}")
        else:
            self.logger.warning(f"Validation failure - {log_data}")
    
    def validate_apn_configuration(self, apn: str, username: str = "", password: str = "", 
                                 source: str = 'api') -> ValidationResult:
        """
        Validate complete APN configuration including credentials.
        
        Args:
            apn: APN name/address
            username: APN username (optional)
            password: APN password (optional)
            
        Returns:
            ValidationResult for the complete APN configuration
        """
        start_time = datetime.now()
        
        # Validate APN name
        apn_result = self._validate_apn('apn', apn, self.validation_rules.get('apn', {}))
        if not apn_result.is_valid:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.log_validation_attempt('apn', apn, 'apn_configuration', source, apn_result, execution_time)
            return apn_result
        
        # Validate username if provided
        if username:
            user_result = self._validate_apn_credential('apn_user', username, self.validation_rules.get('apn_user', {}))
            if not user_result.is_valid:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                self.log_validation_attempt('apn_user', username, 'apn_configuration', source, user_result, execution_time)
                return user_result
        
        # Validate password if provided
        if password:
            pass_result = self._validate_apn_credential('apn_password', password, self.validation_rules.get('apn_password', {}))
            if not pass_result.is_valid:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                self.log_validation_attempt('apn_password', password, 'apn_configuration', source, pass_result, execution_time)
                return pass_result
        
        # Log successful complete validation
        result = ValidationResult(is_valid=True)
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        context = {
            'apn': apn,
            'username_provided': bool(username),
            'password_provided': bool(password)
        }
        
        self.log_validation_attempt('apn_configuration', 'complete', 'apn_configuration', source, result, execution_time, context)
        self.logger.info(f"Complete APN configuration validation successful - APN: {apn}, Username provided: {bool(username)}, Password provided: {bool(password)}")
        
        return result
    
    def validate_connection_required(self, serial_service) -> ValidationResult:
        """
        Validate that device connection is available for operations that require it.
        
        Args:
            serial_service: SerialService instance to check connection status
            
        Returns:
            ValidationResult indicating if connection is available
        """
        if not hasattr(serial_service, 'is_connected') or not serial_service.is_connected:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_connection_required', 'Device connection is required for this operation'),
                error_code='CONNECTION_REQUIRED'
            )
        
        return ValidationResult(is_valid=True)
    
    def validate_profile_data(self, profile_data: Dict) -> ValidationResult:
        """
        Validate configuration profile data structure.
        
        Args:
            profile_data: Dictionary containing profile configuration
            
        Returns:
            ValidationResult indicating if profile data is valid
        """
        if not isinstance(profile_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_invalid_profile_format', 'Profile data must be a valid configuration object'),
                error_code='INVALID_PROFILE_FORMAT'
            )
        
        # Validate required sections
        required_sections = ['version']
        for section in required_sections:
            if section not in profile_data:
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_missing_profile_section', 'Profile is missing required section: {section}').format(section=section),
                    error_code='MISSING_PROFILE_SECTION'
                )
        
        # Validate individual parameters in profile
        errors = []
        for section_name, section_data in profile_data.items():
            if section_name == 'version':
                continue
                
            if isinstance(section_data, dict):
                for param_name, param_value in section_data.items():
                    # Pass the whole section as context so conditional validations
                    # (for example: skip speed_detection_time/speed_limit when
                    # speed_alert_enabled is False) can make decisions based on
                    # sibling fields.
                    result = self.validate_parameter(param_name, param_value, context=section_data)
                    if not result.is_valid:
                        errors.append(f"{section_name}.{param_name}: {result.error_message}")
        
        if errors:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_profile_errors', 'Profile validation errors: {errors}').format(errors="; ".join(errors)),
                error_code='PROFILE_VALIDATION_ERRORS'
            )
        
        return ValidationResult(is_valid=True)
    
    def get_parameter_info(self, param_name: str) -> Optional[Dict]:
        """
        Get validation rules and information for a parameter.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            Dictionary with parameter validation rules or None if not found
        """
        return self.validation_rules.get(param_name)
    
    def get_all_parameters(self) -> List[str]:
        """
        Get list of all supported parameter names.
        
        Returns:
            List of parameter names
        """
        return list(self.validation_rules.keys())    

    def validate_specification_parameter(self, section_name: str, param_name: str, field_name: str, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate a parameter from the specification with proper field mapping.
        
        Args:
            section_name: Name of the parameter section
            param_name: Name of the parameter
            field_name: Name of the specific field (for multi-field parameters)
            value: Value to validate
            context: Optional context for conditional validation
            
        Returns:
            ValidationResult with validation status and error details
        """
        # Map specification field names to validation rule names
        validation_key = self._get_validation_key(section_name, param_name, field_name)
        
        if validation_key:
            return self.validate_parameter(validation_key, value, context)
        else:
            # If no specific validation rule exists, perform basic validation
            return self._validate_basic_field(field_name, value)
    
    def _get_validation_key(self, section_name: str, param_name: str, field_name: str) -> Optional[str]:
        """
        Map specification parameter names to validation rule keys.
        
        Args:
            section_name: Name of the parameter section
            param_name: Name of the parameter
            field_name: Name of the specific field
            
        Returns:
            Validation rule key or None if not found
        """
        # Direct field name mapping
        if field_name in self.validation_rules:
            return field_name
        
        # Section-specific mapping
        mapping = {
            'network_parameters': {
                'apn_settings': {
                    'apn': 'apn',
                    'user': 'apn_user',
                    'password': 'apn_password'
                },
                'server_settings': {
                    'address': 'server_address',
                    'port': 'server_port'
                }
            },
            'time_parameters': {
                'report_intervals': {
                    'moving_time': 'moving_time',
                    'stopped_time': 'stopped_time'
                },
                'heartbeat_intervals': {
                    'moving_heartbeat': 'moving_heartbeat',
                    'stopped_heartbeat': 'stopped_heartbeat'
                }
            },
            'service_parameters': {
                'protocol': 'protocol',
                'tcp_ack': 'tcp_ack'
            },
            'ignition': {
                'ignition_type': {
                    'ignition_mode': 'ignition_mode',
                    'on_voltage': 'on_voltage',
                    'off_voltage': 'off_voltage'
                }
            },
            'speed': {
                'speed_alert': {
                    'detection_time': 'speed_detection_time',
                    'speed_limit': 'speed_limit',
                    'alert_type': 'speed_alert_type'
                }
            },
            'power_saving': {
                'sleep_mode': 'sleep_mode',
                'sleep_time': 'sleep_time'
            },
            'angle': {
                'angle_report': {
                    'min_speed': 'angle_min_speed',
                    'angle_variation': 'angle_variation'
                }
            },
            'battery_alerts': {
                'main_power_alert': {
                    'detection_time': 'power_detection_time',
                    'min_charge_time': 'min_charge_time',
                    'alert_type': 'battery_alert_type'
                }
            },
            'vibration_sensor': {
                'vibration_sensitivity': {
                    'level': 'vibration_level'
                }
            },
            'jammer_detection': {
                'jammer_relay_action': {
                    'confirmation_time': 'jammer_confirmation_time',
                    'speed_limit': 'jammer_speed_limit',
                    'output_operation': 'jammer_output_operation'
                }
            },
            'miscellaneous': {
                'odometer': 'odometer',
                'hourmeter': 'hourmeter'
            }
        }
        
        section_mapping = mapping.get(section_name, {})
        param_mapping = section_mapping.get(param_name, {})
        
        if isinstance(param_mapping, dict):
            return param_mapping.get(field_name)
        else:
            return param_mapping if param_mapping else None
    
    def _validate_basic_field(self, field_name: str, value: Any) -> ValidationResult:
        """
        Perform basic validation for fields without specific rules.
        
        Args:
            field_name: Name of the field
            value: Value to validate
            
        Returns:
            ValidationResult with basic validation
        """
        # Basic validation for common field types
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_required_field', '{param_name} é obrigatório e não pode estar vazio').format(param_name=field_name),
                error_code='REQUIRED_FIELD'
            )
        
        return ValidationResult(is_valid=True)
    
    def get_validation_rules_for_specification(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all validation rules organized by specification sections.
        
        Returns:
            Dictionary of validation rules organized by sections
        """
        return {
            'network_parameters': {
                'apn': self.validation_rules.get('apn'),
                'apn_user': self.validation_rules.get('apn_user'),
                'apn_password': self.validation_rules.get('apn_password'),
                'server_address': self.validation_rules.get('server_address'),
                'server_port': self.validation_rules.get('server_port')
            },
            'time_parameters': {
                'moving_time': self.validation_rules.get('moving_time'),
                'stopped_time': self.validation_rules.get('stopped_time'),
                'moving_heartbeat': self.validation_rules.get('moving_heartbeat'),
                'stopped_heartbeat': self.validation_rules.get('stopped_heartbeat')
            },
            'service_parameters': {
                'protocol': self.validation_rules.get('protocol'),
                'tcp_ack': self.validation_rules.get('tcp_ack')
            },
            'ignition': {
                'ignition_mode': self.validation_rules.get('ignition_mode'),
                'on_voltage': self.validation_rules.get('on_voltage'),
                'off_voltage': self.validation_rules.get('off_voltage')
            },
            'speed': {
                'speed_detection_time': self.validation_rules.get('speed_detection_time'),
                'speed_limit': self.validation_rules.get('speed_limit'),
                'speed_alert_type': self.validation_rules.get('speed_alert_type')
            },
            'power_saving': {
                'sleep_mode': self.validation_rules.get('sleep_mode'),
                'sleep_time': self.validation_rules.get('sleep_time')
            },
            'angle': {
                'angle_min_speed': self.validation_rules.get('angle_min_speed'),
                'angle_variation': self.validation_rules.get('angle_variation')
            },
            'battery_alerts': {
                'power_detection_time': self.validation_rules.get('power_detection_time'),
                'min_charge_time': self.validation_rules.get('min_charge_time'),
                'battery_alert_type': self.validation_rules.get('battery_alert_type')
            },
            'vibration_sensor': {
                'vibration_level': self.validation_rules.get('vibration_level')
            },
            'jammer_detection': {
                'jammer_confirmation_time': self.validation_rules.get('jammer_confirmation_time'),
                'jammer_speed_limit': self.validation_rules.get('jammer_speed_limit'),
                'jammer_output_operation': self.validation_rules.get('jammer_output_operation')
            },
            'miscellaneous': {
                'odometer': self.validation_rules.get('odometer'),
                'hourmeter': self.validation_rules.get('hourmeter')
            }
        }
    
    def _init_debug_logging(self):
        """Initialize enhanced debug logging configuration with comprehensive tracking."""
        # Create dedicated validation logger
        self.validation_logger = logging.getLogger(f"{__name__}.validation")
        
        # Set up structured logging formats for different log types
        validation_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        debug_formatter = logging.Formatter(
            '%(asctime)s - DEBUG - %(funcName)s:%(lineno)d - %(message)s'
        )
        metrics_formatter = logging.Formatter(
            '%(asctime)s - METRICS - %(message)s'
        )
        analytics_formatter = logging.Formatter(
            '%(asctime)s - ANALYTICS - %(message)s'
        )
        
        # Create file handlers for different log types
        try:
            import os
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # Main validation log
            validation_log_file = os.path.join(log_dir, 'validation.log')
            self.validation_file_handler = logging.FileHandler(validation_log_file, encoding='utf-8')
            self.validation_file_handler.setFormatter(validation_formatter)
            self.validation_logger.addHandler(self.validation_file_handler)
            
            # Debug log for detailed troubleshooting
            debug_log_file = os.path.join(log_dir, 'validation_debug.log')
            self.debug_file_handler = logging.FileHandler(debug_log_file, encoding='utf-8')
            self.debug_file_handler.setFormatter(debug_formatter)
            
            # Metrics log for performance and analytics
            metrics_log_file = os.path.join(log_dir, 'validation_metrics.log')
            self.metrics_file_handler = logging.FileHandler(metrics_log_file, encoding='utf-8')
            self.metrics_file_handler.setFormatter(metrics_formatter)
            
            # Analytics log for error pattern analysis
            analytics_log_file = os.path.join(log_dir, 'validation_analytics.log')
            self.analytics_file_handler = logging.FileHandler(analytics_log_file, encoding='utf-8')
            self.analytics_file_handler.setFormatter(analytics_formatter)
            
            # Create separate loggers for different purposes
            self.debug_logger = logging.getLogger(f"{__name__}.debug")
            self.debug_logger.addHandler(self.debug_file_handler)
            self.debug_logger.setLevel(logging.DEBUG)
            
            self.metrics_logger = logging.getLogger(f"{__name__}.metrics")
            self.metrics_logger.addHandler(self.metrics_file_handler)
            self.metrics_logger.setLevel(logging.INFO)
            
            self.analytics_logger = logging.getLogger(f"{__name__}.analytics")
            self.analytics_logger.addHandler(self.analytics_file_handler)
            self.analytics_logger.setLevel(logging.INFO)
            
            # Set initial log level
            self.validation_logger.setLevel(logging.INFO)
            
        except Exception as e:
            self.logger.warning(f"Could not set up validation log files: {e}")
        
        # Initialize enhanced validation analytics tracking
        self._validation_analytics = {
            'hourly_stats': defaultdict(lambda: {'attempts': 0, 'failures': 0, 'avg_time_ms': 0.0}),
            'daily_stats': defaultdict(lambda: {'attempts': 0, 'failures': 0, 'avg_time_ms': 0.0}),
            'error_frequency': defaultdict(int),
            'parameter_trends': defaultdict(list),
            'performance_tracking': deque(maxlen=1000),
            'source_analytics': defaultdict(lambda: {'attempts': 0, 'failures': 0}),
            'validation_rules_hit': defaultdict(int),
            'error_recovery_patterns': defaultdict(list),
            'user_behavior_patterns': defaultdict(list),
            'validation_success_patterns': defaultdict(list),
            'time_based_patterns': defaultdict(lambda: defaultdict(int)),
            'correlation_patterns': defaultdict(lambda: defaultdict(int))
        }
        
        # Initialize debug mode from environment or config
        import os
        self._debug_mode = os.getenv('VALIDATION_DEBUG', 'false').lower() == 'true'
        
        # Enhanced debug configuration
        self._debug_config = {
            'log_context': True,
            'log_performance': True,
            'log_error_patterns': True,
            'log_suggestions': True,
            'detailed_stack_traces': self._debug_mode,
            'log_user_patterns': True,
            'log_correlation_analysis': True,
            'log_success_patterns': True,
            'performance_profiling': self._debug_mode
        }
        
        # Initialize validation success rate monitoring
        self._success_rate_monitor = {
            'window_size': 100,
            'alert_threshold': 70.0,  # Alert if success rate drops below 70%
            'recent_attempts': deque(maxlen=100),
            'last_alert_time': None,
            'alert_cooldown_minutes': 15
        }
        
        if self._debug_mode:
            self.validation_logger.setLevel(logging.DEBUG)
            self.validation_logger.addHandler(self.debug_file_handler)
            self.logger.info("Enhanced validation debug mode enabled with comprehensive tracking")
    
    def log_validation_attempt(self, parameter_name: str, value: str, validation_type: str, 
                             source: str, result: ValidationResult, execution_time_ms: float = 0.0,
                             context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a validation attempt with structured data and comprehensive analytics.
        
        Args:
            parameter_name: Name of the parameter being validated
            value: Value being validated (will be masked for sensitive data)
            validation_type: Type of validation performed
            source: Source of the validation request ('ui', 'command', 'api', 'profile')
            result: ValidationResult from the validation
            execution_time_ms: Time taken for validation in milliseconds
            context: Optional additional context information
        """
        with self._lock:
            # Mask sensitive values
            masked_value = self._mask_sensitive_value(parameter_name, value)
            
            # Create validation attempt record
            attempt = ValidationAttempt(
                timestamp=datetime.now(),
                parameter_name=parameter_name,
                value=masked_value,
                validation_type=validation_type,
                source=source,
                result=result,
                execution_time_ms=execution_time_ms,
                context=context or {}
            )
            
            # Store attempt in memory
            self._validation_attempts.append(attempt)
            
            # Update metrics
            self._update_validation_metrics(attempt)
            
            # Update analytics tracking
            self._update_validation_analytics(attempt)
            
            # Log the attempt
            self._log_structured_attempt(attempt)
            
            # Track error patterns and correlations
            if not result.is_valid:
                self._track_error_pattern(parameter_name, result.error_code, result.error_message)
                self._analyze_error_correlations(attempt)
            else:
                self._track_success_patterns(attempt)
            
            # Monitor success rate and alert if needed
            self._monitor_success_rate(attempt)
            
            # Log performance issues if detected
            if execution_time_ms > self._performance_thresholds['slow_validation_ms']:
                self._log_performance_issue(attempt)
    
    def _mask_sensitive_value(self, parameter_name: str, value: str) -> str:
        """
        Mask sensitive parameter values for logging.
        
        Args:
            parameter_name: Name of the parameter
            value: Value to potentially mask
            
        Returns:
            Masked value for logging
        """
        sensitive_params = {'apn_password', 'password', 'apn_user'}
        
        if parameter_name.lower() in sensitive_params:
            if not value:
                return "[empty]"
            elif len(value) <= 2:
                return "*" * len(value)
            else:
                return value[0] + "*" * (len(value) - 2) + value[-1]
        
        return str(value)
    
    def _update_validation_metrics(self, attempt: ValidationAttempt) -> None:
        """
        Update validation metrics with the latest attempt.
        
        Args:
            attempt: ValidationAttempt to process
        """
        self._metrics.total_attempts += 1
        
        if attempt.result.is_valid:
            self._metrics.successful_validations += 1
        else:
            self._metrics.failed_validations += 1
        
        # Update success rate
        self._metrics.success_rate = (
            self._metrics.successful_validations / self._metrics.total_attempts * 100
        )
        
        # Update average execution time
        total_time = (self._metrics.average_execution_time_ms * (self._metrics.total_attempts - 1) + 
                     attempt.execution_time_ms)
        self._metrics.average_execution_time_ms = total_time / self._metrics.total_attempts
        
        # Update parameter-specific stats
        param_stats = self._parameter_stats[attempt.parameter_name]
        param_stats['attempts'] += 1
        
        if not attempt.result.is_valid:
            param_stats['failures'] += 1
        
        # Update parameter failure rates
        self._metrics.parameter_failure_rates[attempt.parameter_name] = (
            param_stats['failures'] / param_stats['attempts'] * 100
        )
    
    def _log_structured_attempt(self, attempt: ValidationAttempt) -> None:
        """
        Log validation attempt with structured format.
        
        Args:
            attempt: ValidationAttempt to log
        """
        log_data = {
            'timestamp': attempt.timestamp.isoformat(),
            'parameter': attempt.parameter_name,
            'value': attempt.value,
            'validation_type': attempt.validation_type,
            'source': attempt.source,
            'is_valid': attempt.result.is_valid,
            'error_code': attempt.result.error_code,
            'execution_time_ms': attempt.execution_time_ms,
            'context': attempt.context
        }
        
        if attempt.result.is_valid:
            self.validation_logger.info(f"VALIDATION_SUCCESS: {json.dumps(log_data)}")
        else:
            log_data['error_message'] = attempt.result.error_message
            self.validation_logger.warning(f"VALIDATION_FAILURE: {json.dumps(log_data)}")
        
        # Debug mode: log additional details
        if self._debug_mode:
            debug_data = {
                'suggested_value': attempt.result.suggested_value,
                'warning_message': attempt.result.warning_message,
                'validation_level': attempt.result.validation_level
            }
            self.validation_logger.debug(f"VALIDATION_DEBUG: {json.dumps(debug_data)}")
    
    def _track_error_pattern(self, parameter_name: str, error_code: str, error_message: str) -> None:
        """
        Track error patterns for analytics.
        
        Args:
            parameter_name: Name of the parameter that failed validation
            error_code: Error code from validation
            error_message: Error message from validation
        """
        pattern_key = f"{parameter_name}:{error_code}"
        self._error_patterns[pattern_key] += 1
        
        # Update common errors in metrics
        self._metrics.common_errors[error_code] = self._metrics.common_errors.get(error_code, 0) + 1
    
    def _update_validation_analytics(self, attempt: ValidationAttempt) -> None:
        """
        Update comprehensive validation analytics with the latest attempt.
        
        Args:
            attempt: ValidationAttempt to analyze
        """
        timestamp = attempt.timestamp
        hour_key = timestamp.strftime('%Y-%m-%d %H:00')
        day_key = timestamp.strftime('%Y-%m-%d')
        
        # Update hourly statistics
        hourly_stats = self._validation_analytics['hourly_stats'][hour_key]
        hourly_stats['attempts'] += 1
        if not attempt.result.is_valid:
            hourly_stats['failures'] += 1
        
        # Update average execution time for the hour
        current_avg = hourly_stats['avg_time_ms']
        current_count = hourly_stats['attempts']
        hourly_stats['avg_time_ms'] = ((current_avg * (current_count - 1)) + attempt.execution_time_ms) / current_count
        
        # Update daily statistics
        daily_stats = self._validation_analytics['daily_stats'][day_key]
        daily_stats['attempts'] += 1
        if not attempt.result.is_valid:
            daily_stats['failures'] += 1
        
        # Update daily average execution time
        current_avg = daily_stats['avg_time_ms']
        current_count = daily_stats['attempts']
        daily_stats['avg_time_ms'] = ((current_avg * (current_count - 1)) + attempt.execution_time_ms) / current_count
        
        # Track error frequency
        if not attempt.result.is_valid:
            self._validation_analytics['error_frequency'][attempt.result.error_code] += 1
        
        # Track parameter trends
        trend_data = {
            'timestamp': timestamp.isoformat(),
            'is_valid': attempt.result.is_valid,
            'execution_time_ms': attempt.execution_time_ms,
            'source': attempt.source,
            'error_code': attempt.result.error_code if not attempt.result.is_valid else None
        }
        self._validation_analytics['parameter_trends'][attempt.parameter_name].append(trend_data)
        
        # Keep only last 50 trend entries per parameter
        if len(self._validation_analytics['parameter_trends'][attempt.parameter_name]) > 50:
            self._validation_analytics['parameter_trends'][attempt.parameter_name] = \
                self._validation_analytics['parameter_trends'][attempt.parameter_name][-50:]
        
        # Track performance data
        performance_data = {
            'timestamp': timestamp.isoformat(),
            'parameter': attempt.parameter_name,
            'execution_time_ms': attempt.execution_time_ms,
            'validation_type': attempt.validation_type,
            'source': attempt.source
        }
        self._validation_analytics['performance_tracking'].append(performance_data)
        
        # Update source analytics
        source_stats = self._validation_analytics['source_analytics'][attempt.source]
        source_stats['attempts'] += 1
        if not attempt.result.is_valid:
            source_stats['failures'] += 1
        
        # Track validation rules hit
        rule_key = f"{attempt.parameter_name}:{attempt.validation_type}"
        self._validation_analytics['validation_rules_hit'][rule_key] += 1
        
        # Track time-based patterns
        time_pattern_key = timestamp.strftime('%H')  # Hour of day
        self._validation_analytics['time_based_patterns'][time_pattern_key][attempt.parameter_name] += 1
        
        # Log analytics data if debug mode is enabled
        if self._debug_mode and self._debug_config.get('log_user_patterns', False):
            analytics_data = {
                'parameter': attempt.parameter_name,
                'source': attempt.source,
                'hour': hour_key,
                'day': day_key,
                'execution_time_ms': attempt.execution_time_ms,
                'is_valid': attempt.result.is_valid
            }
            self.analytics_logger.info(f"ANALYTICS_UPDATE: {json.dumps(analytics_data)}")
    
    def _analyze_error_correlations(self, attempt: ValidationAttempt) -> None:
        """
        Analyze error correlations to identify patterns in validation failures.
        
        Args:
            attempt: Failed validation attempt to analyze
        """
        if attempt.result.is_valid:
            return
        
        # Look for correlations with recent attempts
        recent_attempts = list(self._validation_attempts)[-10:]  # Last 10 attempts
        
        # Analyze parameter correlation patterns
        for recent_attempt in recent_attempts:
            if recent_attempt.parameter_name != attempt.parameter_name and not recent_attempt.result.is_valid:
                correlation_key = f"{recent_attempt.parameter_name}->{attempt.parameter_name}"
                self._validation_analytics['correlation_patterns'][correlation_key][attempt.result.error_code] += 1
        
        # Analyze source correlation patterns
        source_errors = [a for a in recent_attempts if a.source == attempt.source and not a.result.is_valid]
        if len(source_errors) > 1:
            error_pattern = {
                'source': attempt.source,
                'error_sequence': [a.result.error_code for a in source_errors[-5:]],  # Last 5 errors
                'timestamp': attempt.timestamp.isoformat()
            }
            self._validation_analytics['error_recovery_patterns'][attempt.source].append(error_pattern)
            
            # Keep only last 20 error patterns per source
            if len(self._validation_analytics['error_recovery_patterns'][attempt.source]) > 20:
                self._validation_analytics['error_recovery_patterns'][attempt.source] = \
                    self._validation_analytics['error_recovery_patterns'][attempt.source][-20:]
        
        # Log correlation analysis if debug mode is enabled
        if self._debug_mode and self._debug_config.get('log_correlation_analysis', False):
            correlation_data = {
                'parameter': attempt.parameter_name,
                'error_code': attempt.result.error_code,
                'recent_errors': [a.result.error_code for a in recent_attempts if not a.result.is_valid],
                'source_error_count': len(source_errors),
                'timestamp': attempt.timestamp.isoformat()
            }
            self.analytics_logger.info(f"ERROR_CORRELATION: {json.dumps(correlation_data)}")
    
    def _track_success_patterns(self, attempt: ValidationAttempt) -> None:
        """
        Track patterns in successful validations to identify best practices.
        
        Args:
            attempt: Successful validation attempt to analyze
        """
        if not attempt.result.is_valid:
            return
        
        success_pattern = {
            'parameter': attempt.parameter_name,
            'value_length': len(str(attempt.value)),
            'validation_type': attempt.validation_type,
            'source': attempt.source,
            'execution_time_ms': attempt.execution_time_ms,
            'timestamp': attempt.timestamp.isoformat(),
            'context_keys': list(attempt.context.keys()) if attempt.context else []
        }
        
        self._validation_analytics['validation_success_patterns'][attempt.parameter_name].append(success_pattern)
        
        # Keep only last 30 success patterns per parameter
        if len(self._validation_analytics['validation_success_patterns'][attempt.parameter_name]) > 30:
            self._validation_analytics['validation_success_patterns'][attempt.parameter_name] = \
                self._validation_analytics['validation_success_patterns'][attempt.parameter_name][-30:]
        
        # Log success patterns if debug mode is enabled
        if self._debug_mode and self._debug_config.get('log_success_patterns', False):
            self.analytics_logger.info(f"SUCCESS_PATTERN: {json.dumps(success_pattern)}")
    
    def _monitor_success_rate(self, attempt: ValidationAttempt) -> None:
        """
        Monitor validation success rate and alert if it drops below threshold.
        
        Args:
            attempt: Latest validation attempt
        """
        # Add to recent attempts window
        self._success_rate_monitor['recent_attempts'].append(attempt.result.is_valid)
        
        # Calculate current success rate
        if len(self._success_rate_monitor['recent_attempts']) >= 10:  # Need at least 10 attempts
            recent_successes = sum(self._success_rate_monitor['recent_attempts'])
            success_rate = (recent_successes / len(self._success_rate_monitor['recent_attempts'])) * 100
            
            # Check if success rate is below threshold
            if success_rate < self._success_rate_monitor['alert_threshold']:
                current_time = datetime.now()
                last_alert = self._success_rate_monitor['last_alert_time']
                
                # Check cooldown period
                if (last_alert is None or 
                    (current_time - last_alert).total_seconds() > 
                    self._success_rate_monitor['alert_cooldown_minutes'] * 60):
                    
                    alert_data = {
                        'current_success_rate': success_rate,
                        'threshold': self._success_rate_monitor['alert_threshold'],
                        'window_size': len(self._success_rate_monitor['recent_attempts']),
                        'recent_failures': len(self._success_rate_monitor['recent_attempts']) - recent_successes,
                        'timestamp': current_time.isoformat()
                    }
                    
                    self.validation_logger.warning(f"SUCCESS_RATE_ALERT: {json.dumps(alert_data)}")
                    self._success_rate_monitor['last_alert_time'] = current_time
    
    def _log_performance_issue(self, attempt: ValidationAttempt) -> None:
        """
        Log performance issues for slow validations.
        
        Args:
            attempt: Validation attempt with performance issue
        """
        performance_data = {
            'parameter': attempt.parameter_name,
            'execution_time_ms': attempt.execution_time_ms,
            'validation_type': attempt.validation_type,
            'source': attempt.source,
            'threshold_ms': self._performance_thresholds['slow_validation_ms'],
            'timestamp': attempt.timestamp.isoformat(),
            'context_size': len(attempt.context) if attempt.context else 0
        }
        
        if attempt.execution_time_ms > self._performance_thresholds['very_slow_validation_ms']:
            self.validation_logger.error(f"VERY_SLOW_VALIDATION: {json.dumps(performance_data)}")
        else:
            self.validation_logger.warning(f"SLOW_VALIDATION: {json.dumps(performance_data)}")
        
        # Log additional debug info if debug mode is enabled
        if self._debug_mode and self._debug_config.get('performance_profiling', False):
            debug_data = {
                'parameter_rules': str(self.validation_rules.get(attempt.parameter_name, {})),
                'value_length': len(str(attempt.value)),
                'context': attempt.context
            }
            self.debug_logger.debug(f"PERFORMANCE_DEBUG: {json.dumps(debug_data)}")
    
    def get_validation_metrics(self) -> ValidationMetrics:
        """
        Get current validation metrics.
        
        Returns:
            ValidationMetrics with current statistics
        """
        with self._lock:
            return ValidationMetrics(
                total_attempts=self._metrics.total_attempts,
                successful_validations=self._metrics.successful_validations,
                failed_validations=self._metrics.failed_validations,
                success_rate=self._metrics.success_rate,
                average_execution_time_ms=self._metrics.average_execution_time_ms,
                common_errors=dict(self._metrics.common_errors),
                parameter_failure_rates=dict(self._metrics.parameter_failure_rates)
            )
    
    def get_validation_history(self, limit: int = 100) -> List[ValidationAttempt]:
        """
        Get recent validation attempts.
        
        Args:
            limit: Maximum number of attempts to return
            
        Returns:
            List of recent ValidationAttempt objects
        """
        with self._lock:
            return list(self._validation_attempts)[-limit:]
    
    def get_error_analytics(self) -> Dict[str, Any]:
        """
        Get validation error analytics for troubleshooting.
        
        Returns:
            Dictionary with error analytics data
        """
        with self._lock:
            # Get most common error patterns
            sorted_patterns = sorted(
                self._error_patterns.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Get parameters with highest failure rates
            high_failure_params = {
                param: rate for param, rate in self._metrics.parameter_failure_rates.items()
                if rate > 10.0  # More than 10% failure rate
            }
            
            # Get recent error trends
            recent_attempts = list(self._validation_attempts)[-100:]
            recent_errors = [
                attempt for attempt in recent_attempts 
                if not attempt.result.is_valid
            ]
            
            error_trend = {}
            source_breakdown = {}
            for attempt in recent_errors:
                hour_key = attempt.timestamp.strftime('%Y-%m-%d %H:00')
                error_trend[hour_key] = error_trend.get(hour_key, 0) + 1
                source_breakdown[attempt.source] = source_breakdown.get(attempt.source, 0) + 1
            
            # Get validation success rate by source
            source_success_rates = {}
            for source in ['ui', 'command', 'api', 'profile']:
                source_attempts = [a for a in self._validation_attempts if a.source == source]
                if source_attempts:
                    successful = sum(1 for a in source_attempts if a.result.is_valid)
                    source_success_rates[source] = (successful / len(source_attempts)) * 100
            
            # Get most problematic parameters
            problematic_params = {}
            for param_name, stats in self._parameter_stats.items():
                if stats['attempts'] > 5:  # Only consider parameters with enough attempts
                    failure_rate = (stats['failures'] / stats['attempts']) * 100
                    if failure_rate > 20:  # More than 20% failure rate
                        problematic_params[param_name] = {
                            'failure_rate': failure_rate,
                            'total_attempts': stats['attempts'],
                            'total_failures': stats['failures']
                        }
            
            return {
                'most_common_error_patterns': sorted_patterns[:10],
                'high_failure_rate_parameters': high_failure_params,
                'recent_error_trend': error_trend,
                'error_source_breakdown': source_breakdown,
                'source_success_rates': source_success_rates,
                'problematic_parameters': problematic_params,
                'total_error_patterns': len(self._error_patterns),
                'performance_issues': self._get_performance_issues()
            }
    
    def _get_performance_issues(self) -> List[Dict[str, Any]]:
        """
        Identify validation performance issues.
        
        Returns:
            List of performance issues found
        """
        issues = []
        
        # Check for slow validations
        slow_validations = [
            attempt for attempt in self._validation_attempts
            if attempt.execution_time_ms > self._performance_thresholds['slow_validation_ms']
        ]
        
        if slow_validations:
            avg_slow_time = sum(a.execution_time_ms for a in slow_validations) / len(slow_validations)
            issues.append({
                'type': 'slow_validation',
                'count': len(slow_validations),
                'average_time_ms': avg_slow_time,
                'threshold_ms': self._performance_thresholds['slow_validation_ms']
            })
        
        # Check for very slow validations
        very_slow_validations = [
            attempt for attempt in self._validation_attempts
            if attempt.execution_time_ms > self._performance_thresholds['very_slow_validation_ms']
        ]
        
        if very_slow_validations:
            issues.append({
                'type': 'very_slow_validation',
                'count': len(very_slow_validations),
                'parameters': list(set(a.parameter_name for a in very_slow_validations))
            })
        
        return issues
    
    def enable_debug_mode(self) -> None:
        """Enable debug mode for detailed validation logging."""
        self._debug_mode = True
        self.validation_logger.setLevel(logging.DEBUG)
        self.validation_logger.info("Debug mode enabled")
    
    def disable_debug_mode(self) -> None:
        """Disable debug mode."""
        self._debug_mode = False
        self.validation_logger.setLevel(logging.INFO)
        self.validation_logger.info("Debug mode disabled")
    
    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self._debug_mode
    
    def clear_validation_history(self) -> None:
        """Clear validation history and reset metrics."""
        with self._lock:
            self._validation_attempts.clear()
            self._metrics = ValidationMetrics()
            self._error_patterns.clear()
            self._parameter_stats.clear()
            self.validation_logger.info("Validation history and metrics cleared")
    
    def get_validation_insights(self) -> Dict[str, Any]:
        """
        Get validation insights and recommendations for improving validation success rates.
        
        Returns:
            Dictionary with insights and recommendations
        """
        with self._lock:
            insights = {
                'recommendations': [],
                'trends': {},
                'health_score': 0.0,
                'summary': {}
            }
            
            # Calculate overall health score
            if self._metrics.total_attempts > 0:
                insights['health_score'] = self._metrics.success_rate
            
            # Generate recommendations based on error patterns
            if self._metrics.success_rate < 80:
                insights['recommendations'].append({
                    'type': 'low_success_rate',
                    'message': f'Overall validation success rate is {self._metrics.success_rate:.1f}%. Consider reviewing validation rules.',
                    'priority': 'high'
                })
            
            # Check for slow validations
            if self._metrics.average_execution_time_ms > 50:
                insights['recommendations'].append({
                    'type': 'performance',
                    'message': f'Average validation time is {self._metrics.average_execution_time_ms:.1f}ms. Consider optimizing validation logic.',
                    'priority': 'medium'
                })
            
            # Identify parameters that need attention
            for param_name, rate in self._metrics.parameter_failure_rates.items():
                if rate > 30:  # More than 30% failure rate
                    insights['recommendations'].append({
                        'type': 'parameter_issue',
                        'message': f'Parameter "{param_name}" has {rate:.1f}% failure rate. Review validation rules or user guidance.',
                        'priority': 'high',
                        'parameter': param_name
                    })
            
            # Analyze trends over time
            recent_attempts = list(self._validation_attempts)[-50:]
            if len(recent_attempts) >= 10:
                recent_success_rate = sum(1 for a in recent_attempts if a.result.is_valid) / len(recent_attempts) * 100
                if recent_success_rate < self._metrics.success_rate - 10:
                    insights['trends']['declining_performance'] = True
                    insights['recommendations'].append({
                        'type': 'trend',
                        'message': 'Recent validation success rate is declining. Monitor for system issues.',
                        'priority': 'medium'
                    })
            
            # Summary statistics
            insights['summary'] = {
                'total_validations': self._metrics.total_attempts,
                'success_rate': self._metrics.success_rate,
                'most_common_errors': list(self._metrics.common_errors.keys())[:5],
                'parameters_monitored': len(self._parameter_stats),
                'average_response_time_ms': self._metrics.average_execution_time_ms
            }
            
            return insights
    
    def export_validation_data(self, filepath: str) -> bool:
        """
        Export validation data to a JSON file.
        
        Args:
            filepath: Path to export file
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            with self._lock:
                export_data = {
                    'export_timestamp': datetime.now().isoformat(),
                    'metrics': asdict(self._metrics),
                    'error_patterns': dict(self._error_patterns),
                    'parameter_stats': dict(self._parameter_stats),
                    'insights': self.get_validation_insights(),
                    'recent_attempts': [
                        {
                            'timestamp': attempt.timestamp.isoformat(),
                            'parameter_name': attempt.parameter_name,
                            'value': attempt.value,
                            'validation_type': attempt.validation_type,
                            'source': attempt.source,
                            'is_valid': attempt.result.is_valid,
                            'error_code': attempt.result.error_code,
                            'error_message': attempt.result.error_message,
                            'execution_time_ms': attempt.execution_time_ms,
                            'context': attempt.context
                        }
                        for attempt in list(self._validation_attempts)[-500:]  # Last 500 attempts
                    ]
                }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.validation_logger.info(f"Validation data exported to {filepath}")
            return True
            
        except Exception as e:
            self.validation_logger.error(f"Failed to export validation data: {e}")
            return False
    
    def generate_validation_report(self, include_details: bool = True) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            include_details: Whether to include detailed statistics
            
        Returns:
            Formatted validation report as string
        """
        with self._lock:
            report_lines = []
            report_lines.append("=" * 60)
            report_lines.append("VALIDATION SERVICE REPORT")
            report_lines.append("=" * 60)
            report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("")
            
            # Overall metrics
            report_lines.append("OVERALL METRICS")
            report_lines.append("-" * 20)
            report_lines.append(f"Total Validations: {self._metrics.total_attempts}")
            report_lines.append(f"Successful: {self._metrics.successful_validations}")
            report_lines.append(f"Failed: {self._metrics.failed_validations}")
            report_lines.append(f"Success Rate: {self._metrics.success_rate:.1f}%")
            report_lines.append(f"Average Response Time: {self._metrics.average_execution_time_ms:.1f}ms")
            report_lines.append("")
            
            # Error summary
            if self._metrics.common_errors:
                report_lines.append("MOST COMMON ERRORS")
                report_lines.append("-" * 20)
                for error_code, count in sorted(self._metrics.common_errors.items(), 
                                              key=lambda x: x[1], reverse=True)[:5]:
                    report_lines.append(f"{error_code}: {count} occurrences")
                report_lines.append("")
            
            # Parameter failure rates
            if self._metrics.parameter_failure_rates:
                high_failure_params = {
                    param: rate for param, rate in self._metrics.parameter_failure_rates.items()
                    if rate > 10.0
                }
                if high_failure_params:
                    report_lines.append("HIGH FAILURE RATE PARAMETERS")
                    report_lines.append("-" * 30)
                    for param, rate in sorted(high_failure_params.items(), 
                                            key=lambda x: x[1], reverse=True):
                        report_lines.append(f"{param}: {rate:.1f}% failure rate")
                    report_lines.append("")
            
            # Performance issues
            performance_issues = self._get_performance_issues()
            if performance_issues:
                report_lines.append("PERFORMANCE ISSUES")
                report_lines.append("-" * 20)
                for issue in performance_issues:
                    if issue['type'] == 'slow_validation':
                        report_lines.append(f"Slow validations detected: {issue['count']} validations > {issue['threshold_ms']}ms")
                    elif issue['type'] == 'very_slow_validation':
                        report_lines.append(f"Very slow validations: {issue['count']} validations")
                        report_lines.append(f"Affected parameters: {', '.join(issue['parameters'])}")
                report_lines.append("")
            
            # Insights and recommendations
            insights = self.get_validation_insights()
            if insights['recommendations']:
                report_lines.append("RECOMMENDATIONS")
                report_lines.append("-" * 15)
                for rec in insights['recommendations']:
                    priority_marker = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
                    report_lines.append(f"{priority_marker} {rec['message']}")
                report_lines.append("")
            
            # Debug mode status
            report_lines.append("SYSTEM STATUS")
            report_lines.append("-" * 15)
            report_lines.append(f"Debug Mode: {'Enabled' if self._debug_mode else 'Disabled'}")
            report_lines.append(f"Validation History Size: {len(self._validation_attempts)}")
            report_lines.append(f"Error Patterns Tracked: {len(self._error_patterns)}")
            report_lines.append("")
            
            if include_details and self._validation_attempts:
                report_lines.append("RECENT VALIDATION ATTEMPTS")
                report_lines.append("-" * 30)
                recent_attempts = list(self._validation_attempts)[-10:]
                for attempt in recent_attempts:
                    status = "✓" if attempt.result.is_valid else "✗"
                    report_lines.append(
                        f"{status} {attempt.timestamp.strftime('%H:%M:%S')} "
                        f"{attempt.parameter_name}={attempt.value} "
                        f"({attempt.source}) {attempt.execution_time_ms:.1f}ms"
                    )
                    if not attempt.result.is_valid:
                        report_lines.append(f"    Error: {attempt.result.error_code} - {attempt.result.error_message}")
                report_lines.append("")
            
            report_lines.append("=" * 60)
            
            return "\n".join(report_lines)
    
    def log_validation_summary(self) -> None:
        """Log a summary of validation statistics."""
        summary = {
            'total_attempts': self._metrics.total_attempts,
            'success_rate': self._metrics.success_rate,
            'avg_execution_time_ms': self._metrics.average_execution_time_ms,
            'common_errors': dict(list(self._metrics.common_errors.items())[:3]),
            'debug_mode': self._debug_mode
        }
        
        self.validation_logger.info(f"VALIDATION_SUMMARY: {json.dumps(summary)}")
    
    def reset_validation_metrics(self) -> None:
        """Reset validation metrics while preserving configuration."""
        with self._lock:
            old_total = self._metrics.total_attempts
            self._metrics = ValidationMetrics()
            self._error_patterns.clear()
            self._parameter_stats.clear()
            
            self.validation_logger.info(f"Validation metrics reset. Previous total attempts: {old_total}")
    
    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive validation analytics including error patterns, trends, and correlations.
        
        Returns:
            Dictionary with comprehensive analytics data
        """
        with self._lock:
            analytics = {
                'timestamp': datetime.now().isoformat(),
                'basic_metrics': asdict(self._metrics),
                'time_based_analytics': {
                    'hourly_stats': dict(self._validation_analytics['hourly_stats']),
                    'daily_stats': dict(self._validation_analytics['daily_stats']),
                    'time_patterns': dict(self._validation_analytics['time_based_patterns'])
                },
                'error_analytics': {
                    'error_frequency': dict(self._validation_analytics['error_frequency']),
                    'error_correlations': dict(self._validation_analytics['correlation_patterns']),
                    'error_recovery_patterns': dict(self._validation_analytics['error_recovery_patterns'])
                },
                'parameter_analytics': {
                    'parameter_trends': dict(self._validation_analytics['parameter_trends']),
                    'validation_rules_hit': dict(self._validation_analytics['validation_rules_hit']),
                    'success_patterns': dict(self._validation_analytics['validation_success_patterns'])
                },
                'source_analytics': dict(self._validation_analytics['source_analytics']),
                'performance_analytics': {
                    'recent_performance': list(self._validation_analytics['performance_tracking'])[-50:],
                    'slow_validations': [
                        p for p in self._validation_analytics['performance_tracking']
                        if p['execution_time_ms'] > self._performance_thresholds['slow_validation_ms']
                    ][-20:],
                    'performance_by_parameter': self._get_performance_by_parameter(),
                    'performance_by_source': self._get_performance_by_source()
                },
                'user_behavior_analytics': {
                    'user_patterns': dict(self._validation_analytics['user_behavior_patterns']),
                    'success_rate_trends': self._get_success_rate_trends(),
                    'common_user_errors': self._get_common_user_errors()
                },
                'system_health': {
                    'debug_mode': self._debug_mode,
                    'success_rate_monitor': dict(self._success_rate_monitor),
                    'memory_usage': {
                        'validation_attempts_count': len(self._validation_attempts),
                        'error_patterns_count': len(self._error_patterns),
                        'parameter_stats_count': len(self._parameter_stats)
                    }
                }
            }
            
            return analytics
    
    def _get_performance_by_parameter(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics grouped by parameter."""
        performance_by_param = defaultdict(list)
        
        for perf_data in self._validation_analytics['performance_tracking']:
            performance_by_param[perf_data['parameter']].append(perf_data['execution_time_ms'])
        
        result = {}
        for param, times in performance_by_param.items():
            if times:
                result[param] = {
                    'avg_time_ms': sum(times) / len(times),
                    'max_time_ms': max(times),
                    'min_time_ms': min(times),
                    'sample_count': len(times)
                }
        
        return result
    
    def _get_performance_by_source(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics grouped by source."""
        performance_by_source = defaultdict(list)
        
        for perf_data in self._validation_analytics['performance_tracking']:
            performance_by_source[perf_data['source']].append(perf_data['execution_time_ms'])
        
        result = {}
        for source, times in performance_by_source.items():
            if times:
                result[source] = {
                    'avg_time_ms': sum(times) / len(times),
                    'max_time_ms': max(times),
                    'min_time_ms': min(times),
                    'sample_count': len(times)
                }
        
        return result
    
    def _get_success_rate_trends(self) -> Dict[str, float]:
        """Get success rate trends over different time periods."""
        if not self._validation_attempts:
            return {}
        
        now = datetime.now()
        trends = {}
        
        # Last hour success rate
        hour_ago = now - timedelta(hours=1)
        recent_hour = [a for a in self._validation_attempts if a.timestamp >= hour_ago]
        if recent_hour:
            hour_successes = sum(1 for a in recent_hour if a.result.is_valid)
            trends['last_hour'] = (hour_successes / len(recent_hour)) * 100
        
        # Last day success rate
        day_ago = now - timedelta(days=1)
        recent_day = [a for a in self._validation_attempts if a.timestamp >= day_ago]
        if recent_day:
            day_successes = sum(1 for a in recent_day if a.result.is_valid)
            trends['last_day'] = (day_successes / len(recent_day)) * 100
        
        # Last week success rate
        week_ago = now - timedelta(weeks=1)
        recent_week = [a for a in self._validation_attempts if a.timestamp >= week_ago]
        if recent_week:
            week_successes = sum(1 for a in recent_week if a.result.is_valid)
            trends['last_week'] = (week_successes / len(recent_week)) * 100
        
        return trends
    
    def _get_common_user_errors(self) -> List[Dict[str, Any]]:
        """Get most common user errors with context."""
        error_details = defaultdict(lambda: {'count': 0, 'parameters': set(), 'sources': set()})
        
        for attempt in self._validation_attempts:
            if not attempt.result.is_valid:
                error_code = attempt.result.error_code
                error_details[error_code]['count'] += 1
                error_details[error_code]['parameters'].add(attempt.parameter_name)
                error_details[error_code]['sources'].add(attempt.source)
        
        # Convert to list and sort by frequency
        common_errors = []
        for error_code, details in error_details.items():
            common_errors.append({
                'error_code': error_code,
                'count': details['count'],
                'affected_parameters': list(details['parameters']),
                'sources': list(details['sources'])
            })
        
        return sorted(common_errors, key=lambda x: x['count'], reverse=True)[:10]
    
    def get_debug_information(self, parameter_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed debug information for troubleshooting validation issues.
        
        Args:
            parameter_name: Optional parameter name to focus debug info on
            
        Returns:
            Dictionary with debug information
        """
        with self._lock:
            debug_info = {
                'timestamp': datetime.now().isoformat(),
                'debug_mode': self._debug_mode,
                'debug_config': dict(self._debug_config),
                'system_status': {
                    'total_validation_attempts': len(self._validation_attempts),
                    'error_patterns_tracked': len(self._error_patterns),
                    'parameters_monitored': len(self._parameter_stats),
                    'analytics_data_points': sum(len(trends) for trends in self._validation_analytics['parameter_trends'].values())
                }
            }
            
            if parameter_name:
                # Focused debug info for specific parameter
                debug_info['parameter_focus'] = {
                    'parameter_name': parameter_name,
                    'validation_rules': self.validation_rules.get(parameter_name, {}),
                    'recent_attempts': [
                        {
                            'timestamp': a.timestamp.isoformat(),
                            'value': a.value,
                            'is_valid': a.result.is_valid,
                            'error_code': a.result.error_code,
                            'execution_time_ms': a.execution_time_ms,
                            'source': a.source
                        }
                        for a in self._validation_attempts
                        if a.parameter_name == parameter_name
                    ][-10:],  # Last 10 attempts
                    'error_patterns': {
                        pattern: count for pattern, count in self._error_patterns.items()
                        if pattern.startswith(f"{parameter_name}:")
                    },
                    'trends': self._validation_analytics['parameter_trends'].get(parameter_name, []),
                    'success_patterns': self._validation_analytics['validation_success_patterns'].get(parameter_name, [])
                }
            else:
                # General debug info
                debug_info['recent_errors'] = [
                    {
                        'timestamp': a.timestamp.isoformat(),
                        'parameter': a.parameter_name,
                        'error_code': a.result.error_code,
                        'error_message': a.result.error_message,
                        'source': a.source,
                        'execution_time_ms': a.execution_time_ms
                    }
                    for a in self._validation_attempts
                    if not a.result.is_valid
                ][-20:]  # Last 20 errors
                
                debug_info['performance_issues'] = self._get_performance_issues()
                debug_info['correlation_analysis'] = dict(self._validation_analytics['correlation_patterns'])
            
            return debug_info
    
    def log_analytics_summary(self) -> None:
        """Log a comprehensive analytics summary."""
        analytics = self.get_comprehensive_analytics()
        
        summary = {
            'total_attempts': analytics['basic_metrics']['total_attempts'],
            'success_rate': analytics['basic_metrics']['success_rate'],
            'avg_execution_time_ms': analytics['basic_metrics']['average_execution_time_ms'],
            'top_errors': list(analytics['error_analytics']['error_frequency'].items())[:5],
            'problematic_parameters': [
                param for param, rate in analytics['basic_metrics']['parameter_failure_rates'].items()
                if rate > 20.0
            ],
            'performance_issues_count': len(analytics['performance_analytics']['slow_validations']),
            'debug_mode': analytics['system_health']['debug_mode']
        }
        
        self.analytics_logger.info(f"ANALYTICS_SUMMARY: {json.dumps(summary)}")
    
    def enable_advanced_debugging(self, config: Optional[Dict[str, bool]] = None) -> None:
        """
        Enable advanced debugging with custom configuration.
        
        Args:
            config: Optional debug configuration overrides
        """
        self._debug_mode = True
        self.validation_logger.setLevel(logging.DEBUG)
        self.validation_logger.addHandler(self.debug_file_handler)
        
        if config:
            self._debug_config.update(config)
        
        debug_status = {
            'debug_mode': True,
            'config': dict(self._debug_config),
            'timestamp': datetime.now().isoformat()
        }
        
        self.validation_logger.info(f"ADVANCED_DEBUG_ENABLED: {json.dumps(debug_status)}")
    
    def get_validation_failure_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """
        Analyze validation failures over a specified time period.
        
        Args:
            hours: Number of hours to analyze (default: 24)
            
        Returns:
            Dictionary with failure analysis
        """
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_attempts = [a for a in self._validation_attempts if a.timestamp >= cutoff_time]
            failed_attempts = [a for a in recent_attempts if not a.result.is_valid]
            
            if not recent_attempts:
                return {'message': 'No validation attempts in the specified time period'}
            
            analysis = {
                'time_period_hours': hours,
                'total_attempts': len(recent_attempts),
                'failed_attempts': len(failed_attempts),
                'failure_rate': (len(failed_attempts) / len(recent_attempts)) * 100,
                'failure_breakdown': {
                    'by_parameter': defaultdict(int),
                    'by_error_code': defaultdict(int),
                    'by_source': defaultdict(int),
                    'by_hour': defaultdict(int)
                },
                'patterns': {
                    'consecutive_failures': [],
                    'parameter_correlations': defaultdict(list),
                    'time_correlations': defaultdict(list)
                },
                'recommendations': []
            }
            
            # Analyze failure breakdown
            for attempt in failed_attempts:
                analysis['failure_breakdown']['by_parameter'][attempt.parameter_name] += 1
                analysis['failure_breakdown']['by_error_code'][attempt.result.error_code] += 1
                analysis['failure_breakdown']['by_source'][attempt.source] += 1
                analysis['failure_breakdown']['by_hour'][attempt.timestamp.strftime('%H')] += 1
            
            # Find consecutive failures
            consecutive_count = 0
            for attempt in recent_attempts:
                if not attempt.result.is_valid:
                    consecutive_count += 1
                else:
                    if consecutive_count >= 3:  # 3 or more consecutive failures
                        analysis['patterns']['consecutive_failures'].append({
                            'count': consecutive_count,
                            'ended_at': attempt.timestamp.isoformat()
                        })
                    consecutive_count = 0
            
            # Generate recommendations
            if analysis['failure_rate'] > 30:
                analysis['recommendations'].append({
                    'type': 'high_failure_rate',
                    'message': f"High failure rate ({analysis['failure_rate']:.1f}%) detected. Review validation rules and user guidance.",
                    'priority': 'high'
                })
            
            # Check for parameter-specific issues
            for param, count in analysis['failure_breakdown']['by_parameter'].items():
                if count > len(failed_attempts) * 0.3:  # Parameter accounts for >30% of failures
                    analysis['recommendations'].append({
                        'type': 'parameter_issue',
                        'message': f"Parameter '{param}' has high failure rate. Consider reviewing validation rules or improving user guidance.",
                        'priority': 'medium',
                        'parameter': param
                    })
            
            return analysis
    
    def _init_performance_optimizations(self):
        """Initialize performance optimization components."""
        # Initialize compiled regex patterns cache
        self._compiled_patterns = {}
        self._pattern_performance = defaultdict(list)
        
        # Initialize validation result cache
        self._validation_cache = {}
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
        
        # Initialize async validation components
        self._async_validation_queue = asyncio.Queue() if self._perf_config.async_enabled else None
        self._async_results = {}
        
        # Initialize performance monitoring
        self._performance_monitor = {
            'slow_validations': deque(maxlen=100),
            'timeout_validations': deque(maxlen=50),
            'cache_performance': deque(maxlen=1000),
            'async_performance': deque(maxlen=1000)
        }
        
        # Pre-compile commonly used regex patterns
        self._precompile_regex_patterns()
        
        self.logger.info("Performance optimizations initialized")
    
    def _precompile_regex_patterns(self):
        """Pre-compile commonly used regex patterns for better performance."""
        patterns_to_compile = {
            'apn_domain': self.apn_domain_pattern,
            'apn_ip': self.apn_ip_pattern,
            'apn_url': self.apn_url_pattern,
            'apn_simple': self.apn_simple_pattern,
            'apn_credential': self.apn_credential_pattern,
            'ip_address': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
            'domain': r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$',
            'phone': r'^[\d\s\-\(\)\+]+$',
            'imei': r'^\d{15}$',
            'iccid': r'^\d{19,20}$',
            'imsi': r'^\d{15}$'
        }
        
        with self._pattern_lock:
            for pattern_name, pattern in patterns_to_compile.items():
                try:
                    start_time = time.time()
                    compiled_pattern = re.compile(pattern)
                    compile_time = (time.time() - start_time) * 1000
                    
                    self._compiled_patterns[pattern_name] = compiled_pattern
                    self._pattern_performance[pattern_name].append({
                        'compile_time_ms': compile_time,
                        'timestamp': datetime.now()
                    })
                    
                except re.error as e:
                    self.logger.warning(f"Failed to compile pattern '{pattern_name}': {e}")
    
    def _get_compiled_pattern(self, pattern_name: str) -> Optional[re.Pattern]:
        """Get a pre-compiled regex pattern."""
        with self._pattern_lock:
            return self._compiled_patterns.get(pattern_name)
    
    def _generate_cache_key(self, param_name: str, value: Any, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for validation results."""
        # Create a deterministic hash of the validation inputs
        cache_data = {
            'param': param_name,
            'value': str(value),
            'context': context or {}
        }
        
        # Sort context keys for consistent hashing
        if context:
            cache_data['context'] = {k: v for k, v in sorted(context.items())}
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_cached_validation_result(self, cache_key: str) -> Optional[ValidationResult]:
        """Get a cached validation result if available and not expired."""
        if not self._perf_config.cache_enabled:
            return None
        
        with self._cache_lock:
            cache_entry = self._validation_cache.get(cache_key)
            if not cache_entry:
                self._cache_stats['misses'] += 1
                self._performance_dashboard['cache_stats']['misses'] += 1
                return None
            
            # Check if cache entry is expired
            age_seconds = (datetime.now() - cache_entry.timestamp).total_seconds()
            if age_seconds > self._perf_config.cache_ttl_seconds:
                # Remove expired entry
                del self._validation_cache[cache_key]
                self._cache_stats['evictions'] += 1
                self._cache_stats['misses'] += 1
                self._performance_dashboard['cache_stats']['evictions'] += 1
                return None
            
            # Update access statistics
            cache_entry.access_count += 1
            cache_entry.last_accessed = datetime.now()
            
            self._cache_stats['hits'] += 1
            self._performance_dashboard['cache_stats']['hits'] += 1
            
            # Record cache performance
            self._performance_monitor['cache_performance'].append({
                'timestamp': datetime.now(),
                'cache_key': cache_key[:8],  # First 8 chars for debugging
                'age_seconds': age_seconds,
                'access_count': cache_entry.access_count
            })
            
            return cache_entry.result
    
    def _cache_validation_result(self, cache_key: str, result: ValidationResult) -> None:
        """Cache a validation result."""
        if not self._perf_config.cache_enabled:
            return
        
        with self._cache_lock:
            # Check cache size limit
            if len(self._validation_cache) >= self._perf_config.cache_max_size:
                # Remove oldest entries (LRU eviction)
                self._evict_old_cache_entries()
            
            # Store the result
            self._validation_cache[cache_key] = ValidationCacheEntry(
                result=result,
                timestamp=datetime.now(),
                access_count=1,
                last_accessed=datetime.now()
            )
            
            self._cache_stats['size'] = len(self._validation_cache)
    
    def _evict_old_cache_entries(self) -> None:
        """Evict old cache entries using LRU strategy."""
        if not self._validation_cache:
            return
        
        # Sort by last accessed time and remove oldest 25%
        entries_by_access = sorted(
            self._validation_cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        entries_to_remove = len(entries_by_access) // 4  # Remove 25%
        if entries_to_remove == 0:
            entries_to_remove = 1  # Remove at least one
        
        for i in range(entries_to_remove):
            cache_key, _ = entries_by_access[i]
            del self._validation_cache[cache_key]
            self._cache_stats['evictions'] += 1
            self._performance_dashboard['cache_stats']['evictions'] += 1
    
    async def validate_parameter_async(self, param_name: str, value: Any, 
                                     context: Optional[Dict[str, Any]] = None,
                                     source: str = 'async') -> ValidationResult:
        """
        Asynchronously validate a parameter value.
        
        Args:
            param_name: Name of the parameter to validate
            value: Value to validate
            context: Optional context with other parameter values
            source: Source of the validation request
            
        Returns:
            ValidationResult with validation status
        """
        if not self._perf_config.async_enabled:
            # Fall back to synchronous validation
            return self.validate_parameter(param_name, value, context, source)
        
        start_time = datetime.now()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(param_name, value, context)
            cached_result = self._get_cached_validation_result(cache_key)
            if cached_result:
                return cached_result
            
            # Run validation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                self.validate_parameter,
                param_name, value, context, source
            )
            
            # Cache the result
            self._cache_validation_result(cache_key, result)
            
            # Update async statistics
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self._metrics.async_validations += 1
            self._performance_dashboard['async_stats']['completed'] += 1
            
            self._performance_monitor['async_performance'].append({
                'timestamp': datetime.now(),
                'parameter': param_name,
                'execution_time_ms': execution_time,
                'cached': False
            })
            
            return result
            
        except asyncio.TimeoutError:
            self._metrics.timeout_validations += 1
            self._performance_dashboard['timeout_stats']['timeouts'] += 1
            
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation timeout for {param_name}",
                error_code='VALIDATION_TIMEOUT'
            )
        except Exception as e:
            self.logger.error(f"Async validation error for {param_name}: {e}")
            self._performance_dashboard['async_stats']['errors'] += 1
            
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}",
                error_code='VALIDATION_ERROR'
            )
    
    def validate_parameter_with_timeout(self, param_name: str, value: Any,
                                      context: Optional[Dict[str, Any]] = None,
                                      source: str = 'timeout',
                                      timeout_seconds: Optional[float] = None) -> ValidationResult:
        """
        Validate a parameter with a configurable timeout.
        
        Args:
            param_name: Name of the parameter to validate
            value: Value to validate
            context: Optional context with other parameter values
            source: Source of the validation request
            timeout_seconds: Timeout in seconds (uses config default if None)
            
        Returns:
            ValidationResult with validation status
        """
        timeout = timeout_seconds or self._perf_config.timeout_seconds
        start_time = datetime.now()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(param_name, value, context)
            cached_result = self._get_cached_validation_result(cache_key)
            if cached_result:
                return cached_result
            
            # Run validation with timeout
            future = self._executor.submit(
                self.validate_parameter,
                param_name, value, context, source
            )
            
            result = future.result(timeout=timeout)
            
            # Cache the result
            self._cache_validation_result(cache_key, result)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Monitor for slow validations
            if execution_time > self._performance_thresholds['slow_validation_ms']:
                self._performance_monitor['slow_validations'].append({
                    'timestamp': datetime.now(),
                    'parameter': param_name,
                    'execution_time_ms': execution_time,
                    'value_length': len(str(value)) if value else 0
                })
            
            return result
            
        except FutureTimeoutError:
            self._metrics.timeout_validations += 1
            self._performance_dashboard['timeout_stats']['timeouts'] += 1
            
            self._performance_monitor['timeout_validations'].append({
                'timestamp': datetime.now(),
                'parameter': param_name,
                'timeout_seconds': timeout,
                'value_length': len(str(value)) if value else 0
            })
            
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation timeout ({timeout}s) for {param_name}",
                error_code='VALIDATION_TIMEOUT'
            )
        except Exception as e:
            self.logger.error(f"Timeout validation error for {param_name}: {e}")
            
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}",
                error_code='VALIDATION_ERROR'
            )
    
    def validate_parameters_batch(self, parameters: Dict[str, Any],
                                context: Optional[Dict[str, Any]] = None,
                                source: str = 'batch') -> Dict[str, ValidationResult]:
        """
        Validate multiple parameters in batch with performance optimizations.
        
        Args:
            parameters: Dictionary of parameter names and values
            context: Optional context with additional parameter values
            source: Source of the validation request
            
        Returns:
            Dictionary of parameter names and their validation results
        """
        if not self._perf_config.batch_validation:
            # Fall back to individual validation
            return self.validate_parameter_group(parameters)
        
        start_time = datetime.now()
        results = {}
        cache_hits = 0
        
        # Merge parameters with context for comprehensive validation
        full_context = {**(context or {}), **parameters}
        
        # Check cache for all parameters first
        cached_results = {}
        uncached_params = {}
        
        for param_name, value in parameters.items():
            cache_key = self._generate_cache_key(param_name, value, full_context)
            cached_result = self._get_cached_validation_result(cache_key)
            
            if cached_result:
                cached_results[param_name] = cached_result
                cache_hits += 1
            else:
                uncached_params[param_name] = value
        
        # Validate uncached parameters
        if uncached_params:
            if len(uncached_params) > 1 and self._perf_config.async_enabled:
                # Use thread pool for parallel validation
                with ThreadPoolExecutor(max_workers=min(4, len(uncached_params))) as executor:
                    future_to_param = {
                        executor.submit(self.validate_parameter, param_name, value, full_context, source): param_name
                        for param_name, value in uncached_params.items()
                    }
                    
                    for future in future_to_param:
                        param_name = future_to_param[future]
                        try:
                            result = future.result(timeout=self._perf_config.timeout_seconds)
                            results[param_name] = result
                            
                            # Cache the result
                            cache_key = self._generate_cache_key(param_name, uncached_params[param_name], full_context)
                            self._cache_validation_result(cache_key, result)
                            
                        except FutureTimeoutError:
                            results[param_name] = ValidationResult(
                                is_valid=False,
                                error_message=f"Batch validation timeout for {param_name}",
                                error_code='BATCH_VALIDATION_TIMEOUT'
                            )
                        except Exception as e:
                            results[param_name] = ValidationResult(
                                is_valid=False,
                                error_message=f"Batch validation error: {str(e)}",
                                error_code='BATCH_VALIDATION_ERROR'
                            )
            else:
                # Sequential validation for small batches
                for param_name, value in uncached_params.items():
                    result = self.validate_parameter(param_name, value, full_context, source)
                    results[param_name] = result
                    
                    # Cache the result
                    cache_key = self._generate_cache_key(param_name, value, full_context)
                    self._cache_validation_result(cache_key, result)
        
        # Combine cached and new results
        results.update(cached_results)
        
        # Update performance metrics
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        batch_size = len(parameters)
        
        self._performance_dashboard['cache_stats']['batch_cache_hits'] += cache_hits
        self._performance_dashboard['async_stats']['batch_validations'] += 1
        
        self.logger.debug(f"Batch validation completed: {batch_size} parameters, "
                         f"{cache_hits} cache hits, {execution_time:.1f}ms")
        
        return results
    
    def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive performance dashboard data.
        
        Returns:
            Dictionary with performance metrics and monitoring data
        """
        with self._cache_lock:
            # Calculate cache hit rate
            total_cache_requests = self._cache_stats['hits'] + self._cache_stats['misses']
            cache_hit_rate = (self._cache_stats['hits'] / total_cache_requests * 100) if total_cache_requests > 0 else 0
            
            # Get recent performance data
            recent_slow_validations = list(self._performance_monitor['slow_validations'])[-20:]
            recent_timeouts = list(self._performance_monitor['timeout_validations'])[-10:]
            recent_cache_performance = list(self._performance_monitor['cache_performance'])[-50:]
            recent_async_performance = list(self._performance_monitor['async_performance'])[-50:]
            
            dashboard_data = {
                'timestamp': datetime.now().isoformat(),
                'cache_performance': {
                    'enabled': self._perf_config.cache_enabled,
                    'hit_rate_percent': cache_hit_rate,
                    'total_hits': self._cache_stats['hits'],
                    'total_misses': self._cache_stats['misses'],
                    'total_evictions': self._cache_stats['evictions'],
                    'current_size': self._cache_stats['size'],
                    'max_size': self._perf_config.cache_max_size,
                    'ttl_seconds': self._perf_config.cache_ttl_seconds,
                    'recent_performance': recent_cache_performance
                },
                'async_performance': {
                    'enabled': self._perf_config.async_enabled,
                    'total_async_validations': self._metrics.async_validations,
                    'threshold_ms': self._perf_config.async_threshold_ms,
                    'recent_performance': recent_async_performance,
                    'queue_size': self._async_validation_queue.qsize() if self._async_validation_queue else 0
                },
                'timeout_performance': {
                    'timeout_seconds': self._perf_config.timeout_seconds,
                    'total_timeouts': self._metrics.timeout_validations,
                    'recent_timeouts': recent_timeouts
                },
                'regex_performance': {
                    'optimization_enabled': self._perf_config.regex_optimization,
                    'compiled_patterns_count': len(self._compiled_patterns),
                    'pattern_performance': dict(self._pattern_performance)
                },
                'slow_validation_monitoring': {
                    'threshold_ms': self._performance_thresholds['slow_validation_ms'],
                    'very_slow_threshold_ms': self._performance_thresholds['very_slow_validation_ms'],
                    'recent_slow_validations': recent_slow_validations,
                    'slow_validation_count': len(self._performance_monitor['slow_validations'])
                },
                'batch_performance': {
                    'enabled': self._perf_config.batch_validation,
                    'stats': dict(self._performance_dashboard['async_stats'])
                },
                'overall_metrics': {
                    'total_validations': self._metrics.total_attempts,
                    'success_rate': self._metrics.success_rate,
                    'average_execution_time_ms': self._metrics.average_execution_time_ms,
                    'cache_hit_rate': cache_hit_rate
                }
            }
            
            return dashboard_data
    
    def optimize_regex_patterns(self) -> Dict[str, Any]:
        """
        Optimize regex patterns based on usage patterns and performance data.
        
        Returns:
            Dictionary with optimization results
        """
        if not self._perf_config.regex_optimization:
            return {'message': 'Regex optimization is disabled'}
        
        optimization_results = {
            'timestamp': datetime.now().isoformat(),
            'patterns_analyzed': 0,
            'patterns_optimized': 0,
            'performance_improvements': {},
            'recommendations': []
        }
        
        with self._pattern_lock:
            for pattern_name, performance_data in self._pattern_performance.items():
                optimization_results['patterns_analyzed'] += 1
                
                if not performance_data:
                    continue
                
                # Analyze pattern performance
                compile_times = [p['compile_time_ms'] for p in performance_data]
                avg_compile_time = sum(compile_times) / len(compile_times)
                
                # Check if pattern needs optimization
                if avg_compile_time > 10:  # More than 10ms average compile time
                    optimization_results['recommendations'].append({
                        'pattern': pattern_name,
                        'issue': 'slow_compilation',
                        'avg_compile_time_ms': avg_compile_time,
                        'suggestion': 'Consider simplifying the regex pattern or using alternative validation methods'
                    })
                
                # Record performance data
                optimization_results['performance_improvements'][pattern_name] = {
                    'compile_time_ms': avg_compile_time,
                    'usage_count': len(performance_data),
                    'last_used': performance_data[-1]['timestamp'].isoformat() if performance_data else None
                }
        
        return optimization_results
    
    def clear_performance_cache(self) -> Dict[str, int]:
        """
        Clear the performance cache and return statistics.
        
        Returns:
            Dictionary with cache clearing statistics
        """
        with self._cache_lock:
            stats_before = {
                'cache_size': len(self._validation_cache),
                'cache_hits': self._cache_stats['hits'],
                'cache_misses': self._cache_stats['misses'],
                'cache_evictions': self._cache_stats['evictions']
            }
            
            # Clear cache
            self._validation_cache.clear()
            
            # Reset cache statistics
            self._cache_stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'size': 0
            }
            
            # Clear performance monitoring data
            self._performance_monitor['cache_performance'].clear()
            
            self.logger.info("Performance cache cleared")
            
            return {
                'cleared_entries': stats_before['cache_size'],
                'previous_hits': stats_before['cache_hits'],
                'previous_misses': stats_before['cache_misses'],
                'previous_evictions': stats_before['cache_evictions']
            }
    
    def configure_performance_settings(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update performance configuration settings.
        
        Args:
            config: Dictionary with performance configuration updates
            
        Returns:
            Dictionary with updated configuration
        """
        old_config = asdict(self._perf_config)
        
        # Update configuration
        for key, value in config.items():
            if hasattr(self._perf_config, key):
                setattr(self._perf_config, key, value)
            else:
                self.logger.warning(f"Unknown performance config key: {key}")
        
        # Apply configuration changes
        if 'cache_enabled' in config and not config['cache_enabled']:
            self.clear_performance_cache()
        
        if 'regex_optimization' in config and config['regex_optimization']:
            self._precompile_regex_patterns()
        
        new_config = asdict(self._perf_config)
        
        self.logger.info(f"Performance configuration updated: {config}")
        
        return {
            'old_config': old_config,
            'new_config': new_config,
            'changes_applied': list(config.keys())
        }    
  
  # Security-specific methods
    def create_validation_bypass_token(self, security_context: SecurityContext, 
                                     operation: str, duration_minutes: int = 60) -> Optional[str]:
        """
        Create secure validation bypass token with proper authorization
        
        Args:
            security_context: Security context requesting the bypass
            operation: Operation that needs bypass
            duration_minutes: How long the bypass token is valid
            
        Returns:
            Bypass token string or None if not authorized
        """
        if not self._security_enabled:
            return None
        
        return self.security_service.create_bypass_token(security_context, operation, duration_minutes)
    
    def validate_with_bypass(self, param_name: str, value: Any, bypass_token: str,
                           context: Optional[Dict[str, Any]] = None, 
                           source: str = 'bypass', 
                           security_context: Optional[SecurityContext] = None) -> ValidationResult:
        """
        Validate parameter with bypass token for emergency/admin use
        
        Args:
            param_name: Name of the parameter to validate
            value: Value to validate
            bypass_token: Bypass token for validation override
            context: Optional context with other parameter values
            source: Source of the validation request
            security_context: Security context for audit logging
            
        Returns:
            ValidationResult with validation status
        """
        if not self._security_enabled:
            return self.validate_parameter(param_name, value, context, source)
        
        if security_context is None:
            security_context = SecurityContext(
                user_id="bypass_user",
                session_id="bypass",
                ip_address="127.0.0.1",
                user_agent="BypassValidation",
                timestamp=datetime.now(),
                security_level=SecurityLevel.CRITICAL,
                permissions=["validation_bypass"]
            )
        
        # Validate bypass token
        token_valid, token_error = self.security_service.validate_bypass_token(
            bypass_token, f"validate_{param_name}", security_context
        )
        
        if not token_valid:
            return ValidationResult(
                is_valid=False,
                error_message=f"Bypass validation failed: {token_error}",
                error_code='BYPASS_INVALID'
            )
        
        # Perform validation with bypass (skip some security checks)
        original_security_enabled = self._security_enabled
        try:
            # Temporarily disable some security checks for bypass
            self._security_enabled = False
            result = self.validate_parameter(param_name, value, context, source, security_context)
            
            # Log bypass usage
            self.security_service.audit_log(
                AuditAction.VALIDATION_BYPASS,
                security_context,
                "parameter_validation",
                param_name,
                {
                    "bypass_used": True,
                    "original_validation_result": result.is_valid,
                    "bypass_reason": "admin_override"
                },
                True,
                f"Validation bypass used for parameter {param_name}"
            )
            
            return result
            
        finally:
            self._security_enabled = original_security_enabled
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """
        Get security metrics for monitoring
        
        Returns:
            Dictionary with security metrics
        """
        if not self._security_enabled:
            return {"security_enabled": False}
        
        security_metrics = self.security_service.get_security_metrics()
        validation_metrics = self.get_validation_metrics()
        
        return {
            "security_enabled": True,
            "security_metrics": security_metrics,
            "validation_metrics": {
                "total_attempts": validation_metrics.total_attempts,
                "success_rate": validation_metrics.success_rate,
                "cache_hit_rate": validation_metrics.cache_hit_rate
            },
            "integration_status": "active"
        }
    
    def enable_security(self, enable: bool = True):
        """
        Enable or disable security features
        
        Args:
            enable: Whether to enable security features
        """
        self._security_enabled = enable
        self.logger.info(f"Security features {'enabled' if enable else 'disabled'}")
    
    def sanitize_input_for_logging(self, param_name: str, value: Any) -> str:
        """
        Sanitize input value for safe logging
        
        Args:
            param_name: Parameter name
            value: Parameter value
            
        Returns:
            Sanitized string safe for logging
        """
        if not self._security_enabled:
            return str(value)[:100]  # Simple truncation
        
        # Use security service for proper sanitization
        if isinstance(value, str):
            field_type = 'password' if 'password' in param_name.lower() else 'apn'
            sanitized, _ = self.security_service.sanitize_apn_input(value, field_type)
            
            # Further mask sensitive data for logging
            if 'password' in param_name.lower():
                return "***" if sanitized else ""
            elif len(sanitized) > 50:
                return sanitized[:47] + "..."
            else:
                return sanitized
        
        return str(value)[:100]