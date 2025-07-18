#!/usr/bin/env python3
"""
Debug script to identify radio button responsiveness issues.
"""

import customtkinter as ctk
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from ui.parameter_factory import ParameterFactory

class RadioDebugApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Radio Button Debug - Tipo de Ignição")
        self.geometry("800x600")
        
        # Initialize services
        self.i18n = I18nService()
        self.i18n.set_language('pt_BR')
        self.validation_service = ValidationService(self.i18n)
        
        def log_command(command):
            print(f"Command would be sent: {command}")
            self.log_text.insert(ctk.END, f"Command: {command}\n")
        
        # Create parameter factory
        self.factory = ParameterFactory(self.validation_service, self.i18n, log_command)
        
        # Create layout
        self.create_layout()
        
        # Create both factory-based and manual radio buttons for comparison
        self.create_comparison_widgets()
    
    def create_layout(self):
        """Create the main layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        
        # Main scrollable frame
        self.main_frame = ctk.CTkScrollableFrame(self, label_text="Radio Button Comparison")
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Log frame
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        
        log_label = ctk.CTkLabel(self.log_frame, text="Activity Log:", font=ctk.CTkFont(weight="bold"))
        log_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.log_text = ctk.CTkTextbox(self.log_frame, height=100)
        self.log_text.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
    
    def create_comparison_widgets(self):
        """Create both factory-based and manual radio buttons for comparison."""
        
        # Factory-based radio buttons
        factory_frame = ctk.CTkFrame(self.main_frame)
        factory_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        factory_frame.grid_columnconfigure(0, weight=1)
        
        factory_title = ctk.CTkLabel(factory_frame, text="Factory-based Radio Buttons (ignition_type)", 
                                   font=ctk.CTkFont(size=16, weight="bold"))
        factory_title.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Create ignition_type parameter
        self.ignition_param = self.factory.create_parameter('ignition_type')
        if self.ignition_param:
            self.ignition_widget = self.ignition_param.create_widget(factory_frame)
            self.ignition_widget.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
            
            # Test buttons for factory widget
            factory_test_frame = ctk.CTkFrame(factory_frame)
            factory_test_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
            
            ctk.CTkButton(factory_test_frame, text="Get Value", 
                         command=self.test_factory_get_value).grid(row=0, column=0, padx=5, pady=5)
            ctk.CTkButton(factory_test_frame, text="Set Digital", 
                         command=lambda: self.test_factory_set_value("Digital")).grid(row=0, column=1, padx=5, pady=5)
            ctk.CTkButton(factory_test_frame, text="Set Analog", 
                         command=lambda: self.test_factory_set_value("Analog")).grid(row=0, column=2, padx=5, pady=5)
            ctk.CTkButton(factory_test_frame, text="Send Command", 
                         command=self.test_factory_send_command).grid(row=0, column=3, padx=5, pady=5)
        
        # Manual radio buttons for comparison
        manual_frame = ctk.CTkFrame(self.main_frame)
        manual_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        manual_frame.grid_columnconfigure(0, weight=1)
        
        manual_title = ctk.CTkLabel(manual_frame, text="Manual Radio Buttons (for comparison)", 
                                  font=ctk.CTkFont(size=16, weight="bold"))
        manual_title.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Manual radio button implementation
        manual_radio_frame = ctk.CTkFrame(manual_frame)
        manual_radio_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        manual_radio_frame.grid_columnconfigure(1, weight=1)
        
        manual_label = ctk.CTkLabel(manual_radio_frame, text="Tipo de Ignição:")
        manual_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Manual radio variable
        self.manual_radio_var = ctk.StringVar(value="Digital")
        
        # Manual radio buttons container
        manual_buttons_frame = ctk.CTkFrame(manual_radio_frame)
        manual_buttons_frame.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.manual_digital_radio = ctk.CTkRadioButton(
            manual_buttons_frame, 
            text="Digital", 
            variable=self.manual_radio_var, 
            value="Digital",
            command=self.on_manual_radio_change
        )
        self.manual_digital_radio.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.manual_analog_radio = ctk.CTkRadioButton(
            manual_buttons_frame, 
            text="Analógico", 
            variable=self.manual_radio_var, 
            value="Analog",
            command=self.on_manual_radio_change
        )
        self.manual_analog_radio.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Manual send button
        manual_send_btn = ctk.CTkButton(
            manual_radio_frame,
            text="Enviar",
            width=60,
            command=self.send_manual_command
        )
        manual_send_btn.grid(row=0, column=2, padx=(5, 10), pady=5)
        
        # Test buttons for manual widget
        manual_test_frame = ctk.CTkFrame(manual_frame)
        manual_test_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(manual_test_frame, text="Get Manual Value", 
                     command=self.test_manual_get_value).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkButton(manual_test_frame, text="Set Manual Digital", 
                     command=lambda: self.test_manual_set_value("Digital")).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(manual_test_frame, text="Set Manual Analog", 
                     command=lambda: self.test_manual_set_value("Analog")).grid(row=0, column=2, padx=5, pady=5)
    
    def test_factory_get_value(self):
        """Test getting value from factory radio buttons."""
        if self.ignition_param:
            value = self.ignition_param.get_value()
            self.log_text.insert(ctk.END, f"Factory get_value(): {value}\n")
            print(f"Factory get_value(): {value}")
    
    def test_factory_set_value(self, value):
        """Test setting value in factory radio buttons."""
        if self.ignition_param:
            self.ignition_param.set_value(value)
            self.log_text.insert(ctk.END, f"Factory set_value({value})\n")
            print(f"Factory set_value({value})")
    
    def test_factory_send_command(self):
        """Test sending command from factory radio buttons."""
        if self.ignition_param:
            self.ignition_param.send_command()
            self.log_text.insert(ctk.END, f"Factory send_command() triggered\n")
            print(f"Factory send_command() triggered")
    
    def test_manual_get_value(self):
        """Test getting value from manual radio buttons."""
        value = self.manual_radio_var.get()
        self.log_text.insert(ctk.END, f"Manual get_value(): {value}\n")
        print(f"Manual get_value(): {value}")
    
    def test_manual_set_value(self, value):
        """Test setting value in manual radio buttons."""
        self.manual_radio_var.set(value)
        self.log_text.insert(ctk.END, f"Manual set_value({value})\n")
        print(f"Manual set_value({value})")
    
    def on_manual_radio_change(self):
        """Handle manual radio button change."""
        value = self.manual_radio_var.get()
        self.log_text.insert(ctk.END, f"Manual radio changed to: {value}\n")
        print(f"Manual radio changed to: {value}")
    
    def send_manual_command(self):
        """Send command from manual radio buttons."""
        value = self.manual_radio_var.get()
        command = f"ATSMS:SZCS#ACCLINE={value}#"
        self.log_text.insert(ctk.END, f"Manual command: {command}\n")
        print(f"Manual command: {command}")

def main():
    """Run the radio button debug app."""
    print("Starting Radio Button Debug...")
    app = RadioDebugApp()
    app.mainloop()

if __name__ == "__main__":
    main()