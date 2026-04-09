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

def build_exe(script_name, exe_name, noconsole=True):
    project_root = Path(__file__).parent.absolute()
    main_script = project_root / script_name
    
    if not main_script.exists():
        print(f"Error: {main_script} not found.")
        sys.exit(1)

    print(f"--- Checking for PyInstaller (Building {exe_name}) ---")
    try:
        import PyInstaller
        print("PyInstaller found.")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    print(f"--- Building Executable: {exe_name} ---")
    # PyInstaller command:
    # --onefile: Create a single executable
    # --noconsole: Hide the console window (it's a GUI app)
    # --name: Specify the name of the executable
    # --clean: Clean PyInstaller cache and remove temporary files before building
    # --collect-all: Ensure all submodules and data for specific libraries are included
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", exe_name,
        "--clean",
        "--collect-all", "plugp100",
        "--collect-all", "qasync",
        "--hidden-import", "PySide6",
        str(main_script)
    ]
    if noconsole:
        cmd.insert(2, "--noconsole")
    
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Error during PyInstaller execution for {exe_name}: {e}")
        sys.exit(1)

    print(f"--- Moving Executable to Output Folder: {exe_name} ---")
    dist_folder = project_root / "dist"
    # PyInstaller creates the exe with .exe extension on Windows
    # If on non-Windows, it might not have .exe but we are on Windows here.
    output_exe_name = f"{exe_name}.exe" if os.name == 'nt' else exe_name
    exe_path = dist_folder / output_exe_name
    
    # If CI_OUTPUT is set, use it; otherwise, use Downloads.
    ci_output = os.environ.get("CI_OUTPUT")
    if ci_output:
        destination_path = Path(ci_output) / output_exe_name
        os.makedirs(ci_output, exist_ok=True)
    else:
        downloads_folder = get_downloads_folder()
        destination_path = downloads_folder / output_exe_name

    if exe_path.exists():
        try:
            if destination_path.exists():
                destination_path.unlink()
            shutil.move(str(exe_path), str(destination_path))
            print(f"Successfully moved executable to: {destination_path}")
        except Exception as e:
            print(f"Error moving executable {exe_name}: {e}")
            sys.exit(1)
    else:
        print(f"Error: {exe_path} was not created.")
        sys.exit(1)

    print(f"--- Cleaning Up for {exe_name} ---")
    # Clean up build artifacts
    build_folder = project_root / "build"
    spec_file = project_root / f"{exe_name}.spec"
    
    if build_folder.exists():
        shutil.rmtree(build_folder)
    if dist_folder.exists():
        shutil.rmtree(dist_folder)
    if spec_file.exists():
        spec_file.unlink()
    
    print(f"Cleanup finished for {exe_name}.")
    print(f"Build complete! Your executable is in {destination_path}")

if __name__ == "__main__":
    # Build GUI version
    build_exe("main.py", "TapoP115Control", noconsole=True)
    # Build CLI version
    build_exe("cli.py", "TapoP115Control-CLI", noconsole=False)
