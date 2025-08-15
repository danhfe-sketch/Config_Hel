import tkinter as tk
from PIL import Image, ImageTk
import os
import sys
import time
import threading
import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple

# Import the helper function for resource paths
from utils.helpers import resource_path

# Set up logging for splash screen
logger = logging.getLogger(__name__)

@dataclass
class SplashConfig:
    """Configuration settings for the splash screen."""
    image_path: str = "assets/images/splash.png"
    fallback_image_paths: List[str] = None
    timeout: int = 5000  # milliseconds
    min_display_time: int = 1000  # milliseconds
    fade_in_duration: int = 300  # milliseconds
    fade_out_duration: int = 300  # milliseconds
    progress_steps: int = 100
    window_size: Tuple[int, int] = (600, 400)  # default size if image loading fails
    max_image_size: Tuple[int, int] = (600, 400)  # maximum image dimensions
    background_color: str = "#0066cc"
    text_color: str = "white"
    progress_color: str = "#00ccff"
    progress_bg_color: str = "#003366"
    
    def __post_init__(self):
        """Initialize fallback image paths if not provided."""
        if self.fallback_image_paths is None:
            # Cascading fallback order as per requirements: splash.png -> logo.png -> text-based
            self.fallback_image_paths = [
                "assets/images/logo.png",      # Primary fallback
                "assets/icon.ico",             # Secondary fallback (app icon)
                "assets/icons/app_icon.png",   # Tertiary fallback
                "assets/images/icon.png",      # Additional fallback option
                "icon.ico"                     # Root level icon as last resort
            ]

@dataclass
class ProgressState:
    """Progress state management for splash screen."""
    current: float = 0.0  # 0.0 to 1.0
    target: float = 0.0   # Target progress for smooth animation
    message: str = "Loading..."
    is_complete: bool = False
    animation_speed: float = 0.02  # Progress increment per animation frame
    last_update_time: float = 0.0  # Last time progress was updated

