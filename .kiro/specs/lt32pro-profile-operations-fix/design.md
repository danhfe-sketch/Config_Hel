# Design Document

## Overview

This design addresses the critical issues with LT32Pro profile operations by implementing proper device communication protocol, enhanced parameter extraction, and robust error handling. The solution focuses on fixing the command format (adding "ATSMS:" prefix), implementing correct LT32Pro command syntax, and creating a reliable parameter extraction system that converts device responses into individual parameters for profile validation.

## Architecture

### Core Components

1. **LT32ProCommandFormatter** - Handles proper command formatting with ATSMS prefix for USB communication
2. **LT32ProDeviceReader** - Manages reading configuration from device with correct protocol
3. **LT32ProDeviceWriter** - Manages writing configuration to device with proper command syntax
4. **EnhancedParameterExtractor** - Converts device responses to individual parameters
5. **ProfileOperationManager** - Orchestrates the complete profile operations with progress tracking
6. **LT32ProErrorHandler** - Provides specific error handling for device communication issues

### Communication Flow

```
Profile Operation Request
    ↓
ProfileOperationManager
    ↓
LT32ProCommandFormatter (adds ATSMS prefix for USB)
    ↓
Serial Communication Layer
    ↓
LT32Pro Device
    ↓
Response Parser
    ↓
EnhancedParameterExtractor
    ↓
Profile File Creation/Device Configuration
```

## Components and Interfaces

### LT32ProCommandFormatter

```python
class LT32ProCommandFormatter:
    """Formats commands for LT32Pro device communication."""
    
    def format_read_command(self, command: str) -> str:
        """Format read commands with ATSMS prefix for USB communication."""
        # Examples:
        # "APN" -> "ATSMS:APN#"
        # "IMEI" -> "ATSMS:CXCS#IMEI"
        # "GT06SEL" -> "ATSMS:CXCS#GT06SEL"
    
    def format_write_command(self, command: str, value: str) -> str:
        """Format write commands with ATSMS prefix for USB communication."""
        # Examples:
        # "APN", "internet,user,pass" -> "ATSMS:APN,internet,user,pass#"
        # "SERVER", "0,192.168.1.1,8080,0" -> "ATSMS:SERVER,0,192.168.1.1,8080,0#"
        # "GT06SEL", "2" -> "ATSMS:SZCS#GT06SEL=2"
```

### LT32ProDeviceReader

```python
class LT32ProDeviceReader:
    """Reads configuration from LT32Pro device."""
    
    def read_device_configuration(self, progress_callback=None) -> Dict[str, str]:
        """Read all configuration parameters from device."""
        # Commands to execute:
        # - ATSMS:STATUS#
        # - ATSMS:APN#
        # - ATSMS:SERVER#
        # - ATSMS:CXCS#IMEI
        # - ATSMS:CXCS#ICCID
        # - ATSMS:CXCS#GT06SEL
        # - ATSMS:CXCS#POSBYACK
        # - ATSMS:VERSION#
    
    def read_single_parameter(self, command: str, timeout: int = 5) -> str:
        """Read a single parameter with proper error handling."""
```

### LT32ProDeviceWriter

```python
class LT32ProDeviceWriter:
    """Writes configuration to LT32Pro device."""
    
    def write_device_configuration(self, parameters: Dict[str, str], progress_callback=None) -> Dict[str, bool]:
        """Write configuration parameters to device."""
        # Commands to execute based on parameters:
        # - ATSMS:APN,server,user,password#
        # - ATSMS:SERVER,0,ip,port,0#
        # - ATSMS:SZCS#GT06SEL=value
        # - ATSMS:SZCS#POSBYACK=value
    
    def write_single_parameter(self, command: str, value: str, timeout: int = 10) -> bool:
        """Write a single parameter with response validation."""
```

### EnhancedParameterExtractor

```python
class EnhancedParameterExtractor:
    """Extracts individual parameters from LT32Pro device responses."""
    
    def extract_parameters_from_responses(self, device_responses: Dict[str, str]) -> Dict[str, str]:
        """Convert device responses to individual parameters."""
        # Parsing rules:
        # "APN:internet,user,pass" -> apn_server, apn_user, apn_password
        # "SERVER:0,192.168.1.1,8080,0" -> server_ip, server_port, server_type
        # "READOK: IMEI=123456789" -> device_imei, device_id, imei
        # "READOK: GT06SEL=2" -> protocol, protocol_name (2->CRX)
    
    def add_default_parameters(self, parameters: Dict[str, str]) -> Dict[str, str]:
        """Add default values for commonly required parameters."""
```

