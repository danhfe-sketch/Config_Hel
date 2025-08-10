"""
Ultra Simple Progress Dialog - Minimal, crash-resistant progress dialog.

This is a simplified version that avoids complex widget management and threading issues.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class UltraSimpleProgressInfo:
    """Ultra simple progress information."""
    progress_percentage: float = 0.0
    status_message: str = ""
    current_parameter: int = 0
    total_parameters: int = 0
    is_complete: bool = False
    has_error: bool = False
    error_message: str = ""


class UltraSimpleProgressDialog:
    """Ultra simple, crash-resistant progress dialog using basic Tkinter."""
    
    def __init__(self, parent, operation_type: str = "device_operation"):
        self.parent = parent
        self.operation_type = operation_type
        self.is_cancelled = False
        self.is_closed = False
        self.cancel_callback = None
        self.dialog = None
        
        # Create dialog in main thread
        self._create_dialog()
        
    def _create_dialog(self):
        """Create the ultra simple dialog matching application style."""
        try:
            # Create toplevel window
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("Operação do Dispositivo")
            self.dialog.geometry("500x200")
            self.dialog.resizable(False, False)
            
            # Set dark theme colors to match application
            self.dialog.configure(bg='#2b2b2b')
            
            # Center the dialog
            self._center_dialog()
            
            # Make modal
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            # Create main container with padding
            main_frame = tk.Frame(self.dialog, bg='#2b2b2b', padx=30, pady=30)
            main_frame.pack(fill="both", expand=True)
            
            # Title with icon area (simplified)
            title_frame = tk.Frame(main_frame, bg='#2b2b2b')
            title_frame.pack(fill="x", pady=(0, 20))
            
            # Title label to match the application style
            title_label = tk.Label(
                title_frame,
                text="Salvando Configuração do Dispositivo" if self.operation_type == 'device_to_profile' else "Carregando Configuração para Dispositivo",
                font=("Segoe UI", 14, "bold"),
                fg='white',
                bg='#2b2b2b'
            )
            title_label.pack()
            
            # Status message
            self.status_label = tk.Label(
                main_frame,
                text="Connecting to device and reading current configuration",
                font=("Segoe UI", 10),
                fg='#cccccc',
                bg='#2b2b2b',
                wraplength=440,
                justify='center'
            )
            self.status_label.pack(pady=(0, 20))
            
            # Progress bar using simple Frame-based approach
            progress_frame = tk.Frame(main_frame, bg='#2b2b2b')
            progress_frame.pack(fill="x", pady=(0, 15))
            
            # Create progress bar container
            self.progress_container = tk.Frame(
                progress_frame,
                bg='#404040',
                height=8,
                relief='flat',
                bd=0
            )
            self.progress_container.pack(fill="x")
            
            # Create progress bar fill
            self.progress_fill = tk.Frame(
                self.progress_container,
                bg='#0078d4',
                height=8,
                relief='flat',
                bd=0
            )
            self.progress_fill.place(x=0, y=0, width=0, height=8)
            
            # Percentage label
            self.percentage_label = tk.Label(
                main_frame,
                text="0%",
                font=("Segoe UI", 11),
                fg='#cccccc',
                bg='#2b2b2b'
            )
            self.percentage_label.pack(pady=(0, 20))
            
            # Cancel button with application styling
            self.cancel_button = tk.Button(
                main_frame,
                text="Cancelar",
                command=self._on_cancel,
                font=("Segoe UI", 9),
                bg='#404040',
                fg='white',
                activebackground='#505050',
                activeforeground='white',
                relief='flat',
                borderwidth=0,
                padx=20,
                pady=8
            )
            self.cancel_button.pack()
            
            # Handle window close
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
            
        except Exception as e:
            print(f"Error creating dialog: {e}")
            self.dialog = None
            
    def _center_dialog(self):
        """Center the dialog on parent."""
        try:
            self.dialog.update_idletasks()
            
            # Get parent position and size
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            # Calculate center position
            dialog_width = 500
            dialog_height = 200
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception:
            pass
            
    def update_progress(self, progress_info: UltraSimpleProgressInfo):
        """Update progress - thread safe."""
        if self.is_closed or not self.dialog:
            return
            
        # Schedule update on main thread immediately
        try:
            self.dialog.after_idle(self._do_update, progress_info)
        except Exception:
            pass
            
    def _do_update(self, progress_info: UltraSimpleProgressInfo):
        """Perform the actual update on main thread."""
        try:
            if self.is_closed or not self.dialog:
                return
                
            # Update status message
            status_text = progress_info.status_message
            if progress_info.total_parameters > 0 and progress_info.current_parameter > 0:
                status_text += f"\nParâmetro {progress_info.current_parameter}/{progress_info.total_parameters}"
                
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.config(text=status_text)
            
            # Update progress bar
            if hasattr(self, 'progress_container') and hasattr(self, 'progress_fill'):
                # Get container width
                container_width = 440  # Fixed width for reliability
                progress_width = max(1, int((progress_info.progress_percentage / 100.0) * container_width))
                
                # Update the progress fill frame
                self.progress_fill.place(width=progress_width)
                
                # Change color based on progress
                if progress_info.progress_percentage >= 100:
                    self.progress_fill.config(bg='#00aa00')  # Green when complete
                else:
                    self.progress_fill.config(bg='#0078d4')  # Blue for progress
            
            # Update percentage label
            percentage_text = f"{int(progress_info.progress_percentage)}%"
            if hasattr(self, 'percentage_label') and self.percentage_label:
                self.percentage_label.config(text=percentage_text)
            
            # Handle completion
            if progress_info.is_complete:
                if progress_info.has_error:
                    self._show_error(progress_info.error_message)
                else:
                    self._show_success()
                    
        except Exception as e:
            print(f"Update error: {e}")
            
    def _show_success(self):
        """Show success state."""
        try:
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.config(text="Operação concluída com sucesso!")
            if hasattr(self, 'cancel_button') and self.cancel_button:
                self.cancel_button.config(text="Fechar", bg="lightgreen")
        except Exception:
            pass
            
    def _show_error(self, error_message: str):
        """Show error state."""
        try:
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.config(text=f"Operação falhou: {error_message}")
            if hasattr(self, 'cancel_button') and self.cancel_button:
                self.cancel_button.config(text="Fechar", bg="lightcoral")
        except Exception:
            pass
            
    def set_cancel_callback(self, callback: Callable):
        """Set cancel callback."""
        self.cancel_callback = callback
        
    def _on_cancel(self):
        """Handle cancel."""
        if self.cancel_callback and not self.is_cancelled:
            self.is_cancelled = True
            try:
                self.cancel_callback()
            except Exception:
                pass
        self.close()
        
    def _on_close(self):
        """Handle window close."""
        self._on_cancel()
        
    def show(self):
        """Show dialog."""
        try:
            if self.dialog and not self.is_closed:
                self.dialog.deiconify()
                self.dialog.lift()
        except Exception:
            pass
            
    def hide(self):
        """Hide dialog."""
        try:
            if self.dialog and not self.is_closed:
                self.dialog.withdraw()
        except Exception:
            pass
            
    def close(self):
        """Close dialog."""
        if self.is_closed:
            return
            
        self.is_closed = True
        
        try:
            if self.dialog:
                self.dialog.grab_release()
                self.dialog.destroy()
                self.dialog = None
        except Exception:
            pass
            
        # Clear references
        self.status_label = None
        self.progress_bar = None
        self.progress_var = None
        self.percentage_label = None
        self.cancel_button = None


def create_ultra_simple_progress_info(current_param: int, total_params: int, 
                                     status_message: str = "Processando...") -> UltraSimpleProgressInfo:
    """Create ultra simple progress info."""
    progress_percentage = (current_param / total_params * 100) if total_params > 0 else 0
    
    return UltraSimpleProgressInfo(
        progress_percentage=progress_percentage,
        status_message=status_message,
        current_parameter=current_param,
        total_parameters=total_params
    )