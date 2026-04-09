import os
import shutil
import subprocess
import sys
from pathlib import Path

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

    print(f"--- Copying Executable to Output Folder: {exe_name} ---")
    dist_folder = project_root / "dist"
    # PyInstaller creates the exe with .exe extension on Windows
    # If on non-Windows, it might not have .exe but we are on Windows here.
    output_exe_name = f"{exe_name}.exe" if os.name == 'nt' else exe_name
    exe_path = dist_folder / output_exe_name
    
    # Use output folder in project root by default
    ci_output = os.environ.get("CI_OUTPUT", str(project_root / "output"))
    destination_path = Path(ci_output) / output_exe_name
    os.makedirs(ci_output, exist_ok=True)

    if exe_path.exists():
        try:
            shutil.copy2(str(exe_path), str(destination_path))
            print(f"Successfully copied executable to: {destination_path}")
        except Exception as e:
            print(f"Error copying executable {exe_name}: {e}")
            sys.exit(1)
    else:
        print(f"Error: {exe_path} was not created.")
        sys.exit(1)

    print(f"Build complete for {exe_name}! Your executable is in {destination_path}")

if __name__ == "__main__":
    # Build GUI version
    build_exe("main.py", "TapoP115Control", noconsole=True)
    # Build CLI version
    build_exe("cli.py", "TapoP115Control-CLI", noconsole=False)
