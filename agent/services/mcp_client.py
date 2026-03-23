"""MCP HTTP client for windows-mcp server."""
import json
import os
import re
import requests


class MCPClient:
    def __init__(self, base_url=None, api_key=None, timeout=30):
        self.base_url = base_url or os.environ.get("OC_MCP_BASE_URL", "http://localhost:8001")
        self.api_key = api_key or os.environ.get("OC_MCP_API_KEY", "local-mcp-12345")
        self.timeout = timeout

    def execute_powershell(self, command: str) -> dict:
        """Execute a PowerShell command via MCP server.

        Returns: {"success": bool, "output": str, "error": str|None}
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "command": command,
            "timeout": self.timeout
        }
        try:
            resp = requests.post(
                f"{self.base_url}/PowerShell",
                headers=headers,
                json=body,
                timeout=self.timeout + 5
            )
            text = resp.text.strip()

            try:
                data = resp.json()
            except (json.JSONDecodeError, ValueError):
                data = text

            # Normalize to string for uniform parsing
            if isinstance(data, dict):
                status_code = None
                for key in ["Status Code", "StatusCode", "statusCode"]:
                    if key in data:
                        status_code = int(data[key])
                        break
                output_text = str(data)
            else:
                # String response — parse with regex
                output_text = str(data)
                match = re.search(r'Status Code:\s*(-?\d+)', output_text)
                status_code = int(match.group(1)) if match else None
                # Extract just the response content before status code
                resp_match = re.match(r'Response:\s*(.*?)(?:\n\nStatus Code:|\Z)', output_text, re.DOTALL)
                if resp_match:
                    output_text = resp_match.group(1).strip()

            success = status_code == 0 if status_code is not None else resp.ok
            return {
                "success": success,
                "output": output_text,
                "error": None if success else output_text
            }

        except requests.Timeout:
            return {"success": False, "output": "", "error": f"Timeout after {self.timeout}s"}
        except requests.ConnectionError:
            return {"success": False, "output": "", "error": "MCP server unreachable (localhost:8001)"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    def get_openapi_spec(self) -> dict | None:
        """Fetch OpenAPI spec to verify server is running."""
        try:
            resp = requests.get(f"{self.base_url}/openapi.json", timeout=5)
            return resp.json() if resp.ok else None
        except Exception:
            return None


if __name__ == "__main__":
    client = MCPClient()
    spec = client.get_openapi_spec()
    if spec:
        print(f"MCP server OK: {spec.get('info', {}).get('title', 'unknown')}")
        result = client.execute_powershell("Write-Output 'Hello from MCP'")
        print(f"Test result: {result}")
    else:
        print("MCP server unreachable!")
