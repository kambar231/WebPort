# __TOOL_NAME__

Human setup notes. **Agents: read [SKILL.md](SKILL.md)** — that's the canonical contract.

```bash
pip install -r requirements.txt
cp .env.example .env   # add keys if the tool needs any
python3 engine.py run "hello"   # smoke test — expect one JSON object on stdout
```

Register as a skill (symlink so the repo stays the single source of truth):

```powershell
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\__TOOL_NAME__" -Target "$PWD"
```