## Data Models

### Device Response Formats

Based on LT32Pro manual, expected response formats:

```
APN Response: "APN:internet,user,password"
SERVER Response: "SERVER:0,192.168.1.1,8080,0"
IMEI Response: "READOK: IMEI=864943044534994"
ICCID Response: "READOK: ICCID=89550531150026587260"
Protocol Response: "READOK: GT06SEL=2"
TCP ACK Response: "READOK: POSBYACK=0"
Status Response: "Battery:4.14V;GPRS:Online;GSM Signal Level:31;ACC:ON;GPS:Successful positioning"
Version Response: "LT32Pro_10F8A_B53_V6.56 2025-06-26"
```

### Profile File Format

Enhanced profile format with individual parameters:

```
[Device_Parameters]
# Network Configuration
apn_server=internet
apn_user=user
apn_password=password
server_ip=192.168.1.1
server_port=8080
server_type=0

# Device Information
device_imei=864943044534994
device_iccid=89550531150026587260
device_version=LT32Pro_10F8A_B53_V6.56 2025-06-26

# Communication Settings
protocol=2
protocol_name=CRX
tcp_ack=0

# Default Values
heartbeat_interval=300
report_interval=60
timezone=0
device_name=LT32Pro_4994
```

## Error Handling

### Error Categories

1. **Connection Errors** - Device not connected, COM port issues
2. **Communication Errors** - Command timeout, invalid responses
3. **Protocol Errors** - Incorrect command format, unsupported commands
4. **Validation Errors** - Invalid parameter values, missing required parameters
5. **File Errors** - Profile file read/write issues

### Error Recovery Strategies

```python
class LT32ProErrorHandler:
    """Handles LT32Pro specific errors with recovery strategies."""
    
    def handle_communication_timeout(self, command: str, attempt: int) -> bool:
        """Handle command timeout with exponential backoff."""
        # Retry with increasing delays: 1s, 2s, 4s, 8s
    
    def handle_invalid_response(self, command: str, response: str) -> str:
        """Handle invalid device responses."""
        # Log the issue, attempt to parse partial data
    
    def handle_device_error_response(self, command: str, error: str) -> bool:
        """Handle device error responses."""
        # Parse device error codes, provide user-friendly messages
```

## Testing Strategy

### Unit Tests

1. **Command Formatting Tests**
   - Test ATSMS prefix addition
   - Test command syntax validation
   - Test parameter encoding

2. **Parameter Extraction Tests**
   - Test parsing of all response formats
   - Test default value addition
   - Test error handling for malformed responses

3. **Communication Tests**
   - Mock device communication
   - Test timeout handling
   - Test retry logic

### Integration Tests

1. **Device Communication Tests**
   - Test with real LT32Pro device on COM14
   - Test complete read/write cycles
   - Test error scenarios

2. **Profile Operation Tests**
   - Test load profile from device
   - Test send profile to device
   - Test profile file validation

### Test Data

Use real device responses from LT32Pro manual:
- APN:allcom.br,allcom,allcom2
- SERVER:0,3.216.82.119,8841,0
- READOK: IMEI=864943044534994
- READOK: GT06SEL=2

## Implementation Approach

### Phase 1: Command Formatting
- Implement LT32ProCommandFormatter
- Add ATSMS prefix to all commands
- Test command format validation

### Phase 2: Device Communication
- Implement LT32ProDeviceReader
- Implement LT32ProDeviceWriter
- Add proper timeout and retry logic

### Phase 3: Parameter Extraction
- Implement EnhancedParameterExtractor
- Add parsing for all response formats
- Test with real device responses

### Phase 4: Integration
- Update existing profile managers to use new components
- Add comprehensive error handling
- Implement progress tracking

### Phase 5: Testing and Validation
- Test with real device on COM14
- Validate profile operations end-to-end
- Performance optimization