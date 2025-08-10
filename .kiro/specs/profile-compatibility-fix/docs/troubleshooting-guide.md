# Profile Operations Troubleshooting Guide

## Overview

This guide provides solutions for common issues encountered during profile save and load operations in the LT32Pro Device Configurator. It covers error diagnosis, resolution steps, and prevention strategies.

## Quick Diagnosis Checklist

Before diving into specific issues, run through this quick checklist:

1. **File Access**: Can you read/write to the profile file location?
2. **File Format**: Is the profile file a valid `.lt32config` file?
3. **Device Connection**: Is the device properly connected and responding?
4. **Application Version**: Are you using a compatible application version?
5. **Profile Integrity**: Does the profile file contain all required sections?

## Common Error Categories

### 1. Variable Scoping Errors

#### Error: "cannot access local variable 'param_count' where it is not associated with a value"

**Symptoms**:
- Application crashes when loading profiles
- Error occurs during profile parsing
- Stack trace points to toolbar_frame.py

**Root Cause**:
Variable `param_count` is defined inside a try block but accessed outside when an exception occurs.

**Solution**:
This error has been fixed in the updated codebase. If you encounter it:

1. **Immediate Fix**: Restart the application
2. **Update Required**: Ensure you're using the latest version with the profile compatibility fixes
3. **Manual Fix** (if needed):
   ```python
   # Initialize variables before try block
   param_count = 0
   profile_name = "Unknown Profile"
   profile_created = ""
   
   try:
       # Profile parsing code
       # ...
   except Exception as e:
       # Variables are now safely available
       pass
   ```

**Prevention**:
- Always initialize variables with default values before try blocks
- Use proper exception handling patterns
- Validate profile files before processing

### 2. Profile File Format Issues

#### Error: "Profile file is missing required section"

**Symptoms**:
- Profile loading fails with missing section error
- Validation shows missing `Profile_Info` or `Device_Parameters` sections

**Diagnosis Steps**:
1. Open the profile file in a text editor
2. Check for `[Profile_Info]` and `[Device_Parameters]` sections
3. Verify section names are exactly as specified (case-sensitive)

**Solutions**:

**For Missing Profile_Info Section**:
```ini
# Add this section at the top of your profile file
[Profile_Info]
profile_name = My Device Configuration
created_date = 2025-02-08 15:30:45
parameter_count = 10
app_version = 1.2.3
```

**For Missing Device_Parameters Section**:
```ini
# Add this section with your device parameters
[Device_Parameters]
server_ip = 192.168.1.100
server_port = 8080
# ... other parameters
```

**Prevention**:
- Always use the application's save function to create profiles
- Don't manually edit profile files unless necessary
- Use profile validation before loading

#### Error: "Invalid parameter value"

**Symptoms**:
- Profile loads but some parameters are rejected
- Validation warnings about parameter values
- Device configuration incomplete

**Common Invalid Values**:

| Parameter | Invalid Example | Valid Example | Fix |
|-----------|----------------|---------------|-----|
| server_port | 99999 | 8080 | Use port 1-65535 |
| server_ip | 999.999.999.999 | 192.168.1.100 | Use valid IPv4 |
| transmission_interval | -1 | 300 | Use positive integer |
| apn_name | (empty) | internet.provider.com | Provide APN name |

**Solution Steps**:
1. Review the validation error messages
2. Check parameter value ranges in device documentation
3. Correct invalid values in the profile file
4. Re-validate the profile before loading

### 3. File Access Issues

#### Error: "Permission denied" or "File not found"

**Symptoms**:
- Cannot save profiles to selected location
- Cannot load existing profile files
- File operations fail silently

**Diagnosis**:
```python
# Check file permissions
import os
file_path = "path/to/profile.lt32config"
print(f"File exists: {os.path.exists(file_path)}")
print(f"Readable: {os.access(file_path, os.R_OK)}")
print(f"Writable: {os.access(file_path, os.W_OK)}")
```

**Solutions**:

**For Permission Issues**:
1. Run application as administrator (Windows) or with sudo (Linux)
2. Change file permissions: `chmod 644 profile.lt32config`
3. Move profile to a user-writable directory
4. Check antivirus software blocking file access

**For File Not Found**:
1. Verify the file path is correct
2. Check if file was moved or deleted
3. Look in recent files or backup locations
4. Recreate profile from device if necessary

### 4. Device Communication Issues

#### Error: "Device not responding during profile load"

**Symptoms**:
- Profile validation succeeds but loading fails
- Device connection lost during operation
- Partial parameter deployment

**Diagnosis Steps**:
1. Check device connection status
2. Verify device is powered and responsive
3. Test basic device communication
4. Check for interference or cable issues

**Solutions**:

**Connection Issues**:
1. Reconnect device cable
2. Restart device
3. Check COM port settings
4. Try different USB port

**Communication Timeout**:
1. Increase timeout settings in application
2. Reduce profile size (split into smaller profiles)
3. Check for device firmware issues
4. Verify device compatibility

**Partial Deployment**:
1. Note which parameters failed
2. Retry with only failed parameters
3. Check parameter compatibility with device firmware
4. Manual parameter setting for critical values

### 5. Profile Compatibility Issues

#### Error: "Profile version not supported"

**Symptoms**:
- Old profiles won't load in new application version
- New profiles won't load in old application version
- Migration warnings or failures

**Solutions**:

**For Legacy Profiles**:
1. Use automatic migration feature
2. Backup original profile before migration
3. Verify migrated parameters are correct
4. Update parameter names if needed

