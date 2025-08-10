"""
Simple Device Progress Dialog - Simplified progress dialog for device operations.

This module provides a clean, simple progress dialog for device parameter loading
with proper internationalization support.
"""

import customtkinter as ctk
import threading
import time
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SimpleProgressInfo:
    """Simple progress information for device operations."""
    operation_type: str      # 'device_to_profile', 'profile_to_device'
    current_step: int        # Current step (1-4)
    total_steps: int         # Total steps (4)
    step_name: str          # Localized step name
    status_message: str     # Localized status message
    progress_percentage: float  # Progress percentage (0-100)
    
    # Parameter-based progress tracking
    current_parameter: int = 0    # Current parameter being processed
    total_parameters: int = 0     # Total parameters to process
    parameter_name: str = ""      # Name of current parameter
    
    is_complete: bool = False
    is_cancelled: bool = False
    has_error: bool = False
    error_message: str = ""


class SimpleDeviceProgressDialog:
    """Simple, clean progress dialog for device operations."""
    
    def __init__(self, parent, i18n_service, operation_type: str = "device_operation"):
        self.parent = parent
        self.i18n = i18n_service
        self.operation_type = operation_type
        self.is_cancelled = False
        self.is_destroying = False
        self.cancel_callback = None
        self.last_update_time = time.time()
        self.timeout_seconds = 300  # 5 minutes timeout
        
        # Create dialog window
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(self._get_dialog_title())
        self.dialog.geometry("450x200")
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self._center_dialog()
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create UI elements
        self._create_ui()
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Start timeout monitoring
        self._check_timeout()
        
    def _get_dialog_title(self) -> str:
        """Get localized dialog title based on operation type."""
        titles = {
            'device_to_profile': self.i18n.get('device_to_profile_title', 'Salvando Configuração do Dispositivo'),
            'profile_to_device': self.i18n.get('profile_to_device_title', 'Carregando Configuração para Dispositivo'),
            'device_operation': self.i18n.get('device_operation_title', 'Operação do Dispositivo')
        }
        return titles.get(self.operation_type, titles['device_operation'])
        
    def _center_dialog(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        
        # Get parent window position and size
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calculate center position
        dialog_width = 450
        dialog_height = 200
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
    def _create_ui(self):
        """Create the simplified UI elements."""
        # Main container
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Operation title
        self.title_label = ctk.CTkLabel(
            main_frame,
            text=self._get_operation_title(),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title_label.pack(pady=(0, 15))
        
        # Status message
        self.status_label = ctk.CTkLabel(
            main_frame,
            text=self.i18n.get('initializing', 'Inicializando...'),
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(main_frame, width=350)
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.set(0)
        
        # Progress percentage label
        self.percentage_label = ctk.CTkLabel(
            main_frame,
            text="0%",
            font=ctk.CTkFont(size=11)
        )
        self.percentage_label.pack(pady=(0, 15))
        
        # Cancel button
        self.cancel_button = ctk.CTkButton(
            main_frame,
            text=self.i18n.get('cancel', 'Cancelar'),
            command=self._on_cancel,
            width=100,
            fg_color="gray",
            hover_color="darkgray"
        )
        self.cancel_button.pack()
        
    def _get_operation_title(self) -> str:
        """Get localized operation title."""
        titles = {
            'device_to_profile': self.i18n.get('saving_device_config', 'Salvando Configuração do Dispositivo'),
            'profile_to_device': self.i18n.get('loading_config_to_device', 'Carregando Configuração para Dispositivo'),
            'device_operation': self.i18n.get('device_operation', 'Operação do Dispositivo')
        }
        return titles.get(self.operation_type, titles['device_operation'])
        
    def update_progress(self, progress_info: SimpleProgressInfo):
        """Update the progress dialog with new information."""
        try:
            # Check if dialog is being destroyed
            if self.is_destroying:
                return
                
            # Update last activity time
            self.last_update_time = time.time()
                
            # Multiple safety checks to prevent widget access after destruction
            if not hasattr(self, 'dialog') or self.dialog is None:
                return
                
            if not self.dialog.winfo_exists():
                return
                
            # Check if widgets still exist before updating
            if not hasattr(self, 'status_label') or not hasattr(self, 'progress_bar') or not hasattr(self, 'percentage_label'):
                return
                
            # Create enhanced status message with parameter info
            status_message = progress_info.status_message
            if progress_info.total_parameters > 0 and progress_info.current_parameter > 0:
                if progress_info.parameter_name:
                    status_message = f"{status_message}\n{progress_info.parameter_name} ({progress_info.current_parameter}/{progress_info.total_parameters})"
                else:
                    status_message = f"{status_message}\nParâmetro {progress_info.current_parameter}/{progress_info.total_parameters}"
            
            # Update status message with safety check
            try:
                if hasattr(self.status_label, 'configure'):
                    self.status_label.configure(text=status_message)
            except Exception:
                pass
            
            # Update progress bar with safety check
            try:
                if hasattr(self.progress_bar, 'set'):
                    progress_value = progress_info.progress_percentage / 100.0
                    self.progress_bar.set(progress_value)
            except Exception:
                pass
            
            # Update percentage label with parameter info and safety check
            try:
                if hasattr(self.percentage_label, 'configure'):
                    percentage_text = f"{int(progress_info.progress_percentage)}%"
                    if progress_info.total_parameters > 0:
                        percentage_text += f" ({progress_info.current_parameter}/{progress_info.total_parameters})"
                    self.percentage_label.configure(text=percentage_text)
            except Exception:
                pass
            
            # Handle completion
            if progress_info.is_complete:
                if progress_info.has_error:
                    self._show_error(progress_info.error_message)
                else:
                    self._show_success()
                    
        except Exception as e:
            # Dialog may have been closed, ignore all errors to prevent crashes
            pass
            
    def _show_success(self):
        """Show success state."""
        try:
            if hasattr(self, 'status_label') and hasattr(self.status_label, 'configure'):
                self.status_label.configure(text=self.i18n.get('operation_completed', 'Operação concluída com sucesso!'))
        except Exception:
            pass
            
        try:
            if hasattr(self, 'cancel_button') and hasattr(self.cancel_button, 'configure'):
                self.cancel_button.configure(
                    text=self.i18n.get('close', 'Fechar'),
                    fg_color="green",
                    hover_color="darkgreen"
                )
        except Exception:
            pass
        
    def _show_error(self, error_message: str):
        """Show error state."""
        try:
            if hasattr(self, 'status_label') and hasattr(self.status_label, 'configure'):
                self.status_label.configure(text=f"{self.i18n.get('operation_failed', 'Operação falhou')}: {error_message}")
        except Exception:
            pass
            
        try:
            if hasattr(self, 'cancel_button') and hasattr(self.cancel_button, 'configure'):
                self.cancel_button.configure(
                    text=self.i18n.get('close', 'Fechar'),
                    fg_color="red",
                    hover_color="darkred"
                )
        except Exception:
            pass
        
    def set_cancel_callback(self, callback: Callable):
        """Set callback function for cancel operation."""
        self.cancel_callback = callback
        
    def _on_cancel(self):
        """Handle cancel button click."""
        if self.cancel_callback and not self.is_cancelled:
            self.is_cancelled = True
            self.cancel_callback()
            
        self._close_dialog()
        
    def _on_close(self):
        """Handle window close event."""
        self._on_cancel()
        
    def _close_dialog(self):
        """Close the dialog safely."""
        # Set flag to prevent further updates
        self.is_destroying = True
        
        try:
            if hasattr(self, 'dialog') and self.dialog is not None:
                if self.dialog.winfo_exists():
                    self.dialog.grab_release()
                    self.dialog.destroy()
                self.dialog = None
        except Exception:
            pass
        
        # Clear widget references to prevent further access
        try:
            self.status_label = None
            self.progress_bar = None
            self.percentage_label = None
            self.cancel_button = None
        except Exception:
            pass
            
    def show(self):
        """Show the dialog."""
        try:
            if hasattr(self, 'dialog') and self.dialog is not None and self.dialog.winfo_exists():
                self.dialog.deiconify()
                self.dialog.lift()
                self.dialog.focus()
        except Exception:
            pass
        
    def hide(self):
        """Hide the dialog."""
        try:
            if hasattr(self, 'dialog') and self.dialog is not None and self.dialog.winfo_exists():
                self.dialog.withdraw()
        except Exception:
            pass
            
    def close(self):
        """Close the dialog."""
        self._close_dialog()
        
    def _check_timeout(self):
        """Check for timeout and close dialog if stuck."""
        try:
            if self.is_destroying:
                return
                
            if not hasattr(self, 'dialog') or self.dialog is None or not self.dialog.winfo_exists():
                return
                
            # Check if dialog has been inactive for too long
            current_time = time.time()
            if current_time - self.last_update_time > self.timeout_seconds:
                # Dialog has been stuck, close it
                self._close_dialog()
                return
                
            # Schedule next timeout check
            self.dialog.after(10000, self._check_timeout)  # Check every 10 seconds
            
        except Exception:
            # If there's any error, just close the dialog
            self._close_dialog()


def create_simple_progress_dialog(parent, i18n_service, operation_type: str = "device_operation") -> SimpleDeviceProgressDialog:
    """Factory function to create a simple progress dialog."""
    return SimpleDeviceProgressDialog(parent, i18n_service, operation_type)


# Utility functions for common progress updates
def create_device_to_profile_progress(step: int, total_steps: int, i18n_service, 
                                     current_parameter: int = 0, total_parameters: int = 0,
                                     parameter_name: str = "") -> SimpleProgressInfo:
    """Create progress info for device-to-profile operation with parameter-based progress."""
    # Simplified messages focused on parameter reading
    if total_parameters > 0 and current_parameter > 0:
        step_messages = {
            1: i18n_service.get('reading_parameters', 'Lendo parâmetros do dispositivo...'),
            2: i18n_service.get('reading_parameters', 'Lendo parâmetros do dispositivo...'),
            3: i18n_service.get('processing_parameters', 'Processando parâmetros...'),
            4: i18n_service.get('saving_profile', 'Salvando perfil...')
        }
    else:
        step_messages = {
            1: i18n_service.get('initializing', 'Inicializando...'),
            2: i18n_service.get('reading_parameters', 'Lendo parâmetros do dispositivo...'),
            3: i18n_service.get('creating_profile', 'Criando arquivo de perfil...'),
            4: i18n_service.get('saving_profile', 'Salvando perfil...')
        }
    
    step_names = {
        1: i18n_service.get('step_connecting', 'Conexão'),
        2: i18n_service.get('step_reading', 'Leitura'),
        3: i18n_service.get('step_creating', 'Criação'),
        4: i18n_service.get('step_saving', 'Salvamento')
    }
    
    # Calculate progress purely based on parameters read
    if total_parameters > 0:
        # Pure parameter-based progress (0-100% based on parameters read)
        progress_percentage = (current_parameter / total_parameters) * 100
    else:
        # Fallback to step-based if no parameter info available
        progress_percentage = (step / total_steps) * 100
    
    return SimpleProgressInfo(
        operation_type='device_to_profile',
        current_step=step,
        total_steps=total_steps,
        step_name=step_names.get(step, f'Passo {step}'),
        status_message=step_messages.get(step, f'Executando passo {step}...'),
        progress_percentage=min(progress_percentage, 100),
        current_parameter=current_parameter,
        total_parameters=total_parameters,
        parameter_name=parameter_name
    )


def create_profile_to_device_progress(step: int, total_steps: int, i18n_service,
                                     current_parameter: int = 0, total_parameters: int = 0,
                                     parameter_name: str = "") -> SimpleProgressInfo:
    """Create progress info for profile-to-device operation with parameter-based progress."""
    # Simplified messages focused on parameter deployment
    if total_parameters > 0 and current_parameter > 0:
        step_messages = {
            1: i18n_service.get('preparing_deployment', 'Preparando envio...'),
            2: i18n_service.get('validating_profile', 'Validando configuração...'),
            3: i18n_service.get('deploying_parameters', 'Enviando parâmetros para dispositivo...'),
            4: i18n_service.get('finalizing', 'Finalizando...')
        }
    else:
        step_messages = {
            1: i18n_service.get('loading_profile', 'Carregando arquivo de perfil...'),
            2: i18n_service.get('validating_profile', 'Validando configuração...'),
            3: i18n_service.get('deploying_to_device', 'Enviando para dispositivo...'),
            4: i18n_service.get('updating_interface', 'Atualizando interface...')
        }
    
    step_names = {
        1: i18n_service.get('step_loading', 'Carregamento'),
        2: i18n_service.get('step_validation', 'Validação'),
        3: i18n_service.get('step_deployment', 'Envio'),
        4: i18n_service.get('step_update', 'Atualização')
    }
    
    # Calculate progress purely based on parameters processed
    if total_parameters > 0:
        # Pure parameter-based progress (0-100% based on parameters processed)
        progress_percentage = (current_parameter / total_parameters) * 100
    else:
        # Fallback to step-based if no parameter info available
        progress_percentage = (step / total_steps) * 100
    
    return SimpleProgressInfo(
        operation_type='profile_to_device',
        current_step=step,
        total_steps=total_steps,
        step_name=step_names.get(step, f'Passo {step}'),
        status_message=step_messages.get(step, f'Executando passo {step}...'),
        progress_percentage=min(progress_percentage, 100),
        current_parameter=current_parameter,
        total_parameters=total_parameters,
        parameter_name=parameter_name
    )