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
        """Log in and return the SSID (session id) string.

        Raises:
            ValueError: bad request / API-level error / missing ssid
            PermissionError: 401 or 403
            ConnectionError: network failure, rate limit, or unknown HTTP error
        """

        # Already authenticated? Skip the POST.
        if self.get_session_id: return True
        
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
            try:
                if self.get_session_id:
                    logger.info(f'SSID acquired successfully')
                    return True
            except ValueError:
                logger.error("auth_invalid_json: %s", resp.text)
                raise ValueError("Login response was not valid JSON")

            # if data.get("code") == "success":
            #     ssid = data.get("ssid") or ""
            #     if not ssid:
            #         logger.error("auth_missing_ssid: %s", data)
            #         raise ValueError("Login succeeded but no ssid was returned")
            #     return ssid

            # msg = data.get("message") or str(data)
            # logger.error("auth_api_error: %s", data)
            # raise ValueError(f"Authentication API error: {msg}")

        
        if resp.status_code == 400: # 400 — malformed request
            logger.error("auth_bad_request: %s", resp.text)
            raise ValueError("Bad request (400). Check email/password format.")
        if resp.status_code == 401: # 401 — wrong credentials
            logger.error("auth_unauthorized")
            raise PermissionError("Invalid credentials (401).")
        if resp.status_code == 403: # 403 — IP blocked / WAF
            logger.error("auth_forbidden")
            raise PermissionError("Access denied (403). IP may be blocked.")
        if resp.status_code == 429: # 429 — rate limited
            logger.error("auth_rate_limit")
            raise ConnectionError("Too many login attempts (429). Wait a few minutes.")

        # Anything else non-2xx (5xx, unexpected 4xx) → raise_for_status
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            logger.error("auth_http_error: %s", e)
            raise ConnectionError(f"Auth HTTP error: {resp.status_code}") from e

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