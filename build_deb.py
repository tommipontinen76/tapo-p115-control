import os
import shutil
import subprocess
import sys

PACKAGE_NAME = "tapo-p115-control"
VERSION = "1.0.4"
MAINTAINER = "Tapo P115 Control Team <tommi@users.noreply.github.com>"
DESCRIPTION = "A GUI application to control Tapo P115 smart plugs."

# python3-pyside6 is the correct package name (the alternative was fictitious).
# qasync and plugp100 are not in standard repos -- bundled via pip into the package instead.
DEPENDS = (
    "python3, "
    "python3-pyside6, "
    "python3-aiohttp, "
    "libxcb-cursor0, "
    "libxcb-xinerama0, "
    "libxcb-icccm4, "
    "libxcb-image0, "
    "libxcb-keysyms1, "
    "libxcb-render-util0, "
    "libxcb-shape0, "
    "libxcb-randr0, "
    "libxcb-xkb1, "
    "libxkbcommon-x11-0, "
    "libdbus-1-3"
)

SECTION = "utils"
PRIORITY = "optional"
ARCHITECTURE = "all"

# Packages not available in standard Debian/Ubuntu repos -- bundled into the .deb.
PIP_BUNDLE = ["qasync", "plugp100"]
VENDOR_DIR = f"usr/share/{PACKAGE_NAME}/vendor"


def bundle_pip_packages(build_dir):
    """Download PIP_BUNDLE packages into the vendor directory inside the package tree."""
    vendor_path = os.path.join(build_dir, VENDOR_DIR)
    os.makedirs(vendor_path, exist_ok=True)
    print(f"Bundling pip packages into {vendor_path}: {PIP_BUNDLE}")
    try:
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install",
                "--target", vendor_path,
                "--no-deps",          # avoid duplicating system packages
                "--upgrade",
            ] + PIP_BUNDLE,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error bundling pip packages: {e}")
        raise


def create_deb():
    build_dir = "tapo-p115-control-pkg"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    os.makedirs(f"{build_dir}/DEBIAN")
    os.makedirs(f"{build_dir}/usr/bin")
    os.makedirs(f"{build_dir}/usr/share/{PACKAGE_NAME}")
    os.makedirs(f"{build_dir}/usr/share/applications")

    # 1. DEBIAN/control
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

    # 1a. prerm -- clean up app directory on removal
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

    # 2. Copy application source
    shutil.copy("main.py", f"{build_dir}/usr/share/{PACKAGE_NAME}/main.py")

    # 3. Bundle qasync + plugp100 into vendor/
    bundle_pip_packages(build_dir)

    # 4. Launcher -- prepends vendor dir to PYTHONPATH so bundled packages are found
    launcher_path = f"{build_dir}/usr/bin/{PACKAGE_NAME}"
    launcher_content = f"""#!/bin/bash
export PYTHONPATH="/usr/share/{PACKAGE_NAME}/vendor:$PYTHONPATH"
exec /usr/bin/python3 /usr/share/{PACKAGE_NAME}/main.py "$@"
"""
    with open(launcher_path, "w", newline='\n') as f:
        f.write(launcher_content)
    os.chmod(launcher_path, 0o755)

    # 5. .desktop entry
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

    # 6. Build the .deb
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