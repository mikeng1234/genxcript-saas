"""
run_agents.py
=============
Runs employer agent first, then employee agent sequentially.
Both use the same local Ollama model.

Run:
  cd I:/SaaS/PaySys/genxcript-saas
  python -m scripts.run_agents
"""

import asyncio
import subprocess
import sys
import os
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("run-agents")


def check_ollama():
    """Verify Ollama is running and model is available."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
            import json
            data = json.loads(r.read())
            models = [m["name"] for m in data.get("models", [])]
            log.info(f"  Ollama running. Available models: {models}")
            return models
    except Exception as e:
        log.error(f"  Ollama not reachable: {e}")
        log.error("  Start Ollama with: ollama serve")
        return None


def check_app():
    """Verify Streamlit app is running."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:8501", timeout=5) as r:
            log.info("  Streamlit app is running at http://localhost:8501")
            return True
    except Exception as e:
        log.error(f"  Streamlit app not reachable: {e}")
        log.error("  Start it with: streamlit run app/main.py")
        return False


def check_credentials():
    """Verify credentials are set."""
    from scripts.agent_config import ADMIN_EMAIL, ADMIN_PASSWORD
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        log.error("  ADMIN_EMAIL and ADMIN_PASSWORD not set.")
        log.error("  Edit scripts/agent_config.py or add to .env:")
        log.error("    ADMIN_EMAIL=your@email.com")
        log.error("    ADMIN_PASSWORD=yourpassword")
        return False
    log.info(f"  Credentials set for: {ADMIN_EMAIL}")
    return True


def run_employer():
    from scripts.agent_employer import main as employer_main
    log.info("")
    log.info(">>> STARTING EMPLOYER AGENT <<<")
    log.info("")
    employer_main()


def run_employee():
    from scripts.agent_employee import main as employee_main
    log.info("")
    log.info(">>> STARTING EMPLOYEE AGENT <<<")
    log.info("")
    employee_main()


def main():
    log.info("=" * 62)
    log.info("  GENXCRIPT SAAS  --  LOCAL AI AGENT RUNNER")
    log.info(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 62)

    log.info("")
    log.info("Pre-flight checks:")

    models = check_ollama()
    if models is None:
        sys.exit(1)

    from scripts.agent_config import OLLAMA_MODEL
    if not any(OLLAMA_MODEL.split(":")[0] in m for m in models):
        log.warning(f"  Model '{OLLAMA_MODEL}' not found in Ollama.")
        log.warning(f"  Pull it with: ollama pull {OLLAMA_MODEL}")
        log.warning("  Proceeding anyway — Ollama will auto-pull if configured.")

    if not check_app():
        sys.exit(1)

    if not check_credentials():
        sys.exit(1)

    log.info("")
    log.info("All checks passed. Starting agents...")
    log.info("")

    start = time.time()

    run_employer()

    log.info("")
    log.info("Employer agent done. Waiting 5 seconds before employee agent...")
    time.sleep(5)

    run_employee()

    elapsed = time.time() - start
    log.info("")
    log.info("=" * 62)
    log.info(f"  Both agents completed in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    log.info("  Logs:")
    log.info("    scripts/agent_employer_log.txt")
    log.info("    scripts/agent_employee_log.txt")
    log.info("=" * 62)


if __name__ == "__main__":
    main()
