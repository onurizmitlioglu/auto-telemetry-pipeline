import pytest
import os
from unittest.mock import MagicMock
from ota.firmware import create_package, generate_key_pair, FirmwareManager


@pytest.fixture
def key_pair():
    return generate_key_pair()


@pytest.fixture
def package(key_pair):
    private_key, _ = key_pair
    pkg = create_package("ENGINE", "2.15.0", private_key, size_kb=16)
    yield pkg
    # Cleanup
    if os.path.exists(pkg.file_path):
        os.remove(pkg.file_path)


@pytest.fixture
def firmware_manager(key_pair):
    _, public_key = key_pair
    return FirmwareManager("VHC-001", public_key)


def test_create_package_file_exists(package):
    """Create package file."""
    assert os.path.exists(package.file_path)


def test_create_package_checksum(package):
    """Checksum calculation."""
    import hashlib
    with open(package.file_path, "rb") as f:
        data = f.read()
    assert hashlib.sha256(data).hexdigest() == package.checksum


def test_create_package_has_signature(package):
    """İmza boş olmamalı."""
    assert len(package.signature) > 0


def test_stage_package_valid(firmware_manager, package):
    """Stage should success for valid signature"""
    assert firmware_manager.stage_package(package) is True


def test_stage_package_invalid_signature(package):
    """Stage should fail for invalid signature."""
    _, wrong_public_key = generate_key_pair()
    fm = FirmwareManager("VHC-002", wrong_public_key)
    assert fm.stage_package(package) is False


def test_stage_package_tampered_file(firmware_manager, package):
    """Stage should fail if file is corrupted."""
    with open(package.file_path, "wb") as f:
        f.write(b"tampered data")
    assert firmware_manager.stage_package(package) is False


def test_install_pending(firmware_manager, package):
    """Install successfull after staging."""
    firmware_manager.stage_package(package)
    assert firmware_manager.install_pending("ENGINE") is True


def test_install_without_stage(firmware_manager):
    """Instsall should fail without staging"""
    assert firmware_manager.install_pending("ENGINE") is False


def test_rollback(firmware_manager, package):
    """Rollback should remove pending package."""
    firmware_manager.stage_package(package)
    assert firmware_manager.rollback("ENGINE") is True
    assert firmware_manager.install_pending("ENGINE") is False


def test_get_current_version_default(firmware_manager):
    """Current version is 1.0.0 by default"""
    assert firmware_manager.get_current_version("ENGINE") == "1.0.0"


def test_get_current_version_after_install(firmware_manager, package):
    """Version update after install"""
    firmware_manager.stage_package(package)
    firmware_manager.install_pending("ENGINE")
    assert firmware_manager.get_current_version("ENGINE") == "2.15.0"


def test_handle_command_prepare_valid(firmware_manager, package):
    """PREPARE command should send READY status for valid signature."""
    statuses = []
    def mock_send_status(campaign_id, session_id, status_code, **kwargs):
        statuses.append(status_code)

    payload = {
        "cmd_type": "PREPARE",
        "campaign_id": "TEST-001",
        "session_id": "TEST-001-VHC-001",
        "ecu_target": "ENGINE",
        "fw_version": "2.15.0",
        "package_id": package.package_id,
        "checksum": package.checksum,
        "signature": package.signature.hex(),
    }
    firmware_manager.handle_command(payload, mock_send_status)
    assert "READY" in statuses


def test_handle_command_prepare_invalid(package):
    """Send ERROR status for PREPARE command if signature is invalid."""
    _, wrong_public_key = generate_key_pair()
    fm = FirmwareManager("VHC-002", wrong_public_key)
    
    statuses = []
    def mock_send_status(campaign_id, session_id, status_code, **kwargs):
        statuses.append(status_code)

    payload = {
        "cmd_type": "PREPARE",
        "campaign_id": "TEST-001",
        "session_id": "TEST-001-VHC-002",
        "ecu_target": "ENGINE",
        "fw_version": "2.15.0",
        "package_id": package.package_id,
        "checksum": package.checksum,
        "signature": package.signature.hex(),
    }
    fm.handle_command(payload, mock_send_status)
    assert "ERROR" in statuses