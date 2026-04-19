# GitHub Guide

## Repository Setup

### Initial Push

```bash
git init
git branch -M main
git remote add origin https://github.com/alep0/rat-connectome.git
git add .
#git reset
#git rm --cached old_versions
git status
git remote -v
git commit -m "feat: initial project structure and refactored pipeline"
git remote set-url origin git@github.com:alep0/rat-connectome.git
git push -u origin main

ls -al ~/.ssh
ssh-keygen -t ed25519 -C "aaaguado@ifisc.uib-csic.es"

eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

cat ~/.ssh/id_ed25519.pub
ssh -T git@github.com

git clone git@github.com:alep0/rat-connectome.git
git clone https://github.com/alep0/rat-connectome.git

```

---

## Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable, production-ready code only |
| `develop` | Integration branch for features |
| `feature/<name>` | New features or analyses |
| `fix/<name>` | Bug fixes |
| `docs/<name>` | Documentation updates |

### Example workflow

```bash
git checkout develop
git checkout -b feature/add-fa-mask-v2
# ... make changes ...
git commit -m "feat: add FA mask v2 to group analysis"
git push origin feature/add-fa-mask-v2
# Open Pull Request → develop
```

---

## Commit Message Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
[optional footer]
```

| Type | When to use |
|---|---|
| `feat` | New feature or analysis |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behaviour change |
| `docs` | Documentation only |
| `test` | New or updated tests |
| `chore` | Dependency updates, CI, config changes |

**Examples:**
```
feat(statistics): add Cohen's d to ensemble comparison
fix(tractography): correct FA threshold application in stopping criterion
docs(api): document run_pipeline parameters
test(tau): add edge case for empty streamlines
```

---

## Pull Request Checklist

Before merging a PR, verify:

- [ ] All tests pass: `python3 -m pytest tests/ -v`
- [ ] `validate_environment.py` passes
- [ ] New functions have docstrings
- [ ] Config changes are reflected in `config/connectome_config.json`
- [ ] Log messages added for new pipeline steps
- [ ] `docs/api.md` updated if public interface changed
- [ ] No hard-coded paths (use config values)

---

## `.gitignore` Key Exclusions

```
# Data (large NIfTI files)
data/raw/**/*.nii
data/raw/**/*.nii.gz
data/raw/**/*.dat

# Results (generated outputs)
results/

# Logs
logs/

# Python cache
__pycache__/
*.pyc
.pytest_cache/

# Conda / venv
.venv/
*.egg-info/
```

---

## GitHub Actions CI (optional)

Create `.github/workflows/tests.yml`:

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: conda-incubator/setup-miniconda@v2
        with:
          environment-file: config/environment.yml
          activate-environment: conn_env
      - name: Run tests
        run: |
          conda run -n conn_env python3 -m pytest tests/ -v
```

---

## Releases and Tags

Tag stable releases following [Semantic Versioning](https://semver.org/):

```bash
git tag -a v1.0.0 -m "Release v1.0.0 — initial refactored pipeline"
git push origin v1.0.0
```

Create a GitHub Release from the tag with a changelog entry.
