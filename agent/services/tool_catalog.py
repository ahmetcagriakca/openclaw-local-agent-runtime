"""Named tool catalog — maps high-level tools to PowerShell commands."""

TOOL_CATALOG = [
    {
        "name": "get_system_info",
        "description": "Get CPU usage, RAM usage, disk usage, and system uptime",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "powershell": """
$cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
$os = Get-CimInstance Win32_OperatingSystem
$ramTotal = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$ramFree = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$ramUsed = $ramTotal - $ramFree
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    "$($_.DeviceID) $([math]::Round(($_.Size - $_.FreeSpace) / 1GB, 1))/$([math]::Round($_.Size / 1GB, 1)) GB"
}
$uptime = (Get-Date) - $os.LastBootUpTime
Write-Output "CPU: $cpu%"
Write-Output "RAM: $ramUsed/$ramTotal GB"
Write-Output "Disk: $($disk -join ', ')"
Write-Output "Uptime: $($uptime.Days)d $($uptime.Hours)h $($uptime.Minutes)m"
""",
        "risk": "low"
    },
    {
        "name": "list_processes",
        "description": "List running processes sorted by CPU usage. Shows top N processes.",
        "parameters": {
            "type": "object",
            "properties": {
                "top_n": {
                    "type": "integer",
                    "description": "Number of top processes to show (default: 15)"
                }
            },
            "required": []
        },
        "powershell_template": "Get-Process | Sort-Object CPU -Descending | Select-Object -First {top_n} Name, Id, CPU, WorkingSet64 | Format-Table -AutoSize | Out-String",
        "defaults": {"top_n": 15},
        "risk": "low"
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Full file path to read"
                }
            },
            "required": ["path"]
        },
        "powershell_template": "if (Test-Path -LiteralPath '{path}') {{ Get-Content -LiteralPath '{path}' -Raw }} else {{ Write-Error 'File not found: {path}' }}",
        "risk": "low"
    },
    {
        "name": "write_file",
        "description": "Write content to a file in the results directory (C:\\Users\\AKCA\\oc\\results\\).",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "File name only (no path separators)"
                },
                "content": {
                    "type": "string",
                    "description": "File content to write"
                }
            },
            "required": ["filename", "content"]
        },
        "powershell_template": "$p = Join-Path 'C:\\Users\\AKCA\\oc\\results' '{filename}'; Set-Content -LiteralPath $p -Value '{content}' -Encoding UTF8; Write-Output \"Written: $p\"",
        "risk": "medium"
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories in a directory",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list"
                }
            },
            "required": ["path"]
        },
        "powershell_template": "Get-ChildItem -LiteralPath '{path}' | Select-Object Mode, Length, LastWriteTime, Name | Format-Table -AutoSize | Out-String",
        "risk": "low"
    },
    {
        "name": "search_files",
        "description": "Search for files by name pattern in a directory recursively",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Root directory to search"
                },
                "pattern": {
                    "type": "string",
                    "description": "File name pattern (e.g. '*.txt', 'report*')"
                }
            },
            "required": ["path", "pattern"]
        },
        "powershell_template": "Get-ChildItem -LiteralPath '{path}' -Recurse -Filter '{pattern}' -ErrorAction SilentlyContinue | Select-Object FullName, Length, LastWriteTime | Format-Table -AutoSize | Out-String",
        "risk": "low"
    },
    {
        "name": "get_clipboard",
        "description": "Read current clipboard text content",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "powershell": "Get-Clipboard -Format Text",
        "risk": "low"
    },
    {
        "name": "set_clipboard",
        "description": "Write text to clipboard",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to copy to clipboard"
                }
            },
            "required": ["text"]
        },
        "powershell_template": "Set-Clipboard -Value '{text}'; Write-Output 'Clipboard updated'",
        "risk": "medium"
    },
    {
        "name": "open_application",
        "description": "Open an allowed application. Allowed: notepad, calc, mspaint, explorer",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Application name: notepad, calc, mspaint, explorer",
                    "enum": ["notepad", "calc", "mspaint", "explorer"]
                }
            },
            "required": ["app_name"]
        },
        "powershell_template": "Start-Process '{app_name}'; Write-Output 'Launched: {app_name}'",
        "risk": "medium"
    },
    {
        "name": "open_url",
        "description": "Open a URL in the default web browser",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to open (must start with http:// or https://)"
                }
            },
            "required": ["url"]
        },
        "powershell_template": "Start-Process '{url}'; Write-Output 'Opened: {url}'",
        "risk": "medium"
    },
    {
        "name": "take_screenshot",
        "description": "Capture a screenshot and save to results directory",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "powershell": """
Add-Type -AssemblyName System.Windows.Forms
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$path = "C:\\Users\\AKCA\\oc\\results\\screenshot-$ts.png"
$bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
Write-Output "Screenshot saved: $path"
""",
        "risk": "low"
    },
    {
        "name": "get_system_health",
        "description": "Get full OpenClaw system health status (all 6 components)",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "powershell": "& 'C:\\Users\\AKCA\\oc\\bin\\oc-system-health.ps1'",
        "risk": "low"
    }
]


def get_tools_for_openai() -> list:
    """Convert tool catalog to OpenAI function calling format."""
    tools = []
    for tool in TOOL_CATALOG:
        tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
        })
    return tools


def get_tool(name: str) -> dict | None:
    """Look up a tool by name."""
    for tool in TOOL_CATALOG:
        if tool["name"] == name:
            return tool
    return None


def build_command(tool: dict, params: dict) -> str:
    """Build the PowerShell command from tool definition and parameters."""
    if "powershell" in tool:
        return tool["powershell"].strip()

    if "powershell_template" in tool:
        cmd = tool["powershell_template"]
        defaults = tool.get("defaults", {})
        merged = {**defaults, **params}

        allowed = tool.get("allowed_values", {})
        for key, allowed_list in allowed.items():
            if key in merged and merged[key] not in allowed_list:
                raise ValueError(f"Invalid value for {key}: {merged[key]}. Allowed: {allowed_list}")

        for key, value in merged.items():
            cmd = cmd.replace(f"{{{key}}}", str(value))
        return cmd

    raise ValueError(f"Tool {tool['name']} has no command definition")
