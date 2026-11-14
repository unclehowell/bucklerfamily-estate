# Changelog — Mr Wolf (webapp 40 of 59)

## [2.2.0] - 2026-11-14
### Added
- Leaderboard order toggle: **Our case** (default; the family's framework order, `priority` field) and **Threshold score**. Gauges always use the score (issue #12).
- New leads: MW-16 the 12-year paper playbook at HM Land Registry; MW-17 1974 TV footage of Mary (Nancy) Williams, never before the 1987 court; MW-18 the 1988 footage's release timing.
### Changed
- MW-01: family heirlooms hold John Williams's own signature; lead reframed as the signature comparison and the start of the 1939 → 1952 → 1955 → 1962 chain; rescored 20 → 40.
- MW-11: corrected to the judgment's own words (EG [1987] 2 EGLR 168 pp.170–171): letters sent to her solicitor and received the morning of 4 Nov 1974; execution stayed "pending Mrs Buckler's agreement"; warrant withdrawn "before she had given any instructions"; BP "neither sought nor waited for her acceptance". Family-archive points labelled; later authority (Smith v Molyneaux 2016, Brown v Ridley 2024) added.
- MW-04: reframed to include the 1962 order built on the 1955 order's ambiguity.

## [2.1.1] - 2026-11-14
### Changed
- MW-11: the 1974 squeeze added to the argument timeline (owner addition, issue #9). Letters dated 31 Oct 1974, the first day the warrant could be enforced; execution stayed 4 Nov; warrant withdrawn by 25 Nov, leaving her appeal and her July 1974 ownership plea undecided. Our case: no time and no forum to answer. Scores unchanged.

## [2.1.0] - 2026-11-14
### Changed
- Lead #1 (MW-11) rewritten around our argument (owner feedback, issue #9): every attempt to make her occupation permissive was refused or left unsigned (1949, 1954, 1955 ambiguity, 1959, 1965), she pleaded ownership in July 1974, and the family record is that she wrote back after the 1974 letters. Records widened to the whole chain. Scores unchanged.
- Limb 3 relabelled "New: not raised and decided in 1987" to match Takhar v Gracefield [2019] UKSC 13.
### Added
- `argument` field per lead (1987 court vs our case, then dated steps with record and state), shown as a timeline at the top of the lead modal.
- Each lead modal states why it ranks where it does: limb 2 (goes to the reason BP won) vs proof of deception held today.

## [2.0.1] - 2026-11-14
### Fixed
- Data files are read with literal fetch('leaderboard.json'), fetch('routes.json') and fetch('data/central.json') calls, so the estate build (dbserve FETCHLIT) keeps them as plain files. Root JSON files otherwise answer 404 live without the service worker.

## [2.0.0] - 2026-11-14
### Changed
- Rebuilt as a gauge dashboard (owner brief 14 Nov 2026, issue #7): threshold gauge (best lead vs 100), route gauges (Dishonesty, Concealment, Public bodies), limb gauges (best per Takhar limb, mark at 40 = counsel-ready), chips, then the leaderboard on the landing view.
- All longer text moved into modals (native dialog): each lead row, gauge, chip and the (i) rubric. No text removed.
- Record chips in lead modals show date and title from data/central.json.
### Added
- routes.json: route tags per lead (our classification); leaderboard.json is unchanged.
- mw.js builds every gauge, the table and the modals in the browser from leaderboard.json, routes.json and data/central.json; a score change needs only a JSON edit.

## [1.0.0] - 2026-11-01
### Added
- New webapp at /mr-wolf/ (branch section/mr-wolf): "Mr Wolf", subtitle "What's the time, Mr Wolf?".
- Leaderboard of 15 leads scored out of 200 on the four Takhar limbs (0–50 each); bar marked at the 100 threshold.
- Ten seeded leads merged with the twelve grounds already scored by our reopen research (no duplicates); three leads carry seed scores.
- Each row: rank, score, per-limb breakdown, what would raise it, status, and catalogue records (internal links).
- Published rubric and mapping (reopen research 0–5 per limb x10). Highest score at launch: 80. Nothing reaches 100.
- leaderboard.json for later score updates; "40 of 59" parcel link; en/cy/es interface strings.
