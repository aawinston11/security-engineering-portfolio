# Contributing

This is a personal portfolio repo, not an open-source project soliciting PRs. The conventions below exist so future-me on a new machine, an interview reviewer, or any contributor I invite can move fast without breaking the security posture.

## Local setup

```bash
git clone https://github.com/aawinston11/security-engineering-portfolio.git
cd security-engineering-portfolio
cp .env.example .env
chmod 600 .env                 # group + other should not read API keys
$EDITOR .env                   # fill in ANTHROPIC_API_KEY / OPENAI_API_KEY as needed
```

Then `cd` into any project and run `make help` to see what's available. Each project is independently set up with its own `uv.lock`.

**Required tools:** Python 3.11+, [`uv`](https://docs.astral.sh/uv/), Docker (for the MCP project's SIEM mock), Ansible 2.14+ (for the hardening role only).

**Recommended:** [pre-commit](https://pre-commit.com) (`brew install pre-commit && pre-commit install`) — wires up the gitleaks hook below.

## Security conventions

These exist because the `/cso` audit on 2026-05-08 surfaced gaps. Each rule has a one-line "why."

### Pin GitHub Actions to commit SHAs, not tags

Mutable tags (`@v3`, `@v4`) re-pointing is the canonical CI supply-chain attack. Pin every `uses:` line to a 40-char SHA with the version as a trailing comment:

```yaml
- uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4.3.1
- uses: astral-sh/setup-uv@caf0cab7a618c569241d31dcd442f54681755d39  # v3.2.4
```

Resolve a tag to a SHA:

```bash
gh api repos/<owner>/<repo>/git/refs/tags/<tag> --jq '.object.sha'
# If that returns a tag-object, follow up:
gh api repos/<owner>/<repo>/git/tags/<sha> --jq '.object.sha'
```

Dependabot (`.github/dependabot.yml`) opens weekly PRs to bump the SHAs.

### Secret-scan locally before commits

`.pre-commit-config.yaml` runs gitleaks on every staged file. Once-only setup:

```bash
brew install pre-commit
pre-commit install
pre-commit run --all-files     # one-time scan of the full tree
```

The gitleaks hook is SHA-pinned itself. Run `pre-commit autoupdate` periodically.

### `.env` lives at the repo root, gitignored, mode 0600

```bash
cp .env.example .env
chmod 600 .env
```

Each project's CLI uses `python-dotenv`'s `load_dotenv()`, which walks up from the cwd, so the same `.env` works whether you run from the repo root or any project subdir.

Never commit `.env`. Never weaken its permissions. Never paste real keys into commit messages, PR descriptions, or screenshots.

### Use the test/demo paths a recruiter would, not just the happy path

The CI workflow (`.github/workflows/ci.yml`) runs unit tests across all four Python projects on every push to `main` and `restructure-pillars` and on every PR to `main`. It does NOT run the eval harness — that costs API budget and gates only local runs. Before opening a PR that changes any agent/triage/IR code, run the full eval locally:

```bash
make -C agents/llm-alert-triage eval
make -C agents/ir-copilot eval
make -C agents/ir-copilot redteam
```

For the MCP project specifically, run `make demo` and verify the output looks right — that's what reviewers will run first.

## Commit + branch conventions

Conventional commits, scoped:

```
chore(security): SHA-pin CI actions, add Dependabot, gitleaks pre-commit
feat(agents/llm-alert-triage): provider-specific prompts ship the iteration
docs(notes/writeups): add anthology post bridging the four flagship projects
```

Long-running work happens on feature branches off `main`. The `restructure-pillars` branch is the current integration line; merges to `main` are the ship gate.

Destructive git ops (force push, branch delete, history rewrite) need explicit per-action authorization. Don't let a tool blanket-authorize them.

## Merging to `main` (PR workflow, required)

`main` is protected. Direct pushes are rejected unless all four CI jobs (`detection-as-code`, `mcp-security-tooling`, `llm-alert-triage`, `ir-copilot`) have passed on the exact commit SHA being pushed. Force-push and branch deletion are blocked. Admin (the repo owner) can override in emergencies; nobody else can.

The supported workflow is PR-based:

```bash
# Push your work to the integration branch
git push origin restructure-pillars

# Open a PR against main
gh pr create --base main --head restructure-pillars \
  --title "Merge restructure-pillars: <one-line summary>" \
  --body "<what shipped, why, anything to watch>"

# CI runs against the PR's merge commit. When all 4 jobs are green:
gh pr merge --merge        # preserves the --no-ff merge commit pattern
                           # (--squash for flat history; --rebase for linear, both allowed)
```

Why this is the workflow, not "annoying overhead":
- Every merge commit on `main` had green CI on its exact SHA *before* it landed. No "I'll just push and let CI tell me" drift.
- Each PR is a permanent, linkable artifact: description, diff, checks, conversation. Recruiters scrolling the Pull Requests tab see the project's history as reviewable units.
- Branch protection settings are publicly visible via the GitHub API. "Yes, `main` is protected" is itself a portfolio signal.

The `restructure-pillars` branch is recreated from `main` after each merge:

```bash
git checkout main && git pull origin main
git branch -D restructure-pillars                         # local cleanup; remote auto-deleted by gh pr merge --delete-branch
git checkout -b restructure-pillars && git push -u origin restructure-pillars
```

Or just keep using the existing branch — `git pull origin main` into it, resolve any conflicts, and continue.

## Adding a new project to the portfolio

1. Pick the right pillar: `agents/`, `detection/`, or `foundations/`.
2. Use `notes/_TEMPLATE.md` as the per-project README skeleton (Problem / What's shipped / How it works / Run it / Layout / Interview-ready / References).
3. Ship a `Makefile` with the standard surface: `help`, `setup`, `test`, plus project-specific verbs (`run`, `eval`, `demo`, `redteam`, etc.). Every target gets a `## description` so `make help` works.
4. Ship a `pyproject.toml` with pinned floors and a `uv.lock`. Track the lock.
5. Pin `.python-version` to `3.11`.
6. Add a `pip` ecosystem entry to `.github/dependabot.yml`.
7. Add a CI job to `.github/workflows/ci.yml` (use existing jobs as templates — same SHA-pinned actions).
8. Wire `--help`, `-h`, and `help` into any new CLI from day one. Every bare invocation prints the usage to stderr and exits 2.
9. Surface the project in the root `README.md` flagship table with a one-liner and concrete metrics.

## Methodology

See [METHODOLOGY.md](METHODOLOGY.md) for the AI-assisted / human-validated, evidence-first, interview-ready operating principles.
