"""Account Ops agent: tool-calling loop over the CultPass DB tools.

Security: the authenticated customer id is injected into every tool call that takes `user_id`,
so the LLM can never act on another customer's data."""
import json
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage

from agentic.config import get_llm
from agentic.logging_utils import log_event
from agentic.tools.account_tools import ACCOUNT_TOOLS

MAX_STEPS = 6
ESCALATE_CODES = {"USER_BLOCKED", "USER_NOT_FOUND", "DB_ERROR"}

SYSTEM = """You are CultPass's account-operations agent helping customer {name} (user_id={user_id}).
Use the tools to look up data or perform actions. Rules:
- Never guess ids; use list_experiences / list_reservations to find them. Ask the customer if ambiguous.
- Before reserving, confirm which experience the customer means. Report tool errors plainly and suggest what they can do.
- Never promise refunds or policy exceptions. Be concise and friendly.
Customer memory: {memory}"""


def account_ops_node(state):
    tid, uid = state["ticket_id"], state["external_user_id"]
    tools = {t.name: t for t in ACCOUNT_TOOLS}
    llm = get_llm().bind_tools(ACCOUNT_TOOLS)
    name = (state.get("user_profile") or {}).get("name") or "the customer"
    msgs = [SystemMessage(content=SYSTEM.format(name=name, user_id=uid, memory=state.get("memory_context") or "none")),
            *state["messages"][-10:]]
    usage, results, final = [], [], None

    try:
        for _ in range(MAX_STEPS):
            ai = llm.invoke(msgs)
            msgs.append(ai)
            if not ai.tool_calls:
                final = ai
                break
            for call in ai.tool_calls:
                tool = tools.get(call["name"])
                args = dict(call["args"])
                if tool is None:
                    res = {"ok": False, "error_code": "UNKNOWN_TOOL", "message": call["name"]}
                else:
                    if "user_id" in tool.args:
                        args["user_id"] = uid          # enforce authenticated identity
                    try:
                        res = tool.invoke(args)
                    except Exception as exc:  # noqa: BLE001 (bad args etc.)
                        res = {"ok": False, "error_code": "TOOL_EXCEPTION", "message": str(exc)}
                results.append(res)
                usage.append({"tool": call["name"], "args": args, "ok": res.get("ok"),
                              "error_code": res.get("error_code")})
                log_event(tid, "account_ops", "tool_call", tool=call["name"], args=args,
                          ok=res.get("ok"), error_code=res.get("error_code"))
                msgs.append(ToolMessage(content=json.dumps(res, default=str), tool_call_id=call["id"]))
    except Exception as exc:  # noqa: BLE001
        log_event(tid, "account_ops", "error", error=str(exc))
        return {"tool_usage": usage, "resolution": "needs_escalation", "escalation_reason": "account_agent_error"}

    codes = {r.get("error_code") for r in results if not r.get("ok")}
    if codes & ESCALATE_CODES:
        reason = "user_blocked" if "USER_BLOCKED" in codes else "account_tool_failure"
        log_event(tid, "account_ops", "escalate", reason=reason, codes=sorted(codes))
        return {"tool_usage": usage, "resolution": "needs_escalation", "escalation_reason": reason}
    if final is None:
        log_event(tid, "account_ops", "escalate", reason="tool_loop_exhausted")
        return {"tool_usage": usage, "resolution": "needs_escalation", "escalation_reason": "tool_loop_exhausted"}

    confidence = 0.85 if any(r.get("ok") for r in results) else 0.7
    log_event(tid, "account_ops", "resolved", confidence=confidence, tools_used=[u["tool"] for u in usage])
    return {"messages": [AIMessage(content=final.content)], "tool_usage": usage,
            "confidence": confidence, "resolution": "resolved"}
