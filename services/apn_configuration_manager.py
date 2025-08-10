"""
APN Configuration Manager

This service manages saved APN configurations including:
- Configuration persistence with encrypted credential storage
- Configuration suggestion system based on user input patterns
- Methods for saving, loading, and deleting APN configurations
- Configuration validation before saving to prevent storing invalid configurations
"""

import json
import os
import sys
import hashlib
import base64
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from components.apn_validation_component import APNValidationComponent, ValidationResult
from services.apn_security_service import APNSecurityService, SecurityContext, SecurityLevel, AuditAction


@dataclass
class APNConfiguration:
    """Data class representing an APN configuration"""
    id: str
    apn: str
    username: str
    password: str
    carrier_name: str
    country: str
    created_date: str
    last_used: str
    success_count: int
    description: str = ""
    is_favorite: bool = False


class APNConfigurationManager:
    """Manages APN configurations with encrypted storage and suggestions"""
    
    CONFIG_FILE = "apn_configurations.json"
    ENCRYPTION_KEY_FILE = "apn_key.key"
    
    def __init__(self):
        """Initialize the APN Configuration Manager"""
        self.validator = APNValidationComponent()
        self.security_service = APNSecurityService()
        self.configurations = []
        self.encryption_key = self._get_or_create_encryption_key()
        self._load_configurations()
    
    def save_successful_configuration(self, apn: str, username: str = "", password: str = "", 
                                    carrier_name: str = "", country: str = "", 
                                    description: str = "", security_context: Optional[SecurityContext] = None) -> bool:
        """
        Save a successful APN configuration for future use with security audit logging
        
        Args:
            apn: APN name/address
            username: Optional username
            password: Optional password
            carrier_name: Optional carrier name
            country: Optional country
            description: Optional description
            security_context: Security context for audit logging
            
        Returns:
            True if saved successfully, False otherwise
        """
        # Create default security context if not provided
        if security_context is None:
            security_context = SecurityContext(
                user_id="system",
                session_id="config_save",
                ip_address="127.0.0.1",
                user_agent="APNConfigManager",
                timestamp=datetime.now(),
                security_level=SecurityLevel.MEDIUM,
                permissions=[]
            )
        
        # Security: Input sanitization
        apn_sanitized, apn_issues = self.security_service.sanitize_apn_input(apn, "apn")
        username_sanitized, user_issues = self.security_service.sanitize_apn_input(username, "username")
        password_sanitized, pass_issues = self.security_service.sanitize_apn_input(password, "password")
        
        # Log sanitization issues if any
        all_issues = apn_issues + user_issues + pass_issues
        if all_issues:
            self.security_service.audit_log(
                AuditAction.SECURITY_VIOLATION,
                security_context,
                "configuration_sanitization",
                "apn_config",
                {"sanitization_issues": all_issues},
                True,
                f"Input sanitization applied during config save: {', '.join(all_issues)}"
            )
        # Validate configuration before saving (use sanitized values)
        validation_result = self.validator.validate_apn_configuration(apn_sanitized, username_sanitized, password_sanitized)
        if not validation_result.is_valid:
            # Security audit: Log failed configuration save attempt
            self.security_service.audit_log(
                AuditAction.CONFIGURATION_CREATE,
                security_context,
                "apn_configuration",
                f"apn:{apn_sanitized}",
                {"validation_error": validation_result.error_message},
                False,
                f"Cannot save invalid APN configuration: {validation_result.error_message}"
            )
            print(f"Cannot save invalid APN configuration: {validation_result.error_message}")
            return False
        
        # Check if configuration already exists (use sanitized values)
        existing_config = self._find_existing_configuration(apn_sanitized, username_sanitized)
        if existing_config:
            # Update existing configuration
            existing_config.last_used = datetime.now().isoformat()
            existing_config.success_count += 1
            if description:
                existing_config.description = description
            if carrier_name:
                existing_config.carrier_name = carrier_name
            if country:
                existing_config.country = country
            
            # Security audit: Log configuration update
            self.security_service.audit_log(
                AuditAction.CONFIGURATION_UPDATE,
                security_context,
                "apn_configuration",
                existing_config.id,
                {"success_count": existing_config.success_count},
                True,
                f"Updated existing APN configuration: {existing_config.id}"
            )
        else:
            # Create new configuration (use sanitized values)
            config_id = self._generate_config_id(apn_sanitized, username_sanitized)
            new_config = APNConfiguration(
                id=config_id,
                apn=apn_sanitized,
                username=username_sanitized,
                password=password_sanitized,
                carrier_name=carrier_name or self._detect_carrier(apn_sanitized),
                country=country or self._detect_country(apn_sanitized),
                created_date=datetime.now().isoformat(),
                last_used=datetime.now().isoformat(),
                success_count=1,
                description=description
            )
            self.configurations.append(new_config)
            
            # Security audit: Log new configuration creation
            self.security_service.audit_log(
                AuditAction.CONFIGURATION_CREATE,
                security_context,
                "apn_configuration",
                config_id,
                {"apn": apn_sanitized, "carrier": new_config.carrier_name},
                True,
                f"Created new APN configuration: {config_id}"
            )
        
        return self._save_configurations()
    
    def get_saved_configurations(self) -> List[APNConfiguration]:
        """
        Get all saved APN configurations
        
        Returns:
            List of APNConfiguration objects
        """
        # Sort by success count and last used date
        sorted_configs = sorted(
            self.configurations,
            key=lambda x: (x.is_favorite, x.success_count, x.last_used),
            reverse=True
        )
        return sorted_configs
    
    def suggest_configurations(self, partial_input: str) -> List[APNConfiguration]:
        """
        Suggest APN configurations based on partial input
        
        Args:
            partial_input: Partial APN input from user
            
        Returns:
            List of matching APNConfiguration objects
        """
        if not partial_input:
            # Return most successful configurations
            return self.get_saved_configurations()[:5]
        
        partial_lower = partial_input.lower()
        suggestions = []
        
        # Find configurations that match the partial input
        for config in self.configurations:
            score = 0
            
            # Exact match gets highest score
            if config.apn.lower() == partial_lower:
                score = 100
            # Starts with partial input
            elif config.apn.lower().startswith(partial_lower):
                score = 80
            # Contains partial input
            elif partial_lower in config.apn.lower():
                score = 60
            # Carrier name matches
            elif partial_lower in config.carrier_name.lower():
                score = 40
            # Description matches
            elif partial_lower in config.description.lower():
                score = 20
            
            if score > 0:
                # Boost score based on success count and favorites
                if config.is_favorite:
                    score += 20
                score += min(config.success_count * 2, 20)  # Max 20 points from success count
                
                suggestions.append((score, config))
        
        # Sort by score and return top suggestions
        suggestions.sort(key=lambda x: x[0], reverse=True)
        return [config for score, config in suggestions[:10]]
    
    def delete_configuration(self, config_id: str) -> bool:
        """
        Delete a saved APN configuration
        
        Args:
            config_id: ID of configuration to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        original_count = len(self.configurations)
        self.configurations = [config for config in self.configurations if config.id != config_id]
        
        if len(self.configurations) < original_count:
            return self._save_configurations()
        
        return False
    
    def update_configuration(self, config_id: str, **kwargs) -> bool:
        """
        Update an existing APN configuration
        
        Args:
            config_id: ID of configuration to update
            **kwargs: Fields to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        config = self._find_configuration_by_id(config_id)
        if not config:
            return False
        
        # Update allowed fields
        allowed_fields = ['apn', 'username', 'password', 'carrier_name', 'country', 
                         'description', 'is_favorite']
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(config, field, value)
        
        # Validate if APN-related fields were updated
        if any(field in kwargs for field in ['apn', 'username', 'password']):
            validation_result = self.validator.validate_apn_configuration(
                config.apn, config.username, config.password
            )
            if not validation_result.is_valid:
                print(f"Cannot update to invalid APN configuration: {validation_result.error_message}")
                return False
        
        return self._save_configurations()
    
    def get_configuration_by_id(self, config_id: str) -> Optional[APNConfiguration]:
        """
        Get a specific configuration by ID
        
        Args:
            config_id: Configuration ID
            
        Returns:
            APNConfiguration object or None if not found
        """
        return self._find_configuration_by_id(config_id)
    
    def get_carrier_configurations(self, carrier_name: str) -> List[APNConfiguration]:
        """
        Get all configurations for a specific carrier
        
        Args:
            carrier_name: Name of the carrier
            
        Returns:
            List of APNConfiguration objects for the carrier
        """
        carrier_lower = carrier_name.lower()
        return [
            config for config in self.configurations
            if carrier_lower in config.carrier_name.lower()
        ]
    
    def get_usage_statistics(self) -> Dict[str, any]:
        """
        Get usage statistics for saved configurations
        
        Returns:
            Dictionary with usage statistics
        """
        if not self.configurations:
            return {
                'total_configurations': 0,
                'most_used_carrier': 'None',
                'average_success_count': 0,
                'favorite_count': 0
            }
        
        # Calculate statistics
        total_configs = len(self.configurations)
        carrier_counts = {}
        total_success = 0
        favorite_count = 0
        
        for config in self.configurations:
            # Count carriers
            carrier = config.carrier_name or 'Unknown'
            carrier_counts[carrier] = carrier_counts.get(carrier, 0) + 1
            
            # Sum success counts
            total_success += config.success_count
            
            # Count favorites
            if config.is_favorite:
                favorite_count += 1
        
        most_used_carrier = max(carrier_counts.items(), key=lambda x: x[1])[0] if carrier_counts else 'None'
        average_success = total_success / total_configs if total_configs > 0 else 0
        
        return {
            'total_configurations': total_configs,
            'most_used_carrier': most_used_carrier,
            'average_success_count': round(average_success, 1),
            'favorite_count': favorite_count,
            'carrier_distribution': carrier_counts
        }
    
    def export_configurations(self, file_path: str, include_passwords: bool = False) -> bool:
        """
        Export configurations to a file
        
        Args:
            file_path: Path to export file
            include_passwords: Whether to include encrypted passwords
            
        Returns:
            True if exported successfully, False otherwise
        """
        try:
            export_data = {
                'export_date': datetime.now().isoformat(),
                'version': '1.0',
                'configurations': []
            }
            
            for config in self.configurations:
                config_dict = asdict(config)
                if not include_passwords:
                    config_dict['password'] = ''  # Remove password for security
                    config_dict['username'] = ''  # Also remove username to maintain consistency
                export_data['configurations'].append(config_dict)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error exporting configurations: {e}")
            return False
    
    def import_configurations(self, file_path: str, merge: bool = True) -> Tuple[bool, str]:
        """
        Import configurations from a file
        
        Args:
            file_path: Path to import file
            merge: Whether to merge with existing configurations or replace
            
        Returns:
            Tuple of (success, message)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if 'configurations' not in import_data:
                return False, "Invalid import file format"
            
            imported_count = 0
            skipped_count = 0
            
            if not merge:
                self.configurations = []
            
            for config_data in import_data['configurations']:
                try:
                    # Validate required fields
                    if not all(field in config_data for field in ['id', 'apn']):
                        skipped_count += 1
                        continue
                    
                    # Check if configuration already exists (when merging)
                    if merge and self._find_configuration_by_id(config_data['id']):
                        skipped_count += 1
                        continue
                    
                    # Create configuration object
                    config = APNConfiguration(**config_data)
                    
                    # Validate APN configuration (allow empty passwords for imported configs)
                    validation_result = self.validator.validate_apn_configuration(
                        config.apn, config.username, config.password
                    )
                    if not validation_result.is_valid:
                        # Try validation without password in case it was exported without passwords
                        if config.password == "":
                            validation_result = self.validator.validate_apn_configuration(
                                config.apn, config.username, ""
                            )
                        if not validation_result.is_valid:
                            print(f"Skipping invalid configuration: {config.apn} - {validation_result.error_message}")
                            skipped_count += 1
                            continue
                    
                    self.configurations.append(config)
                    imported_count += 1
                    
                except Exception as e:
                    print(f"Error importing configuration: {e}")
                    skipped_count += 1
            
            if imported_count > 0:
                self._save_configurations()
            
            message = f"Imported {imported_count} configurations"
            if skipped_count > 0:
                message += f", skipped {skipped_count} invalid/duplicate configurations"
            
            return True, message
            
        except Exception as e:
            return False, f"Error importing configurations: {e}"
    
    def _get_or_create_encryption_key(self) -> bytes:
        """
        Get or create encryption key for password storage
        
        Returns:
            Encryption key bytes
        """
        key_path = self._get_key_file_path()
        
        if os.path.exists(key_path):
            try:
                with open(key_path, 'rb') as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading encryption key: {e}")
        
        # Generate new key
        try:
            # Use a simple key derivation for demo purposes
            # In production, you might want to use user-specific data
            password = b"lt32pro_apn_config_key_v1"
            salt = b"lt32pro_salt_2024"
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            # Save key to file
            key_dir = os.path.dirname(key_path)
            if key_dir and not os.path.exists(key_dir):
                os.makedirs(key_dir, exist_ok=True)
            
            with open(key_path, 'wb') as f:
                f.write(key)
            
            return key
            
        except Exception as e:
            print(f"Error creating encryption key: {e}")
            # Fallback to a simple key (not secure, but functional)
            fallback_key = base64.urlsafe_b64encode(b"fallback_key_lt32pro_apn_mgr_2024")
            
            # Try to save fallback key
            try:
                key_dir = os.path.dirname(key_path)
                if key_dir and not os.path.exists(key_dir):
                    os.makedirs(key_dir, exist_ok=True)
                with open(key_path, 'wb') as f:
                    f.write(fallback_key)
            except:
                pass  # Ignore save errors for fallback
            
            return fallback_key
    
    def _encrypt_password(self, password: str) -> str:
        """
        Encrypt password for storage
        
        Args:
            password: Plain text password
            
        Returns:
            Encrypted password string
        """
        if not password:
            return ""
        
        try:
            fernet = Fernet(self.encryption_key)
            encrypted = fernet.encrypt(password.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            print(f"Error encrypting password: {e}")
            return password  # Return plain text as fallback (not secure)
    
    def _decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt password from storage
        
        Args:
            encrypted_password: Encrypted password string
            
        Returns:
            Plain text password
        """
        if not encrypted_password:
            return ""
        
        try:
            fernet = Fernet(self.encryption_key)
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_password.encode('utf-8'))
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            print(f"Error decrypting password: {e}")
            return encrypted_password  # Return as-is if decryption fails
    
    def _load_configurations(self) -> None:
        """Load configurations from file"""
        try:
            config_path = self._get_config_file_path()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.configurations = []
                for config_data in data.get('configurations', []):
                    try:
                        # Decrypt password if present
                        if config_data.get('password'):
                            config_data['password'] = self._decrypt_password(config_data['password'])
                        
                        config = APNConfiguration(**config_data)
                        self.configurations.append(config)
                    except Exception as e:
                        print(f"Error loading configuration: {e}")
                        continue
                
                print(f"Loaded {len(self.configurations)} APN configurations")
            else:
                self.configurations = []
                
        except Exception as e:
            print(f"Error loading APN configurations: {e}")
            self.configurations = []
    
    def _save_configurations(self) -> bool:
        """Save configurations to file"""
        try:
            config_path = self._get_config_file_path()
            config_dir = os.path.dirname(config_path)
            
            # Ensure directory exists
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            # Prepare data for saving
            save_data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'configurations': []
            }
            
            for config in self.configurations:
                config_dict = asdict(config)
                # Encrypt password before saving
                if config_dict.get('password'):
                    config_dict['password'] = self._encrypt_password(config_dict['password'])
                save_data['configurations'].append(config_dict)
            
            # Save to file
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
            print(f"Saved {len(self.configurations)} APN configurations to {config_path}")
            return True
            
        except Exception as e:
            print(f"Error saving APN configurations: {e}")
            return False
    
    def _get_config_file_path(self) -> str:
        """Get the path to the configuration file"""
        try:
            # Use same pattern as AppConfigService
            user_home = os.path.expanduser("~")
            app_config_dir = os.path.join(user_home, ".lt32pro_config")
            
            # Test if we can write to this directory
            if not os.path.exists(app_config_dir):
                try:
                    os.makedirs(app_config_dir, exist_ok=True)
                    # Test write access
                    test_file = os.path.join(app_config_dir, "test_write.tmp")
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    return os.path.join(app_config_dir, self.CONFIG_FILE)
                except (PermissionError, OSError):
                    pass
            else:
                # Directory exists, test write access
                try:
                    test_file = os.path.join(app_config_dir, "test_write.tmp")
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    return os.path.join(app_config_dir, self.CONFIG_FILE)
                except (PermissionError, OSError):
                    pass
            
            # Fall back to application directory
            base_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
            return os.path.join(base_dir, self.CONFIG_FILE)
            
        except Exception as e:
            print(f"Error determining config path: {e}")
            return self.CONFIG_FILE
    
    def _get_key_file_path(self) -> str:
        """Get the path to the encryption key file"""
        config_path = self._get_config_file_path()
        config_dir = os.path.dirname(config_path)
        return os.path.join(config_dir, self.ENCRYPTION_KEY_FILE)
    
    def _generate_config_id(self, apn: str, username: str) -> str:
        """
        Generate unique ID for configuration
        
        Args:
            apn: APN name
            username: Username
            
        Returns:
            Unique configuration ID
        """
        # Create hash from APN and username
        content = f"{apn}|{username}|{datetime.now().isoformat()}"
        hash_object = hashlib.md5(content.encode())
        return hash_object.hexdigest()[:12]  # Use first 12 characters
    
    def _find_existing_configuration(self, apn: str, username: str) -> Optional[APNConfiguration]:
        """
        Find existing configuration with same APN and username
        
        Args:
            apn: APN name
            username: Username
            
        Returns:
            Existing APNConfiguration or None
        """
        for config in self.configurations:
            if config.apn.lower() == apn.lower() and config.username.lower() == username.lower():
                return config
        return None
    
    def _find_configuration_by_id(self, config_id: str) -> Optional[APNConfiguration]:
        """
        Find configuration by ID
        
        Args:
            config_id: Configuration ID
            
        Returns:
            APNConfiguration or None
        """
        for config in self.configurations:
            if config.id == config_id:
                return config
        return None
    
    def _detect_carrier(self, apn: str) -> str:
        """
        Detect carrier name from APN
        
        Args:
            apn: APN name
            
        Returns:
            Detected carrier name or 'Unknown'
        """
        apn_lower = apn.lower()
        
        # Brazilian carriers
        if 'vivo' in apn_lower:
            return 'Vivo'
        elif 'tim' in apn_lower:
            return 'TIM'
        elif 'claro' in apn_lower:
            return 'Claro'
        elif 'oi' in apn_lower:
            return 'Oi'
        elif 'allcom' in apn_lower:
            return 'Allcom'
        
        # International carriers
        elif 'att' in apn_lower or 'cingular' in apn_lower:
            return 'AT&T'
        elif 'verizon' in apn_lower or 'vzw' in apn_lower:
            return 'Verizon'
        elif 'tmobile' in apn_lower or 't-mobile' in apn_lower:
            return 'T-Mobile'
        elif 'vodafone' in apn_lower:
            return 'Vodafone'
        elif 'orange' in apn_lower:
            return 'Orange'
        elif 'three' in apn_lower:
            return 'Three'
        
        return 'Unknown'
    
    def _detect_country(self, apn: str) -> str:
        """
        Detect country from APN
        
        Args:
            apn: APN name
            
        Returns:
            Detected country or 'Unknown'
        """
        apn_lower = apn.lower()
        
        # Country detection based on TLD or carrier
        if '.br' in apn_lower or any(carrier in apn_lower for carrier in ['vivo', 'tim', 'claro', 'oi', 'allcom']):
            return 'Brazil'
        elif '.com' in apn_lower and any(carrier in apn_lower for carrier in ['att', 'verizon', 'tmobile']):
            return 'United States'
        elif '.co.uk' in apn_lower or 'three.co.uk' in apn_lower:
            return 'United Kingdom'
        elif '.fr' in apn_lower:
            return 'France'
        elif 'vodafone' in apn_lower:
            return 'Multiple'  # Vodafone operates in many countries
        
        return 'Unknown'