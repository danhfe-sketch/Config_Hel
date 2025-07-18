import customtkinter as ctk
import pyperclip
from tkinter import filedialog
import datetime
import os
import re
import time
from collections import deque

class LogFrame(ctk.CTkFrame):
    # Maximum number of log entries to keep in memory
    MAX_LOG_ENTRIES = 1000
    
    # Message type color mapping
    MESSAGE_COLORS = {
        "APP": "#4CAF50",      # Green for app commands
        "DEV": "#2196F3",      # Blue for device responses
        "INFO": "#9E9E9E",     # Gray for info messages
        "ERROR": "#F44336",    # Red for errors
        "WARNING": "#FF9800",  # Orange for warnings
        "DEBUG": "#607D8B",    # Blue-gray for debug messages
        "SYSTEM": "#9C27B0"    # Purple for system messages
    }
    
    def __init__(self, master, i18n, serial_service):
        super().__init__(master)
        self.i18n = i18n
        self.serial_service = serial_service
        
        # Use a deque to store log entries for better performance with large logs
        self.log_entries = deque(maxlen=self.MAX_LOG_ENTRIES)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Title and Actions ---
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(top_frame, text=self.i18n.get("serial_log"), font=ctk.CTkFont(weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w")

        self.copy_button = ctk.CTkButton(top_frame, text=self.i18n.get("copy_log"), width=80, command=self.copy_log)
        self.copy_button.grid(row=0, column=1, padx=5)

        self.export_button = ctk.CTkButton(top_frame, text=self.i18n.get("export_log"), width=80, command=self.export_log)
        self.export_button.grid(row=0, column=2)

        self.clear_button = ctk.CTkButton(top_frame, text=self.i18n.get("clear_log", "Clear"), width=80, command=self.clear_log)
        self.clear_button.grid(row=0, column=3, padx=5)

        # --- Log Text Area ---
        self.log_textbox = ctk.CTkTextbox(self, state="disabled", wrap="word")
        self.log_textbox.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        
        # CustomTkinter's CTkTextbox doesn't support tag_configure
        # We'll use a different approach for text coloring

        # --- Free Command Section ---
        command_frame = ctk.CTkFrame(self, fg_color="transparent")
        command_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")
        command_frame.grid_columnconfigure(1, weight=1)

        self.command_label = ctk.CTkLabel(command_frame, text=self.i18n.get("free_command"))
        self.command_label.grid(row=0, column=0, padx=(0, 5), pady=5)

        self.command_entry = ctk.CTkEntry(command_frame)
        self.command_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.command_entry.bind("<Return>", self.send_free_command)

        self.send_command_button = ctk.CTkButton(command_frame, text=self.i18n.get("send"), width=80, command=self.send_free_command)
        self.send_command_button.grid(row=0, column=2, padx=(5, 0), pady=5)
        
        # Last log update time to throttle updates for performance
        self.last_log_update = 0
        self.log_buffer = []
        self.update_interval = 100  # milliseconds

    def log_message(self, message):
        """
        Appends a message to the log text area with proper formatting and color coding.
        Uses buffering for better performance with rapid log messages.
        """
        # Store the message in the deque for history
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_entries.append((timestamp, message))
        
        # Add to buffer for batched updates
        self.log_buffer.append(message)
        
        # Immediately update for critical messages (errors, connection issues)
        if "ERROR:" in message and ("connection" in message.lower() or "disconnected" in message.lower()):
            # Force immediate update for connection errors
            self._update_log_display()
            
            # Ensure the log is visible by scrolling to the end
            self.after(10, self.log_textbox.see, "end")
            
            # Flash the log area to draw attention for connection errors
            self._flash_log_for_attention()
        else:
            # Check if we should update the display now for regular messages
            current_time = time.time() * 1000  # Convert to milliseconds
            if current_time - self.last_log_update > self.update_interval:
                self._update_log_display()
                
    def _flash_log_for_attention(self, success=False):
        """
        Flash the log textbox background briefly to draw attention to important messages.
        
        Args:
            success: If True, flash with green for success, otherwise red for errors
        """
        original_bg = self.log_textbox.cget("fg_color")
        
        # Flash with appropriate background color
        if success:
            # Light green for success
            self.log_textbox.configure(fg_color="#E0FFE0")
        else:
            # Light red for errors
            self.log_textbox.configure(fg_color="#FFE0E0")
        
        # Reset after a short delay
        self.after(500, lambda: self.log_textbox.configure(fg_color=original_bg))
    
    def _update_log_display(self):
        """Update the log display with all buffered messages."""
        if not self.log_buffer:
            return
            
        self.log_textbox.configure(state="normal")
        
        for message in self.log_buffer:
            # Determine message type
            if message.startswith("APP:"):
                tag = "APP"
                prefix_len = 4
            elif message.startswith("DEV:"):
                tag = "DEV"
                prefix_len = 4
            elif message.startswith("INFO:"):
                tag = "INFO"
                prefix_len = 5
            elif message.startswith("ERROR:"):
                tag = "ERROR"
                prefix_len = 6
            elif message.startswith("WARNING:"):
                tag = "WARNING"
                prefix_len = 8
            elif message.startswith("DEBUG:"):
                tag = "DEBUG"
                prefix_len = 6
            else:
                tag = "SYSTEM"
                prefix_len = 0
            
            # Format the message with a clear prefix
            if prefix_len > 0:
                formatted_prefix = f"[{tag}] "
                formatted_message = formatted_prefix + message[prefix_len:]
            else:
                formatted_prefix = "[SYSTEM] "
                formatted_message = formatted_prefix + message
            
            # Insert the message with a newline
            self.log_textbox.insert("end", formatted_message + "\n")
        
        # Clear the buffer
        self.log_buffer = []
        
        # Update the last update time
        self.last_log_update = time.time() * 1000
        
        # Check if we need to trim the log for performance
        self._trim_log_if_needed()
        
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")
    
    def _trim_log_if_needed(self):
        """
        Trim the log text if it gets too large to maintain performance.
        This keeps the most recent entries and removes older ones.
        """
        # Get the current number of lines
        num_lines = int(self.log_textbox.index('end-1c').split('.')[0])
        
        # If we have more than MAX_LOG_ENTRIES lines, trim the log
        if num_lines > self.MAX_LOG_ENTRIES:
            # Calculate how many lines to remove
            lines_to_remove = num_lines - self.MAX_LOG_ENTRIES
            
            # Delete the oldest lines
            self.log_textbox.delete("1.0", f"{lines_to_remove + 1}.0")
            
            # Add a note that older entries were removed
            self.log_textbox.insert("1.0", f"[INFO] Older log entries were removed to maintain performance.\n")

    def clear_log(self):
        """Clears the log text area."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        self.log_entries.clear()
        self.log_buffer = []

    def copy_log(self):
        """Copies the entire log content to the clipboard."""
        log_content = self.log_textbox.get("1.0", "end-1c")
        if log_content:
            pyperclip.copy(log_content)
            # Show feedback that log was copied
            self.log_message("INFO: Log copied to clipboard\n")

    def export_log(self):
        """Exports the log content to a text file with proper formatting."""
        # Get the log content
        log_content = self.log_textbox.get("1.0", "end-1c")
        if not log_content:
            self.log_message("WARNING: No log content to export\n")
            return
        
        # Format the log content with timestamps and categorization
        formatted_log = self.format_log_for_export(log_content)
        
        # Open file dialog to select save location
        default_filename = f"LT32Pro_Log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Log files", "*.log"), ("All files", "*.*")],
            title=self.i18n.get("export_log"),
            initialfile=default_filename
        )
        
        if not file_path:
            return  # User cancelled the dialog
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Add header with export date and time
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"LT32Pro Device Configurator - Log Export\n")
                f.write(f"Export Date: {current_time}\n")
                
                # Add device information if available
                if hasattr(self.serial_service, 'device_info'):
                    if self.serial_service.device_info.get('imei'):
                        f.write(f"Device IMEI: {self.serial_service.device_info['imei']}\n")
                    if self.serial_service.device_info.get('iccid'):
                        f.write(f"Device ICCID: {self.serial_service.device_info['iccid']}\n")
                
                f.write("-" * 50 + "\n\n")
                
                # Write the formatted log content
                f.write(formatted_log)
            
            # Log success message
            self.log_message(f"INFO: Log exported successfully to {os.path.basename(file_path)}\n")
            
            # Try to open the containing folder to show the user where the file was saved
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(os.path.dirname(file_path))
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', os.path.dirname(file_path)])
            except Exception:
                # Silently ignore if we can't open the folder
                pass
                
        except Exception as e:
            # Log error message
            self.log_message(f"ERROR: Failed to export log: {str(e)}\n")

    def format_log_for_export(self, log_content):
        """
        Format the log content for export with timestamps and clear categorization.
        
        Args:
            log_content: The raw log content from the text box
            
        Returns:
            Formatted log content with timestamps and categorization
        """
        lines = log_content.split('\n')
        formatted_lines = []
        
        # Use the actual log entries with their timestamps if available
        if self.log_entries:
            for timestamp, message in self.log_entries:
                if not message.strip():
                    continue
                
                # Extract category from the message
                if message.startswith("APP:"):
                    category = "APP"
                    content = message[4:].strip()
                elif message.startswith("DEV:"):
                    category = "DEV"
                    content = message[4:].strip()
                elif message.startswith("INFO:"):
                    category = "INFO"
                    content = message[5:].strip()
                elif message.startswith("ERROR:"):
                    category = "ERROR"
                    content = message[6:].strip()
                elif message.startswith("WARNING:"):
                    category = "WARNING"
                    content = message[8:].strip()
                elif message.startswith("DEBUG:"):
                    category = "DEBUG"
                    content = message[6:].strip()
                else:
                    category = "SYSTEM"
                    content = message.strip()
                
                # Format with full date and time
                full_timestamp = f"{datetime.datetime.now().strftime('%Y-%m-%d')} {timestamp}"
                formatted_line = f"[{full_timestamp}] [{category}] {content}"
                formatted_lines.append(formatted_line)
        else:
            # Fallback to parsing the text content if log_entries is not available
            current_time = datetime.datetime.now()
            
            for line in lines:
                if not line.strip():
                    continue
                
                # Extract category from the formatted log line
                category_match = re.match(r'\[(APP|DEV|INFO|ERROR|WARNING|DEBUG|SYSTEM)\]\s+(.*)', line)
                if category_match:
                    category = category_match.group(1)
                    message = category_match.group(2).strip()
                else:
                    category = "SYSTEM"
                    message = line.strip()
                
                # Add timestamp to each line
                timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Format the line with timestamp and category
                formatted_line = f"[{timestamp}] [{category}] {message}"
                formatted_lines.append(formatted_line)
                
                # Increment time slightly for sequential entries
                current_time += datetime.timedelta(milliseconds=100)
        
        return '\n'.join(formatted_lines)

    def send_free_command(self, event=None):
        """Sends the command from the free command entry."""
        command = self.command_entry.get().strip()
        if command and self.serial_service.is_connected:
            self.serial_service.send_command(command)
            self.command_entry.delete(0, "end")
    
    def update_language_display(self):
        """Updates all UI elements with the current language."""
        # Update title
        self.title_label.configure(text=self.i18n.get("serial_log"))
        
        # Update buttons
        self.copy_button.configure(text=self.i18n.get("copy_log"))
        self.export_button.configure(text=self.i18n.get("export_log"))
        self.clear_button.configure(text=self.i18n.get("clear_log", "Clear"))
        
        # Update free command section
        self.command_label.configure(text=self.i18n.get("free_command"))
        self.send_command_button.configure(text=self.i18n.get("send"))