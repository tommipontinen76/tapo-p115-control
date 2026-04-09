import os
import shutil
import subprocess

PACKAGE_NAME = "tapo-p115-control"
VERSION = "1.0.4"
MAINTAINER = "Tapo P115 Control Team <tommi@users.noreply.github.com>"
DESCRIPTION = "A GUI application to control Tapo P115 smart plugs."

# Only deps that are genuinely universal across all Debian-based distros.
# PySide6, plugp100, and qasync are handled by postinst via pip.
DEPENDS = "python3, python3-pip, python3-aiohttp, libxcb-cursor0, libxcb-xinerama0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-shape0, libxcb-randr0, libxcb-xkb1, libxkbcommon-x11-0, libdbus-1-3"
SECTION = "utils"
PRIORITY = "optional"
ARCHITECTURE = "all"

# Python packages to install via pip (not reliably available as apt packages)
PIP_PACKAGES = ["PySide6", "qasync", "plugp100"]

def create_deb():
    build_dir = "tapo-p115-control-pkg"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    os.makedirs(f"{build_dir}/DEBIAN")
    os.makedirs(f"{build_dir}/usr/bin")
    os.makedirs(f"{build_dir}/usr/share/{PACKAGE_NAME}")
    os.makedirs(f"{build_dir}/usr/share/applications")

    # DEBIAN/control
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

    # postinst: install pip packages after the deb is unpacked
    pip_install_line = " ".join(PIP_PACKAGES)
    postinst_content = f"""#!/bin/bash
set -e
if [ "$1" = "configure" ]; then
    echo "Installing Python dependencies via pip..."
    pip3 install --break-system-packages {pip_install_line} || \
        pip3 install {pip_install_line}
fi
exit 0
"""
    postinst_path = f"{build_dir}/DEBIAN/postinst"
    with open(postinst_path, "w", newline='\n') as f:
        f.write(postinst_content)
    os.chmod(postinst_path, 0o755)

    # prerm: remove pip packages and app files on uninstall
    prerm_content = f"""#!/bin/bash
set -e
if [ "$1" = "remove" ]; then
    echo "Removing Python dependencies..."
    pip3 uninstall -y {" ".join(PIP_PACKAGES)} || true
    rm -rf "/usr/share/{PACKAGE_NAME}"
fi
exit 0
"""
    prerm_path = f"{build_dir}/DEBIAN/prerm"
    with open(prerm_path, "w", newline='\n') as f:
        f.write(prerm_content)
    os.chmod(prerm_path, 0o755)

    # Application files
    shutil.copy("main.py", f"{build_dir}/usr/share/{PACKAGE_NAME}/main.py")

    # Launcher
    launcher_path = f"{build_dir}/usr/bin/{PACKAGE_NAME}"
    with open(launcher_path, "w", newline='\n') as f:
        f.write(f"""#!/bin/bash
/usr/bin/python3 /usr/share/{PACKAGE_NAME}/main.py "$@"
""")
    os.chmod(launcher_path, 0o755)

    # .desktop entry
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

    try:
        subprocess.run(["dpkg-deb", "--build", build_dir], check=True)
        print(f"Successfully created {build_dir}.deb")
    except FileNotFoundError:
        print("Error: 'dpkg-deb' not found. Run this on a Debian-based system.")
    except subprocess.CalledProcessError as e:
        print(f"Error building .deb package: {e}")
    finally:
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)

if __name__ == "__main__":
    create_deb()