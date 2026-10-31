# Intake: adopting a third-party creative tool

Use this for any repository, skill, prompt pack or library Atelier wants to learn from or copy. The goal: take its core logic, never its risks. Worked example: huashu-art-motion, adopted on 30 Oct 2026 (the last section).

Keep a working folder outside this repository for each tool: `<sandbox>/<tool>/_vet/` (the source copy, the scan, the verdict, the referee, a log) and `<sandbox>/<tool>/_module/` (what we keep). Only the module's files, once tested, come into the repository.

## Step 1. Vet (read only, run nothing)
1. An Opus agent does the vet. Nobody clones, installs or runs the tool before the verdict.
2. Get the source without running anything: `git -c core.hooksPath=/dev/null clone --no-checkout <url> _vet/src`, then check out. No submodules, no LFS. Record the commit SHA.
3. Scan every file, reading bytes only: executable and archive headers, bad media headers, invisible and bidi characters, long base64 runs; network, exec, environment and secret reads, home-folder and Claude-config access, install steps, file writes, obfuscation, and injection phrases in every language the source uses.
4. Read in full: every skill or prompt file (the skill file, agent files, every reference the skill tells the agent to read), and every script that touches the network, credentials, the file system outside the project, or a subprocess. Read each line the scan hit.
5. Check bundled third-party files against the official release by the git blob hash, not the file on disk (line-end conversion on Windows changes the disk file).
6. Look for: prompt injection; self-editing instructions (in every reference file the skill points to, not only the main skill file); update checks and telemetry; inline dependency blocks (PEP 723 `# /// script`) and code that spawns `uv run`, `npx` or `pip`; credential, browser or home-folder reads; writes to `~/.claude`, settings, hooks or skills; install or postinstall scripts; typosquatted dependencies; paid APIs.
7. Write `_vet/VERDICT.md`: SAFE, SAFE WITH CONDITIONS or NOT SAFE; each finding with file:line; coverage as counts with denominators; what the tool does in 5 plain lines.
8. A second Opus agent checks the verdict against the source and writes `_vet/REFEREE.md`. The vet is not verified before that.

Stop on NOT SAFE. Report it and keep nothing.

## Step 2. Licence
1. Read the licence file. Record the exact holder line and the SPDX id.
2. Answer two questions: may we copy its code and logic into Atelier, and may we use its output in public posts?
3. List what the main licence does not cover: fonts, data files, bundled libraries, sample media, brand or character IP, living artists' styles.
4. No licence file means all rights reserved: learn ideas only, copy no code and no text.
5. Copyleft (GPL, AGPL): copy no code into Atelier; rewrite from the ideas.

## Step 3. Extract
1. Name the abilities: what kinds of output it makes.
2. Write the method in Atelier's words: the rules and numbers that make the output good, and when each applies. Translate; do not paste long passages.
3. Copy only small, pure, reusable code (no network, no file system, no credentials), from the git blob at the vetted commit.
4. Add one header line to each copied file: source path, commit, licence, and every change you made.
5. Put the full licence text beside the copied code.

## Step 4. Strip
Remove, and list with the reason:
- self-editing, auto-update and version-check steps;
- telemetry, analytics and calls home;
- install, setup and postinstall steps;
- paid API clients and credential loaders;
- media downloaders;
- unsafe runtime flags (for example `--disable-web-security`) and remote URL loading;
- promotion files and links to remote "agent protocols";
- assets outside the licence (fonts, sample media, characters).
Replace a stripped runner with new code that does the safe part and blocks every request that is not a local file. In Atelier, prefer joining an existing script to adding a second one.

## Step 5. Test
1. Make one small real piece with the module, on a sample topic, with no client names or data. Local tools only: no paid service, no downloads.
2. Prove it with numbers: format, size, duration, frame count (ffprobe), and a determinism check where it applies.
3. Look at stills and a contact sheet. Fix defects and render again.
4. A second agent reviews the output only, never the code, and scores it. Report the score and the gap plainly.
5. Scan every file you wrote for U+2013 and U+2014 with a script: zero hits.

