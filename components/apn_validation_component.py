"""
APN Validation Component

This component provides dedicated APN validation logic including:
- Domain format validation to catch malformed domains
- IP address validation for APN configurations  
- Carrier-specific validation rules for common providers
- Suggestion system for correcting invalid APN formats
"""

import re
import ipaddress
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of APN validation with details and suggestions"""
    is_valid: bool
    error_message: str
    error_code: str
    suggestions: List[str]
    field_name: str
    validated_value: str


class APNValidationComponent:
    """Dedicated component for APN-specific validation logic"""
    
    def __init__(self):
        # Common carrier APN patterns for validation and suggestions
        self.carrier_apns = {
            # Brazil carriers
            'vivo': ['zap.vivo.com.br', 'vivo.br', 'vivo'],
            'tim': ['tim.br', 'tim.com.br', 'timbrasil.br'],
            'claro': ['claro.com.br', 'claro.br', 'bandalarga.claro.com.br'],
            'oi': ['gprs.oi.com.br', 'oi.com.br'],
            'allcom': ['allcom.br'],
            
            # International carriers
            'att': ['phone', 'wap.cingular', 'broadband'],
            'verizon': ['vzwinternet', 'internet'],
            'tmobile': ['fast.t-mobile.com', 'epc.tmobile.com'],
            'vodafone': ['internet', 'live.vodafone.com'],
            'orange': ['orange', 'orange.fr'],
            'three': ['3internet', 'three.co.uk']
        }
        
        # Pattern to detect consecutive dots (invalid) - this is the main issue
        self.consecutive_dots_pattern = re.compile(r'\.{2,}')
        
        # Pattern to detect invalid trailing/leading dots
        self.invalid_dots_pattern = re.compile(r'^\.|\.$')
        
        # Pattern to detect single character labels between dots (like .t.t.t)
        self.single_char_labels_pattern = re.compile(r'\.([a-zA-Z0-9])\.([a-zA-Z0-9])\.')
        
        # Domain validation patterns - strict validation
        self.domain_pattern = re.compile(
            r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'
            r'(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        )
        
        # APN name validation - more restrictive to catch malformed domains
        self.apn_pattern = re.compile(
            r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]{0,98}[a-zA-Z0-9])?$'
        )
    
    def validate_domain_format(self, domain: str) -> ValidationResult:
        """
        Validate domain format to catch malformed domains like 'allcom.br.t.t.t'
        
        Args:
            domain: Domain string to validate
            
        Returns:
            ValidationResult with validation status and suggestions
        """
        if not domain:
            return ValidationResult(
                is_valid=False,
                error_message="Domain cannot be empty",
                error_code="EMPTY_DOMAIN",
                suggestions=["Enter a valid domain name like 'example.com'"],
                field_name="apn",
                validated_value=domain
            )
        
        # Check for consecutive dots (main issue to fix)
        if self.consecutive_dots_pattern.search(domain):
            suggestions = self._suggest_domain_corrections(domain)
            return ValidationResult(
                is_valid=False,
                error_message="Domain contains consecutive dots which is invalid",
                error_code="CONSECUTIVE_DOTS",
                suggestions=suggestions,
                field_name="apn",
                validated_value=domain
            )
        
        # Check for malformed domains like "allcom.br.t.t.t" (suspicious patterns)
        if self._is_malformed_domain(domain):
            suggestions = self._suggest_domain_corrections(domain)
            return ValidationResult(
                is_valid=False,
                error_message="Domain appears to be malformed or corrupted",
                error_code="MALFORMED_DOMAIN",
                suggestions=suggestions,
                field_name="apn",
                validated_value=domain
            )
        
        # Check for leading/trailing dots
        if self.invalid_dots_pattern.search(domain):
            corrected = domain.strip('.')
            return ValidationResult(
                is_valid=False,
                error_message="Domain cannot start or end with a dot",
                error_code="INVALID_DOT_POSITION",
                suggestions=[corrected] if corrected else ["Enter a valid domain name"],
                field_name="apn",
                validated_value=domain
            )
        
        # Check domain length limits first
        if len(domain) > 253:
            return ValidationResult(
                is_valid=False,
                error_message="Domain name too long (maximum 253 characters)",
                error_code="DOMAIN_TOO_LONG",
                suggestions=[domain[:253]],
                field_name="apn",
                validated_value=domain
            )
        
        # Check overall domain format
        if not self.domain_pattern.match(domain):
            suggestions = self._suggest_domain_corrections(domain)
            return ValidationResult(
                is_valid=False,
                error_message="Invalid domain format",
                error_code="INVALID_DOMAIN_FORMAT",
                suggestions=suggestions,
                field_name="apn",
                validated_value=domain
            )
        
        # Check individual label lengths
        labels = domain.split('.')
        for label in labels:
            if len(label) > 63:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Domain label '{label}' too long (maximum 63 characters)",
                    error_code="LABEL_TOO_LONG",
                    suggestions=self._suggest_domain_corrections(domain),
                    field_name="apn",
                    validated_value=domain
                )
        
        return ValidationResult(
            is_valid=True,
            error_message="",
            error_code="",
            suggestions=[],
            field_name="apn",
            validated_value=domain
        )
    
    def validate_ip_address(self, ip: str) -> ValidationResult:
        """
        Validate IP address format for APN configurations
        
        Args:
            ip: IP address string to validate
            
        Returns:
            ValidationResult with validation status
        """
        if not ip:
            return ValidationResult(
                is_valid=False,
                error_message="IP address cannot be empty",
                error_code="EMPTY_IP",
                suggestions=["Enter a valid IP address like '192.168.1.1'"],
                field_name="apn",
                validated_value=ip
            )
        
        try:
            # Try to parse as IPv4 or IPv6
            parsed_ip = ipaddress.ip_address(ip)
            
            # Check if it's a valid public IP (not private/reserved)
            if parsed_ip.is_private:
                return ValidationResult(
                    is_valid=True,  # Still valid, but with warning
                    error_message="",
                    error_code="PRIVATE_IP_WARNING",
                    suggestions=["Private IP addresses may not work for APN configuration"],
                    field_name="apn",
                    validated_value=ip
                )
            
            return ValidationResult(
                is_valid=True,
                error_message="",
                error_code="",
                suggestions=[],
                field_name="apn",
                validated_value=ip
            )
            
        except ValueError:
            return ValidationResult(
                is_valid=False,
                error_message="Invalid IP address format",
                error_code="INVALID_IP_FORMAT",
                suggestions=["Enter a valid IP address like '192.168.1.1' or '2001:db8::1'"],
                field_name="apn",
                validated_value=ip
            )
    
    def is_common_carrier_apn(self, apn: str) -> bool:
        """
        Check if APN matches common carrier patterns
        
        Args:
            apn: APN string to check
            
        Returns:
            True if matches known carrier APN
        """
        apn_lower = apn.lower()
        
        for carrier, apn_list in self.carrier_apns.items():
            for carrier_apn in apn_list:
                if apn_lower == carrier_apn.lower() or apn_lower in carrier_apn.lower():
                    return True
        
        return False
    
    def suggest_corrections(self, invalid_apn: str) -> List[str]:
        """
        Suggest corrections for invalid APN formats
        
        Args:
            invalid_apn: Invalid APN string
            
        Returns:
            List of suggested corrections
        """
        suggestions = []
        
        # Fix consecutive dots
        if self.consecutive_dots_pattern.search(invalid_apn):
            corrected = re.sub(r'\.{2,}', '.', invalid_apn)
            suggestions.append(corrected)
        
        # Fix leading/trailing dots
        if self.invalid_dots_pattern.search(invalid_apn):
            corrected = invalid_apn.strip('.')
            if corrected:
                suggestions.append(corrected)
        
        # Suggest carrier-specific APNs based on partial match
        apn_lower = invalid_apn.lower()
        for carrier, apn_list in self.carrier_apns.items():
            if carrier in apn_lower:
                suggestions.extend(apn_list[:2])  # Add top 2 suggestions per carrier
        
        # Generic domain suggestions if it looks like a domain
        if '.' in invalid_apn and not suggestions:
            suggestions.extend(self._suggest_domain_corrections(invalid_apn))
        
        # Remove duplicates and limit suggestions
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:5]  # Limit to 5 suggestions
    
    def validate_credentials(self, username: str, password: str) -> ValidationResult:
        """
        Validate APN credentials (username/password)
        
        Args:
            username: Username string
            password: Password string
            
        Returns:
            ValidationResult with validation status
        """
        errors = []
        suggestions = []
        
        # Username validation
        if username:
            if len(username) > 64:
                errors.append("Username too long (maximum 64 characters)")
                suggestions.append(f"Shorten username to: {username[:64]}")
            
            # Check for invalid characters in username
            if re.search(r'[<>"\s]', username):
                errors.append("Username contains invalid characters")
                suggestions.append("Remove spaces and special characters from username")
        
        # Password validation
        if password:
            if len(password) > 64:
                errors.append("Password too long (maximum 64 characters)")
                suggestions.append("Use a shorter password (max 64 characters)")
            
            # Check for invalid characters in password
            if re.search(r'[<>"]', password):
                errors.append("Password contains invalid characters")
                suggestions.append("Remove quotes and angle brackets from password")
        
        # If both username and password are empty, consider them valid
        if not username and not password:
            return ValidationResult(
                is_valid=True,
                error_message="",
                error_code="",
                suggestions=[],
                field_name="credentials",
                validated_value=f"{username}:{password}"
            )
        
        # Check credential consistency (if one is provided, the other should be too)
        if bool(username) != bool(password):
            errors.append("Both username and password must be provided together, or both left empty")
            if username and not password:
                suggestions.append("Provide a password for the username")
            elif password and not username:
                suggestions.append("Provide a username for the password")
        
        if errors:
            return ValidationResult(
                is_valid=False,
                error_message="; ".join(errors),
                error_code="INVALID_CREDENTIALS",
                suggestions=suggestions,
                field_name="credentials",
                validated_value=f"{username}:{password}"
            )
        
        return ValidationResult(
            is_valid=True,
            error_message="",
            error_code="",
            suggestions=[],
            field_name="credentials",
            validated_value=f"{username}:{password}"
        )
    
    def validate_apn_configuration(self, apn: str, username: str = "", password: str = "") -> ValidationResult:
        """
        Comprehensive APN configuration validation
        
        Args:
            apn: APN name/address
            username: Optional username
            password: Optional password
            
        Returns:
            ValidationResult with overall validation status
        """
        # If APN is empty, consider it valid and proceed to validate credentials
        if not apn:
            # Validate credentials even if APN is empty
            cred_result = self.validate_credentials(username, password)
            if not cred_result.is_valid:
                return cred_result
            
            return ValidationResult(
                is_valid=True,
                error_message="",
                error_code="",
                suggestions=[],
                field_name="apn",
                validated_value=apn
            )
        
        # Check if it's an IP address
        ip_result = self.validate_ip_address(apn)
        if ip_result.is_valid:
            # It's a valid IP, now check credentials
            cred_result = self.validate_credentials(username, password)
            if not cred_result.is_valid:
                return cred_result
            return ip_result
        
        # Check if it's a domain
        domain_result = self.validate_domain_format(apn)
        if not domain_result.is_valid:
            return domain_result
        
        # Validate credentials
        cred_result = self.validate_credentials(username, password)
        if not cred_result.is_valid:
            return cred_result
        
        # All validations passed
        return ValidationResult(
            is_valid=True,
            error_message="",
            error_code="",
            suggestions=[],
            field_name="apn_configuration",
            validated_value=f"{apn}|{username}|{password}"
        )
    
    def _suggest_domain_corrections(self, domain: str) -> List[str]:
        """Generate domain correction suggestions"""
        suggestions = []
        
        # Fix consecutive dots
        if self.consecutive_dots_pattern.search(domain):
            corrected = re.sub(r'\.{2,}', '.', domain)
            suggestions.append(corrected)
        
        # Fix malformed patterns like .t.t.t, .x.x.x, .a.a.a
        domain_lower = domain.lower()
        malformed_patterns = [
            (r'\.t\.t\.t$', ''),
            (r'\.x\.x\.x$', ''),
            (r'\.a\.a\.a$', ''),
        ]
        
        for pattern, replacement in malformed_patterns:
            if re.search(pattern, domain_lower):
                corrected = re.sub(pattern, replacement, domain_lower)
                if corrected:
                    suggestions.append(corrected)
                    # Also suggest with .br extension if it looks like a Brazilian domain
                    if not corrected.endswith('.br') and any(carrier in corrected for carrier in ['allcom', 'vivo', 'tim', 'claro']):
                        suggestions.append(f"{corrected}.br")
                        suggestions.append(f"{corrected}.com.br")
        
        # Fix common typos in Brazilian domains
        if 'br.t.t.t' in domain.lower():
            base_domain = domain.lower().replace('.t.t.t', '')
            suggestions.extend([
                base_domain,
                f"{base_domain}.br",
                f"{base_domain}.com.br"
            ])
        
        # Suggest carrier-specific domains based on content
        if 'allcom' in domain_lower:
            suggestions.append('allcom.br')
        elif 'vivo' in domain_lower:
            suggestions.extend(['zap.vivo.com.br', 'vivo.br'])
        elif 'tim' in domain_lower:
            suggestions.extend(['tim.br', 'tim.com.br'])
        elif 'claro' in domain_lower:
            suggestions.extend(['claro.com.br', 'bandalarga.claro.com.br'])
        
        # Remove duplicates and empty suggestions
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion and suggestion not in unique_suggestions:
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:3]  # Limit to 3 suggestions
    
    def _is_malformed_domain(self, domain: str) -> bool:
        """
        Detect malformed domains like 'allcom.br.t.t.t'
        
        Args:
            domain: Domain to check
            
        Returns:
            True if domain appears malformed
        """
        # Check for known malformed patterns first (most specific)
        domain_lower = domain.lower()
        malformed_patterns = [
            r'\.t\.t\.t$',  # Ends with .t.t.t (the specific bug case)
            r'\.x\.x\.x$',  # Ends with .x.x.x
            r'\.a\.a\.a$',  # Ends with .a.a.a
        ]
        
        for pattern in malformed_patterns:
            if re.search(pattern, domain_lower):
                return True
        
        # Split into labels for more analysis
        labels = domain.split('.')
        
        # Check for suspicious patterns - be more conservative
        # Only flag if we have 3+ consecutive single character labels at the end
        if len(labels) >= 4:
            last_three = labels[-3:]
            if all(len(label) == 1 for label in last_three):
                # Check if they're the same character repeated (like .t.t.t)
                if len(set(last_three)) == 1:  # All same character
                    return True
        
        return False
    
    def _get_common_apn_suggestions(self) -> List[str]:
        """Get list of common APN suggestions"""
        common_apns = []
        
        # Add most common APNs from each carrier
        for carrier, apn_list in self.carrier_apns.items():
            if apn_list:
                common_apns.append(apn_list[0])  # Add the first (most common) APN
        
        return common_apns[:8]  # Limit to 8 suggestions
    
    def get_carrier_suggestions(self, partial_input: str) -> List[Tuple[str, str]]:
        """
        Get carrier-specific APN suggestions based on partial input
        
        Args:
            partial_input: Partial APN input from user
            
        Returns:
            List of tuples (carrier_name, apn) matching the input
        """
        suggestions = []
        partial_lower = partial_input.lower()
        
        for carrier, apn_list in self.carrier_apns.items():
            # Check if carrier name matches
            if partial_lower in carrier.lower():
                for apn in apn_list[:2]:  # Top 2 APNs per carrier
                    suggestions.append((carrier.title(), apn))
            else:
                # Check if any APN matches
                for apn in apn_list:
                    if partial_lower in apn.lower():
                        suggestions.append((carrier.title(), apn))
        
        return suggestions[:10]  # Limit to 10 suggestions