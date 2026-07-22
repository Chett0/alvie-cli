import json
import os
import urllib.error
import urllib.request

# The viewer and its backend are reachable at these addresses by default (see docker-compose.yaml).
DEFAULT_BACKEND_VIEWER_URL = "http://backend:8000"
DEFAULT_FRONTEND_VIEWER_URL = "http://localhost:4242"

class Viewer():
    """Singleton holding the viewer information and methods to interact with it."""

    _instance: "Viewer | None" = None

    def __new__(cls) -> "Viewer":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def _backend_url(self) -> str:
        return os.environ.get("ALVIE_BACKEND_URL", DEFAULT_BACKEND_VIEWER_URL).rstrip("/")

    @property
    def _viewer_url(self) -> str:
        return os.environ.get("ALVIE_VIEWER_URL", DEFAULT_FRONTEND_VIEWER_URL).rstrip("/")

    def get_link(self, output_id: int) -> str:
        """Build the viewer URL that opens a stored parsed output by its backend id."""
        return f"{self._viewer_url}/?file={output_id}"
    
    def post_parsed_output(
        self,
        document: dict,
        filename: str,
        timeout: float = 10.0,
    ) -> int:
        """POST a parsed output document to the backend and return its stored id.

        Raises ``RuntimeError``"""
        endpoint = f"{self._backend_url}/api/outputs"
        payload = json.dumps({
            "filename": filename, 
            "data": document
        }).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Backend rejected the parsed output ({exc.code})"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach the backend at {endpoint}: {exc.reason}"
            ) from exc
        except (TimeoutError, ValueError, OSError) as exc:
            raise RuntimeError(
                f"Unexpected response from the backend: {exc}"
            ) from exc

        output_id = body.get("id") if isinstance(body, dict) else None
        if output_id is None:
            raise RuntimeError("Backend response did not include an output id.")
        return output_id



