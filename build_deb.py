import os
import shutil
import subprocess

# Package metadata
PACKAGE_NAME = "tapo-p115-control"
VERSION = "1.0.0"
MAINTAINER = "Tapo P115 Control Team <tommi@users.noreply.github.com>"
DESCRIPTION = "A GUI application to control Tapo P115 smart plugs."
# Some dependencies may not be in official Debian repos and should be installed via pip if not found.
# Recommended: python3-pyside6, python3-aiohttp
DEPENDS = "python3, python3-pyside6, python3-aiohttp, python3-pip"
SECTION = "utils"
PRIORITY = "optional"
ARCHITECTURE = "all"

def create_deb():
    # Temporary directory for building the package
    build_dir = "tapo-p115-control-pkg"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    
    # Create directory structure
    os.makedirs(f"{build_dir}/DEBIAN")
    os.makedirs(f"{build_dir}/usr/bin")
    os.makedirs(f"{build_dir}/usr/share/{PACKAGE_NAME}")
    os.makedirs(f"{build_dir}/usr/share/applications")
    
    # 1. Create the DEBIAN/control file
    control_content = f"""Package: {PACKAGE_NAME}
Version: {VERSION}
Section: {SECTION}
Priority: {PRIORITY}
Architecture: {ARCHITECTURE}
Depends: {DEPENDS}
Maintainer: {MAINTAINER}
Description: {DESCRIPTION}
"""
    with open(f"{build_dir}/DEBIAN/control", "w") as f:
        f.write(control_content)
    
    # 2. Copy the application files to /usr/share/tapo-p115-control
    # We copy main.py to /usr/share/tapo-p115-control/main.py
    shutil.copy("main.py", f"{build_dir}/usr/share/{PACKAGE_NAME}/main.py")
    
    # 3. Create a launcher script in /usr/bin/tapo-p115-control
    launcher_path = f"{build_dir}/usr/bin/{PACKAGE_NAME}"
    launcher_content = f"""#!/bin/bash
python3 /usr/share/{PACKAGE_NAME}/main.py "$@"
"""
    with open(launcher_path, "w") as f:
        f.write(launcher_content)
    os.chmod(launcher_path, 0o755)
    
    # 4. Create the .desktop entry
    desktop_content = f"""[Desktop Entry]
Type=Application
Name=Tapo P115 Control
Comment={DESCRIPTION}
Exec={PACKAGE_NAME}
Icon=utilities-terminal
Terminal=false
Categories=Utility;
"""
    with open(f"{build_dir}/usr/share/applications/{PACKAGE_NAME}.desktop", "w") as f:
        f.write(desktop_content)
    
    # 5. Build the .deb package
    try:
        subprocess.run(["dpkg-deb", "--build", build_dir], check=True)
        print(f"Successfully created {PACKAGE_NAME}.deb")
    except FileNotFoundError:
        print("Error: 'dpkg-deb' command not found. This script must be run on a Debian-based system or a system with dpkg-deb installed.")
    except subprocess.CalledProcessError as e:
        print(f"Error building .deb package: {e}")
    finally:
        # Clean up the build directory
        # shutil.rmtree(build_dir)
        pass

if __name__ == "__main__":
    create_deb()
