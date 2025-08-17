"""
APN Security Service

This service provides comprehensive security enhancements for APN validation including:
- Input sanitization to prevent injection attacks through APN fields
- Audit logging for all APN configuration access and modifications
- Validation integrity checks to prevent tampering with validation rules
- Rate limiting for validation attempts to prevent abuse
- Secure validation bypass controls with proper authorization
"""

import re
import time
import hashlib
import hmac
import logging
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from functools import wraps
from enum import Enum


class SecurityLevel(Enum):
    """Security levels for different operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditAction(Enum):
    """Types of actions that can be audited"""
    VALIDATION_ATTEMPT = "validation_attempt"
    CONFIGURATION_ACCESS = "configuration_access"
    CONFIGURATION_CREATE = "configuration_create"
    CONFIGURATION_UPDATE = "configuration_update"
    CONFIGURATION_DELETE = "configuration_delete"
    VALIDATION_BYPASS = "validation_bypass"
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


@dataclass
class SecurityContext:
    """Security context for operations"""
    user_id: str
    session_id: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    security_level: SecurityLevel
    permissions: List[str]


@dataclass
class AuditLogEntry:
    """Audit log entry for security events"""
    timestamp: datetime
    action: AuditAction
    user_id: str
    session_id: str
    ip_address: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    security_level: SecurityLevel
    success: bool
    error_message: str = ""


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    max_attempts: int
    time_window_seconds: int
    lockout_duration_seconds: int
    progressive_delay: bool = True


@dataclass
class ValidationIntegrityCheck:
    """Integrity check for validation rules"""
    rule_name: str
    rule_hash: str
    last_verified: datetime
    verification_count: int
    tamper_detected: bool = False


class APNSecurityService:
    """Comprehensive security service for APN validation and configuration"""
    
    def __init__(self, config_file: str = "apn_security_config.json"):
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file
        
        # Security configuration
        self.security_config = self._load_security_config()
        
        # Rate limiting storage
        self._rate_limits: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._rate_limit_lock = threading.RLock()
        
        # Audit logging
        self._audit_log: deque = deque(maxlen=10000)  # Keep last 10k entries in memory
        self._audit_lock = threading.Lock()
        
        # Validation integrity
        self._validation_rules_hash: Dict[str, str] = {}
        self._integrity_checks: Dict[str, ValidationIntegrityCheck] = {}
        self._integrity_lock = threading.Lock()
        
        # Security bypass controls
        self._bypass_tokens: Dict[str, Dict[str, Any]] = {}
        self._bypass_lock = threading.Lock()
        
        # Input sanitization patterns
        self._init_sanitization_patterns()
        
        # Initialize security components
        self._init_rate_limiting()
        self._init_audit_logging()
        self._init_integrity_checks()
    
    def sanitize_apn_input(self, input_value: str, field_type: str = "apn") -> Tuple[str, List[str]]:
        """
        Comprehensive input sanitization to prevent injection attacks
        
        Args:
            input_value: Raw input value to sanitize
            field_type: Type of field (apn, username, password, etc.)
            
        Returns:
            Tuple of (sanitized_value, list_of_issues_found)
        """
        if not input_value:
            return "", []
        
        issues_found = []
        sanitized = input_value
        
        # Remove null bytes and control characters
        if '\x00' in sanitized:
            sanitized = sanitized.replace('\x00', '')
            issues_found.append("Removed null bytes")
        
        # Remove other control characters except allowed ones
        control_chars = ''.join(chr(i) for i in range(32) if i not in [9, 10, 13])  # Keep tab, LF, CR
        for char in control_chars:
            if char in sanitized:
                sanitized = sanitized.replace(char, '')
                issues_found.append(f"Removed control character: {repr(char)}")
        
        # Field-specific sanitization
        if field_type == "apn":
            sanitized, apn_issues = self._sanitize_apn_field(sanitized)
            issues_found.extend(apn_issues)
        elif field_type in ["username", "password"]:
            sanitized, cred_issues = self._sanitize_credential_field(sanitized)
            issues_found.extend(cred_issues)
        
        # Check for potential injection patterns
        injection_issues = self._detect_injection_patterns(sanitized)
        issues_found.extend(injection_issues)
        
        # Length validation
        max_lengths = {
            "apn": 253,
            "username": 64,
            "password": 64
        }
        
        max_length = max_lengths.get(field_type, 255)
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            issues_found.append(f"Truncated to {max_length} characters")
        
        return sanitized, issues_found
    
    def audit_log(self, action: AuditAction, security_context: SecurityContext, 
                  resource_type: str, resource_id: str, details: Dict[str, Any], 
                  success: bool, error_message: str = "") -> None:
        """
        Add entry to audit log for security monitoring
        
        Args:
            action: Type of action being audited
            security_context: Security context of the operation
            resource_type: Type of resource being accessed
            resource_id: ID of the resource
            details: Additional details about the operation
            success: Whether the operation was successful
            error_message: Error message if operation failed
        """
        # Sanitize sensitive data in details
        sanitized_details = self._sanitize_audit_details(details)
        
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            action=action,
            user_id=security_context.user_id,
            session_id=security_context.session_id,
            ip_address=security_context.ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            details=sanitized_details,
            security_level=security_context.security_level,
            success=success,
            error_message=error_message
        )
        
        with self._audit_lock:
            self._audit_log.append(entry)
        
        # Log to file for persistence
        self._write_audit_log_entry(entry)
        
        # Check for security violations
        self._analyze_security_patterns(entry)
    
    def check_rate_limit(self, identifier: str, operation: str, 
                        security_context: SecurityContext) -> Tuple[bool, Optional[str]]:
        """
        Check if operation is within rate limits
        
        Args:
            identifier: Unique identifier for rate limiting (IP, user, etc.)
            operation: Type of operation being rate limited
            security_context: Security context of the operation
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        config = self.security_config.get("rate_limits", {}).get(operation)
        if not config:
            return True, None  # No rate limit configured
        
        rate_config = RateLimitConfig(**config)
        current_time = time.time()
        
        with self._rate_limit_lock:
            # Get or create rate limit data for this identifier
            if identifier not in self._rate_limits:
                self._rate_limits[identifier] = {}
            
            if operation not in self._rate_limits[identifier]:
                self._rate_limits[identifier][operation] = {
                    "attempts": [],
                    "locked_until": 0,
                    "consecutive_violations": 0
                }
            
            rate_data = self._rate_limits[identifier][operation]
            
            # Check if currently locked out
            if current_time < rate_data["locked_until"]:
                remaining_lockout = int(rate_data["locked_until"] - current_time)
                self.audit_log(
                    AuditAction.RATE_LIMIT_EXCEEDED,
                    security_context,
                    "rate_limit",
                    f"{identifier}:{operation}",
                    {"remaining_lockout_seconds": remaining_lockout},
                    False,
                    f"Rate limit lockout active for {remaining_lockout} seconds"
                )
                return False, f"Rate limit exceeded. Try again in {remaining_lockout} seconds."
            
            # Clean old attempts outside the time window
            cutoff_time = current_time - rate_config.time_window_seconds
            rate_data["attempts"] = [t for t in rate_data["attempts"] if t > cutoff_time]
            
            # Check if within rate limit
            if len(rate_data["attempts"]) >= rate_config.max_attempts:
                # Rate limit exceeded
                rate_data["consecutive_violations"] += 1
                
                # Calculate lockout duration (progressive if enabled)
                lockout_duration = rate_config.lockout_duration_seconds
                if rate_config.progressive_delay:
                    lockout_duration *= (2 ** min(rate_data["consecutive_violations"] - 1, 5))  # Max 32x
                
                rate_data["locked_until"] = current_time + lockout_duration
                
                self.audit_log(
                    AuditAction.RATE_LIMIT_EXCEEDED,
                    security_context,
                    "rate_limit",
                    f"{identifier}:{operation}",
                    {
                        "attempts_in_window": len(rate_data["attempts"]),
                        "max_attempts": rate_config.max_attempts,
                        "lockout_duration": lockout_duration,
                        "consecutive_violations": rate_data["consecutive_violations"]
                    },
                    False,
                    f"Rate limit exceeded: {len(rate_data['attempts'])} attempts in {rate_config.time_window_seconds} seconds"
                )
                
                return False, f"Rate limit exceeded. Locked out for {lockout_duration} seconds."
            
            # Within rate limit, record this attempt
            rate_data["attempts"].append(current_time)
            rate_data["consecutive_violations"] = 0  # Reset on successful check
            
            return True, None
    
    def verify_validation_integrity(self, validation_rules: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Verify integrity of validation rules to prevent tampering
        
        Args:
            validation_rules: Current validation rules to verify
            
        Returns:
            Tuple of (integrity_ok, list_of_issues)
        """
        issues = []
        
        with self._integrity_lock:
            for rule_name, rule_data in validation_rules.items():
                # Calculate current hash of the rule
                rule_json = json.dumps(rule_data, sort_keys=True)
                current_hash = hashlib.sha256(rule_json.encode()).hexdigest()
                
                # Check if we have a stored hash for this rule
                if rule_name in self._validation_rules_hash:
                    stored_hash = self._validation_rules_hash[rule_name]
                    if current_hash != stored_hash:
                        issues.append(f"Validation rule '{rule_name}' has been modified")
                        
                        # Update integrity check record
                        if rule_name in self._integrity_checks:
                            self._integrity_checks[rule_name].tamper_detected = True
                        else:
                            self._integrity_checks[rule_name] = ValidationIntegrityCheck(
                                rule_name=rule_name,
                                rule_hash=current_hash,
                                last_verified=datetime.now(),
                                verification_count=1,
                                tamper_detected=True
                            )
                
                # Update stored hash and verification record
                self._validation_rules_hash[rule_name] = current_hash
                
                if rule_name in self._integrity_checks:
                    check = self._integrity_checks[rule_name]
                    check.rule_hash = current_hash
                    check.last_verified = datetime.now()
                    check.verification_count += 1
                else:
                    self._integrity_checks[rule_name] = ValidationIntegrityCheck(
                        rule_name=rule_name,
                        rule_hash=current_hash,
                        last_verified=datetime.now(),
                        verification_count=1
                    )
        
        return len(issues) == 0, issues
    
    def create_bypass_token(self, security_context: SecurityContext, 
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
        # Check if user has bypass permissions
        if "validation_bypass" not in security_context.permissions:
            self.audit_log(
                AuditAction.SECURITY_VIOLATION,
                security_context,
                "bypass_token",
                operation,
                {"reason": "insufficient_permissions"},
                False,
                "User does not have validation bypass permissions"
            )
            return None
        
        # Check security level requirements
        required_level = self.security_config.get("bypass_requirements", {}).get("min_security_level", "high")
        if security_context.security_level.value != required_level and security_context.security_level != SecurityLevel.CRITICAL:
            self.audit_log(
                AuditAction.SECURITY_VIOLATION,
                security_context,
                "bypass_token",
                operation,
                {"reason": "insufficient_security_level", "required": required_level, "provided": security_context.security_level.value},
                False,
                f"Security level {security_context.security_level.value} insufficient for bypass (requires {required_level})"
            )
            return None
        
        # Generate secure token
        token_data = {
            "user_id": security_context.user_id,
            "session_id": security_context.session_id,
            "operation": operation,
            "created": datetime.now().isoformat(),
            "expires": (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()
        }
        
        token_json = json.dumps(token_data, sort_keys=True)
        token_hash = hmac.new(
            self.security_config.get("bypass_secret", "default_secret").encode(),
            token_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{token_hash}:{token_json}"
        
        with self._bypass_lock:
            self._bypass_tokens[token_hash] = {
                "token_data": token_data,
                "created_by": security_context.user_id,
                "used_count": 0,
                "max_uses": self.security_config.get("bypass_requirements", {}).get("max_uses", 10)
            }
        
        self.audit_log(
            AuditAction.VALIDATION_BYPASS,
            security_context,
            "bypass_token",
            operation,
            {"token_hash": token_hash[:8], "duration_minutes": duration_minutes},
            True,
            "Bypass token created"
        )
        
        return token
    
    def validate_bypass_token(self, token: str, operation: str, 
                             security_context: SecurityContext) -> Tuple[bool, str]:
        """
        Validate bypass token for secure validation bypass
        
        Args:
            token: Bypass token to validate
            operation: Operation requesting bypass
            security_context: Current security context
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not token:
            return False, "No bypass token provided"
        
        try:
            # Parse token
            if ':' not in token:
                return False, "Invalid token format"
            
            token_hash, token_json = token.split(':', 1)
            token_data = json.loads(token_json)
            
            # Verify token signature
            expected_hash = hmac.new(
                self.security_config.get("bypass_secret", "default_secret").encode(),
                token_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(token_hash, expected_hash):
                self.audit_log(
                    AuditAction.SECURITY_VIOLATION,
                    security_context,
                    "bypass_token",
                    operation,
                    {"reason": "invalid_signature", "token_hash": token_hash[:8]},
                    False,
                    "Invalid bypass token signature"
                )
                return False, "Invalid token signature"
            
            # Check if token exists in our records
            with self._bypass_lock:
                if token_hash not in self._bypass_tokens:
                    return False, "Token not found or expired"
                
                stored_token = self._bypass_tokens[token_hash]
                
                # Check expiration
                expires = datetime.fromisoformat(token_data["expires"])
                if datetime.now() > expires:
                    del self._bypass_tokens[token_hash]
                    return False, "Token has expired"
                
                # Check operation match
                if token_data["operation"] != operation:
                    return False, f"Token is for operation '{token_data['operation']}', not '{operation}'"
                
                # Check usage limits
                if stored_token["used_count"] >= stored_token["max_uses"]:
                    return False, "Token usage limit exceeded"
                
                # Check user match (optional, for additional security)
                if self.security_config.get("bypass_requirements", {}).get("strict_user_match", True):
                    if token_data["user_id"] != security_context.user_id:
                        return False, "Token user mismatch"
                
                # Token is valid, increment usage
                stored_token["used_count"] += 1
                
                self.audit_log(
                    AuditAction.VALIDATION_BYPASS,
                    security_context,
                    "bypass_token",
                    operation,
                    {
                        "token_hash": token_hash[:8],
                        "used_count": stored_token["used_count"],
                        "max_uses": stored_token["max_uses"]
                    },
                    True,
                    "Bypass token validated and used"
                )
                
                return True, "Token validated successfully"
        
        except Exception as e:
            self.audit_log(
                AuditAction.SECURITY_VIOLATION,
                security_context,
                "bypass_token",
                operation,
                {"reason": "token_validation_error", "error": str(e)},
                False,
                f"Error validating bypass token: {e}"
            )
            return False, f"Token validation error: {e}"
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """
        Get security metrics for monitoring
        
        Returns:
            Dictionary with security metrics
        """
        with self._audit_lock:
            recent_entries = [entry for entry in self._audit_log 
                            if entry.timestamp > datetime.now() - timedelta(hours=24)]
        
        metrics = {
            "audit_log": {
                "total_entries": len(self._audit_log),
                "recent_24h": len(recent_entries),
                "security_violations_24h": len([e for e in recent_entries 
                                              if e.action == AuditAction.SECURITY_VIOLATION]),
                "failed_operations_24h": len([e for e in recent_entries if not e.success])
            },
            "rate_limiting": {
                "active_limits": len(self._rate_limits),
                "locked_identifiers": len([data for data in self._rate_limits.values() 
                                         for op_data in data.values() 
                                         if op_data.get("locked_until", 0) > time.time()])
            },
            "validation_integrity": {
                "rules_monitored": len(self._integrity_checks),
                "tamper_detected": len([check for check in self._integrity_checks.values() 
                                      if check.tamper_detected])
            },
            "bypass_tokens": {
                "active_tokens": len(self._bypass_tokens),
                "total_uses": sum(token["used_count"] for token in self._bypass_tokens.values())
            }
        }
        
        return metrics 
   
    def _load_security_config(self) -> Dict[str, Any]:
        """Load security configuration from file"""
        default_config = {
            "rate_limits": {
                "validation": {
                    "max_attempts": 100,
                    "time_window_seconds": 300,  # 5 minutes
                    "lockout_duration_seconds": 900,  # 15 minutes
                    "progressive_delay": True
                },
                "configuration_access": {
                    "max_attempts": 50,
                    "time_window_seconds": 300,
                    "lockout_duration_seconds": 600,
                    "progressive_delay": True
                },
                "bypass_request": {
                    "max_attempts": 5,
                    "time_window_seconds": 3600,  # 1 hour
                    "lockout_duration_seconds": 3600,
                    "progressive_delay": True
                }
            },
            "bypass_requirements": {
                "min_security_level": "high",
                "max_uses": 10,
                "strict_user_match": True
            },
            "bypass_secret": "lt32pro_bypass_secret_2024_change_in_production",
            "audit_log_file": "apn_security_audit.log",
            "sanitization": {
                "max_field_length": 255,
                "allow_unicode": True,
                "strict_mode": False
            }
        }
        
        try:
            import os
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    for key, value in loaded_config.items():
                        if isinstance(value, dict) and key in default_config:
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
        except Exception as e:
            self.logger.warning(f"Could not load security config from {self.config_file}: {e}")
        
        return default_config
    
    def _init_sanitization_patterns(self):
        """Initialize patterns for input sanitization"""
        # SQL injection patterns
        self.sql_injection_patterns = [
            re.compile(r"('|(\\')|(;)|(\\;))", re.IGNORECASE),
            re.compile(r"((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))", re.IGNORECASE),
            re.compile(r"union.*select", re.IGNORECASE),
            re.compile(r"insert.*into", re.IGNORECASE),
            re.compile(r"delete.*from", re.IGNORECASE),
            re.compile(r"drop.*table", re.IGNORECASE),
            re.compile(r"update.*set", re.IGNORECASE)
        ]
        
        # Command injection patterns
        self.command_injection_patterns = [
            re.compile(r"[;&|`$(){}[\]<>]"),
            re.compile(r"(\\x[0-9a-fA-F]{2})+"),  # Hex encoded
            re.compile(r"(%[0-9a-fA-F]{2})+"),    # URL encoded
        ]
        
        # Script injection patterns
        self.script_injection_patterns = [
            re.compile(r"<script", re.IGNORECASE),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"vbscript:", re.IGNORECASE),
            re.compile(r"onload=", re.IGNORECASE),
            re.compile(r"onerror=", re.IGNORECASE)
        ]
        
        # LDAP injection patterns
        self.ldap_injection_patterns = [
            re.compile(r"[()=*!&|]"),
            re.compile(r"\\[0-9a-fA-F]{2}")
        ]
    
    def _sanitize_apn_field(self, value: str) -> Tuple[str, List[str]]:
        """Sanitize APN field specifically"""
        issues = []
        sanitized = value.strip()
        
        # Remove dangerous characters for APN
        dangerous_chars = ['<', '>', '"', "'", '\\', '\n', '\r', '\t']
        for char in dangerous_chars:
            if char in sanitized:
                sanitized = sanitized.replace(char, '')
                issues.append(f"Removed dangerous character: {char}")
        
        # Normalize consecutive dots (the main security issue)
        if '..' in sanitized:
            sanitized = re.sub(r'\.{2,}', '.', sanitized)
            issues.append("Normalized consecutive dots")
        
        # Check for malformed patterns like .t.t.t
        if re.search(r'\.([a-zA-Z])\.\1\.', sanitized):
            # Remove repeated single character patterns
            sanitized = re.sub(r'\.([a-zA-Z])\.\1\..*$', '', sanitized)
            issues.append("Removed malformed domain pattern")
        
        # Remove leading/trailing dots
        original_length = len(sanitized)
        sanitized = sanitized.strip('.')
        if len(sanitized) != original_length:
            issues.append("Removed leading/trailing dots")
        
        return sanitized, issues
    
    def _sanitize_credential_field(self, value: str) -> Tuple[str, List[str]]:
        """Sanitize username/password fields"""
        issues = []
        sanitized = value.strip()
        
        # Remove null bytes and control characters
        control_chars = ''.join(chr(i) for i in range(32) if i not in [9])  # Keep tab
        for char in control_chars:
            if char in sanitized:
                sanitized = sanitized.replace(char, '')
                issues.append(f"Removed control character from credential")
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', '\\', '\n', '\r']
        for char in dangerous_chars:
            if char in sanitized:
                sanitized = sanitized.replace(char, '')
                issues.append(f"Removed dangerous character from credential: {char}")
        
        return sanitized, issues
    
    def _detect_injection_patterns(self, value: str) -> List[str]:
        """Detect potential injection attack patterns"""
        issues = []
        
        # Check SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if pattern.search(value):
                issues.append("Potential SQL injection pattern detected")
                break
        
        # Check command injection patterns
        for pattern in self.command_injection_patterns:
            if pattern.search(value):
                issues.append("Potential command injection pattern detected")
                break
        
        # Check script injection patterns
        for pattern in self.script_injection_patterns:
            if pattern.search(value):
                issues.append("Potential script injection pattern detected")
                break
        
        # Check LDAP injection patterns (less common but possible)
        ldap_matches = sum(1 for pattern in self.ldap_injection_patterns if pattern.search(value))
        if ldap_matches > 1:  # Multiple LDAP special chars might indicate injection
            issues.append("Potential LDAP injection pattern detected")
        
        return issues
    
    def _sanitize_audit_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data in audit log details"""
        sanitized = {}
        
        sensitive_keys = ['password', 'token', 'secret', 'key', 'credential']
        
        for key, value in details.items():
            key_lower = key.lower()
            
            # Mask sensitive values
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                if isinstance(value, str) and value:
                    sanitized[key] = f"***{value[-2:]}" if len(value) > 2 else "***"
                else:
                    sanitized[key] = "***"
            else:
                # Recursively sanitize nested dictionaries
                if isinstance(value, dict):
                    sanitized[key] = self._sanitize_audit_details(value)
                elif isinstance(value, str):
                    # Limit string length in audit logs
                    sanitized[key] = value[:500] + "..." if len(value) > 500 else value
                else:
                    sanitized[key] = value
        
        return sanitized
    
    def _write_audit_log_entry(self, entry: AuditLogEntry):
        """Write audit log entry to persistent storage"""
        try:
            log_file = self.security_config.get("audit_log_file", "apn_security_audit.log")
            
            log_data = {
                "timestamp": entry.timestamp.isoformat(),
                "action": entry.action.value,
                "user_id": entry.user_id,
                "session_id": entry.session_id,
                "ip_address": entry.ip_address,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "details": entry.details,
                "security_level": entry.security_level.value,
                "success": entry.success,
                "error_message": entry.error_message
            }
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to write audit log entry: {e}")
    
    def _analyze_security_patterns(self, entry: AuditLogEntry):
        """Analyze audit log entries for security patterns"""
        # This could be expanded to detect patterns like:
        # - Multiple failed attempts from same IP
        # - Unusual access patterns
        # - Potential brute force attacks
        # - Suspicious validation bypass attempts
        
        if not entry.success and entry.action in [AuditAction.VALIDATION_ATTEMPT, AuditAction.CONFIGURATION_ACCESS]:
            # Log security concern for failed operations
            self.logger.warning(f"Security concern: Failed {entry.action.value} from {entry.ip_address} for user {entry.user_id}")
    
    def _init_rate_limiting(self):
        """Initialize rate limiting system"""
        self.logger.info("Rate limiting system initialized")
    
    def _init_audit_logging(self):
        """Initialize audit logging system"""
        self.logger.info("Audit logging system initialized")
        
        # Create audit log file if it doesn't exist
        try:
            import os
            log_file = self.security_config.get("audit_log_file", "apn_security_audit.log")
            if not os.path.exists(log_file):
                with open(log_file, 'w') as f:
                    f.write("")  # Create empty file
        except Exception as e:
            self.logger.warning(f"Could not initialize audit log file: {e}")
    
    def _init_integrity_checks(self):
        """Initialize validation integrity checking"""
        self.logger.info("Validation integrity checking initialized")


# Decorator for securing validation operations
def secure_validation(operation_name: str):
    """
    Decorator to add security checks to validation operations
    
    Args:
        operation_name: Name of the operation for rate limiting and auditing
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # This would be used to wrap validation methods with security checks
            # For now, just call the original function
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


# Context manager for security operations
class SecurityContextManager:
    """Context manager for security-aware operations"""
    
    def __init__(self, security_service: APNSecurityService, 
                 security_context: SecurityContext, operation: str):
        self.security_service = security_service
        self.security_context = security_context
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        error_message = str(exc_val) if exc_val else ""
        
        self.security_service.audit_log(
            AuditAction.VALIDATION_ATTEMPT,
            self.security_context,
            "validation",
            self.operation,
            {"duration_ms": (datetime.now() - self.start_time).total_seconds() * 1000},
            success,
            error_message
        )