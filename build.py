import os
import subprocess
import sys
import shutil
import platform

def main():
    print("Building Video Library Application...")
    
    app_name = "VideoLibrary"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Generate icon from SVG
    try:
        import make_icon
        make_icon.convert_svg_to_ico()
        icon_path = os.path.join("resources", "icons", "app_icon.ico")
    except Exception as e:
        print(f"Warning: Could not generate icon: {e}")
        icon_path = None
    
    # Set up PyInstaller command
    cmd = [
        "pyinstaller",
        f"--name={app_name}",
        "--onefile",
        "--windowed",
        "--add-data=resources;resources",
        "--clean",
        "app.py"
    ]
    
    # Add icon if available
    if icon_path and os.path.exists(icon_path):
        cmd.insert(5, f"--icon={icon_path}")
    
    try:
        subprocess.check_call(cmd)
        
        executable_name = f"{app_name}.exe" if platform.system() == "Windows" else app_name
        executable_path = os.path.join(current_dir, "dist", executable_name)
        
        if os.path.exists(executable_path):
            print(f"Build successful! Executable created at: {executable_path}")
        else:
            print("Build completed but executable not found.")
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()