## Step 6. Credit and register
A new tool touches the files below and no others. No test and no script is edited: `tests/test_motion.py` reads every tool section of vendor/MANIFEST.md, checks each against its own folder, commit and licence, checks that a `.gitattributes` keeps the folder's bytes and that CREDITS.md credits the tool (item 3), fails on any file under vendor/ that no section lists, and scans every code file a section lists for spawned installers. Its test `test_second_tool` registers a fake tool this way in a temp copy, and it passes; take away its CREDITS row or its `.gitattributes`, and it fails.
1. **The vendor folder**, `plugins/mansions/skills/atelier/vendor/<tool>/`: the copied files, each starting with its header line (step 3, item 4), the full licence text (for example `LICENSE-<tool>.txt`), and a `.gitattributes` holding `* -text`, so every checkout keeps the bytes, and so the blob hashes, as they are.
2. **The MANIFEST rows**, in `plugins/mansions/skills/atelier/vendor/MANIFEST.md`: one row in the top table (source, commit, licence, what is included, what is excluded and why, where Atelier uses it), and a section of its own in this form:
   ```
   ## <tool>
   Folder: `<tool>/`. Commit: <short sha> (<full 40-character sha>). Licence: <SPDX id>, `<licence file>`.

   | File | Upstream path | Upstream blob | Vendored blob | Lines changed besides the header |
   |---|---|---|---|---|
   | `<licence file>` | `LICENSE` | <blob> | <blob> | none (no header) |
   | `lib/<file>.js` | `<upstream path>` | <upstream blob> | <vendored blob> | <count> |
   ```
   Every file in the folder (`.gitattributes` aside) has a row, the licence file among them. `git hash-object <file>` prints the vendored blob. A row marked `none (no header)` is copied unchanged; every other file's first line names the commit as `commit <short sha>` and the licence by its SPDX id.
3. **CREDITS**, in `CREDITS.md` and `plugins/mansions/skills/atelier/CREDITS.md` (keep the two identical): one row with the exact holder line and one credit line in this form, "<what> adapted from <repo> by <author>, commit <sha>" (for example "Five drawing files adapted from alchaincyf/huashu-art-motion by alchaincyf, commit 8a0d7d7"; tests/test_motion.py checks the form and the commit), and the tool's name in the "Vendored files" sentence under the table.
4. **The licence** is the file in item 1, beside the code.
5. **The counts and names**: the number of bundled projects in the opening line of both CREDITS.md copies ("bundles files from seven of these projects"), and the tool's name in the list of the "Credits" section of README.md. A licence not yet listed joins the list "(MIT, Apache 2.0)" in the licence section of README.md and in both LICENSE copies.

Using the tool's code in a page (a loader such as `assets/lib/art-motion.js`, a reference file, a script option) is a feature, not registration. It comes with tests of its own.

A later upgrade repeats steps 1 to 5 on the diff between the vetted commit and the new one, then updates the commit and the blob hashes in the tool's section. Never pull blindly.

## Worked example: huashu-art-motion (30 Oct 2026)
- **Vet.** Commit 8a0d7d7 of alchaincyf/huashu-art-motion. Byte signatures checked on 509 of 509 files, pattern scan on 372 of 372 text files, 24 files read in full; nothing was installed or run. Verdict: SAFE WITH CONDITIONS. The referee (a second Opus agent) scored the verdict 7 of 10, agreed with it, and added three findings: write-back steps in 21 reference files, unpinned inline dependency blocks in 10 Python files, and the author's likeness excluded from the licence.
- **Licence.** MIT, "Copyright (c) 2026 alchaincyf (花叔 · 花生)". Not covered: 45 fonts (OFL), Arphic stroke data, the author's likeness, showcase media and the studio or living-artist styles some cards imitate.
- **Extract.** The method (shot list, camera language, six ways to fail, film gates) became references/art-motion.md. Five pure drawing files (util, motion, camera, palettes, finish) were copied to vendor/huashu-art-motion/lib with a header line; the only other change made their em and en dashes ASCII.
- **Strip.** The skill file and every reference file (self-editing, a GitHub check every 30 days), every Python script (unpinned dependencies), the renderer (web security off, remote URLs), voice cloning (a paid cloud API reading two credentials), the image fetcher, fonts, stroke data, showcase media and likeness files. The renderer was not replaced by a second one: Atelier's scripts/motion.mjs renders drawn films through assets/lib/art-motion.js and now blocks every request that is not a local file.
- **Test.** tests/test_motion.py (blob hashes, no spawned installers, a fixed-seed film rendered twice, a still stretch under film grain, a blocked remote request) and one real piece, reported in docs/run/README.md.
- **Register.** vendor/MANIFEST.md (files, commit, blob hashes, conditions) and CREDITS.md.
