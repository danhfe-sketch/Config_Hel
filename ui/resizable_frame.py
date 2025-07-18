import customtkinter as ctk
import tkinter as tk

class ColumnDivider(ctk.CTkFrame):
    """A draggable divider for resizing columns."""
    
    def __init__(self, master, left_column, right_column, min_left=100, min_right=100, **kwargs):
        """
        Initialize a column divider.
        
        Args:
            master: Parent widget
            left_column: Index of the column to the left of the divider
            right_column: Index of the column to the right of the divider
            min_left: Minimum width for the left column
            min_right: Minimum width for the right column
        """
        # Set a narrow width for the divider
        kwargs["width"] = kwargs.get("width", 5)
        kwargs["fg_color"] = kwargs.get("fg_color", "#888888")
        kwargs["cursor"] = "sb_h_double_arrow"  # Horizontal resize cursor
        
        super().__init__(master, **kwargs)
        
        self.master = master
        self.left_column = left_column
        self.right_column = right_column
        self.min_left = min_left
        self.min_right = min_right
        
        # Track drag state
        self.dragging = False
        self.start_x = 0
        self.start_width_left = 0
        self.start_width_right = 0
        
        # Bind mouse events
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_drag_start)
        self.bind("<ButtonRelease-1>", self._on_drag_end)
        self.bind("<B1-Motion>", self._on_drag_motion)
    
    def _on_enter(self, event):
        """Handle mouse enter event."""
        self.configure(fg_color="#AAAAAA")  # Highlight on hover
    
    def _on_leave(self, event):
        """Handle mouse leave event."""
        if not self.dragging:
            self.configure(fg_color="#888888")  # Reset color when not dragging
    
    def _on_drag_start(self, event):
        """Handle drag start event."""
        self.dragging = True
        self.start_x = event.x_root
        
        # Get current column widths
        self.start_width_left = self.master.grid_bbox(column=self.left_column)[2]  # Width of left column
        self.start_width_right = self.master.grid_bbox(column=self.right_column)[2]  # Width of right column
        
        # Change color to indicate dragging
        self.configure(fg_color="#5555FF")
    
    def _on_drag_end(self, event):
        """Handle drag end event."""
        self.dragging = False
        self.configure(fg_color="#888888")
    
    def _on_drag_motion(self, event):
        """Handle drag motion event."""
        if not self.dragging:
            return
        
        # Calculate the drag distance
        delta_x = event.x_root - self.start_x
        
        # Calculate new widths
        new_width_left = max(self.min_left, self.start_width_left + delta_x)
        new_width_right = max(self.min_right, self.start_width_right - delta_x)
        
        # Update column widths
        self.master.grid_columnconfigure(self.left_column, minsize=new_width_left)
        self.master.grid_columnconfigure(self.right_column, minsize=new_width_right)
        
        # Update the UI
        self.master.update_idletasks()


class ResizableFrame(ctk.CTkFrame):
    """A frame with resizable columns."""
    
    def __init__(self, master, column_count=3, **kwargs):
        """
        Initialize a frame with resizable columns.
        
        Args:
            master: Parent widget
            column_count: Number of columns in the frame
        """
        super().__init__(master, **kwargs)
        
        self.column_count = column_count
        self.dividers = []
        
        # Configure grid
        for i in range(column_count):
            self.grid_columnconfigure(i*2, weight=1)
            if i < column_count - 1:
                # Add a column for the divider (no weight)
                self.grid_columnconfigure(i*2 + 1, weight=0)
        
        # Create dividers
        for i in range(column_count - 1):
            divider = ColumnDivider(
                self,
                left_column=i*2,
                right_column=(i+1)*2
            )
            divider.grid(row=0, column=i*2 + 1, sticky="ns")
            self.dividers.append(divider)
    
    def add_widget(self, widget, column, **kwargs):
        """
        Add a widget to a specific column.
        
        Args:
            widget: Widget to add
            column: Column index (0-based)
            **kwargs: Additional grid options
        """
        if column >= self.column_count:
            raise ValueError(f"Column index {column} out of range (0-{self.column_count-1})")
        
        # Place widget in the appropriate grid cell
        widget.grid(column=column*2, **kwargs)