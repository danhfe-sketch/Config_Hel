#!/usr/bin/env python3
"""
Script to convert an image to Windows ICO format.

This script converts PNG/JPG images to ICO format with multiple sizes.
"""

from PIL import Image
import os
import sys

def create_ico_from_image(input_path, output_path):
    """
    Convert an image to ICO format with multiple sizes.
    
    Args:
        input_path: Path to input image (PNG, JPG, etc.)
        output_path: Path for output ICO file
    """
    try:
        # Open the source image
        img = Image.open(input_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Define icon sizes
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        # Create resized versions
        icon_images = []
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            icon_images.append(resized)
        
        # Save as ICO with multiple sizes
        icon_images[0].save(
            output_path,
            format='ICO',
            sizes=[(img.width, img.height) for img in icon_images],
            append_images=icon_images[1:]
        )
        
        print(f"✅ Successfully created icon: {output_path}")
        print(f"📏 Icon contains {len(sizes)} sizes: {', '.join([f'{w}x{h}' for w, h in sizes])}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating icon: {e}")
        return False

def main():
    """Main function with example usage."""
    print("=" * 50)
    print("Image to ICO Converter")
    print("=" * 50)
    
    # Example usage
    input_image = "my_app_logo.png"  # Change this to your image path
    output_icon = "assets/icons/my_custom_icon.ico"
    
    # Check if input exists
    if not os.path.exists(input_image):
        print(f"❌ Input image not found: {input_image}")
        print("\nUsage:")
        print("1. Place your image file (PNG/JPG) in the project folder")
        print("2. Update the 'input_image' variable in this script")
        print("3. Run this script to create the ICO file")
        return False
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_icon), exist_ok=True)
    
    # Convert image to ICO
    success = create_ico_from_image(input_image, output_icon)
    
    if success:
        print(f"\n✅ Icon created successfully!")
        print(f"📁 Location: {output_icon}")
        print(f"💡 Now update main.py to use this icon:")
        print(f'   icon_path = resource_path("{output_icon}")')
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)