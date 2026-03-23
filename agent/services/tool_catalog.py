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
        "risk": "low",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "none",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
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
        "risk": "low",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "none",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
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
        "risk": "low",
        "governance": {
            "filesystemTouching": True,
            "mutationSurface": "none",
            "workingSetScopeRequired": True,
            "requiresPathResolution": True
        }
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
        "risk": "medium",
        "governance": {
            "filesystemTouching": True,
            "mutationSurface": "code",
            "workingSetScopeRequired": True,
            "requiresPathResolution": True
        }
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
        "risk": "low",
        "governance": {
            "filesystemTouching": True,
            "mutationSurface": "none",
            "workingSetScopeRequired": True,
            "requiresPathResolution": True
        }
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
        "risk": "low",
        "governance": {
            "filesystemTouching": True,
            "mutationSurface": "none",
            "workingSetScopeRequired": True,
            "requiresPathResolution": True
        }
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
        "risk": "low",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "none",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
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
        "risk": "medium",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "system",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
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
        "risk": "medium",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "system",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
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
        "risk": "medium",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "system",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
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
        "risk": "low",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "none",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
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
        "risk": "low",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "none",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
    },
    {
        "name": "close_application",
        "description": "Close a running application by name. REQUIRES APPROVAL — this is a destructive operation.",
        "parameters": {
            "type": "object",
            "properties": {
                "process_name": {
                    "type": "string",
                    "description": "Process name to close (e.g. 'notepad', 'chrome', 'calc')"
                }
            },
            "required": ["process_name"]
        },
        "powershell_template": "Stop-Process -Name '{process_name}' -Force -ErrorAction SilentlyContinue; Write-Output 'Closed: {process_name}'",
        "risk": "high",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "system",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
    },
    {
        "name": "lock_screen",
        "description": "Lock the Windows workstation screen",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "powershell": "rundll32.exe user32.dll,LockWorkStation; Write-Output 'Screen locked'",
        "risk": "medium",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "system",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
    },
    {
        "name": "system_shutdown",
        "description": "Shutdown the computer. CRITICAL — requires explicit approval.",
        "parameters": {
            "type": "object",
            "properties": {
                "delay_seconds": {
                    "type": "integer",
                    "description": "Delay in seconds before shutdown (default: 30, minimum: 10)"
                }
            },
            "required": []
        },
        "powershell_template": "Write-Output 'Shutdown scheduled in {delay_seconds} seconds...'; shutdown /s /t {delay_seconds}",
        "defaults": {"delay_seconds": 30},
        "risk": "critical",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "system",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
    },
    {
        "name": "system_restart",
        "description": "Restart the computer. CRITICAL — requires explicit approval.",
        "parameters": {
            "type": "object",
            "properties": {
                "delay_seconds": {
                    "type": "integer",
                    "description": "Delay in seconds before restart (default: 30, minimum: 10)"
                }
            },
            "required": []
        },
        "powershell_template": "Write-Output 'Restart scheduled in {delay_seconds} seconds...'; shutdown /r /t {delay_seconds}",
        "defaults": {"delay_seconds": 30},
        "risk": "critical",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "system",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
    },
    {
        "name": "submit_runtime_task",
        "description": "Submit a predefined task to the oc runtime system (e.g. create_note, notepad_then_ready)",
        "parameters": {
            "type": "object",
            "properties": {
                "task_name": {
                    "type": "string",
                    "description": "Task definition name (e.g. 'create_note', 'notepad_then_ready')"
                },
                "arguments": {
                    "type": "string",
                    "description": "JSON string of task arguments (e.g. '{\"filename\":\"test.txt\",\"content\":\"hello\"}')"
                }
            },
            "required": ["task_name"]
        },
        "powershell_template": "& 'C:\\Users\\AKCA\\oc\\wsl\\oc-bridge-submit' '{task_name}' '{arguments}'",
        "defaults": {"arguments": "{}"},
        "risk": "medium",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "system",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
    },
    {
        "name": "check_runtime_task",
        "description": "Check the status of a runtime task by its task ID",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID (e.g. 'task-20260323-143022-001')"
                }
            },
            "required": ["task_id"]
        },
        "powershell_template": "& 'C:\\Users\\AKCA\\oc\\wsl\\oc-bridge-status' '{task_id}'",
        "risk": "low",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "none",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
    },
    {
        "name": "mcp_status",
        "description": "Check if the WMCP (windows-mcp) server is running and healthy",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "powershell": "try { $r = Invoke-RestMethod 'http://localhost:8001/openapi.json' -TimeoutSec 5; Write-Output \"WMCP OK: $($r.info.title) on port 8001\" } catch { Write-Output \"WMCP DOWN: $($_.Exception.Message)\" }",
        "risk": "low",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "none",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
    },
    {
        "name": "mcp_restart",
        "description": "Restart the WMCP (windows-mcp) server. Kills existing process and restarts.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "powershell": "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -like '*mcpo*' -or $_.CommandLine -like '*windows-mcp*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Start-Sleep 2; Start-Process -WindowStyle Hidden powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File C:\\Users\\AKCA\\oc\\bin\\start-wmcp-server.ps1'; Start-Sleep 10; try { $r = Invoke-RestMethod 'http://localhost:8001/openapi.json' -TimeoutSec 5; Write-Output \"WMCP restarted OK: $($r.info.title)\" } catch { Write-Output 'WMCP restart may still be starting...' }",
        "risk": "high",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "system",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
    },
    {
        "name": "find_in_files",
        "description": "Search for text content inside files recursively",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Root directory to search"
                },
                "text": {
                    "type": "string",
                    "description": "Text to search for inside files"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File pattern to search in (e.g. '*.txt', '*.ps1'). Default: all files."
                }
            },
            "required": ["path", "text"]
        },
        "powershell_template": "Get-ChildItem -LiteralPath '{path}' -Recurse -File -Filter '{file_pattern}' -ErrorAction SilentlyContinue | Select-String -Pattern '{text}' -SimpleMatch | Select-Object -First 20 Path, LineNumber, Line | Format-Table -AutoSize | Out-String",
        "defaults": {"file_pattern": "*"},
        "risk": "low",
        "governance": {
            "filesystemTouching": True,
            "mutationSurface": "none",
            "workingSetScopeRequired": True,
            "requiresPathResolution": True
        }
    },
    {
        "name": "get_process_details",
        "description": "Get detailed information about a specific running process by name or PID",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Process name (e.g. 'chrome', 'notepad')"
                }
            },
            "required": ["name"]
        },
        "powershell_template": "Get-Process -Name '{name}' -ErrorAction SilentlyContinue | Select-Object Name, Id, CPU, WorkingSet64, StartTime, Path | Format-List | Out-String",
        "risk": "low",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "none",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
    },
    {
        "name": "get_network_info",
        "description": "Get network adapter information, IP addresses, and connectivity status",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "powershell": "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' } | Select-Object InterfaceAlias, IPAddress, PrefixLength | Format-Table -AutoSize | Out-String; Write-Output '---'; Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet | ForEach-Object { if ($_) { Write-Output 'Internet: Connected' } else { Write-Output 'Internet: Disconnected' } }",
        "risk": "low",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "none",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
    },
    {
        "name": "list_scheduled_tasks",
        "description": "List Windows scheduled tasks filtered by name pattern. Default: OpenClaw tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Task name filter (e.g. 'OpenClaw*'). Default: all OpenClaw tasks."
                }
            },
            "required": []
        },
        "powershell_template": "Get-ScheduledTask | Where-Object {{ $_.TaskName -like '{filter}' }} | Select-Object TaskName, State | Format-Table -AutoSize | Out-String",
        "defaults": {"filter": "OpenClaw*"},
        "risk": "low",
        "governance": {
            "filesystemTouching": False,
            "mutationSurface": "none",
            "workingSetScopeRequired": False,
            "requiresPathResolution": False
        }
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
        # Unescape doubled braces: {{ -> { and }} -> }
        cmd = cmd.replace("{{", "{").replace("}}", "}")
        return cmd

    raise ValueError(f"Tool {tool['name']} has no command definition")


# --- Governance helpers (Sprint 0) ---

def get_tool_governance(name: str) -> dict | None:
    """Return governance metadata for a tool. None if tool not found."""
    tool = get_tool(name)
    if not tool:
        return None
    return tool.get("governance", {})


def is_filesystem_touching(name: str) -> bool:
    """Check if a tool touches the filesystem."""
    gov = get_tool_governance(name)
    return gov.get("filesystemTouching", False) if gov else False


def get_mutation_surface(name: str) -> str:
    """Get mutation surface of a tool: 'none', 'code', or 'system'."""
    gov = get_tool_governance(name)
    return gov.get("mutationSurface", "none") if gov else "none"


def validate_catalog_governance() -> list[str]:
    """Startup check: every tool must have complete governance metadata."""
    required_fields = ["filesystemTouching", "mutationSurface",
                       "workingSetScopeRequired", "requiresPathResolution"]
    errors = []
    for tool in TOOL_CATALOG:
        gov = tool.get("governance")
        if not gov:
            errors.append(f"{tool['name']}: missing governance block")
            continue
        for field in required_fields:
            if field not in gov:
                errors.append(f"{tool['name']}: missing governance.{field}")
    return errors
