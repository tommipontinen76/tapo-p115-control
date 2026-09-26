import os
import shutil
import subprocess

PACKAGE_NAME = "tapo-p115-control"
VERSION = "1.0.5"
MAINTAINER = "Tapo P115 Control Team <tommi@users.noreply.github.com>"
DESCRIPTION = "A GUI and CLI application to control Tapo P115 smart plugs."

# All pip-only packages are vendored into the package; only system libs remain in REQUIRES.
REQUIRES = (
    "python3, "
    "libxcb, "
    "libxcb-cursor, "
    "libxcb-xinerama, "
    "libxcb-icccm, "
    "libxcb-image, "
    "libxcb-keysyms1, "
    "libxcb-render-util, "
    "libxcb-shape, "
    "libxcb-randr, "
    "libxcb-xkb, "
    "libxkbcommon-x11, "
    "dbus-libs"
)

LICENSE = "MIT"
GROUP = "Applications/Utilities"


def get_architecture():
    """Determine the package architecture by querying rpm or falling back to platform.machine()."""
    # 1. Environment variable override
    if "RPM_ARCH" in os.environ:
        return os.environ["RPM_ARCH"]

    # 2. Query rpm (the standard way)
    try:
        result = subprocess.run(
            ["rpm", "--eval", "%{_arch}"],
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
        return "x86_64"
    elif machine in ["aarch64", "arm64", "armv8l"]:
        return "aarch64"
    elif machine.startswith("armv7") or machine == "armhf":
        return "armv7hl"
    elif machine in ["i386", "i686"]:
        return "i686"
    return machine


# PySide6 ships compiled .so files, so the package is architecture-specific.
ARCHITECTURE = get_architecture()

# All bundled via pip into vendor/ -- none of these are in standard Fedora/RHEL repos.
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
        "No python3 with pip found. Install pip with: sudo dnf install python3-pip"
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


def create_rpm():
    build_dir = "tapo-p115-control-pkg"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    os.makedirs(f"{build_dir}/BUILD")
    os.makedirs(f"{build_dir}/BUILDROOT")
    os.makedirs(f"{build_dir}/RPMS")
    os.makedirs(f"{build_dir}/SOURCES")
    os.makedirs(f"{build_dir}/SPECS")
    os.makedirs(f"{build_dir}/SRPMS")

    # 1. Spec file
    spec_content = f"""Name:           {PACKAGE_NAME}
Version:        {VERSION}
Release:        1%{{?dist}}
Summary:        {DESCRIPTION}
License:        {LICENSE}
Group:          {GROUP}
BuildArch:      {ARCHITECTURE}
Requires:       {REQUIRES}

%description
{DESCRIPTION}

%prep
# Nothing to prepare

%build
# Nothing to build

%install
rm -rf %{{buildroot}}
mkdir -p %{{buildroot}}/usr/bin
mkdir -p %{{buildroot}}/usr/share/{PACKAGE_NAME}
mkdir -p %{{buildroot}}/usr/share/applications

# Copy application source
cp main.py %{{buildroot}}/usr/share/{PACKAGE_NAME}/main.py
cp cli.py %{{buildroot}}/usr/share/{PACKAGE_NAME}/cli.py

# Bundle qasync + plugp100 into vendor/
# (done externally by bundle_pip_packages before rpmbuild is called)

# GUI Launcher
cat > %{{buildroot}}/usr/bin/{PACKAGE_NAME} << 'EOF'
#!/bin/bash
export PYTHONPATH="/usr/share/{PACKAGE_NAME}/vendor:$PYTHONPATH"
exec /usr/bin/python3 "/usr/share/{PACKAGE_NAME}/main.py" "$@"
EOF
chmod 755 %{{buildroot}}/usr/bin/{PACKAGE_NAME}

# CLI Launcher
cat > %{{buildroot}}/usr/bin/{PACKAGE_NAME}-cli << 'EOF'
#!/bin/bash
export PYTHONPATH="/usr/share/{PACKAGE_NAME}/vendor:$PYTHONPATH"
exec /usr/bin/python3 "/usr/share/{PACKAGE_NAME}/cli.py" "$@"
EOF
chmod 755 %{{buildroot}}/usr/bin/{PACKAGE_NAME}-cli

# .desktop entry
cat > %{{buildroot}}/usr/share/applications/{PACKAGE_NAME}.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Tapo P115 Control
Comment={DESCRIPTION}
Exec={PACKAGE_NAME}
Icon=utilities-terminal
Terminal=false
Categories=Utility;
EOF

%post
# Post-install: nothing needed

%preun
# Pre-uninstall: nothing needed

%postun
# Post-uninstall: clean up app directory
if [ $1 -eq 0 ]; then
    rm -rf "/usr/share/{PACKAGE_NAME}"
fi

%files
%defattr(-,root,root,-)
/usr/bin/{PACKAGE_NAME}
/usr/bin/{PACKAGE_NAME}-cli
/usr/share/{PACKAGE_NAME}/main.py
/usr/share/{PACKAGE_NAME}/cli.py
/usr/share/{PACKAGE_NAME}/vendor/
/usr/share/applications/{PACKAGE_NAME}.desktop

%changelog
* Sat Sep 26 2026 {MAINTAINER} - {VERSION}-1
- Initial RPM package
"""
    spec_path = f"{build_dir}/SPECS/{PACKAGE_NAME}.spec"
    with open(spec_path, "w", newline='\n') as f:
        f.write(spec_content)

    # 2. Copy application source into BUILDROOT for the spec to reference
    buildroot = f"{build_dir}/BUILDROOT"
    os.makedirs(f"{buildroot}/usr/bin")
    os.makedirs(f"{buildroot}/usr/share/{PACKAGE_NAME}")
    os.makedirs(f"{buildroot}/usr/share/applications")

    shutil.copy("main.py", f"{buildroot}/usr/share/{PACKAGE_NAME}/main.py")
    shutil.copy("cli.py", f"{buildroot}/usr/share/{PACKAGE_NAME}/cli.py")

    # 3. Bundle qasync + plugp100 into vendor/
    bundle_pip_packages(buildroot)

    # 4. Launchers -- prepends vendor dir to PYTHONPATH so bundled packages are found
    # We use /usr/bin/python3 which is standard on RPM-based systems.

    # GUI Launcher
    launcher_path = f"{buildroot}/usr/bin/{PACKAGE_NAME}"
    launcher_content = f"""#!/bin/bash
export PYTHONPATH="/usr/share/{PACKAGE_NAME}/vendor:$PYTHONPATH"
exec /usr/bin/python3 "/usr/share/{PACKAGE_NAME}/main.py" "$@"
"""
    with open(launcher_path, "w", newline='\n') as f:
        f.write(launcher_content)
    os.chmod(launcher_path, 0o755)

    # CLI Launcher
    cli_launcher_path = f"{buildroot}/usr/bin/{PACKAGE_NAME}-cli"
    cli_launcher_content = f"""#!/bin/bash
export PYTHONPATH="/usr/share/{PACKAGE_NAME}/vendor:$PYTHONPATH"
exec /usr/bin/python3 "/usr/share/{PACKAGE_NAME}/cli.py" "$@"
"""
    with open(cli_launcher_path, "w", newline='\n') as f:
        f.write(cli_launcher_content)
    os.chmod(cli_launcher_path, 0o755)

    # 5. .desktop entry
    with open(f"{buildroot}/usr/share/applications/{PACKAGE_NAME}.desktop", "w", newline='\n') as f:
        f.write(f"""[Desktop Entry]
Type=Application
Name=Tapo P115 Control
Comment={DESCRIPTION}
Exec={PACKAGE_NAME}
Icon=utilities-terminal
Terminal=false
Categories=Utility;
""")

    # 6. Build the .rpm
    rpm_output = f"{PACKAGE_NAME}-{VERSION}-1.{ARCHITECTURE}.rpm"
    print(f"Building {rpm_output} (this may take a minute for compression)...")
    try:
        subprocess.run(
            [
                "rpmbuild", "-bb",
                "--define", f"_topdir {os.path.abspath(build_dir)}",
                spec_path,
            ],
            check=True,
        )
        # Find the built RPM
        rpm_path = None
        for root, dirs, files in os.walk(f"{build_dir}/RPMS"):
            for fname in files:
                if fname.endswith(".rpm"):
                    rpm_path = os.path.join(root, fname)
                    break
        if rpm_path:
            # Copy to current directory
            dest = os.path.join(os.getcwd(), os.path.basename(rpm_path))
            shutil.copy2(rpm_path, dest)
            print(f"Successfully created {dest}")
        else:
            print("Warning: rpmbuild succeeded but RPM file not found.")
    except FileNotFoundError:
        print("Error: 'rpmbuild' not found. Run this on an RPM-based system with rpm-build installed.")
    except subprocess.CalledProcessError as e:
        print(f"Error building .rpm package: {e}")
    finally:
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)


if __name__ == "__main__":
    create_rpm()
