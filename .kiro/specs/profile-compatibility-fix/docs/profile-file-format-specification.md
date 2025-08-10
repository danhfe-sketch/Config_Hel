# Profile File Format Specification

## Overview

This document defines the standardized profile file format used by the LT32Pro Device Configurator for saving and loading device configurations. The format ensures compatibility between save and load operations and provides a robust structure for profile data management.

## File Format

### File Extension
- **Extension**: `.lt32config`
- **Encoding**: UTF-8
- **Format**: INI-style configuration file using Python's `configparser` format

### File Structure

```ini
[Profile_Info]
profile_name = Device Configuration Profile
created_date = 2025-02-08 15:30:45
device_imei = 123456789012345
device_version = LT32Pro v2.1
parameter_count = 45
app_version = 1.2.3
checksum = a1b2c3d4e5f6

[Device_Parameters]
server_ip = 192.168.1.100
server_port = 8080
apn_name = internet.provider.com
apn_username = user123
apn_password = pass456
transmission_interval = 300
heartbeat_interval = 60
# ... additional parameters
```

## Section Specifications

### Profile_Info Section

**Purpose**: Contains metadata about the profile and the device it was created from.

**Required Fields**:
- `profile_name` (string): Human-readable name for the profile
- `created_date` (string): ISO format timestamp when profile was created
- `parameter_count` (integer): Total number of device parameters in the profile
- `app_version` (string): Version of the application that created the profile

**Optional Fields**:
- `device_imei` (string): IMEI of the device the profile was created from
- `device_version` (string): Firmware version of the source device
- `checksum` (string): MD5 hash of the parameter data for integrity verification
- `description` (string): User-provided description of the profile
- `tags` (string): Comma-separated tags for profile categorization

**Field Specifications**:

| Field | Type | Max Length | Format | Example |
|-------|------|------------|--------|---------|
| profile_name | string | 100 | UTF-8 text | "Production Server Config" |
| created_date | string | 19 | YYYY-MM-DD HH:MM:SS | "2025-02-08 15:30:45" |
| device_imei | string | 15 | Numeric | "123456789012345" |
| device_version | string | 50 | Version string | "LT32Pro v2.1" |
| parameter_count | integer | - | Positive integer | 45 |
| app_version | string | 20 | Semantic version | "1.2.3" |
| checksum | string | 32 | MD5 hex | "a1b2c3d4e5f6..." |

### Device_Parameters Section

**Purpose**: Contains all device configuration parameters with their values.

**Parameter Naming Convention**:
- Use lowercase with underscores: `server_ip`, `apn_name`
- Group related parameters with prefixes: `apn_name`, `apn_username`, `apn_password`
- Use descriptive names that match the device command structure

**Parameter Categories**:

#### Network Configuration
- `server_ip`: Server IP address (IPv4 format)
- `server_port`: Server port number (1-65535)
- `server_url`: Alternative server URL format
- `protocol_type`: Communication protocol (TCP/UDP/HTTP)

#### APN Configuration
- `apn_name`: Access Point Name
- `apn_username`: APN authentication username
- `apn_password`: APN authentication password
- `apn_auth_type`: Authentication type (NONE/PAP/CHAP)

#### Timing Parameters
- `transmission_interval`: Data transmission interval in seconds
- `heartbeat_interval`: Heartbeat signal interval in seconds
- `connection_timeout`: Connection timeout in seconds
- `retry_interval`: Retry interval for failed operations

#### Device Settings
- `device_name`: Custom device identifier
- `ignition_type`: Ignition detection type
- `vibration_sensitivity`: Vibration sensor sensitivity level
- `defense_mode`: Security/defense mode setting

## Data Types and Validation

### String Parameters
- **Encoding**: UTF-8
- **Maximum Length**: 255 characters unless specified otherwise
- **Special Characters**: Escaped using standard INI escaping rules
- **Empty Values**: Represented as empty strings, not null

### Numeric Parameters
- **Integers**: Standard decimal notation, no leading zeros
- **Ranges**: Validated according to device specifications
- **Invalid Values**: Cause validation errors during loading

### Boolean Parameters
- **True Values**: "true", "1", "yes", "on" (case-insensitive)
- **False Values**: "false", "0", "no", "off" (case-insensitive)
- **Default**: Use "true" or "false" for consistency

### IP Address Parameters
- **Format**: IPv4 dotted decimal notation (e.g., "192.168.1.100")
- **Validation**: Must be valid IPv4 address
- **Special Values**: "0.0.0.0" for unset, "255.255.255.255" for broadcast

## Version Compatibility

### Format Version History

#### Version 1.0 (Current)
- Initial standardized format
- Required Profile_Info and Device_Parameters sections
- UTF-8 encoding
- INI-style structure

