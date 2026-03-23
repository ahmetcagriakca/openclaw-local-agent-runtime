"""Agent runner library — reusable by CLI and Mission Controller."""
import json
import time

from providers.factory import create_provider
from services.mcp_client import MCPClient
from services.tool_catalog import get_tools_for_openai, get_tool, build_command
from services.risk_engine import RiskEngine
from services.approval_service import ApprovalService
from services.artifact_store import ArtifactStore

DEFAULT_SYSTEM_PROMPT = """You are a Windows automation assistant for the OpenClaw system.
You help the user manage their Windows computer through specialized tools.

Rules:
- Use the provided tools to answer the user's request
- If no tool fits the request, explain what you cannot do
- Be concise and actionable
- Answer in the same language the user uses (Turkish or English)
- If a tool call fails, explain the error clearly
- Never try to work around tool restrictions
- IMPORTANT: When the user asks you to do something, call the tool directly. Do NOT ask for confirmation — the system has its own approval mechanism for dangerous operations. Just call the tool and the system will handle risk assessment and approval.

You have access to tools for: system information, process management, file operations,
clipboard, application management, screenshots, system health checks, network info,
scheduled tasks, MCP server management, runtime task submission, screen lock,
system shutdown/restart (with approval), and content search.

You do NOT have access to: direct PowerShell execution, file deletion, or registry modification."""


