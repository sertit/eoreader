# AI Policy

> [!NOTE] 
> In this policy, "AI" means generative AI tools (LLMs and coding agents) that write or modify code and produce human-like text.

AI tools are a regular part of many developers' workflows. 
We expect that, and we do not want this policy to constrain too much which tooling contributors
choose. What it aims to guarantee is only that contributions stay maintainable. 

Writing code is no longer the scarce resource in a project like EOReader: **maintenance** is. 
The goal is simple: AI-assisted contributions should cost maintainers *less* review time, not more.

The policy is based on **trust**, not on surveillance: we ask for disclosure and accountability, not proof. 
Review questions are about the change, not about which tools were used. 
The only process this policy imposes is the
[*AI-assisted review* section of the pull request template](https://github.com/sertit/eoreader/blob/main/.github/pull_request_template.md),
anything beyond it is a conversation, not a checkpoint.

## Responsibility

You own every change you submit, whether you wrote it by hand or an AI did.
Before submitting, you must understand the change and the surrounding code well enough to defend every choice in it. 
**A change you cannot explain in your own words is not ready.**

An AI tool is never the author of a contribution: behind every change stands a human who understood it, took responsibility for it, and will maintain it.
If an AI-assisted change introduces a bug, the one accountable is the human who submitted and reviewed it.

## Disclosure

If AI played a material role in developing your pull request 
(code completion and explanations are not material, generated code that you accept is), say so. 
The PR description is written by you, in your own words,
using the [pull request template](https://github.com/sertit/eoreader/blob/main/.github/pull_request_template.md),
its *AI-assisted review* section is the single record of the self-review.
This policy keeps no parallel checklist. 
If AI assistance was not used or was not material, skip the section or mark it n/a.

Disclose factually (e.g. "AI-assisted, fully reviewed by me"), without advertising a particular vendor or model.

## Communication

In issues, discussions, pull requests, and reviews, the voice is yours: 
AI may fix grammar or translate, but the explanation and its reasoning are yours to produce. 

AI may also polish your prose or draft supporting lists and tables.
Raw AI output, however, does not go into issue or PR threads. 

If a reviewer's question exposes a gap in your understanding, re-read the code before answering.

## Code quality

Contributors are expected to submit changes that meet EOReader's standards and stay inside its invariants: 
- sensor-agnostic API, 
- lazy `load()`/`stack()`, 
- minimal diffs (see [ARCHITECTURE.md](https://github.com/sertit/eoreader/blob/main/ARCHITECTURE.md)).

Unreviewed AI output (verbose, speculative, or off-topic) is rejected.

Watch for the typical AI failure modes this project cares about: 
- scope creep and unrelated refactors, 
- hallucinated band names or APIs, 
- over-verbose code and comments, 
- missing edge-case tests, 
- fixes that address the symptom rather than the cause, 
- and constellation quirks leaking into the base `Product` class.

## No AI authorship or service advertising

Never credit an AI service with anything in the project (commits, pull requests, issues, documentation, review comments). 

Do not add AI tools as commit authors, co-authors, maintainers, reviewers, or credited contributors: 
the human contributor's name, account, and judgment must remain attached to the work.

## Copyright and licensing

All code in EOReader is released under the Apache 2.0 license.
Be aware that AI output can silently reproduce or adapt existing implementations without citing them: 
for major features or conceptual changes, do a reasonable search for prior work. 
If it can be imported as a new dependency, prefer that. If not, cite it, and make sure anything reused or
adapted is [Apache 2.0 compatible](https://github.com/sertit/eoreader/blob/main/LICENSE).
Flag such material explicitly to maintainers.  
Submitting through an AI does **not** relieve you of these obligations.

## AI agents

Running an agent locally (drafting code, reviewing a diff, finding missing tests) is fine: 
you read the result, decide what matters, and make the changes. 
An agent may not open a pull request on its own: whatever it drafts must be checked and submitted by a human.

Agents must not act in EOReader's project spaces (GitHub issues, PRs, Discussions, GitLab) **without human approval**: 
- no opening issues or PRs, 
- no pushing commits, 
- no posting comments or responses, 
- no applying labels, 
- no merging, 
- no release-related changes (tags, version bumps, publish workflows). 

It must never tag maintainers, post progress updates, or request issue assignments. 

See the [hard limits in AGENTS.md](https://github.com/sertit/eoreader/blob/main/AGENTS.md).

## Large AI-assisted contributions

Agents draft quickly, but the review cost is paid by **maintainers**.  
A large diff simply moves that burden from the contributor to the reviewer. 

So for any large AI-assisted contribution (say a major refactor, a framework migration, or a new subsystem), 
open an issue first and build consensus on scope and approach before writing code. 

The issue defines the scope: anything outside it is **out of scope** for the PR.

## Validation

The checks that could be run locally were run and reported accurately: `pre-commit run --all-files`. 
When data is available: `python -m pytest ci/on_push/<relevant>.py --ci_db_dir <local-data-dir>`.
Otherwise, the PR declares CI to be the validation path (e.g. licensed test data, missing SNAP/DEM).

Never report a test as passing if it was not run.

## Handling non-compliant contributions

If a contribution looks like it offloads review work onto maintainers,
maintainers may request changes, close the pull request, or lock the discussion. 

**Red flags**:

- the contributor cannot explain the change,
- the PR reads like raw AI output, including a predominantly AI-generated description,
- it contains hallucinated APIs, files, tests, or behaviour,
- it credits an AI service with authorship,
- AI-generated responses are reposted without understanding,
- the change is far larger or more speculative than the issue requires.

The response is proportional and aimed at rework, not punishment: 
reduce the scope, explain the change in your own words, run and report the project's checks, and confirm the personal review. 
Until then, the PR is not ready for maintainer review.

## Maintainer discretion

Maintainers may waive parts of this policy for trivial or mechanical changes (typo fixes, dependency bumps, pre-commit autoupdates) 
and may require additional validation for complex changes.  
The policy exists to route better contributions to review faster, not to add paperwork.

## Recommended workflow for AI-drafted contributions

**Preferred: human-written, AI-assisted.** 
Write the code yourself, use AI where it helps 
(finding missing tests, spotting edge cases in band/window/CRS handling, reviewing your diff, improving docstrings).

**Accepted: AI-generated, carefully reviewed.** 
The strongest signal that a change drafted by an agent is ready for maintainer review:

1. Start from an existing issue with a consensus on the solution (or open one first).
2. Draft with the agent, constrained by
   [AGENTS.md](https://github.com/sertit/eoreader/blob/main/AGENTS.md)
   (hard limits, verification checklist, self-review questions),
   and ask for a small, focused diff, not a project-wide improvement.
3. Self-review the diff line by line, delete what you don't understand.
4. Run the project checks and an AI review pass using the
   [self-review table in AGENTS.md](https://github.com/sertit/eoreader/blob/main/AGENTS.md#self-review-pass-after-the-checks),
   accept, reject, or fix each finding yourself. Do not apply review output blindly.
5. Write the PR description yourself (including the *AI-assisted review* section),
   submit, and answer review questions in your own words.

## Other resources

These are not part of the policy, they are useful background on the
pitfalls of AI-assisted contributions:

- [LLVM's AI tool policy](https://llvm.org/docs/AIToolPolicy.html)
- [Scientific Python: community considerations around AI](https://blog.scientific-python.org/scientific-python/community-considerations-around-ai/)
- [Open-source AI contribution policies](https://github.com/melissawm/open-source-ai-contribution-policies)

## Acknowledgements

This policy borrows its structure and several conventions from the AI
policies of
[NumPy](https://numpy.org/devdocs/dev/ai_policy.html),
[SciPy](https://docs.scipy.org/doc/scipy/dev/conduct/ai_policy.html),
[GeoUtils](https://geoutils.readthedocs.io/en/latest/contributing.html#ai-policy),
[xarray](https://github.com/pydata/xarray/blob/main/doc/contribute/ai-policy.md).

---

This policy is maintained by the EOReader maintainers and applies to everyone, including maintainers. 
It is reviewed when the contribution flow changes materially, and at least once a year. 

Disagreements or requests for clarification should be raised as GitHub issues, not in PR threads.

_Last reviewed: October 2026._
