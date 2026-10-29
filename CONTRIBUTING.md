# Contribute

A guide for **AI coding agents** (hard limits + agentic rules) lives in [AGENTS.md](https://github.com/sertit/eoreader/blob/main/AGENTS.md).  
The technical reference (architecture, modules, build & test setup, code style, CI/CD, pitfalls) lives in [ARCHITECTURE.md](https://github.com/sertit/eoreader/blob/main/ARCHITECTURE.md).  
The project's AI-assisted contribution policy lives in [AI_POLICY.md](https://github.com/sertit/eoreader/blob/main/AI_POLICY.md).

## Quick start

1. **Find or open an issue**. For new features or behavior changes, there should be an issue with a consensus on the solution. If none exists, open one first (see [Report issues](#report-issues)).
2. **Set up a dev environment**. See [Submit patches](#submit-patches) (`pip install -e .` + `pre-commit install`).
3. **Make a small, focused change**. Keep the diff minimal and scoped to the issue. For new constellations or bands, 
   follow the patterns in [ARCHITECTURE.md](https://github.com/sertit/eoreader/blob/main/ARCHITECTURE.md#key-patterns-for-contributors) and the [templates](#templates).
4. **Run the checks**. `pre-commit run --all-files` must pass. Run the relevant tests if you have local product data (otherwise CI validates for you. See [Running the test suite](#running-the-test-suite)).
5. **Open a PR against `main`** using the [pull request template](https://github.com/sertit/eoreader/blob/main/.github/pull_request_template.md), 
   with a `CHANGES.md` entry and a commit message following the [conventions below](#commit-message-conventions).

Everything else in this file is reference material for the steps above.

## Report issues

Issue tracker: https://github.com/sertit/eoreader/issues

Please check that a similar issue does not already exist and include the following information in your post:

- Describe what you expected to happen.
- If possible, include a [minimal reproducible example](https://stackoverflow.com/help/minimal-reproducible-example) to help us identify the issue. 
  This also helps check that the issue is not with your own code.
- Describe what actually happened. Include the full traceback if there was an exception.
- List your Python and EOReader versions. If possible, check if this issue is already fixed in the latest releases or the latest code in the repository.
- For issues involving a specific product, include the product name (constellation, product type, and, if public, the granule/product ID). Never attach licensed products themselves.

## Submit patches

If you intend to contribute to **EOReader** source code:

```bash
conda env create -f environment.yml
conda activate eoreader
pip install -e .
pre-commit install
```

For the STAC features, also install the `stac` extra: `pip install -e ".[stac]"`.

We use `pre-commit` to run a suite of linters, formatters and pre-commit hooks (`ruff`) to ensure the code base is homogeneously formatted and easier to read. 
It's important that you install it, since we run the exact same hooks in the Continuous Integration. You can also run the hooks manually:

```bash
pre-commit run --all-files
```

The hooks must pass before you submit a PR. If a hook fails, fix the issue. Do not skip or bypass the hook.

Please be sure that your code is running on Python 3.11+.

### Copyright header

Every Python file must start with the Apache 2.0 header:

```python
# Copyright 2026, SERTIT-ICube - France, https://sertit.unistra.fr/
# This file is part of eoreader project
#     https://github.com/sertit/eoreader
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ...
```

The year in the header is the **current release year**. AI tools tend to update the year in every file they touch, but it is only changed project-wide at release time (a `DOC:` commit). 
Do not update the year in unrelated files. New files use the year as it appears in the other headers.

### Running the test suite

For now, you won't be able to run the test suite as we cannot provide an example of each product (some are licensed). 
We will take care of that for you in CI (see [ARCHITECTURE.md](https://github.com/sertit/eoreader/blob/main/ARCHITECTURE.md#cicd) for details).

If you do have access to EO products, tests can be pointed at a local directory with the CI database layout (`optical/`, `sar/`, `others/`, `broken_products/`):

```bash
python -m pytest ci/on_push --ci_db_dir /path/to/ci/database
```

Tests live in `ci/on_push/` (per-PR suite) and `ci/weekly/` (end-to-end suite). SAR tests additionally require the ESA SNAP `gpt` executable to be on your `PATH`.

## Commit message conventions

Commit your changes with an explanatory message. Commit prefixes in use:

- `FIX:` bug fix
- `ENH:` enhancement, new functionality
- `OPTIM:` performance improvement
- `CI:` continuous integration changes
- `DEPS:` dependency updates
- `DOC:` documentation changes
- `LINT:` linting / formatting changes
- `TST:` test changes

Message structure:

- A subject line starting with the prefix, under 80 characters.
- One blank line.
- Optionally, a commit message body.
- Reference the related GitHub issue in the subject or body: `[#242](https://github.com/sertit/eoreader/issues/242)`.

Example:

```text
FIX: Don't fail when trying to load DEM bands if `window=None` [#314](https://github.com/sertit/eoreader/issues/314)
```

## Pull requests

- Create your branch from `main` and open the pull request against `main`.
- Follow the [pull request template](https://github.com/sertit/eoreader/blob/main/.github/pull_request_template.md): check the commit message style and that your code passes linting and tests.
- Make sure your change is covered by tests when possible, and that it is noted in `CHANGES.md` with the right prefix (see *Commit message conventions*).
- Keep pull requests small and focused. Break large work (e.g. a new constellation) into smaller, reviewable steps.
- For new features or behavior changes, there should be a corresponding issue with a consensus on the solution. If there isn't one, open an issue first.
- New public behavior must respect the sensor-agnostic API: generic behavior lives in `eoreader/products/product.py`, sensor specifics in the constellation modules 
  (see [ARCHITECTURE.md](https://github.com/sertit/eoreader/blob/main/ARCHITECTURE.md#key-patterns-for-contributors)).

## Templates

Use the following templates for common tasks. **AI-specific warnings are included in each template.**

- [New Sensor Support](https://github.com/sertit/eoreader/blob/main/.github/templates/new_sensor_template.md)
- [Test Files](https://github.com/sertit/eoreader/blob/main/.github/templates/test_template.md)
- [Documentation Updates](https://github.com/sertit/eoreader/blob/main/.github/templates/doc_update_template.md)

## AI-Assisted Contributions

We recognise that AI coding assistants are now a regular part of many developers' workflows.  
**The preferred path is human-written code**, with AI in a supporting role (finding bugs, suggesting tests, reviewing, improving documentation).  
**AI-generated code is accepted when it is carefully reviewed**: you must be able to explain and defend every line you submit.

The short version of the conditions:

- **You are the author and fully accountable**, regardless of the tools used.
- **Be transparent**: write the PR description (motivation, approach, validation) yourself, and disclose material AI assistance in it.
  (code completion and explanations are not material, generated code that you accept is)
- **No AI authorship or advertising**: no AI tools as authors, co-authors, or credited contributors. No "Generated by ..." in commits, PRs, or changelogs.
- **Agents must not act on your behalf** in project spaces (opening issues or PRs, posting comments, tagging maintainers) without your explicit instruction. 
- **New features and behavior changes need a linked issue** with a consensus on the solution (or say in the description that no issue applies. PRs without one are deprioritized in triage).
- **Follow the pull request template**, including its *AI-assisted review* section.

When interacting with other contributors and maintainers, do not use AI to speak for you (translation or grammar editing is fine). 
Human-to-human communication is essential for an open source community to thrive.

The full policy (the step-by-step workflow for AI-drafted contributions, the rules for automated agents, and how non-compliant contributions are handled) 
is in [AI_POLICY.md](https://github.com/sertit/eoreader/blob/main/AI_POLICY.md).

## Release EOReader

Releases are made by tagging a commit on the `main` branch. To make a new release,

* Ensure you correctly updated `README.md` and `CHANGES.md`
* Check that the version string in `eoreader/__meta__.py` (the variable `__version__`) is correctly updated
* Push your local main branch to remote.
* Create a new release on GitHub. A tag will be created and this will trigger the PyPI publish workflow (`.github/workflows/publish.yml`).

### Update notebooks

* Run the notebooks in a dedicated docker container that points to the data.
* Be sure you have the latest version of EOReader installed (why not installing it in editable mode) `pip install -e <path-to-eoreader>`
* `cd <path-to-eoreader>`
* Run sphinx (here with 14 CPUs) `sphinx-build docs docs/_build/html -E -j 14`
* Zip the `eoreader/docs/_build.jupyter_cache` folder 
* Place it where the path given by the `JUPYTER_CACHE_URL` environment variable points (used in the `readthedocs.yml` file)
