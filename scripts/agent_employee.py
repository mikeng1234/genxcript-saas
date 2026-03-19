"""
agent_employee.py
=================
AI agent that acts as employee Iris Tan (MDC-009).
Uses LangChain (sync) + Playwright (sync) + ReAct prompting.

Run:
  cd I:/SaaS/PaySys/genxcript-saas
  python -m scripts.agent_employee
"""

import json
import logging
import re
import sys
import os
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts.agent_config import (
    APP_URL, OLLAMA_MODEL,
    EMPLOYEE_EMAIL, EMPLOYEE_PASSWORD, MAX_STEPS, HEADLESS,
)
from scripts import browser_tools as bt

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(os.path.dirname(__file__), "agent_employee_log.txt")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("employee-agent")

# ── Tool registry ─────────────────────────────────────────────────────────────
TOOLS = {
    "navigate":      (bt.tool_navigate,  ["url"],                          "Navigate to a URL"),
    "get_page_text": (bt.tool_get_text,  [],                               "Read all visible text on the current page"),
    "click":         (bt.tool_click,     ["text_or_selector"],              "Click an element by visible text or CSS selector"),
    "fill_input":    (bt.tool_fill,      ["label_or_placeholder", "value"], "Type into a field"),
    "wait":          (bt.tool_wait,      ["seconds"],                       "Wait N seconds"),
    "scroll":        (bt.tool_scroll,    ["direction"],                     "Scroll 'up' or 'down'"),
    "get_url":       (bt.tool_get_url,   [],                               "Return current URL"),
    "done":          (None,              ["summary"],                       "Call when all tasks complete with a summary string."),
}

TOOL_DOCS = "\n".join(
    f"- {name}({', '.join(sig[1])}): {sig[2]}"
    for name, sig in TOOLS.items()
)

SYSTEM = f"""You are Iris Tan (MDC-009), Sales Representative at Mabini Digital Co.
Login: email="{EMPLOYEE_EMAIL}" password="{EMPLOYEE_PASSWORD}".
Portal: {APP_URL}

You control a browser using tools. On each turn, output exactly:
Thought: <your reasoning>
Action: <tool_name>
Input: <JSON object with parameters, or {{}} if no params>

Available tools:
{TOOL_DOCS}

After the tool runs you receive:
Observation: <result>

TASKS:
1. LOGIN: navigate to exactly "{APP_URL}" (no path suffix — never add /login or anything after the port). Fill email, fill password, click Sign In, wait 3, get_page_text.
2. PAYSLIP: click "Employee Portal" in sidebar, wait 2, get_page_text. Find Payslips tab. Note gross and net pay.
3. ATTENDANCE: find Attendance/DTR tab. Set date range March 2026. Note late days.
4. LEAVE REQUEST: find Leave Requests tab. File new request:
   Type=VL, Start=2026-05-05, End=2026-05-07, Reason="Annual family vacation". Submit. Confirm Pending.
5. OT REQUEST: find OT Requests tab. File:
   Date=2026-04-25, Start=17:00, End=19:00, Hours=2, Reason="Monthly report preparation". Submit. Confirm Pending.
6. LEAVE BALANCE: find Leave Balance tab. Note VL, SL, CL remaining.
7. UPDATE PROFILE: find Profile tab. Update mobile to 09171234999. Save.
8. DONE: call done with full summary of payslip amounts, leave balance, requests filed, any issues.

RULES:
- Output ONLY Thought/Action/Input lines — nothing else.
- Always call get_page_text after navigating or clicking before deciding next action.
- Wait 2-3 seconds after sidebar clicks.
- If a click fails, get_page_text first and use the exact text shown.
"""


def parse_action(text: str):
    thought = ""
    action = ""
    input_data = {}

    m = re.search(r"Thought:\s*(.+?)(?=\nAction:|\Z)", text, re.DOTALL)
    if m:
        thought = m.group(1).strip()

    m = re.search(r"Action:\s*(\w+)", text)
    if m:
        action = m.group(1).strip()

    m = re.search(r"Input:\s*(\{.*?\}|\{.*\})", text, re.DOTALL)
    if m:
        try:
            input_data = json.loads(m.group(1))
        except json.JSONDecodeError:
            try:
                raw = re.sub(r"(\w+):", r'"\1":', m.group(1).strip())
                input_data = json.loads(raw)
            except Exception:
                input_data = {}

    return thought, action, input_data


def call_tool(action: str, input_data: dict) -> str:
    if action not in TOOLS:
        return f"ERROR: Unknown tool '{action}'. Available: {list(TOOLS.keys())}"

    fn, params, _ = TOOLS[action]

    if action == "done":
        return "DONE:" + input_data.get("summary", "")

    if not params:
        return str(fn())

    args = [input_data.get(p, "") for p in params]
    try:
        return str(fn(*args))
    except Exception as e:
        return f"ERROR calling {action}: {e}"


def run_agent():
    llm = ChatOpenAI(
        model=OLLAMA_MODEL,
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        temperature=0.1,
        timeout=120.0,
    )

    messages = [
        SystemMessage(content=SYSTEM),
        HumanMessage(content="Begin. Output your first Thought/Action/Input now."),
    ]

    for step in range(1, MAX_STEPS + 1):
        log.info(f"── Step {step}/{MAX_STEPS} ──────────────────────────────────────")

        response = llm.invoke(messages)
        text = response.content
        log.info(f"LLM:\n{text[:600]}")
        messages.append(AIMessage(content=text))

        thought, action, input_data = parse_action(text)
        log.info(f"  → Action: {action}  Input: {input_data}")

        if not action:
            obs = "ERROR: No Action found. Output Thought/Action/Input format."
            log.warning(obs)
        else:
            obs = call_tool(action, input_data)
            if obs.startswith("DONE:"):
                summary = obs[5:]
                log.info("")
                log.info("=" * 62)
                log.info("  ALL TASKS COMPLETE")
                log.info(f"  Summary:\n{summary}")
                log.info("=" * 62)
                return summary

        log.info(f"  ← Observation: {str(obs)[:300]}")
        messages.append(HumanMessage(content=f"Observation: {obs}"))

    return "Max steps reached."


def main():
    if not EMPLOYEE_EMAIL or not EMPLOYEE_PASSWORD:
        log.error("EMPLOYEE_EMAIL and EMPLOYEE_PASSWORD must be set.")
        sys.exit(1)

    log.info("=" * 62)
    log.info("  EMPLOYEE AGENT  --  Iris Tan (MDC-009)")
    log.info(f"  Model  : {OLLAMA_MODEL}")
    log.info(f"  App    : {APP_URL}")
    log.info(f"  Steps  : max {MAX_STEPS}")
    log.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 62)

    bt.start_browser(headless=HEADLESS)
    try:
        result = run_agent()
        log.info(f"  Final result: {result}")
    except Exception as e:
        log.error(f"Agent error: {type(e).__name__}: {e}")
        raise
    finally:
        bt.stop_browser()
        log.info(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"  Log saved: {LOG_FILE}")


if __name__ == "__main__":
    main()
