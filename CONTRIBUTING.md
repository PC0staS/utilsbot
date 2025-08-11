Contributing to UtilsBot

Thanks for your interest in contributing!

How to contribute
- Discuss: Open an issue to propose a feature or bug fix before starting work.
- Fork & branch: Create a feature branch in your fork.
- Style: Keep changes focused and small. Include tests when feasible.
- Commits: Use clear messages (e.g., fix: ..., feat: ...).
- PRs: Describe what changed and why, and include screenshots/logs if relevant.

Local setup
- Create a virtual environment
- Install requirements: pip install -r requirements.txt
- Copy .env.example to .env and set DISCORD_TOKEN
- Run: python bot.py

Code guidelines
- Prefer async I/O for network operations
- Guard external calls with timeouts and error handling
- Avoid hardcoding secrets; use environment variables

Thank you for helping improve UtilsBot!
