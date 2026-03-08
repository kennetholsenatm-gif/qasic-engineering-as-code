"""
VyOS API client wrapper: pyvyos (HTTPS) with fallback to vymgmt (SSH).
"""

from typing import Any, List, Optional

# Prefer pyvyos (HTTPS API)
try:
    from pyvyos import VyOS
    PYVYOS_AVAILABLE = True
except ImportError:
    PYVYOS_AVAILABLE = False
    VyOS = None  # type: ignore

try:
    import vymgmt
    VYMGMT_AVAILABLE = True
except ImportError:
    VYMGMT_AVAILABLE = False
    vymgmt = None  # type: ignore


class VyOSClient:
    """Unified client for VyOS: pyvyos or vymgmt."""

    def __init__(
        self,
        host: str,
        api_key: Optional[str] = None,
        use_https: bool = True,
        ssh_user: str = "vyos",
        ssh_key: Optional[str] = None,
        ssh_password: Optional[str] = None,
    ) -> None:
        self.host = host
        self.api_key = api_key
        self.use_https = use_https
        self._client: Any = None
        self._backend = "pyvyos" if (use_https and PYVYOS_AVAILABLE and api_key) else "vymgmt"
        self.ssh_user = ssh_user
        self.ssh_key = ssh_key
        self.ssh_password = ssh_password

    def connect(self) -> None:
        if self._backend == "pyvyos" and PYVYOS_AVAILABLE and self.api_key:
            self._client = VyOS(hostname=self.host, key=self.api_key)
        elif VYMGMT_AVAILABLE:
            self._backend = "vymgmt"
            self._client = vymgmt.VyOS(
                hostname=self.host,
                username=self.ssh_user,
                password=self.ssh_password,
                key=self.ssh_key,
            )
            self._client.login()
        else:
            raise RuntimeError("No VyOS client available. Install pyvyos or vymgmt.")

    def configure_set(self, path: List[str], value: Optional[str] = None) -> None:
        """Set config at path. path e.g. ['protocols', 'bgp', '65001', 'parameters', 'local-preference', '150']"""
        full_path = path if value is None else path + [value]
        if self._backend == "pyvyos":
            self._client.configure_set(path=full_path)
        else:
            self._client.set(" ".join(full_path))

    def commit(self) -> None:
        if self._backend == "pyvyos":
            self._client.commit()
        else:
            self._client.commit()

    def save(self) -> None:
        if self._backend == "pyvyos":
            self._client.config_file_save()
        else:
            self._client.save()

    def disconnect(self) -> None:
        if self._backend == "vymgmt" and self._client:
            try:
                self._client.exit()
            except Exception:
                pass
        self._client = None