**For Version Mismatch**:
1. Update application to latest version
2. Export parameters manually if needed
3. Recreate profile with current application
4. Check compatibility matrix in documentation

### 6. Data Integrity Issues

#### Error: "Profile checksum verification failed"

**Symptoms**:
- Profile appears corrupted
- Checksum mismatch warnings
- Unexpected parameter values

**Diagnosis**:
```python
# Verify profile integrity
import hashlib
import configparser

def verify_profile_checksum(profile_path):
    config = configparser.ConfigParser()
    config.read(profile_path)
    
    if 'Profile_Info' in config and 'checksum' in config['Profile_Info']:
        stored_checksum = config['Profile_Info']['checksum']
        # Calculate current checksum
        # Compare with stored value
        return stored_checksum == calculated_checksum
    return True  # No checksum to verify
```

**Solutions**:
1. **Recalculate Checksum**: Remove checksum line and let application regenerate
2. **Restore from Backup**: Use backup copy if available
3. **Recreate Profile**: Create new profile from device
4. **Manual Verification**: Check critical parameters manually

## Advanced Troubleshooting

### Debug Mode

Enable debug logging to get detailed information:

```python
# Add to application startup
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
export PROFILE_DEBUG=1
```

### Profile Validation Tool

Use the built-in validation tool:

```python
from services.profile_validator import ProfileValidator

validator = ProfileValidator()
result = validator.validate_profile_file("profile.lt32config")

if not result.is_valid:
    for error in result.errors:
        print(f"Error: {error.message}")
        if error.suggestion:
            print(f"Suggestion: {error.suggestion}")
```

### Log Analysis

Check application logs for detailed error information:

**Windows**: `%APPDATA%/LT32Pro/logs/`
**Linux**: `~/.local/share/LT32Pro/logs/`

Key log files:
- `profile_operations.log`: Profile save/load operations
- `validation.log`: Profile validation results
- `profile_errors.log`: Detailed error information

## Prevention Strategies

### Best Practices

1. **Regular Backups**: Keep multiple copies of important profiles
2. **Validation First**: Always validate profiles before loading
3. **Incremental Changes**: Make small changes and test frequently
4. **Version Control**: Track profile changes over time
5. **Documentation**: Document custom profiles and their purposes

### Automated Checks

Set up automated validation:

```python
# Profile health check script
def check_profile_health(profile_path):
    checks = [
        check_file_access,
        check_format_validity,
        check_parameter_ranges,
        check_checksum_integrity
    ]
    
    for check in checks:
        result = check(profile_path)
        if not result.passed:
            print(f"Check failed: {result.message}")
            return False
    
    return True
```

### Monitoring

Monitor profile operations:

1. **Success Rates**: Track successful vs failed operations
2. **Error Patterns**: Identify recurring issues
3. **Performance**: Monitor operation timing
4. **User Feedback**: Collect user-reported issues

## Emergency Recovery

### Profile Recovery

If profiles are corrupted or lost:

1. **Check Backups**: Look for automatic backups in `profiles/backups/`
2. **Device Export**: Re-export configuration from device
3. **Partial Recovery**: Extract valid parameters from corrupted files
4. **Template Profiles**: Use known-good profiles as templates

### System Recovery

If the entire profile system fails:

1. **Reset Configuration**: Clear profile cache and settings
2. **Reinstall Components**: Reinstall profile-related components
3. **Factory Reset**: Reset application to default state
4. **Support Contact**: Contact technical support with logs

## Getting Help

### Information to Collect

When reporting issues, include:

1. **Error Messages**: Exact error text and stack traces
2. **Profile Files**: Problematic profile files (sanitized)
3. **Application Version**: Version number and build date
4. **System Information**: OS, hardware, device model
5. **Steps to Reproduce**: Detailed reproduction steps
6. **Log Files**: Relevant log file excerpts

### Support Channels

1. **Documentation**: Check latest documentation updates
2. **FAQ**: Review frequently asked questions
3. **Community Forums**: Search community discussions
4. **Technical Support**: Contact official support channels

### Self-Help Resources

1. **Profile Validator**: Use built-in validation tools
2. **Sample Profiles**: Reference working profile examples
3. **Debug Tools**: Enable debug mode for detailed information
4. **Log Analysis**: Review application logs for clues

## Appendix: Error Code Reference

### Profile Error Codes

| Code | Description | Severity | Solution |
|------|-------------|----------|----------|
| P001 | Missing Profile_Info section | Critical | Add required section |
| P002 | Missing Device_Parameters section | Critical | Add parameters section |
| P003 | Invalid parameter value | Error | Correct parameter value |
| P004 | Checksum verification failed | Warning | Recalculate or ignore |
| P005 | Version compatibility issue | Warning | Update or migrate |
| P006 | File access denied | Critical | Check permissions |
| P007 | Device communication timeout | Error | Check device connection |
| P008 | Partial parameter deployment | Warning | Retry failed parameters |

### Recovery Actions

| Error Code | Automatic Recovery | Manual Action Required |
|------------|-------------------|----------------------|
| P001-P002 | No | Add missing sections |
| P003 | Partial | Correct invalid values |
| P004 | Yes | Verify critical parameters |
| P005 | Yes | Review migrated parameters |
| P006 | No | Fix file permissions |
| P007 | Retry | Check device connection |
| P008 | Retry | Manual parameter setting |

This troubleshooting guide should help resolve most common profile operation issues. For complex problems, enable debug logging and consult the developer documentation for additional technical details.