"""Workflow-state inspection for UDA-Hub using LangGraph APIs.

Shows, for one thread_id (= ticket_id):
  1. the graph structure (get_graph) -> also exported to agentic/design/workflow_graph.mmd
  2. the latest state snapshot (get_state): messages, route, resolution, tool_usage
  3. the full checkpoint history (get_state_history): how state evolved node by node

Usage:
    python 04_inspect_state.py                    # runs a 2-turn demo, then inspects it
    python 04_inspect_state.py --thread-id t-001  # inspect an existing thread only
"""
import argparse
import os
import uuid

from langchain_core.messages import HumanMessage

from agentic.workflow import orchestrator

DEMO_USER = "f556c0"  # Bob, active premium
DEMO_TURNS = [
    "Can you show me my current reservations?",
    "Thanks! And how do I reserve a spot for an event?",
]


def export_graph(path="agentic/design/workflow_graph.mmd"):
    """Mermaid generated from the REAL compiled graph (proves code matches the design doc)."""
    mermaid = orchestrator.get_graph().draw_mermaid()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(mermaid)
    print(f"Graph nodes: {list(orchestrator.get_graph().nodes)}")
    print(f"Mermaid exported to {path}\n")


def run_demo(thread_id):
    cfg = {"configurable": {"thread_id": thread_id}}
    for text in DEMO_TURNS:
        out = orchestrator.invoke(
            {"messages": [HumanMessage(content=text)], "external_user_id": DEMO_USER,
             "channel": "chat", "account_id": "cultpass"}, cfg)
        print(f"[turn] {text}\n  -> {out['messages'][-1].content[:120]}\n")


def inspect_thread(thread_id):
    cfg = {"configurable": {"thread_id": thread_id}}

    # 1) Latest snapshot
    snap = orchestrator.get_state(cfg)
    v = snap.values
    print("=" * 70)
    print(f"LATEST STATE  thread_id={thread_id}  next={snap.next}")
    print("=" * 70)
    for k in ("external_user_id", "route", "resolution", "confidence", "escalation_reason"):
        print(f"{k:18}: {v.get(k)}")
    print(f"{'classification':18}: {v.get('classification')}")
    print(f"{'memory_context':18}: {v.get('memory_context')}")
    print(f"\nMessages ({len(v.get('messages', []))}):")
    for m in v.get("messages", []):
        print(f"  [{m.type:5}] {str(m.content)[:100]}")
    print("\nTool usage (last turn; reset by Intake each turn):")
    for t in v.get("tool_usage", []) or []:
        print(f"  - {t['tool']} args={t['args']} ok={t['ok']} error={t['error_code']}")

    # 2) Checkpoint history (newest first -> reverse for chronological)
    print("\n" + "=" * 70)
    print("CHECKPOINT HISTORY (chronological)")
    print("=" * 70)
    history = list(orchestrator.get_state_history(cfg))
    all_tools = []
    for s in reversed(history):
        meta = s.metadata or {}
        tools = [t["tool"] for t in (s.values.get("tool_usage") or [])]
        all_tools.extend(tools)
        print(f"step={meta.get('step'):>3} next={str(s.next):28} route={s.values.get('route') or '-':12} "
              f"resolution={s.values.get('resolution') or '-':18} msgs={len(s.values.get('messages', []))} "
              f"tools={tools}")
    print(f"\nDistinct tool calls seen across thread: {sorted(set(all_tools)) or 'none'}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--thread-id", default=None)
    a = p.parse_args()
    export_graph()
    if a.thread_id:
        inspect_thread(a.thread_id)
    else:
        tid = f"inspect-{uuid.uuid4().hex[:6]}"
        run_demo(tid)
        inspect_thread(tid)