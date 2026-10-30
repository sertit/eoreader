### Your checklist for this pull request
Please review the [guidelines for contributing](../CONTRIBUTING.md) and the
[AI-assisted contribution policy](../AI_POLICY.md) to this repository.

- [ ] Check the commit's or even all commits' message styles matches our requested structure.
- [ ] Check your code additions will fail neither code linting checks nor unit test.
- [ ] Check `CHANGES.md` contains an entry with the right prefix (`FIX:`, `ENH:`, `OPTIM:`, `CI:`, `DEPS:`, `DOC:`, `LINT:`, `TST:`) — *or mark n/a for mechanical changes and say why*.
- [ ] The change is scoped to the issue it resolves (no unrelated changes) — *or explain in the description if no issue applies*.

### AI-assisted review

If AI assistance was material for this PR (and only then), please complete
this section. See [AI_POLICY.md](../AI_POLICY.md) for the full policy and the
recommended workflow.

- [ ] I personally reviewed all AI-generated code, tests, and documentation, and I understand them.
- [ ] I ran the project checks (`pre-commit run --all-files`, targeted `pytest`) and report the results in the description below.
- [ ] This PR does not attribute authorship to any AI tool or service.
- [ ] I disclosed AI assistance in the PR description (if applicable).

**Summary (a few sentences, in your own words — this is sufficient evidence of
review):**

- What AI generated, and what you accepted/rejected and why
  (e.g., "rejected the suggested refactor of `_load_dem` as out of scope").
- What you manually verified
  (e.g., "verified band mappings against `s2_product.py`").
- Which checks you ran (e.g., `pre-commit run --all-files`,
  `pytest ci/on_push/test_satellites.py`) — or state that CI is the validation
  path and why (e.g., no local test data, no SNAP).

> 

For mechanical PRs (dependency bump, pre-commit autoupdate, typo), write
"n/a" in this section. You may also add the `ai-assisted` label to the PR.
### Description
Please describe your pull request in your own words.

### Further comments
If this is a relatively large or complex change, kick off the discussion by explaining why you chose the solution you did and what alternatives you considered, etc...

Thank you!
