# AGENTS.md — rules for agents working in this repository

Znanjograf is an open diagnostic knowledge graph for Serbian primary-school
mathematics (grades 1–8): topics, prerequisite edges, a verified question bank
and a static site. Read `docs/superpowers/specs/2026-11-26-znanjograf-design.md`
before changing anything structural; it is the source of truth for the design.

## Commands

```
python3 -m zg all        # every gate CI runs; must be green before any commit
python3 -m zg validate   # structural rules V1–V11
python3 -m zg verify     # recompute every answer from its `check`
python3 -m zg lint
python3 -m zg build      # writes _site/ in both scripts
python3 -m zg status     # what is verified, what is stale, per grade
node --test              # engine, figures, layout, formulas
```

## Hard rules

- **Python standard library only** in `zg/`. No `eval`, no pip dependencies.
- **English identifiers, Serbian content.** File names, JSON keys, commands and
  code are English; every string a pupil or teacher reads is Serbian Latin.
- **Latin is the source of truth.** Never hand-write Cyrillic; it is generated.
- **Never copy** text, data or code from `cn-math-taxonomy` or any other
  curriculum dataset. Everything here is authored for this repository.
- **Curriculum texts**: follow the rule recorded in
  `data/curriculum/sources.json` (verbatim only with a recorded legal basis;
  otherwise paraphrase with a pointer to the act and page).
- **Ids are forever.** A topic `id` is never renamed or deleted; merge or split
  through `data/aliases.json` and `data/registry.json`.
- **One file, one owner.** When several agents work in parallel, each writes
  only the files it was assigned; shared seam files are wired by the
  coordinator.
- **A gate that fails means the content is not done.** Do not weaken a check to
  make content pass; fix the content.
- Numbers in the README come from `python3 -m zg report`; never type them.
- **UI strings**: every sentence a user reads lives in `site/js/strings.js` (Serbian Latin);
  write placeholders in the `${name}` form — the build protects `${…}` while transliterating
  and would turn a bare `{n}` into `{н}` in the Cyrillic mirror.
- **Node tests**: `node --test "tests/node/**/*.test.js"` with the quotes; a bare directory
  argument reports one false failure.

## Commits

Conventional commits: `type(scope): subject`. Types: `feat`, `fix`, `docs`,
`data`, `test`, `chore`, `refactor`. Commit after every verified step; the
session may be cut off at any time and only committed work survives.

## Content conventions (summary)

- Math in `$…$` LaTeX; decimal comma inside math is `{,}`; `\cdot`, `:`, `15\,\%`.
- Serbian decimal comma, space as thousands separator, `15 %`, Latin unit
  symbols in both scripts.
- Each topic: at least 2 `basic` and 2 `standard` questions; the first standard
  question is a typed number wherever possible, the second is multi-step.
- The full rules are in `docs/autorski-vodic.md`.
