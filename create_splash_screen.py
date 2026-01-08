from PIL import Image, ImageDraw, ImageFont
import os

def create_splash_screen(version_text, master_image_path, output_path):
    """
    Adds a version text to a master splash screen image.

    Args:
        version_text (str): The version text to display on the splash screen.
        master_image_path (str): The path to the master splash screen image.
        output_path (str): The path to save the generated image.
    """
    try:
        # Open the master image
        image = Image.open(master_image_path).convert("RGBA")
        draw = ImageDraw.Draw(image)

        # Font settings
        try:
            font = ImageFont.truetype("arial.ttf", 35)
        except IOError:
            font = ImageFont.load_default()

        # Text color
        text_color = (255, 255, 255, 255)  # White

        # Position for the version text (centered)
        text_bbox = draw.textbbox((0, 0), version_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (image.width - text_width) / 2
        y = (image.height - text_height) / 2 + 100  # Adjust Y position as needed

        # Draw the version text
        draw.text((x, y), version_text, font=font, fill=text_color)

        # Save the image
        image.save(output_path, "PNG")
        print(f"Splash screen saved to {output_path}")

    except FileNotFoundError:
        print(f"Error: Master splash image not found at '{master_image_path}'")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    version = "1.3.2"
    master_image = "Master_splash.png"
    output_image = "splash.png"
    create_splash_screen(f"Version {version}", master_image, output_image)