#### Legacy Formats (Pre-1.0)
- Various inconsistent formats
- Missing metadata sections
- Encoding issues
- Supported through automatic migration

### Migration Rules

1. **Legacy Profile Detection**: Profiles without `Profile_Info` section are considered legacy
2. **Automatic Migration**: Legacy profiles are automatically converted to current format
3. **Backup Creation**: Original files are backed up before migration
4. **Parameter Mapping**: Legacy parameter names are mapped to current conventions

## File Integrity

### Checksum Calculation
```python
import hashlib
import configparser

def calculate_profile_checksum(profile_path):
    config = configparser.ConfigParser()
    config.read(profile_path)
    
    # Extract only Device_Parameters for checksum
    if 'Device_Parameters' in config:
        param_data = dict(config['Device_Parameters'])
        param_string = ''.join(f"{k}={v}" for k, v in sorted(param_data.items()))
        return hashlib.md5(param_string.encode('utf-8')).hexdigest()
    return None
```

### Validation Process
1. **Structure Validation**: Verify required sections exist
2. **Parameter Validation**: Check parameter names and value formats
3. **Integrity Check**: Verify checksum if present
4. **Compatibility Check**: Ensure version compatibility

## Error Handling

### Common Format Errors

#### Missing Required Section
```
Error: Profile file is missing required 'Profile_Info' section
Solution: Add [Profile_Info] section with required fields
```

#### Invalid Parameter Value
```
Error: Parameter 'server_port' has invalid value '99999' (must be 1-65535)
Solution: Correct the parameter value to be within valid range
```

#### Encoding Issues
```
Error: Profile file contains invalid UTF-8 characters
Solution: Re-save the file with UTF-8 encoding
```

#### Checksum Mismatch
```
Error: Profile checksum verification failed - file may be corrupted
Solution: Re-create the profile from the original device configuration
```

## Best Practices

### Creating Profiles
1. Always include complete metadata in Profile_Info section
2. Use descriptive profile names
3. Include device IMEI for traceability
4. Verify parameter count matches actual parameters

### Modifying Profiles
1. Create backup before manual editing
2. Maintain UTF-8 encoding
3. Update parameter_count if parameters are added/removed
4. Recalculate checksum after modifications

### Loading Profiles
1. Validate profile before deployment
2. Check compatibility with target device
3. Review validation warnings before proceeding
4. Monitor deployment progress for errors

## Example Complete Profile

```ini
[Profile_Info]
profile_name = Production Fleet Configuration
created_date = 2025-02-08 15:30:45
device_imei = 123456789012345
device_version = LT32Pro v2.1.3
parameter_count = 12
app_version = 1.2.3
checksum = 7d4c8b2a9f1e6d3c5b8a4e7f2d9c6b1a
description = Standard configuration for production fleet vehicles
tags = production,fleet,standard

[Device_Parameters]
server_ip = 192.168.1.100
server_port = 8080
server_url = 
protocol_type = TCP
apn_name = internet.provider.com
apn_username = fleet_user
apn_password = secure_pass_123
apn_auth_type = PAP
transmission_interval = 300
heartbeat_interval = 60
connection_timeout = 30
retry_interval = 120
device_name = Fleet_Vehicle_001
ignition_type = voltage
vibration_sensitivity = 3
defense_mode = enabled
```

## Technical Implementation Notes

### Reading Profiles
```python
import configparser

def read_profile(file_path):
    config = configparser.ConfigParser()
    config.read(file_path, encoding='utf-8')
    
    # Validate structure
    if 'Profile_Info' not in config:
        raise ValueError("Missing Profile_Info section")
    if 'Device_Parameters' not in config:
        raise ValueError("Missing Device_Parameters section")
    
    return config
```

### Writing Profiles
```python
import configparser
from datetime import datetime

def write_profile(file_path, profile_data, metadata):
    config = configparser.ConfigParser()
    
    # Add Profile_Info section
    config['Profile_Info'] = {
        'profile_name': metadata.get('name', 'Device Configuration'),
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'parameter_count': str(len(profile_data)),
        'app_version': metadata.get('app_version', '1.0.0')
    }
    
    # Add optional metadata
    for key in ['device_imei', 'device_version', 'description', 'tags']:
        if key in metadata and metadata[key]:
            config['Profile_Info'][key] = str(metadata[key])
    
    # Add Device_Parameters section
    config['Device_Parameters'] = profile_data
    
    # Write file
    with open(file_path, 'w', encoding='utf-8') as f:
        config.write(f)
```

This specification ensures consistent, reliable profile file handling across all application components and provides a foundation for future enhancements while maintaining backward compatibility.