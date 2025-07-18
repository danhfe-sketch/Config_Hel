import tkinter as tk
import customtkinter as ctk
import json
import os
from services.i18n_service import I18nService
from services.validation_service import ValidationService, ValidationResult

class ValidationLocalizationTest(ctk.CTk):
    """Test application for verifying validation error message localization."""
    
    def __init__(self):
        super().__init__()
        
        self.title("Validation Error Message Localization Test")
        self.geometry("1000x700")
        
        # Initialize I18n service
        self.i18n = I18nService()
        
        # Initialize ValidationService
        self.validation_service = ValidationService(self.i18n)
        
        # Create UI
        self.create_ui()
        
    def create_ui(self):
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Language selection
        lang_frame = ctk.CTkFrame(main_frame)
        lang_frame.pack(fill="x", padx=10, pady=10)
        
        lang_label = ctk.CTkLabel(lang_frame, text="Select Language:")
        lang_label.pack(side="left", padx=10)
        
        self.lang_var = tk.StringVar(value="en_US")
        
        # Language radio buttons
        en_radio = ctk.CTkRadioButton(
            lang_frame, 
            text="English", 
            variable=self.lang_var, 
            value="en_US",
            command=self.change_language
        )
        en_radio.pack(side="left", padx=10)
        
        pt_radio = ctk.CTkRadioButton(
            lang_frame, 
            text="Português", 
            variable=self.lang_var, 
            value="pt_BR",
            command=self.change_language
        )
        pt_radio.pack(side="left", padx=10)
        
        es_radio = ctk.CTkRadioButton(
            lang_frame, 
            text="Español", 
            variable=self.lang_var, 
            value="es_ES",
            command=self.change_language
        )
        es_radio.pack(side="left", padx=10)
        
        # Create scrollable frame for test sections
        self.scroll_frame = ctk.CTkScrollableFrame(main_frame)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create validation test sections
        self.create_validation_test_sections()
        
    def create_validation_test_sections(self):
        # Create sections for different validation error types
        self.create_numeric_validation_section()
        self.create_text_validation_section()
        self.create_selection_validation_section()
        self.create_special_validation_section()
        self.create_profile_validation_section()
        
    def create_numeric_validation_section(self):
        # Create section for numeric validation errors
        section_frame = self.create_section_frame("Numeric Validation Errors")
        
        # Test cases for numeric validation
        test_cases = [
            {
                "name": "Integer Required",
                "param": "vibration",
                "value": "12.5",
                "expected_code": "INTEGER_REQUIRED"
            },
            {
                "name": "Below Minimum",
                "param": "sensitivity",
                "value": "0",
                "expected_code": "MIN_VALUE"
            },
            {
                "name": "Above Maximum",
                "param": "vibration",
                "value": "300",
                "expected_code": "MAX_VALUE"
            },
            {
                "name": "Range Error",
                "param": "timer_ign_on",
                "value": "0",
                "expected_code": "RANGE_ERROR"
            },
            {
                "name": "Not Numeric",
                "param": "speed_limit",
                "value": "abc",
                "expected_code": "NUMERIC_REQUIRED"
            }
        ]
        
        self.add_test_cases(section_frame, test_cases)
        
    def create_text_validation_section(self):
        # Create section for text validation errors
        section_frame = self.create_section_frame("Text Validation Errors")
        
        # Test cases for text validation
        test_cases = [
            {
                "name": "Required Field",
                "param": "apn_server",
                "value": "",
                "expected_code": "REQUIRED_FIELD"
            },
            {
                "name": "Min Length",
                "param": "imei",
                "value": "12345",
                "expected_code": "MIN_LENGTH"
            },
            {
                "name": "Max Length",
                "param": "apn_server",
                "value": "a" * 60,
                "expected_code": "MAX_LENGTH"
            },
            {
                "name": "Invalid IMEI",
                "param": "imei",
                "value": "12345abcde12345",
                "expected_code": "INVALID_IMEI"
            },
            {
                "name": "Invalid ICCID",
                "param": "iccid",
                "value": "123456",
                "expected_code": "INVALID_ICCID"
            },
            {
                "name": "Invalid APN",
                "param": "apn_server",
                "value": "invalid@apn",
                "expected_code": "INVALID_APN"
            }
        ]
        
        self.add_test_cases(section_frame, test_cases)
        
    def create_selection_validation_section(self):
        # Create section for selection validation errors
        section_frame = self.create_section_frame("Selection Validation Errors")
        
        # Test cases for selection validation
        test_cases = [
            {
                "name": "Invalid Selection",
                "param": "heartbeat_interval",
                "value": "2min",
                "expected_code": "INVALID_SELECTION"
            },
            {
                "name": "Invalid Radio Selection",
                "param": "lock_type",
                "value": "Password",
                "expected_code": "INVALID_SELECTION"
            }
        ]
        
        self.add_test_cases(section_frame, test_cases)
        
    def create_special_validation_section(self):
        # Create section for special validation errors
        section_frame = self.create_section_frame("Special Validation Errors")
        
        # Test cases for special validation
        test_cases = [
            {
                "name": "Invalid IP",
                "param": "server_ip",
                "value": "192.168.1",
                "expected_code": "INVALID_IP"
            },
            {
                "name": "Invalid Domain",
                "param": "server_domain",
                "value": "-invalid.com",
                "expected_code": "INVALID_DOMAIN"
            },
            {
                "name": "Invalid Phone",
                "param": "phone_number",
                "value": "123abc456",
                "expected_code": "INVALID_PHONE"
            },
            {
                "name": "Phone Too Short",
                "param": "phone_number",
                "value": "123",
                "expected_code": "PHONE_TOO_SHORT"
            },
            {
                "name": "Phone Too Long",
                "param": "phone_number",
                "value": "1234567890123456789",
                "expected_code": "PHONE_TOO_LONG"
            },
            {
                "name": "Unknown Parameter",
                "param": "nonexistent_param",
                "value": "test",
                "expected_code": "UNKNOWN_PARAMETER"
            }
        ]
        
        self.add_test_cases(section_frame, test_cases)
        
    def create_profile_validation_section(self):
        # Create section for profile validation errors
        section_frame = self.create_section_frame("Profile Validation Errors")
        
        # Test cases for profile validation
        test_cases = [
            {
                "name": "Invalid Profile Format",
                "param": "profile_format",
                "value": "not_a_dict",
                "expected_code": "INVALID_PROFILE_FORMAT",
                "custom_test": "profile_format"
            },
            {
                "name": "Missing Profile Section",
                "param": "missing_section",
                "value": {},
                "expected_code": "MISSING_PROFILE_SECTION",
                "custom_test": "missing_section"
            },
            {
                "name": "Profile Validation Errors",
                "param": "profile_errors",
                "value": {"version": "1.0", "apn_config": {"server": ""}},
                "expected_code": "PROFILE_VALIDATION_ERRORS",
                "custom_test": "profile_errors"
            }
        ]
        
        self.add_test_cases(section_frame, test_cases)
        
    def create_section_frame(self, title):
        # Create a section with a title
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.pack(fill="x", padx=5, pady=10)
        
        # Section title
        title_label = ctk.CTkLabel(
            section_frame, 
            text=title, 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(anchor="w", padx=10, pady=5)
        
        return section_frame
        
    def add_test_cases(self, section_frame, test_cases):
        # Create a grid for test cases
        grid_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=5)
        
        # Add header
        headers = ["Test Case", "Parameter", "Value", "Error Code", "Error Message"]
        for i, header in enumerate(headers):
            header_label = ctk.CTkLabel(
                grid_frame, 
                text=header, 
                font=ctk.CTkFont(weight="bold")
            )
            header_label.grid(row=0, column=i, padx=5, pady=5, sticky="w")
        
        # Add test cases
        for i, test_case in enumerate(test_cases, 1):
            # Test name
            name_label = ctk.CTkLabel(grid_frame, text=test_case["name"])
            name_label.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            
            # Parameter name
            param_label = ctk.CTkLabel(grid_frame, text=test_case["param"])
            param_label.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            
            # Value
            value_str = str(test_case["value"])
            if len(value_str) > 20:
                value_str = value_str[:17] + "..."
            value_label = ctk.CTkLabel(grid_frame, text=value_str)
            value_label.grid(row=i, column=2, padx=5, pady=2, sticky="w")
            
            # Error code
            code_label = ctk.CTkLabel(grid_frame, text=test_case["expected_code"])
            code_label.grid(row=i, column=3, padx=5, pady=2, sticky="w")
            
            # Error message (will be updated with translations)
            error_label = ctk.CTkLabel(grid_frame, text="", wraplength=400)
            error_label.grid(row=i, column=4, padx=5, pady=2, sticky="w")
            
            # Store reference to error label and test case
            test_case["label"] = error_label
        
        # Store test cases for updating
        if not hasattr(self, "test_cases"):
            self.test_cases = []
        self.test_cases.extend(test_cases)
    
    def update_error_messages(self):
        # Update all error messages based on current language
        for test_case in self.test_cases:
            error_message = self.get_error_message(test_case)
            test_case["label"].configure(text=error_message)
    
    def get_error_message(self, test_case):
        # Get error message for a test case
        if "custom_test" in test_case:
            if test_case["custom_test"] == "profile_format":
                return self.validation_service.validate_profile_data("not_a_dict").error_message
            elif test_case["custom_test"] == "missing_section":
                return self.validation_service.validate_profile_data({}).error_message
            elif test_case["custom_test"] == "profile_errors":
                return self.validation_service.validate_profile_data(
                    {"version": "1.0", "apn_config": {"server": ""}}
                ).error_message
        else:
            result = self.validation_service.validate_parameter(
                test_case["param"], test_case["value"]
            )
            return result.error_message
    
    def change_language(self):
        # Change language and update all error messages
        language = self.lang_var.get()
        self.i18n.set_language(language)
        
        # Recreate validation service with new language
        self.validation_service = ValidationService(self.i18n)
        
        # Update all error messages
        self.update_error_messages()
        
        # Update window title
        self.title(f"Validation Error Message Localization Test - {language}")

if __name__ == "__main__":
    app = ValidationLocalizationTest()
    app.mainloop()