def run_agent_with_config(message: str, agent_id: str, user_id: str,
                          session_id: str, max_turns: int = 10,
                          tool_policy: str = None,
                          system_prompt_override: str = None) -> dict:
    """Run agent with optional tool filtering and prompt override.

    tool_policy: specialist name ("analyst", "executor") or None for all tools
    system_prompt_override: custom system prompt, or None for default
    """
    start_time = time.time()
    tool_log = []
    approval_log = []

    # Initialize services
    risk_engine = RiskEngine()
    approval_service = ApprovalService(timeout_seconds=60)
    artifact_store = ArtifactStore(session_id)

    # Initialize provider from agent config
    try:
        provider, agent_config = create_provider(agent_id)
        max_turns = agent_config.get("maxTurns", max_turns)
    except Exception as e:
        return {
            "status": "error",
            "agentId": agent_id,
            "sessionId": session_id,
            "error": f"Failed to initialize provider: {e}",
            "artifacts": [{"type": "error", "data": {"error": str(e), "recoverable": False}}]
        }

    # Initialize MCP client
    mcp = MCPClient()

    # Verify MCP server
    spec = mcp.get_openapi_spec()
    if not spec:
        return {
            "status": "error",
            "agentId": agent_id,
            "sessionId": session_id,
            "error": "MCP server unreachable at localhost:8001",
            "artifacts": [{"type": "error", "data": {"error": "MCP server unreachable", "recoverable": True}}]
        }

    # Get available tools — filter by specialist policy if set
    all_tools = get_tools_for_openai()
    if tool_policy:
        from mission.specialists import get_specialist_tools
        allowed = get_specialist_tools(tool_policy)
        if allowed:
            all_tools = [t for t in all_tools if t["function"]["name"] in allowed]

    # Select system prompt
    if system_prompt_override:
        system_prompt = system_prompt_override
    elif tool_policy:
        from mission.specialists import get_specialist_prompt
        system_prompt = get_specialist_prompt(tool_policy)
    else:
        system_prompt = DEFAULT_SYSTEM_PROMPT

    # Build conversation
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]

    # Multi-turn conversation loop
    final_text = None
    turns_used = 0

    for turn in range(max_turns):
        turns_used = turn + 1

        try:
            response = provider.chat(messages, all_tools)
        except Exception as e:
            return {
                "status": "error",
                "agentId": agent_id,
                "sessionId": session_id,
                "error": f"LLM API error: {e}",
                "toolCalls": tool_log,
                "turnsUsed": turns_used,
                "artifacts": [{"type": "error", "data": {"error": str(e), "recoverable": True}}]
            }

        # If agent has text and no tool calls — done
        if response.text and not response.tool_calls:
            final_text = response.text
            break

        # If agent wants to use tools
        if response.tool_calls:
            # Add assistant message to conversation (OpenAI format)
            assistant_msg = {"role": "assistant", "content": response.text}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.params)
                    }
                }
                for tc in response.tool_calls
            ]
            messages.append(assistant_msg)

            # Execute each tool call
            for tc in response.tool_calls:
                tool_start = time.time()
                tool_entry = {
                    "tool": tc.name,
                    "params": tc.params,
                    "risk": "unknown"
                }

                tool_def = get_tool(tc.name)
                if not tool_def:
                    result_text = f"Error: Unknown tool '{tc.name}'"
                    tool_entry["success"] = False
                    tool_entry["error"] = result_text
                else:
                    tool_entry["risk"] = tool_def.get("risk", "medium")
                    try:
                        command = build_command(tool_def, tc.params)

                        # Risk classification
                        risk_result = risk_engine.classify(tc.name, tool_def.get("risk", "medium"), command)
                        tool_entry["risk"] = risk_result["risk"]
                        tool_entry["riskAction"] = risk_result["action"]

                        if risk_result["action"] == "reject":
                            result_text = f"BLOCKED: {risk_result['reason']}"
                            tool_entry["success"] = False
                            tool_entry["error"] = result_text
                            tool_entry["blocked"] = True

                        elif risk_result["action"] in ("require_approval", "require_approval_confirmed"):
                            approval = approval_service.request_approval(
                                tool_name=tc.name,
                                tool_params=tc.params,
                                risk=risk_result["risk"],
                                powershell_command=command,
                                session_id=session_id
                            )
                            tool_entry["approvalId"] = approval["approvalId"]
                            tool_entry["approvalMethod"] = approval["method"]
                            approval_log.append({
                                "approvalId": approval["approvalId"],
                                "tool": tc.name,
                                "risk": risk_result["risk"],
                                "approved": approval["approved"],
                                "method": approval["method"]
                            })

                            if not approval["approved"]:
                                result_text = f"DENIED: Tool call '{tc.name}' was denied ({approval['method']})"
                                tool_entry["success"] = False
                                tool_entry["error"] = result_text
                                tool_entry["approved"] = False
                            else:
                                tool_entry["approved"] = True
                                mcp_result = mcp.execute_powershell(command)
                                result_text = mcp_result["output"] if mcp_result["success"] else f"Error: {mcp_result['error']}"
                                tool_entry["success"] = mcp_result["success"]
                                if not mcp_result["success"]:
                                    tool_entry["error"] = mcp_result["error"]

                        else:
                            tool_entry["approved"] = True
                            mcp_result = mcp.execute_powershell(command)
                            result_text = mcp_result["output"] if mcp_result["success"] else f"Error: {mcp_result['error']}"
                            tool_entry["success"] = mcp_result["success"]
                            if not mcp_result["success"]:
                                tool_entry["error"] = mcp_result["error"]

                    except Exception as e:
                        result_text = f"Error executing tool: {e}"
                        tool_entry["success"] = False
                        tool_entry["error"] = str(e)

                tool_entry["durationMs"] = int((time.time() - tool_start) * 1000)
                tool_log.append(tool_entry)

                # Create typed artifact from tool result
                artifact_store.add_from_tool_result(
                    tc.name, tc.params, result_text, tool_entry.get("success", False)
                )

                # Add tool result to conversation (OpenAI format)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text
                })

            # If response also had text, it might be the final answer
            if response.text and response.stop_reason == "end_turn":
                final_text = response.text
                break

        # No tool calls, no text — unexpected, break
        if not response.tool_calls and not response.text:
            final_text = "Islem tamamlanamadi."
            break

    if final_text is None:
        final_text = "Islem tamamlandi ancak ozet olusturulamadi."

    # Add final text response as artifact
    artifact_store.add("text_response", {"message": final_text})
    artifact_store.save_session()

    total_duration = int((time.time() - start_time) * 1000)
    artifacts = artifact_store.get_all()

    # Audit log
    try:
        from services.audit_service import log_agent_run
        log_agent_run(
            session_id=session_id, agent_id=agent_id, user_id=user_id,
            user_message=message, tool_calls=tool_log, response=final_text,
            status="completed", turns_used=turns_used, duration_ms=total_duration,
            approvals=approval_log, artifacts=artifacts
        )
    except Exception:
        pass  # Audit is best-effort

    return {
        "status": "completed",
        "agentId": agent_id,
        "sessionId": session_id,
        "response": final_text,
        "artifacts": artifacts,
        "toolCalls": tool_log,
        "turnsUsed": turns_used,
        "totalDurationMs": total_duration
    }
