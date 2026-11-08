import sys
import logging
import requests

logger = logging.getLogger(__name__)


class IQAuth:
    """Synchronous IQ Option authentication client."""

    def __init__(self, email: str, password: str, timeout: float = 15.0):
        self.email = email
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()

        if not all([self.email, self.password]):
            print("Email and password are required!")
            sys.exit()

    def acquire_ssid(self) -> str:
        """Log in and return the SSID string.

        Raises:
            ValueError: bad request, or login succeeded but no ssid returned
            PermissionError: 401 or 403
            ConnectionError: network failure, rate limit, or unexpected HTTP status
        """
        ssid = self.get_session_id
        if ssid:                                   # already authenticated
            return ssid

        try:
            resp = self.session.post(
                "https://auth.iqoption.com/api/v2/login",
                json={"identifier": self.email, "password": self.password},
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            logger.error("auth_network_error: %s", e)
            raise ConnectionError(f"Connection error during login: {e}") from e

        if resp.status_code == 200:
            ssid = self.get_session_id             # read from the session cookies
            if ssid:
                logger.info("SSID acquired successfully")
                return ssid
            logger.error("auth_missing_ssid: %s", resp.text)
            raise ValueError("Login succeeded but no ssid was returned")

        if resp.status_code == 400:
            logger.error("auth_bad_request: %s", resp.text)
            raise ValueError("Bad request (400). Check email/password format.")
        if resp.status_code == 401:
            logger.error("auth_unauthorized")
            raise PermissionError("Invalid credentials (401).")
        if resp.status_code == 403:
            # TODO: inspect resp.json() here, 403 may mean "2FA required"
            logger.error("auth_forbidden: %s", resp.text)
            raise PermissionError("Access denied (403). IP blocked or 2FA required.")
        if resp.status_code == 429:
            logger.error("auth_rate_limit")
            raise ConnectionError("Too many login attempts (429). Wait a few minutes.")

        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            logger.error("auth_http_error: %s", e)
            raise ConnectionError(f"Auth HTTP error: {resp.status_code}") from e
        raise ConnectionError(f"Unexpected login response: {resp.status_code}")

    @property
    def get_session_id(self):
        """
        Get the current session ID (SSID) from cookies.
        
        Returns:
            str: Session ID if available, None otherwise
        """
        return self.session.cookies.get('ssid')

    def destroy_ssid(self, data=None) -> str:
        """
        Log out from IQOption and close session.
        
        Args:
            data (dict, optional): Additional logout data
        """
        if self.session.post(
            url="https://auth.iqoption.com/api/v1.0/logout", 
            data=data).status_code == 200:
            self._connected = False
            logger.info(f'SSID destroyed successfully')