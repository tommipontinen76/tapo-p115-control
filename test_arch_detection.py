import os
import subprocess
from unittest.mock import MagicMock, patch

# Import the function from build_deb.py
# Since it's in the same directory, we can try to import it directly
try:
    from build_deb import get_architecture
except ImportError:
    # If it fails, we can try to exec it (not ideal, but let's assume import works in this environment)
    pass

def test_get_architecture():
    print("Testing get_architecture...")
    
    # 1. Test Environment Variable
    with patch.dict(os.environ, {"DEB_ARCH": "test_arch"}):
        arch = get_architecture()
        print(f"  Env var test: {arch} == test_arch")
        assert arch == "test_arch"

    # 2. Test dpkg success
    with patch.dict(os.environ, {}, clear=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="arm64\n", returncode=0)
            arch = get_architecture()
            print(f"  dpkg test: {arch} == arm64")
            assert arch == "arm64"
            mock_run.assert_called_with(["dpkg", "--print-architecture"], capture_output=True, text=True, check=True)

    # 3. Test fallback to platform.machine()
    with patch.dict(os.environ, {}, clear=True):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch("platform.machine") as mock_machine:
                # Test aarch64
                mock_machine.return_value = "aarch64"
                arch = get_architecture()
                print(f"  Fallback aarch64: {arch} == arm64")
                assert arch == "arm64"
                
                # Test x86_64
                mock_machine.return_value = "x86_64"
                arch = get_architecture()
                print(f"  Fallback x86_64: {arch} == amd64")
                assert arch == "amd64"
                
                # Test armv7l
                mock_machine.return_value = "armv7l"
                arch = get_architecture()
                print(f"  Fallback armv7l: {arch} == armhf")
                assert arch == "armhf"

    print("All tests passed!")

if __name__ == "__main__":
    test_get_architecture()