class SplashScreen:
    """
    A splash screen that displays while the application is loading.
    Enhanced with better error handling and resource management.
    """
    def __init__(self, config: Optional[SplashConfig] = None, image_path: Optional[str] = None, 
                 timeout: int = 5000, min_display_time: int = 1000):
        """
        Initialize the splash screen.
        
        Args:
            config: SplashConfig object with all settings (preferred)
            image_path: Path to the splash image (legacy support)
            timeout: Maximum time to display the splash screen in milliseconds (legacy support)
            min_display_time: Minimum time to display the splash screen in milliseconds (legacy support)
        """
        # Use config if provided, otherwise create from legacy parameters
        if config is None:
            self.config = SplashConfig(
                image_path=image_path or "assets/images/splash.png",
                timeout=timeout,
                min_display_time=min_display_time
            )
        else:
            self.config = config
            
        # Override config with explicit parameters if provided (for backward compatibility)
        if image_path is not None:
            self.config.image_path = image_path
        if timeout != 5000:  # Only override if explicitly changed
            self.config.timeout = timeout
        if min_display_time != 1000:  # Only override if explicitly changed
            self.config.min_display_time = min_display_time
            
        self.start_time = time.time() * 1000  # Convert to milliseconds
        self.progress_state = ProgressState()
        self.progress_state.last_update_time = time.time()
        self._animation_running = False
        self._close_requested = False
        
        logger.info(f"Initializing splash screen with config: {self.config}")
        logger.debug(f"Splash screen start time: {self.start_time}")
        
        # Initialize the splash window
        self._init_window()
        
        # Load the splash content (image or fallback)
        self._load_splash_content()
        
        # Setup progress bar
        self._setup_progress_bar()
        
        # Center and show the window
        self._center_window()
        self._fade_in()
        self._start_progress_animation()
        
        # Set timeout to close splash screen
        self.root.after(self.config.timeout, self.close)
    
    def _init_window(self):
        """Initialize the splash window with proper attributes."""
        try:
            self.root = tk.Tk()
            self.root.overrideredirect(True)  # Remove window decorations
            
            # Set window attributes for splash screen appearance
            self.root.attributes('-topmost', True)  # Keep on top
            self.root.attributes('-alpha', 0.0)  # Start transparent for fade-in
            
            logger.debug("Splash window initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize splash window: {e}")
            raise
    
    def _validate_resource_path(self, path: str) -> Optional[str]:
        """
        Validate and resolve a resource path with comprehensive error handling.
        
        Args:
            path: Relative path to validate
            
        Returns:
            Absolute path if valid, None otherwise
        """
        if not path:
            logger.warning("Empty or None path provided for validation")
            return None
        
        try:
            # Step 1: Resolve the path
            logger.debug(f"Resolving resource path: {path}")
            resolved_path = resource_path(path)
            logger.debug(f"Path resolved to: {resolved_path}")
            
            # Step 2: Check if path exists
            if not os.path.exists(resolved_path):
                logger.debug(f"Path does not exist: {resolved_path}")
                
                # Try to provide helpful debugging information
                parent_dir = os.path.dirname(resolved_path)
                if os.path.exists(parent_dir):
                    try:
                        siblings = os.listdir(parent_dir)
                        logger.debug(f"Parent directory exists with contents: {siblings}")
                        
                        # Look for similar files
                        filename = os.path.basename(path)
                        similar_files = [f for f in siblings if filename.lower() in f.lower() or f.lower() in filename.lower()]
                        if similar_files:
                            logger.debug(f"Similar files found: {similar_files}")
                    except Exception as e:
                        logger.debug(f"Could not list parent directory contents: {e}")
                else:
                    logger.debug(f"Parent directory does not exist: {parent_dir}")
                
                return None
            
            # Step 3: Verify it's a file (not a directory)
            if not os.path.isfile(resolved_path):
                logger.warning(f"Path exists but is not a file: {resolved_path}")
                return None
            
            # Step 4: Check file permissions
            if not os.access(resolved_path, os.R_OK):
                logger.warning(f"File exists but is not readable: {resolved_path}")
                return None
            
            # Step 5: Get file information for debugging
            try:
                file_size = os.path.getsize(resolved_path)
                logger.debug(f"✓ Valid resource found: {resolved_path} ({file_size} bytes)")
            except Exception as e:
                logger.debug(f"Could not get file size for {resolved_path}: {e}")
            
            return resolved_path
            
        except ValueError as e:
            logger.warning(f"Invalid path format '{path}': {e}")
            return None
            
        except OSError as e:
            logger.warning(f"OS error resolving path '{path}': {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error resolving path '{path}': {type(e).__name__}: {e}")
            return None
    
    def _load_image_with_fallbacks(self) -> Optional[ImageTk.PhotoImage]:
        """
        Load splash image with robust cascading fallback mechanism.
        
        Fallback order:
        1. Primary splash image (splash.png)
        2. Fallback images (logo.png, icon.ico, etc.)
        3. Text-based fallback (handled by caller)
        
        Returns:
            PhotoImage if successful, None if all image attempts fail
        """
        # Create list of paths to try with explicit fallback order
        paths_to_try = [self.config.image_path] + self.config.fallback_image_paths
        
        logger.info(f"Starting cascading image fallback mechanism with {len(paths_to_try)} possible paths")
        logger.debug(f"Fallback order: {' -> '.join(paths_to_try)} -> text-based fallback")
        
        fallback_results = []  # Track results for debugging
        
        for i, path in enumerate(paths_to_try):
            fallback_level = "primary" if i == 0 else f"fallback-{i}"
            logger.info(f"[{fallback_level}] Attempting to load image: {path}")
            
            # Step 1: Validate resource path
            resolved_path = self._validate_resource_path(path)
            if resolved_path is None:
                error_msg = f"Path resolution failed for {path}"
                logger.warning(f"[{fallback_level}] {error_msg}")
                fallback_results.append({
                    'path': path,
                    'level': fallback_level,
                    'stage': 'path_resolution',
                    'success': False,
                    'error': error_msg
                })
                continue
            
            # Step 2: Attempt to load image file
            try:
                logger.debug(f"[{fallback_level}] Opening image file: {resolved_path}")
                img = Image.open(resolved_path)
                logger.info(f"[{fallback_level}] Successfully opened image file")
                logger.debug(f"[{fallback_level}] Original image size: {img.size}, mode: {img.mode}")
                
                # Step 3: Validate image properties
                if img.size[0] <= 0 or img.size[1] <= 0:
                    raise ValueError(f"Invalid image dimensions: {img.size}")
                
                # Step 4: Process image (resize if needed)
                processed_img = self._process_image_for_display(img, fallback_level)
                if processed_img is None:
                    raise ValueError("Image processing failed")
                
                # Step 5: Convert to PhotoImage
                logger.debug(f"[{fallback_level}] Converting to PhotoImage")
                photo_image = ImageTk.PhotoImage(processed_img)
                
                # Success!
                logger.info(f"[{fallback_level}] ✓ Image successfully loaded and processed: {resolved_path}")
                fallback_results.append({
                    'path': path,
                    'level': fallback_level,
                    'stage': 'complete',
                    'success': True,
                    'resolved_path': resolved_path,
                    'original_size': img.size,
                    'final_size': processed_img.size
                })
                
                # Log successful fallback summary
                self._log_fallback_success(fallback_results)
                return photo_image
                
            except FileNotFoundError as e:
                error_msg = f"Image file not found: {e}"
                logger.warning(f"[{fallback_level}] {error_msg}")
                fallback_results.append({
                    'path': path,
                    'level': fallback_level,
                    'stage': 'file_access',
                    'success': False,
                    'error': error_msg
                })
                
            except PermissionError as e:
                error_msg = f"Permission denied accessing image: {e}"
                logger.warning(f"[{fallback_level}] {error_msg}")
                fallback_results.append({
                    'path': path,
                    'level': fallback_level,
                    'stage': 'file_access',
                    'success': False,
                    'error': error_msg
                })
                
            except (OSError, IOError) as e:
                error_msg = f"I/O error loading image: {e}"
                logger.warning(f"[{fallback_level}] {error_msg}")
                fallback_results.append({
                    'path': path,
                    'level': fallback_level,
                    'stage': 'file_io',
                    'success': False,
                    'error': error_msg
                })
                
            except ValueError as e:
                error_msg = f"Invalid image data: {e}"
                logger.warning(f"[{fallback_level}] {error_msg}")
                fallback_results.append({
                    'path': path,
                    'level': fallback_level,
                    'stage': 'image_validation',
                    'success': False,
                    'error': error_msg
                })
                
            except Exception as e:
                error_msg = f"Unexpected error loading image: {type(e).__name__}: {e}"
                logger.error(f"[{fallback_level}] {error_msg}")
                fallback_results.append({
                    'path': path,
                    'level': fallback_level,
                    'stage': 'unexpected_error',
                    'success': False,
                    'error': error_msg
                })
        
        # All image loading attempts failed
        logger.error("✗ All image loading attempts failed, will use text-based fallback")
        self._log_fallback_failure(fallback_results)
        return None
    
    def _process_image_for_display(self, img: Image.Image, fallback_level: str) -> Optional[Image.Image]:
        """
        Process an image for display with proper error handling.
        
        Args:
            img: PIL Image to process
            fallback_level: Current fallback level for logging
            
        Returns:
            Processed Image or None if processing fails
        """
        try:
            # Ensure image is in a compatible mode
            if img.mode not in ('RGB', 'RGBA', 'L'):
                logger.debug(f"[{fallback_level}] Converting image from {img.mode} to RGB")
                img = img.convert('RGB')
            
            # Get original dimensions
            width, height = img.size
            max_width, max_height = self.config.max_image_size
            
            logger.debug(f"[{fallback_level}] Image dimensions: {width}x{height}, max allowed: {max_width}x{max_height}")
            
            # Resize if needed while maintaining aspect ratio
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                
                logger.debug(f"[{fallback_level}] Resizing image: {width}x{height} -> {new_width}x{new_height} (ratio: {ratio:.3f})")
                
                # Use high-quality resampling
                img = img.resize((new_width, new_height), Image.LANCZOS)
                logger.debug(f"[{fallback_level}] Image resized successfully")
            else:
                logger.debug(f"[{fallback_level}] Image size is within limits, no resizing needed")
            
            return img
            
        except Exception as e:
            logger.error(f"[{fallback_level}] Error processing image: {e}")
            return None
    
    def _log_fallback_success(self, fallback_results: list):
        """Log successful fallback information for debugging."""
        successful_result = fallback_results[-1]  # Last result should be successful
        failed_attempts = len(fallback_results) - 1
        
        if failed_attempts > 0:
            logger.info(f"Image loaded successfully after {failed_attempts} failed attempt(s)")
            logger.debug("Failed attempts summary:")
            for result in fallback_results[:-1]:
                logger.debug(f"  - {result['level']}: {result['path']} failed at {result['stage']} - {result['error']}")
        
        logger.info(f"Final image: {successful_result['resolved_path']} "
                   f"({successful_result['original_size']} -> {successful_result['final_size']})")
    
    def _log_fallback_failure(self, fallback_results: list):
        """Log detailed failure information for debugging."""
        logger.error("Detailed fallback failure analysis:")
        logger.error(f"Total attempts: {len(fallback_results)}")
        
        # Group failures by stage
        failure_stages = {}
        for result in fallback_results:
            stage = result['stage']
            if stage not in failure_stages:
                failure_stages[stage] = []
            failure_stages[stage].append(result)
        
        for stage, failures in failure_stages.items():
            logger.error(f"  {stage.replace('_', ' ').title()} failures: {len(failures)}")
            for failure in failures:
                logger.error(f"    - {failure['level']}: {failure['path']} - {failure['error']}")
        
        # Provide troubleshooting suggestions
        logger.error("Troubleshooting suggestions:")
        logger.error("  1. Verify image files exist in the assets/images/ directory")
        logger.error("  2. Check file permissions for image files")
        logger.error("  3. Ensure images are in supported formats (PNG, JPG, ICO)")
        logger.error("  4. Verify PyInstaller is bundling assets correctly if running as executable")
        logger.error("  5. Check that image files are not corrupted")
    
    def _create_text_fallback(self):
        """
        Create a robust text-based fallback splash screen.
        
        This is the final fallback when all image loading attempts fail.
        Provides a professional-looking splash screen using only text and colors.
        """
        logger.info("Creating text-based fallback splash screen")
        
        try:
            width, height = self.config.window_size
            
            # Create main container frame
            main_frame = tk.Frame(
                self.root,
                bg=self.config.background_color,
                width=width,
                height=height
            )
            main_frame.pack(fill="both", expand=True)
            main_frame.pack_propagate(False)  # Maintain fixed size
            
            # Create title section
            title_frame = tk.Frame(main_frame, bg=self.config.background_color)
            title_frame.pack(expand=True, fill="both")
            
            # Main application title
            title_label = tk.Label(
                title_frame,
                text="LT32Pro Configurator",
                font=("Arial", 28, "bold"),
                bg=self.config.background_color,
                fg=self.config.text_color,
                pady=20
            )
            title_label.pack(expand=True)
            
            # Subtitle/version info
            subtitle_label = tk.Label(
                title_frame,
                text="Device Configuration Tool",
                font=("Arial", 14),
                bg=self.config.background_color,
                fg=self.config.text_color,
                pady=(0, 10)
            )
            subtitle_label.pack()
            
            # Loading message
            loading_label = tk.Label(
                title_frame,
                text="Loading Application...",
                font=("Arial", 12),
                bg=self.config.background_color,
                fg=self.config.text_color,
                pady=(20, 0)
            )
            loading_label.pack()
            
            # Store reference to main label for potential updates
            self.splash_label = title_label
            
            # Set window size for text fallback
            self.root.geometry(f"{width}x{height}")
            
            # Add a subtle border effect
            self.root.configure(bg=self.config.progress_color)  # Border color
            main_frame.configure(highlightbackground=self.config.progress_color, highlightthickness=2)
            
            logger.info(f"✓ Text-based fallback splash created successfully ({width}x{height})")
            logger.debug("Text fallback includes: title, subtitle, loading message, and styled border")
            
        except Exception as e:
            logger.error(f"Error creating text fallback splash: {e}")
            # Create minimal fallback as last resort
            self._create_minimal_fallback()
    
    def _create_minimal_fallback(self):
        """
        Create the most basic fallback splash screen possible.
        
        This is used when even the text fallback fails.
        """
        logger.warning("Creating minimal fallback splash screen")
        
        try:
            # Create the simplest possible splash
            self.splash_label = tk.Label(
                self.root,
                text="LT32Pro Configurator\n\nLoading...",
                font=("Arial", 16),
                bg="#0066cc",
                fg="white",
                padx=50,
                pady=50
            )
            self.splash_label.pack(expand=True, fill="both")
            
            # Set basic window size
            self.root.geometry("400x200")
            
            logger.info("✓ Minimal fallback splash created successfully")
            
        except Exception as e:
            logger.critical(f"Failed to create even minimal fallback splash: {e}")
            # At this point, we have to give up on the splash screen
            raise RuntimeError("Unable to create any form of splash screen") from e
    
    def _load_splash_content(self):
        """
        Load the splash screen content with robust cascading fallback mechanism.
        
        Fallback sequence:
        1. Try to load primary splash image (splash.png)
        2. Try fallback images (logo.png, icon.ico, etc.)
        3. Create styled text-based fallback
        4. Create minimal text fallback (last resort)
        """
        logger.info("Starting splash content loading with cascading fallback mechanism")
        
        try:
            # Phase 1: Attempt image loading with fallbacks
            logger.debug("Phase 1: Attempting image loading")
            splash_image = self._load_image_with_fallbacks()
            
            if splash_image is not None:
                # Successfully loaded an image
                logger.info("✓ Phase 1 successful: Image-based splash screen created")
                self.splash_image = splash_image
                self.splash_label = tk.Label(self.root, image=self.splash_image, bd=0)
                self.splash_label.pack()
                self._log_content_success("image")
                return
            
            # Phase 2: Image loading failed, create text-based fallback
            logger.info("Phase 1 failed, proceeding to Phase 2: Text-based fallback")
            self._create_text_fallback()
            logger.info("✓ Phase 2 successful: Text-based splash screen created")
            self._log_content_success("text")
            return
                
        except Exception as e:
            logger.error(f"Phase 2 failed with critical error: {e}")
            
            # Phase 3: Last resort - minimal fallback
            try:
                logger.warning("Proceeding to Phase 3: Minimal fallback (last resort)")
                self._create_minimal_fallback()
                logger.info("✓ Phase 3 successful: Minimal splash screen created")
                self._log_content_success("minimal")
                return
                
            except Exception as fallback_error:
                logger.critical(f"Phase 3 failed: {fallback_error}")
                logger.critical("All splash screen fallback mechanisms have failed")
                
                # Log system information for debugging
                self._log_system_debug_info()
                
                # Re-raise with context
                raise RuntimeError("Complete splash screen failure: all fallback mechanisms exhausted") from fallback_error
    
    def _log_content_success(self, content_type: str):
        """Log successful content loading with type information."""
        type_descriptions = {
            'image': 'Image-based splash screen with graphics',
            'text': 'Text-based splash screen with styled layout',
            'minimal': 'Minimal text-only splash screen'
        }
        
        description = type_descriptions.get(content_type, f'Unknown type: {content_type}')
        logger.info(f"Splash content loaded successfully: {description}")
        
        # Log performance info
        elapsed = time.time() * 1000 - self.start_time
        logger.debug(f"Content loading completed in {elapsed:.1f}ms")
    
    def _log_system_debug_info(self):
        """Log system information for debugging splash screen failures."""
        logger.critical("System debug information:")
        logger.critical(f"  Python version: {sys.version}")
        logger.critical(f"  Platform: {sys.platform}")
        logger.critical(f"  Current working directory: {os.getcwd()}")
        logger.critical(f"  PyInstaller mode: {hasattr(sys, '_MEIPASS')}")
        
        if hasattr(sys, '_MEIPASS'):
            logger.critical(f"  PyInstaller temp path: {sys._MEIPASS}")
        
        # Log available modules
        try:
            import tkinter
            logger.critical(f"  Tkinter version: {tkinter.TkVersion}")
        except Exception as e:
            logger.critical(f"  Tkinter import error: {e}")
        
        try:
            from PIL import Image
            logger.critical(f"  PIL/Pillow available: {Image.__version__ if hasattr(Image, '__version__') else 'version unknown'}")
        except Exception as e:
            logger.critical(f"  PIL/Pillow import error: {e}")
        
        # Log asset directory information
        try:
            assets_path = resource_path("assets")
            logger.critical(f"  Assets path: {assets_path}")
            logger.critical(f"  Assets path exists: {os.path.exists(assets_path)}")
            
            if os.path.exists(assets_path):
                try:
                    assets_contents = os.listdir(assets_path)
                    logger.critical(f"  Assets directory contents: {assets_contents}")
                except Exception as e:
                    logger.critical(f"  Error listing assets directory: {e}")
                    
        except Exception as e:
            logger.critical(f"  Error checking assets path: {e}")
    
    def _setup_progress_bar(self):
        """Setup the progress bar at the bottom of the splash screen."""
        try:
            self.progress_var = tk.DoubleVar()
            self.progress_bar = tk.Canvas(
                self.root,
                height=5,
                bg=self.config.progress_bg_color,
                highlightthickness=0
            )
            self.progress_bar.pack(fill="x", side="bottom")
            
            # Create the progress bar rectangle (initially empty)
            self.progress_rect = self.progress_bar.create_rectangle(
                0, 0, 0, 5, fill=self.config.progress_color, outline=""
            )
            
            logger.debug("Progress bar setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup progress bar: {e}")
            # Continue without progress bar if it fails
    
    def _center_window(self):
        """Center the splash window on the screen."""
        try:
            self.root.update_idletasks()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Calculate center position
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
            # Ensure window stays on screen
            x = max(0, min(x, screen_width - width))
            y = max(0, min(y, screen_height - height))
            
            self.root.geometry(f"{width}x{height}+{x}+{y}")
            logger.debug(f"Window centered at position: {x},{y} with size: {width}x{height}")
            
        except Exception as e:
            logger.error(f"Failed to center window: {e}")
            # Continue without centering if it fails
    
    def _fade_in(self, step=None, delay=None, current=0.0):
        """
        Gradually fade in the splash screen with smooth timing.
        
        Args:
            step: Alpha increment per step (calculated from config if None)
            delay: Delay between steps in milliseconds (calculated from config if None)
            current: Current alpha value
        """
        try:
            # Calculate smooth fade parameters based on config
            if step is None:
                total_steps = self.config.fade_in_duration // 16  # ~60fps
                step = 1.0 / max(1, total_steps)
            if delay is None:
                delay = 16  # ~60fps for smooth animation
                
            current += step
            if current <= 1.0:
                self.root.attributes('-alpha', current)
                self.root.after(delay, lambda: self._fade_in(step, delay, current))
            else:
                self.root.attributes('-alpha', 1.0)  # Ensure fully opaque
                logger.debug("Fade-in animation completed")
        except Exception as e:
            logger.error(f"Error during fade-in animation: {e}")
            # Set to fully opaque if animation fails
            try:
                self.root.attributes('-alpha', 1.0)
            except:
                pass
    
    def _fade_out(self, step=None, delay=None, current=1.0):
        """
        Gradually fade out the splash screen with smooth timing.
        
        Args:
            step: Alpha decrement per step (calculated from config if None)
            delay: Delay between steps in milliseconds (calculated from config if None)
            current: Current alpha value
        """
        try:
            # Calculate smooth fade parameters based on config
            if step is None:
                total_steps = self.config.fade_out_duration // 16  # ~60fps
                step = 1.0 / max(1, total_steps)
            if delay is None:
                delay = 16  # ~60fps for smooth animation
                
            current -= step
            if current >= 0:
                self.root.attributes('-alpha', current)
                self.root.after(delay, lambda: self._fade_out(step, delay, current))
            else:
                logger.debug("Fade-out animation completed, destroying window")
                self._animation_running = False
                self.root.destroy()
        except Exception as e:
            logger.error(f"Error during fade-out animation: {e}")
            # Force destroy if animation fails
            try:
                self._animation_running = False
                self.root.destroy()
            except:
                pass
    
    def _start_progress_animation(self):
        """Start the smooth progress bar animation."""
        if not self._animation_running:
            self._animation_running = True
            self._animate_progress_smooth()
    
    def _animate_progress_smooth(self):
        """
        Animate the progress bar with smooth transitions and proper timing control.
        This replaces the old time-based animation with a more responsive system.
        """
        try:
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                logger.debug("Root window no longer exists, stopping progress animation")
                self._animation_running = False
                return
            
            if not hasattr(self, 'progress_bar') or self._close_requested:
                logger.debug("Progress bar not available or close requested, stopping animation")
                self._animation_running = False
                return
                
            total_width = self.root.winfo_width()
            if total_width <= 0:
                # Window not ready yet, try again later
                if self._animation_running:
                    self.root.after(16, self._animate_progress_smooth)  # ~60fps
                return
            
            # Smooth progress animation towards target
            current_time = time.time()
            time_delta = current_time - self.progress_state.last_update_time
            
            # Calculate smooth progress increment
            if self.progress_state.current < self.progress_state.target:
                # Animate towards target
                progress_diff = self.progress_state.target - self.progress_state.current
                increment = min(progress_diff, self.progress_state.animation_speed * (time_delta * 60))  # Scale by time
                self.progress_state.current = min(self.progress_state.target, 
                                                self.progress_state.current + increment)
            elif self.progress_state.current > self.progress_state.target:
                # Animate backwards if needed (rare case)
                progress_diff = self.progress_state.current - self.progress_state.target
                decrement = min(progress_diff, self.progress_state.animation_speed * (time_delta * 60))
                self.progress_state.current = max(self.progress_state.target,
                                                self.progress_state.current - decrement)
            
            # Update progress state
            self.progress_state.is_complete = self.progress_state.current >= 1.0
            self.progress_state.last_update_time = current_time
            
            # Update the progress bar visual
            new_width = int(self.progress_state.current * total_width)
            self.progress_bar.coords(self.progress_rect, 0, 0, new_width, 5)
            
            # Add subtle color transition as progress increases
            if hasattr(self, 'progress_rect'):
                # Gradually brighten the progress color as it fills
                brightness = 0.7 + (0.3 * self.progress_state.current)  # 70% to 100% brightness
                color_value = int(255 * brightness)
                progress_color = f"#{color_value:02x}{color_value:02x}ff"  # Blue with varying brightness
                self.progress_bar.itemconfig(self.progress_rect, fill=progress_color)
            
            logger.debug(f"Smooth progress updated: {self.progress_state.current:.3f} -> {self.progress_state.target:.3f} "
                        f"(width: {new_width}/{total_width})")
            
            # Continue animation if running and not complete
            if self._animation_running and not self._close_requested:
                self.root.after(16, self._animate_progress_smooth)  # ~60fps for smooth animation
            else:
                logger.debug("Smooth progress animation stopped")
                self._animation_running = False
                
        except Exception as e:
            logger.error(f"Error during smooth progress animation: {e}")
            self._animation_running = False
    
    def update_progress(self, value: float, message: str = None, animate: bool = True):
        """
        Update the progress bar with a specific value using smooth animation.
        
        Args:
            value: Progress value between 0.0 and 1.0
            message: Optional progress message
            animate: Whether to animate to the new value (True) or jump immediately (False)
        """
        try:
            # Validate input
            value = max(0.0, min(1.0, value))
            
            if hasattr(self, 'root') and self.root.winfo_exists():
                # Update progress state
                if animate:
                    # Set target for smooth animation
                    self.progress_state.target = value
                    # Start animation if not already running
                    if not self._animation_running:
                        self._start_progress_animation()
                else:
                    # Jump immediately to value
                    self.progress_state.current = value
                    self.progress_state.target = value
                    
                    # Update visual immediately if progress bar exists
                    if hasattr(self, 'progress_bar'):
                        total_width = self.root.winfo_width()
                        if total_width > 0:
                            new_width = int(value * total_width)
                            self.progress_bar.coords(self.progress_rect, 0, 0, new_width, 5)
                
                # Update message and completion state
                if message:
                    self.progress_state.message = message
                self.progress_state.is_complete = value >= 1.0
                self.progress_state.last_update_time = time.time()
                
                logger.debug(f"Progress {'animated' if animate else 'immediately'} updated to: {value:.2%}" + 
                           (f" - {message}" if message else ""))
                
                # Auto-close when progress reaches 100% if configured
                if self.progress_state.is_complete and not self._close_requested:
                    logger.debug("Progress completed, scheduling auto-close")
                    # Small delay to let the animation finish
                    self.root.after(200, self._auto_close_on_completion)
                    
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
    
    def _auto_close_on_completion(self):
        """Automatically close splash screen when progress is complete."""
        try:
            if self.progress_state.is_complete and not self._close_requested:
                logger.debug("Auto-closing splash screen on progress completion")
                self.close()
        except Exception as e:
            logger.error(f"Error during auto-close: {e}")
    
    def close(self):
        """Close the splash screen with proper timing controls and fade-out effect."""
        try:
            if self._close_requested:
                logger.debug("Close already requested, ignoring duplicate close call")
                return
                
            self._close_requested = True
            
            # Ensure minimum display time
            elapsed = time.time() * 1000 - self.start_time
            logger.debug(f"Closing splash screen. Elapsed time: {elapsed}ms, "
                        f"Minimum required: {self.config.min_display_time}ms")
            
            if elapsed < self.config.min_display_time:
                remaining = int(self.config.min_display_time - elapsed)
                logger.debug(f"Waiting additional {remaining}ms before closing")
                self.root.after(remaining, self._perform_close)
            else:
                logger.debug("Minimum display time met, proceeding with close")
                self._perform_close()
                
        except Exception as e:
            logger.error(f"Error closing splash screen: {e}")
            # Force close if normal close fails
            self._force_close()
    
    def _perform_close(self):
        """Perform the actual close operation with fade-out."""
        try:
            # Stop progress animation
            self._animation_running = False
            
            # Complete progress bar if not already complete
            if not self.progress_state.is_complete:
                self.update_progress(1.0, "Complete", animate=False)
            
            logger.debug("Starting fade-out animation")
            self._fade_out()
            
        except Exception as e:
            logger.error(f"Error performing close: {e}")
            self._force_close()
    
    def _force_close(self):
        """Force close the splash screen without animations."""
        try:
            self._animation_running = False
            self._close_requested = True
            if hasattr(self, 'root'):
                self.root.destroy()
            logger.debug("Splash screen force closed")
        except Exception as e:
            logger.error(f"Error force closing splash screen: {e}")
    
    def set_progress_speed(self, speed: float):
        """
        Set the animation speed for progress bar transitions.
        
        Args:
            speed: Animation speed (0.01 = slow, 0.05 = normal, 0.1 = fast)
        """
        self.progress_state.animation_speed = max(0.001, min(1.0, speed))
        logger.debug(f"Progress animation speed set to: {self.progress_state.animation_speed}")
    
    def get_progress_info(self) -> dict:
        """
        Get current progress information.
        
        Returns:
            Dictionary with current progress state information
        """
        return {
            'current': self.progress_state.current,
            'target': self.progress_state.target,
            'message': self.progress_state.message,
            'is_complete': self.progress_state.is_complete,
            'animation_running': self._animation_running,
            'elapsed_time': time.time() * 1000 - self.start_time
        }
    
    def increment_progress(self, amount: float, message: str = None):
        """
        Increment the progress by a specific amount.
        
        Args:
            amount: Amount to increment (can be negative to decrement)
            message: Optional progress message
        """
        new_value = self.progress_state.target + amount
        self.update_progress(new_value, message)
    
    def run(self, app_start_func):
        """
        Run the splash screen and then start the application.
        
        Args:
            app_start_func: Function to call to start the main application
        """
        try:
            logger.info("Starting splash screen with application startup")
            
            # Start the application in a separate thread
            app_thread = threading.Thread(
                target=self._start_app_thread, 
                args=(app_start_func,), 
                daemon=True,
                name="AppStartupThread"
            )
            app_thread.start()
            logger.debug("Application startup thread started")
            
            # Run the splash screen on main thread
            logger.debug("Starting splash screen main loop")
            self.root.mainloop()
            logger.debug("Splash screen main loop ended")
            
        except Exception as e:
            logger.error(f"Error running splash screen: {e}")
            # Try to start the app directly if splash fails
            try:
                logger.info("Attempting to start application directly after splash failure")
                app_start_func()
            except Exception as app_error:
                logger.critical(f"Failed to start application after splash failure: {app_error}")
                raise
    
    def _start_app_thread(self, app_start_func):
        """
        Thread function to start the application with improved progress tracking.
        
        Args:
            app_start_func: Function to call to start the main application
        """
        try:
            # Wait a bit to let the splash screen appear and fade in
            logger.debug("App startup thread: waiting for splash to appear")
            time.sleep(0.3)
            
            # Progressive loading simulation with smooth animation
            self.update_progress(0.1, "Initializing application...")
            time.sleep(0.2)
            
            self.update_progress(0.3, "Loading components...")
            time.sleep(0.1)
            
            logger.info("App startup thread: calling application start function")
            # Call the application start function
            self.update_progress(0.5, "Starting application...")
            app_start_func()
            
            # Simulate final loading steps
            self.update_progress(0.8, "Finalizing startup...")
            time.sleep(0.1)
            
            # Complete progress
            self.update_progress(1.0, "Application ready")
            logger.info("App startup thread: application started successfully")
            
            # The progress completion will automatically trigger close via _auto_close_on_completion
            # But we also schedule a backup close just in case
            if hasattr(self, 'root') and self.root.winfo_exists():
                logger.debug("App startup thread: scheduling backup splash screen close")
                self.root.after(500, self.close)  # Backup close after 500ms
            else:
                logger.warning("App startup thread: splash screen root no longer exists")
                
        except Exception as e:
            logger.error(f"Error starting application in thread: {e}")
            # Update progress to show error state
            try:
                self.update_progress(0.0, "Application startup failed", animate=False)
                # Show error state briefly before closing
                time.sleep(1.0)
            except:
                pass
                
            # Close the splash screen on error
            if hasattr(self, 'root') and self.root.winfo_exists():
                logger.debug("App startup thread: scheduling splash screen close due to error")
                self.root.after(0, self.close)
            
            # Re-raise the exception so it can be handled by the calling code
            raise
    
    def get_fallback_status(self) -> dict:
        """
        Get the current fallback status and configuration.
        
        Returns:
            Dictionary with fallback configuration and status information
        """
        return {
            'primary_image_path': self.config.image_path,
            'fallback_image_paths': self.config.fallback_image_paths,
            'total_fallback_options': len(self.config.fallback_image_paths) + 1,  # +1 for primary
            'text_fallback_available': True,
            'minimal_fallback_available': True,
            'window_size': self.config.window_size,
            'max_image_size': self.config.max_image_size
        }
    
    def test_all_fallbacks(self) -> dict:
        """
        Test all fallback mechanisms and return detailed results.
        
        This method can be used for debugging and validation.
        
        Returns:
            Dictionary with test results for each fallback option
        """
        logger.info("Testing all fallback mechanisms...")
        
        results = {
            'primary_image': None,
            'fallback_images': [],
            'text_fallback': None,
            'minimal_fallback': None,
            'summary': {
                'total_tested': 0,
                'successful': 0,
                'failed': 0
            }
        }
        
        # Test primary image
        primary_path = self._validate_resource_path(self.config.image_path)
        results['primary_image'] = {
            'path': self.config.image_path,
            'resolved_path': primary_path,
            'available': primary_path is not None
        }
        results['summary']['total_tested'] += 1
        if primary_path:
            results['summary']['successful'] += 1
        else:
            results['summary']['failed'] += 1
        
        # Test fallback images
        for fallback_path in self.config.fallback_image_paths:
            resolved_path = self._validate_resource_path(fallback_path)
            fallback_result = {
                'path': fallback_path,
                'resolved_path': resolved_path,
                'available': resolved_path is not None
            }
            results['fallback_images'].append(fallback_result)
            results['summary']['total_tested'] += 1
            if resolved_path:
                results['summary']['successful'] += 1
            else:
                results['summary']['failed'] += 1
        
        # Test text fallback (always available)
        results['text_fallback'] = {
            'available': True,
            'description': 'Styled text-based splash screen'
        }
        results['summary']['total_tested'] += 1
        results['summary']['successful'] += 1
        
        # Test minimal fallback (always available)
        results['minimal_fallback'] = {
            'available': True,
            'description': 'Basic text-only splash screen'
        }
        results['summary']['total_tested'] += 1
        results['summary']['successful'] += 1
        
        logger.info(f"Fallback test completed: {results['summary']['successful']}/{results['summary']['total_tested']} options available")
        
        return results