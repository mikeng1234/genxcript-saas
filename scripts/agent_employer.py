"""
agent_employer.py
=================
AI agent that acts as the business owner / HR admin.
Uses LangChain (sync) + Playwright (sync) + ReAct prompting.
No browser-use, no async, no AgentExecutor.

Run:
  cd I:/SaaS/PaySys/genxcript-saas
  python -m scripts.agent_employer

Requirements:
  - Ollama running:  ollama serve
  - Model pulled:    ollama pull qwen2.5:7b
  - App running:     streamlit run app/main.py
  - playwright installed: playwright install chromium
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
    ADMIN_EMAIL, ADMIN_PASSWORD, MAX_STEPS, HEADLESS,
)
from scripts import browser_tools as bt

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(os.path.dirname(__file__), "agent_employer_log.txt")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("employer-agent")

# ── Tool registry ─────────────────────────────────────────────────────────────
TOOLS = {
    "navigate":      (bt.tool_navigate,  ["url"],                      "Navigate to a URL"),
    "get_page_text": (bt.tool_get_text,  [],                           "Read all visible text on the current page"),
    "click":         (bt.tool_click,     ["text_or_selector"],          "Click an element by visible text or CSS selector"),
    "fill_input":    (bt.tool_fill,      ["label_or_placeholder","value"], "Type into a field"),
    "wait":          (bt.tool_wait,      ["seconds"],                   "Wait N seconds"),
    "scroll":        (bt.tool_scroll,    ["direction"],                 "Scroll 'up' or 'down'"),
    "get_url":       (bt.tool_get_url,   [],                           "Return current URL"),
    "done":          (None,              ["summary"],                   "Call this when all tasks are complete. Pass a summary string."),
}

TOOL_DOCS = "\n".join(
    f"- {name}({', '.join(sig[1])}): {sig[2]}"
    for name, sig in TOOLS.items()
)

# ── System prompt (ReAct format) ──────────────────────────────────────────────
SYSTEM = f"""You are an HR admin using a payroll app at {APP_URL}.
Login: email="{ADMIN_EMAIL}" password="{ADMIN_PASSWORD}". Company: "Mabini Digital Co."

You control a browser using tools. On each turn, output exactly this format:
Thought: <your reasoning>
Action: <tool_name>
Input: <JSON object with the parameters, or {{}} if no params>

Available tools:
{TOOL_DOCS}

After the tool runs, you will receive:
Observation: <result>

Then output your next Thought/Action/Input. Repeat until all tasks done.
When fully done, use: Action: done / Input: {{"summary": "your full summary"}}

TASKS:
1. LOGIN: navigate to exactly "{APP_URL}" (no path suffix — never add /login or anything after the port). Fill email, fill password, click Sign In, wait 3, get_page_text.
2. DASHBOARD: get_page_text. Note headcount, pending approvals, pay period status.
3. EMPLOYEES: click "Employees" sidebar link, wait 2, get_page_text. Count employees.
4. DTR: click "Attendance" sidebar link, wait 2, get_page_text.
5. APPROVE LEAVE: find pending leave requests, approve each (add note "Approved by HR admin.").
6. APPROVE OT: find pending OT requests, approve each (note "OT approved. Will be included in next payroll.").
7. PAYROLL: click "Payroll Run", wait 2, get_page_text. Note gross pay totals.
8. GOV REPORTS: click "Government Reports", find Monthly Reports, note SSS and PhilHealth totals.
9. COMPANY SETUP: click "Company Setup", check Locations and Schedules tabs.
10. DONE: call done with a full summary.

RULES:
- Output ONLY Thought/Action/Input — no other text.
- Always call get_page_text after navigating or clicking before deciding next action.
- Wait 2-3 seconds after sidebar clicks (Streamlit needs time to load).
- If a click fails, try the exact text shown on screen from get_page_text.
"""


def parse_action(text: str):
    """Parse Thought/Action/Input from LLM response. Returns (thought, action, input_dict)."""
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
            # Try to extract a plain string value as fallback
            raw = m.group(1).strip()
            if raw.startswith("{") and ":" in raw:
                # try lenient parse
                try:
                    raw = re.sub(r"(\w+):", r'"\1":', raw)
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
            obs = "ERROR: No Action found in your response. Remember to output Thought/Action/Input."
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

    return "Max steps reached without completing all tasks."


def main():
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        log.error("ADMIN_EMAIL and ADMIN_PASSWORD must be set.")
        sys.exit(1)

    log.info("=" * 62)
    log.info("  EMPLOYER AGENT  --  Mabini Digital Co.")
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
