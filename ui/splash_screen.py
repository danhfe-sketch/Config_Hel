import tkinter as tk
from PIL import Image, ImageTk
import os
import sys
import time
import threading

# Import the helper function for resource paths
from utils.helpers import resource_path

class SplashScreen:
    """
    A splash screen that displays while the application is loading.
    """
    def __init__(self, image_path=None, timeout=5000, min_display_time=1000):
        """
        Initialize the splash screen.
        
        Args:
            image_path: Path to the splash image
            timeout: Maximum time to display the splash screen in milliseconds
            min_display_time: Minimum time to display the splash screen in milliseconds
        """
        self.timeout = timeout
        self.min_display_time = min_display_time
        self.start_time = time.time() * 1000  # Convert to milliseconds
        
        # Create the splash window
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # Remove window decorations
        
        # Set window attributes for splash screen appearance
        self.root.attributes('-topmost', True)  # Keep on top
        self.root.attributes('-alpha', 0.0)  # Start transparent for fade-in
        
        # Try to load the splash image
        try:
            # Use the provided image path or default to logo
            if image_path is None:
                image_path = resource_path("assets/images/splash.png")
            
            # Check if the file exists, otherwise use logo.png
            if not os.path.exists(image_path):
                image_path = resource_path("assets/images/logo.png")
                
            # Load and resize the image
            img = Image.open(image_path)
            
            # Set a reasonable size for the splash screen
            width, height = img.size
            max_width, max_height = 600, 400
            
            # Resize if needed while maintaining aspect ratio
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                width = int(width * ratio)
                height = int(height * ratio)
                img = img.resize((width, height), Image.LANCZOS)
            
            # Convert to PhotoImage
            self.splash_image = ImageTk.PhotoImage(img)
            
            # Create a label with the image
            self.splash_label = tk.Label(self.root, image=self.splash_image, bd=0)
            self.splash_label.pack()
            
        except Exception as e:
            print(f"Error loading splash image: {e}")
            # Create a default splash screen with text
            width, height = 500, 300
            self.splash_label = tk.Label(
                self.root, 
                text="LT32Pro Configurator\nLoading...", 
                font=("Arial", 24),
                bg="#0066cc",
                fg="white",
                width=30,
                height=10
            )
            self.splash_label.pack(fill="both", expand=True)
        
        # Add a progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = tk.Canvas(
            self.root, 
            height=5, 
            bg="#003366", 
            highlightthickness=0
        )
        self.progress_bar.pack(fill="x", side="bottom")
        
        # Create the progress bar rectangle (initially empty)
        self.progress_rect = self.progress_bar.create_rectangle(
            0, 0, 0, 5, fill="#00ccff", outline=""
        )
        
        # Center the window on the screen
        self._center_window()
        
        # Start with fade-in effect
        self._fade_in()
        
        # Start progress animation
        self._animate_progress()
        
        # Set a timeout to close the splash screen
        self.root.after(self.timeout, self.close)
    
    def _center_window(self):
        """Center the splash window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def _fade_in(self, step=0.05, delay=20, current=0.0):
        """
        Gradually fade in the splash screen.
        
        Args:
            step: Alpha increment per step
            delay: Delay between steps in milliseconds
            current: Current alpha value
        """
        current += step
        if current <= 1.0:
            self.root.attributes('-alpha', current)
            self.root.after(delay, lambda: self._fade_in(step, delay, current))
    
    def _fade_out(self, step=0.05, delay=20, current=1.0):
        """
        Gradually fade out the splash screen.
        
        Args:
            step: Alpha decrement per step
            delay: Delay between steps in milliseconds
            current: Current alpha value
        """
        current -= step
        if current >= 0:
            self.root.attributes('-alpha', current)
            self.root.after(delay, lambda: self._fade_out(step, delay, current))
        else:
            self.root.destroy()
    
    def _animate_progress(self, width=0):
        """
        Animate the progress bar.
        
        Args:
            width: Current width of the progress bar
        """
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return
            
        total_width = self.root.winfo_width()
        increment = total_width / 100  # Divide the animation into 100 steps
        
        # Calculate progress based on elapsed time
        elapsed = time.time() * 1000 - self.start_time
        progress = min(1.0, elapsed / self.timeout)
        
        # Update the progress bar
        new_width = int(progress * total_width)
        self.progress_bar.coords(self.progress_rect, 0, 0, new_width, 5)
        
        # Continue animation if not complete
        if progress < 1.0:
            self.root.after(50, self._animate_progress)
    
    def update_progress(self, value):
        """
        Update the progress bar with a specific value.
        
        Args:
            value: Progress value between 0.0 and 1.0
        """
        if hasattr(self, 'root') and self.root.winfo_exists():
            total_width = self.root.winfo_width()
            new_width = int(value * total_width)
            self.progress_bar.coords(self.progress_rect, 0, 0, new_width, 5)
    
    def close(self):
        """Close the splash screen with a fade-out effect."""
        # Ensure minimum display time
        elapsed = time.time() * 1000 - self.start_time
        if elapsed < self.min_display_time:
            remaining = int(self.min_display_time - elapsed)
            self.root.after(remaining, self._fade_out)
        else:
            self._fade_out()
    
    def run(self, app_start_func):
        """
        Run the splash screen and then start the application.
        
        Args:
            app_start_func: Function to call to start the main application
        """
        # Start the application in a separate thread
        threading.Thread(target=self._start_app_thread, args=(app_start_func,), daemon=True).start()
        
        # Run the splash screen
        self.root.mainloop()
    
    def _start_app_thread(self, app_start_func):
        """
        Thread function to start the application.
        
        Args:
            app_start_func: Function to call to start the main application
        """
        # Wait a bit to let the splash screen appear
        time.sleep(0.5)
        
        try:
            # Call the application start function
            app_start_func()
            
            # Close the splash screen
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.after(0, self.close)
                
        except Exception as e:
            print(f"Error starting application: {e}")
            # Close the splash screen on error
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.after(0, self.close)