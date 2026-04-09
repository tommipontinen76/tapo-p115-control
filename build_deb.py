import os
import shutil
import subprocess

# Package metadata
PACKAGE_NAME = "tapo-p115-control"
VERSION = "1.0.3"
MAINTAINER = "Tapo P115 Control Team <tommi@users.noreply.github.com>"
DESCRIPTION = "A GUI application to control Tapo P115 smart plugs."
# We'll use a virtual environment in /usr/share/tapo-p115-control/venv 
# to avoid conflicts with system-wide python packages.
# Added libxcb-cursor0 and other Qt6 dependencies to solve 'xcb' plugin issues.
DEPENDS = "python3, python3-pip, python3-venv, libxcb-cursor0, libxcb-xinerama0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-shape0, libxcb-randr0, libxcb-xkb1, libxkbcommon-x11-0, libdbus-1-3"
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
    with open(f"{build_dir}/DEBIAN/control", "w", newline='\n') as f:
        f.write(control_content)

    # 1a. Create the postinst script to install pip dependencies in a venv
    postinst_content = f"""#!/bin/bash
set -e
VENV_DIR="/usr/share/{PACKAGE_NAME}/venv"
echo "Setting up virtual environment in $VENV_DIR..."
python3 -m venv "$VENV_DIR"
echo "Installing dependencies into virtual environment..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install PySide6 aiohttp plugp100 qasync --upgrade
chown -R root:root "$VENV_DIR"
exit 0
"""
    postinst_path = f"{build_dir}/DEBIAN/postinst"
    with open(postinst_path, "w", newline='\n') as f:
        f.write(postinst_content)
    os.chmod(postinst_path, 0o755)

    # 2. Copy the application files to /usr/share/tapo-p115-control
    # We copy main.py to /usr/share/tapo-p115-control/main.py
    shutil.copy("main.py", f"{build_dir}/usr/share/{PACKAGE_NAME}/main.py")
    
    # 3. Create a launcher script in /usr/bin/tapo-p115-control
    launcher_path = f"{build_dir}/usr/bin/{PACKAGE_NAME}"
    launcher_content = f"""#!/bin/bash
# Use the virtual environment's python to run the application
/usr/share/{PACKAGE_NAME}/venv/bin/python /usr/share/{PACKAGE_NAME}/main.py "$@"
"""
    with open(launcher_path, "w", newline='\n') as f:
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
    with open(f"{build_dir}/usr/share/applications/{PACKAGE_NAME}.desktop", "w", newline='\n') as f:
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
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)

if __name__ == "__main__":
    create_deb()
