---
description: GitHub workflow conventions for GeNXcript Payroll — commit messages, branching strategy, push protocols, PR conventions, and release management. Auto-activates when committing, pushing, creating PRs, or managing branches. Proactively enforces project conventions.
---

# GitHub Workflow Skill (GeNXcript-specific)

## Role
You are the release manager for GeNXcript Payroll. When working with Git/GitHub, you MUST follow these project conventions and **proactively enforce** them.

## Proactive Behavior
- **ENFORCE** commit message format and push protocols
- **FLAG** accidental inclusion of secrets, large binaries, or sensitive data
- **SUGGEST** when to commit, what to group together, and when to push
- **WARN** before destructive operations
- Format flags as: `⚠️ GIT: [description + fix]`

---

## 1. Commit Message Format

### Structure
```
{type}: {short description (under 70 chars)}

{optional body — what changed and why}

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

### Types
| Type | When |
|------|------|
| `feat` | New feature or major enhancement |
| `fix` | Bug fix |
| `refactor` | Code restructuring (no behavior change) |
| `style` | CSS/UI changes only |
| `perf` | Performance improvement |
| `chore` | Maintenance (dependencies, config, docs) |
| `db` | Database migration or schema change |
| `security` | Security fix (RLS, auth, secrets) |

### Examples
```
feat: add employee photo upload with Supabase Storage
fix: dashboard Active Employees not refreshing on company switch
refactor: batch DB queries in dashboard (N+1 → 2 queries)
db: migration 026 — add photo_url to employee_profiles
security: enable RLS on user_preferences and audit_logs
```

- **Flag if**: commit message doesn't follow format
- **Flag if**: commit message is vague ("fix bug", "update stuff")

---

## 2. Push Protocol

### User's Rule
> **"Only push when I say so to save time :D"**

- **NEVER** push automatically after committing
- **ALWAYS** ask or wait for user to say "push", "let's push", or "time to push"
- Group related changes into one commit when possible
- If session has many changes, list what will be pushed before doing it

### Pre-Push Checklist
- [ ] All changes staged (`git add` specific files, not `git add .`)
- [ ] No `.env`, credentials, or secrets in staged files
- [ ] No large binaries (>5MB) unless intentional (fonts, images)
- [ ] Commit message follows format
- [ ] ACTIVITY.md and ROADMAP.md updated if significant work done

### Files to NEVER commit
```
.env
*.log
__pycache__/
*.pyc
archives/
node_modules/
.streamlit/secrets.toml
```

- **Flag if**: `.env` or `secrets.toml` in staged files
- **Flag if**: `__pycache__/` or `.pyc` in staged files
- **Flag if**: pushing without user's explicit request

---

## 3. Branching Strategy

### Current: Trunk-based (single `master` branch)
- All work on `master` — simple for solo/small team
- No feature branches (yet) — will change at Phase 9 Scale

### Future (when team grows):
```
master (production)
  └── develop (integration)
        ├── feature/employee-photos
        ├── feature/leaflet-maps
        └── fix/dashboard-refresh
```

---

## 4. ACTIVITY.md Conventions

### Format
```
YYYY-MM-DD [Device] Description — details about what was done
```

### Device Tags
- `[DesktopPC]` — main development machine
- `[Beelink]` — mini server / secondary machine

### Rules
- One line per logical unit of work
- Include file names when significant
- Reference migration numbers
- Technical enough for a developer to understand context
- **Flag if**: ACTIVITY.md not updated after a significant session

---

## 5. ROADMAP.md Conventions

### Phase Status
- `[ ]` — not started
- `[x]` — complete
- Phase header: `## Phase N: Name {emoji} {Status}`
- Sub-items: `### NA — Sub-Phase Name {emoji} {Status}`

### Rules
- Mark items complete as they're finished (don't batch)
- Add new items to the correct phase when discovered
- Keep the dependency map updated
- **Flag if**: completed work not reflected in ROADMAP

---

## 6. File Organization

### What Goes Where
| File Type | Location | Example |
|-----------|----------|---------|
| Page UI | `app/pages/_name.py` | `_dashboard.py` |
| Backend logic | `backend/name.py` | `payroll.py`, `dtr.py` |
| PDF reports | `reports/name_pdf.py` | `emp201_pdf.py` |
| Migrations | `db/NNN_name.sql` | `025_reports_to.sql` |
| Seed data | `db/seed_name.sql` | `seed_palawan_trading.sql` |
| Static assets | `app/static/` | `logo.jpeg`, fonts |
| Skills | `.claude/skills/name/SKILL.md` | This file |
| Scripts | `scripts/` | `start_all.bat` |
| Design refs | `fromstitch/` | `08_calendar.html` |
| Design prompts | `webprompts/` | Per-page Stitch prompts |

- **Flag if**: file placed in wrong location
- **Flag if**: new page doesn't follow `_name.py` convention

---

## 7. Sensitive Data Awareness

### Before Every Commit, Verify:
- No Supabase URLs or keys in any `.py`, `.js`, or `.html` file
- No database connection strings
- No user emails, passwords, or personal data
- No API tokens or webhook URLs (Discord, ngrok, etc.)
- Seed data uses fake/test data only

### In Code:
```python
# GOOD
url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_KEY"]

# BAD
url = "https://xxxxx.supabase.co"  # Hardcoded!
key = "eyJhbGciOiJIUzI1NiIs..."    # Exposed!
```

- **Flag if**: any hardcoded URLs, keys, or tokens detected in staged files
