import hashlib
import os
import json
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

@dataclass
class FirmwarePackage:
    ecu_target: str
    version_major: int
    version_minor: int
    version_patch: int
    package_id: str
    file_path: str
    checksum: str
    size_bytes: int
    signature: bytes = b""

    @property
    def version(self) -> str:
        return f"{self.version_major}.{self.version_minor}.{self.version_patch}"
    
def create_package(ecu_target: str, version: str, private_key, size_kb: int = 512) -> FirmwarePackage:
    major, minor, patch = map(int, version.split("."))
    package_id = f"{ecu_target}-{version}"
        
    os.makedirs("ota/packages", exist_ok=True)
    file_path = f"ota/packages/{package_id}.bin"
        
    # Create binary file
    data = os.urandom(size_kb * 1024)
    with open(file_path, "wb") as f:
        f.write(data)
        
    # SHA-256 checksum
    checksum = hashlib.sha256(data).hexdigest()

    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
        
    return FirmwarePackage(
        ecu_target=ecu_target,
        version_major=major,
        version_minor=minor,
        version_patch=patch,
        package_id=package_id,
        file_path=file_path,
        checksum=checksum,
        size_bytes=len(data),
        signature=signature,
    )

def generate_key_pair():
    """Generate OEM private/public key pair"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key


class FirmwareManager:
    def __init__(self, vehicle_id: str, public_key):
        self.vehicle_id = vehicle_id
        self._public_key = public_key
        self._installed: dict[str, FirmwarePackage] = {}  # ecu_target → package
        self._pending: dict[str, FirmwarePackage] = {}    # ecu_target → package


    def get_current_version(self, ecu_target: str) -> str:
        if ecu_target in self._installed:
            return self._installed[ecu_target].version
        return "1.0.0"  # default

    def stage_package(self, package: FirmwarePackage) -> bool:
        if not os.path.exists(package.file_path):
            return False
        
        with open(package.file_path, "rb") as f:
            data = f.read()
        
        # SHA-256 checksum
        actual_checksum = hashlib.sha256(data).hexdigest()
        if actual_checksum != package.checksum:
            return False
        
        # RSA signature verify
        try:
            self._public_key.verify(
                package.signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        except Exception:
            return False
        
        self._pending[package.ecu_target] = package
        return True

    def install_pending(self, ecu_target: str) -> bool:
        """Install pending package"""
        if ecu_target not in self._pending:
            return False
        self._installed[ecu_target] = self._pending.pop(ecu_target)
        return True

    def rollback(self, ecu_target: str) -> bool:
        """Cancel pending package"""
        if ecu_target not in self._pending:
            return False
        self._pending.pop(ecu_target)
        return True
    
    def handle_command(self, payload: dict, send_status):
        cmd_type = payload.get("cmd_type")
        campaign_id = payload.get("campaign_id")
        session_id = payload.get("session_id")
        ecu_target = payload.get("ecu_target")
        fw_version = payload.get("fw_version")
        package_id = payload.get("package_id")
        checksum = payload.get("checksum")

        if cmd_type == "PREPARE":
            send_status(campaign_id, session_id, "DOWNLOADING", progress_pct=0)
            
            # Find package and verify
            file_path = f"ota/packages/{package_id}.bin"
            major, minor, patch = map(int, fw_version.split("."))
            signature = bytes.fromhex(payload.get("signature", ""))
            pkg = FirmwarePackage(
                ecu_target=ecu_target,
                version_major=major,
                version_minor=minor,
                version_patch=patch,
                package_id=package_id,
                file_path=file_path,
                checksum=checksum,
                size_bytes=0,
                signature=signature,
            )
            
            send_status(campaign_id, session_id, "VERIFYING", progress_pct=50)
            
            if self.stage_package(pkg):
                send_status(campaign_id, session_id, "READY", progress_pct=100)
            else:
                send_status(campaign_id, session_id, "ERROR", progress_pct=0, error_code=1)

        elif cmd_type == "INSTALL":
            if self.install_pending(ecu_target):
                send_status(campaign_id, session_id, "DONE", progress_pct=100, fw_version=fw_version)
            else:
                send_status(campaign_id, session_id, "ERROR", progress_pct=0, error_code=2)

        elif cmd_type == "ACTIVATE":
            send_status(campaign_id, session_id, "ACTIVATED", progress_pct=100, fw_version=fw_version)

        elif cmd_type == "ROLLBACK":
            self.rollback(ecu_target)
            send_status(campaign_id, session_id, "ROLLED_BACK", progress_pct=0)