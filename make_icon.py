import os
import sys
from PIL import Image, ImageDraw

def convert_svg_to_ico():
    print("Creating application icon...")
    ico_path = os.path.join("resources", "icons", "app_icon.ico")
    
    # Create icons directory if it doesn't exist
    os.makedirs(os.path.dirname(ico_path), exist_ok=True)
    
    try:
        # Create a simple colored image as icon
        sizes = [16, 32, 48, 64, 128]
        images = []
        
        for size in sizes:
            # Create base image with blue background
            img = Image.new('RGBA', (size, size), color=(52, 152, 219, 255))
            draw = ImageDraw.Draw(img)
            
            # Calculate proportions
            margin = int(size * 0.1)
            screen_height = int(size * 0.45)
            
            # Draw screen (white rectangle)
            draw.rectangle(
                [(margin, margin), (size - margin, margin + screen_height)],
                fill=(236, 240, 241, 255)
            )
            
            # Draw play button (red triangle)
            play_size = int(size * 0.25)
            play_x = int(size * 0.42)
            play_y = int(size * 0.3)
            draw.polygon(
                [(play_x, play_y - play_size/2), 
                 (play_x + play_size, play_y), 
                 (play_x, play_y + play_size/2)],
                fill=(231, 76, 60, 255)
            )
            
            # Draw thumbnails at the bottom
            thumb_size = int(size * 0.2)
            thumb_y = int(size * 0.7)
            spacing = int((size - 2*margin - 3*thumb_size) / 2)
            
            for i in range(3):
                left = margin + i * (thumb_size + spacing)
                draw.rectangle(
                    [(left, thumb_y), (left + thumb_size, thumb_y + thumb_size)],
                    fill=(236, 240, 241, 255)
                )
            
            images.append(img)
        
        # Save as ICO with multiple sizes
        images[0].save(ico_path, format='ICO', 
                      sizes=[(img.width, img.height) for img in images],
                      append_images=images[1:])
        
        print(f"Icon successfully created at {ico_path}")
        return True
        
    except Exception as e:
        print(f"Error creating icon: {e}")
        return False

if __name__ == "__main__":
    convert_svg_to_ico() 