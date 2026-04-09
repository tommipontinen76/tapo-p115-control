import os
import shutil
import subprocess
import sys
from pathlib import Path

def get_downloads_folder():
    """Returns the current user's Downloads folder path."""
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return Path(location)
    else:
        return Path.home() / "Downloads"

def build_exe():
    project_root = Path(__file__).parent.absolute()
    main_script = project_root / "main.py"
    exe_name = "TapoP115Control.exe"
    
    if not main_script.exists():
        print(f"Error: {main_script} not found.")
        sys.exit(1)

    print("--- Checking for PyInstaller ---")
    try:
        import PyInstaller
        print("PyInstaller found.")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    print("--- Building Executable ---")
    # PyInstaller command:
    # --onefile: Create a single executable
    # --noconsole: Hide the console window (it's a GUI app)
    # --name: Specify the name of the executable
    # --clean: Clean PyInstaller cache and remove temporary files before building
    # --collect-all: Ensure all submodules and data for specific libraries are included
    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name", "TapoP115Control",
        "--clean",
        "--collect-all", "plugp100",
        "--collect-all", "qasync",
        "--hidden-import", "PySide6",
        str(main_script)
    ]
    
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Error during PyInstaller execution: {e}")
        sys.exit(1)

    print("--- Moving Executable to Downloads ---")
    dist_folder = project_root / "dist"
    exe_path = dist_folder / exe_name
    downloads_folder = get_downloads_folder()
    destination_path = downloads_folder / exe_name

    if exe_path.exists():
        try:
            shutil.move(str(exe_path), str(destination_path))
            print(f"Successfully moved executable to: {destination_path}")
        except Exception as e:
            print(f"Error moving executable: {e}")
            sys.exit(1)
    else:
        print(f"Error: {exe_path} was not created.")
        sys.exit(1)

    print("--- Cleaning Up ---")
    # Clean up build artifacts
    build_folder = project_root / "build"
    spec_file = project_root / "TapoP115Control.spec"
    
    if build_folder.exists():
        shutil.rmtree(build_folder)
    if dist_folder.exists():
        shutil.rmtree(dist_folder)
    if spec_file.exists():
        spec_file.unlink()
    
    print("Cleanup finished.")
    print(f"Build complete! Your executable is in {destination_path}")

if __name__ == "__main__":
    build_exe()
