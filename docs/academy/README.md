# Restoration Evidence Academy

Learning companion for Controlled-300 and the completed physical-damage supplement.

[Open the Academy](https://rahul-ds25m008.github.io/painting_restoration_eval/).

## Content

The Academy contains **39 chapters**: N01–N36 and D02–D04, with D01 and N12A
covered within N12. Each chapter has six activities and five questions, for
**195 notebook questions**, plus seven synthesis rooms and an 18-question defence
recap. The existing chapter order and earlier figures are retained.

- **D02 — Focused portrait audit:** matched hand/control comparisons and exploratory rendered lightness using existing benchmark outputs. Its visual assessment is automated inspection with researcher review and masked model identities, not independent expert ratings.
- **D03 — Real-damage dataset preparation:** source rights, two paintings per
  category, unchanged preprocessing, reviewed partial masks, scale checks and
  the eligible-case handoff. The saved ten-painting mask atlas is embedded.
- **D04 — Real-damage restoration and evaluation:** four methods, targeted SD
  prompts, forty primary candidates, ten four-seed groups, reference-free
  diagnostics and descriptive controlled comparisons. Saved rd004 comparison
  and seed-variability figures illustrate the interpretation limits.

The lessons use saved evidence; they do not run inference or recompute metrics.
The physical supplement is separate from the frozen Zenodo v1.0.0 archive.
Source credits and reuse qualifications continue to apply to embedded figures.

## Build and preview

`source.html` contains editable lesson data, figures and the interface.
`index.html` is its generated standalone publication. From the repository root:

```powershell
.\.venv\Scripts\python.exe tools/build_academy.py
.\.venv\Scripts\python.exe -m http.server 8502 --bind 127.0.0.1 --directory docs/academy
```

Open <http://127.0.0.1:8502/>. Stop the server with Ctrl+C. Commit the source
and regenerated publication together. No external renderer, account, token or
runtime evidence download is required.

Progress is stored in the browser on the current origin. Existing compatible
learning records are retained; it is not an authenticated or graded record.
Discussion controls provide revision questions for independent study or a
discussion partner. They do not send messages. Reset requires confirmation.

## Deployment

The **Deploy Evidence Academy** workflow publishes only `index.html` to GitHub
Pages after changes to `docs/academy/**` reach `main`. Pages uses **GitHub Actions**
as its deployment source. The workflow enforces the two-megabyte publication
limit. The museum's Streamlit deployment is separate.

After publication, open both new chapters, inspect their figures, answer a
question and refresh to check retained progress. The workflow can also be
dispatched manually from Actions. Older dated validation records describe
their original revision, not the current chapter count.
