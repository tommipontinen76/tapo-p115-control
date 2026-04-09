import os
import shutil
import subprocess

PACKAGE_NAME = "tapo-p115-control"
VERSION = "1.0.4"
MAINTAINER = "Tapo P115 Control Team <tommi@users.noreply.github.com>"
DESCRIPTION = "A GUI application to control Tapo P115 smart plugs."

# Added libxcb-cursor0 and other Qt6 dependencies.
# Using python3-pyside6 (or qtpy-pyside6 metapackage) and python3-aiohttp from system packages.
# Note: plugp100 and qasync might not be in standard repos, so we assume they are provided or handled.
DEPENDS = "python3, python3-pyside6 | python3-qtpy-pyside6, python3-aiohttp, libxcb-cursor0, libxcb-xinerama0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-shape0, libxcb-randr0, libxcb-xkb1, libxkbcommon-x11-0, libdbus-1-3"
SECTION = "utils"
PRIORITY = "optional"
ARCHITECTURE = "all"

def create_deb():
    build_dir = "tapo-p115-control-pkg"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

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

    # 1a. Create the prerm script to clean up the application directory
    prerm_content = f"""#!/bin/bash
set -e
if [ "$1" = "remove" ]; then
    rm -rf "/usr/share/{PACKAGE_NAME}"
fi
exit 0
"""
    prerm_path = f"{build_dir}/DEBIAN/prerm"
    with open(prerm_path, "w", newline='\n') as f:
        f.write(prerm_content)
    os.chmod(prerm_path, 0o755)

    # 2. Copy the application files to /usr/share/tapo-p115-control
    shutil.copy("main.py", f"{build_dir}/usr/share/{PACKAGE_NAME}/main.py")

    # 3. Create a launcher script in /usr/bin/tapo-p115-control
    launcher_path = f"{build_dir}/usr/bin/{PACKAGE_NAME}"
    launcher_content = f"""#!/bin/bash
# Use system python to run the application
/usr/bin/python3 /usr/share/{PACKAGE_NAME}/main.py "$@"
"""
    with open(launcher_path, "w", newline='\n') as f:
        f.write(launcher_content)
    os.chmod(launcher_path, 0o755)
    
    # 4. Create the .desktop entry
    with open(f"{build_dir}/usr/share/applications/{PACKAGE_NAME}.desktop", "w", newline='\n') as f:
        f.write(f"""[Desktop Entry]
Type=Application
Name=Tapo P115 Control
Comment={DESCRIPTION}
Exec={PACKAGE_NAME}
Icon=utilities-terminal
Terminal=false
Categories=Utility;
""")

    # 5. Build the .deb package
    try:
        subprocess.run(["dpkg-deb", "--build", build_dir], check=True)
        print(f"Successfully created {PACKAGE_NAME}.deb")
    except FileNotFoundError:
        print("Error: 'dpkg-deb' not found. Run this on a Debian-based system.")
    except subprocess.CalledProcessError as e:
        print(f"Error building .deb package: {e}")
    finally:
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)

if __name__ == "__main__":
    create_deb()