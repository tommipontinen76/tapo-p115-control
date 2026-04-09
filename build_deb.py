import os
import shutil
import subprocess

PACKAGE_NAME = "tapo-p115-control"
VERSION = "1.0.5"
MAINTAINER = "Tapo P115 Control Team <tommi@users.noreply.github.com>"
DESCRIPTION = "A GUI application to control Tapo P115 smart plugs."

# All pip-only packages are vendored into the package; only system libs remain in DEPENDS.
DEPENDS = (
    "python3, "
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
def get_architecture():
    """Determine the package architecture by querying dpkg or falling back to platform.machine()."""
    # 1. Environment variable override
    if "DEB_ARCH" in os.environ:
        return os.environ["DEB_ARCH"]

    # 2. Query dpkg-architecture (the standard way)
    try:
        result = subprocess.run(
            ["dpkg", "--print-architecture"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # 3. Fallback to platform.machine()
    import platform
    machine = platform.machine().lower()
    if machine in ["x86_64", "amd64"]:
        return "amd64"
    elif machine in ["aarch64", "arm64", "armv8l"]:
        return "arm64"
    elif machine.startswith("armv7") or machine == "armhf":
        return "armhf"
    elif machine in ["i386", "i686"]:
        return "i386"
    return machine


# PySide6 ships compiled .so files, so the package is architecture-specific.
ARCHITECTURE = get_architecture()

# All bundled via pip into vendor/ -- none of these are in standard Ubuntu/Mint repos.
# We use PySide6-Essentials to keep the package size manageable (excludes Addons like Qt3D, etc).
PIP_BUNDLE = ["PySide6-Essentials", "qasync", "plugp100"]
VENDOR_DIR = f"usr/share/{PACKAGE_NAME}/vendor"


def find_python3():
    """Return a python3 interpreter that has pip available."""
    # We prefer the system's default python3 to ensure binary compatibility
    # with the launcher script which uses /usr/bin/python3.
    candidates = ["python3", "python3.12", "python3.11", "python3.10"]
    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, "-m", "pip", "--version"],
                capture_output=True,
            )
            if result.returncode == 0:
                return candidate
        except FileNotFoundError:
            continue
    raise RuntimeError(
        "No python3 with pip found. Install pip with: sudo apt install python3-pip"
    )


def bundle_pip_packages(build_dir):
    """Download PIP_BUNDLE packages into the vendor directory inside the package tree."""
    vendor_path = os.path.join(build_dir, VENDOR_DIR)
    os.makedirs(vendor_path, exist_ok=True)
    python = find_python3()
    print(f"Using {python} to bundle {PIP_BUNDLE} into {vendor_path}")
    try:
        subprocess.run(
            [
                python, "-m", "pip", "install",
                "--target", vendor_path,
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
    # We use /usr/bin/python3 which is standard on Debian systems.
    launcher_path = f"{build_dir}/usr/bin/{PACKAGE_NAME}"
    launcher_content = f"""#!/bin/bash
export PYTHONPATH="/usr/share/{PACKAGE_NAME}/vendor:$PYTHONPATH"
exec /usr/bin/python3 "/usr/share/{PACKAGE_NAME}/main.py" "$@"
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
    print(f"Building {PACKAGE_NAME}_{VERSION}_{ARCHITECTURE}.deb (this may take a minute for compression)...")
    try:
        subprocess.run(["dpkg-deb", "--build", build_dir, f"{PACKAGE_NAME}_{VERSION}_{ARCHITECTURE}.deb"], check=True)
        print(f"Successfully created {PACKAGE_NAME}_{VERSION}_{ARCHITECTURE}.deb")
    except FileNotFoundError:
        print("Error: 'dpkg-deb' not found. Run this on a Debian-based system.")
    except subprocess.CalledProcessError as e:
        print(f"Error building .deb package: {e}")
    finally:
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)


if __name__ == "__main__":
    create_deb()