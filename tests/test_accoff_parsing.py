import pytest
from services.device_command_mapper import DeviceCommandMapper

def test_parse_bare_accoffalm_comma_response():
    mapper = DeviceCommandMapper()
    response = "ACCOFFALM,OFF"
    parsed = mapper.parse_device_response(response, command_type="get_acc_off_alert")
    assert isinstance(parsed, dict)
    # Our tolerant parser should capture parameter name and value
    assert parsed.get("parameter") in ("ACCOFFALM", "ACCOFFALM".upper())
    assert parsed.get("value") == "OFF"
    assert parsed.get("status") == "success" or parsed.get("status") == "ok" or "success" in parsed.get("status", "")

def test_parse_bare_accoffalm_space_response():
    mapper = DeviceCommandMapper()
    response = "ACCOFFALM OFF"
    parsed = mapper.parse_device_response(response, command_type="get_acc_off_alert")
    assert parsed.get("parameter") == "ACCOFFALM"
    assert parsed.get("value") == "OFF"
    assert parsed.get("status") == "success" or parsed.get("status") == "ok" or "success" in parsed.get("status", "")

def test_parse_bare_accoffalm_colon_response():
    mapper = DeviceCommandMapper()
    response = "ACCOFFALM:ON,1"
    parsed = mapper.parse_device_response(response, command_type="get_acc_off_alert")
    # Should capture ON numeric/state correctly
    assert parsed.get("parameter") == "ACCOFFALM"
    assert parsed.get("value") in ("ON", "1")
    assert parsed.get("status") == "success" or parsed.get("status") == "ok" or "success" in parsed.get("status", "")