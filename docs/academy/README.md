# Restoration Evidence Academy

Supervisor learning companion for the completed Controlled-300 study.

Expected public URL after deployment:
<https://rahul-ds25m008.github.io/painting_restoration_eval/>

## Content and scope

The approved detailed academy contains 37 chapters (N01–N36 plus D02, with
D01 and N12A inside N12), six activities per chapter, 185 notebook questions,
seven synthesis rooms and an 18-question defence recap. Only stale N12/N21/N26/
N29/N33 content was corrected before adding N34–N36. The other 29 original
chapters and the original 34 embedded figures were retained.

The 3 October reporting errata supplements the frozen evidence; this learning
page is not a new scientific run or a replacement Zenodo release.

## Deploy once, then update by pushing

1. Open this repository's **Settings → Pages**.
2. Under **Build and deployment**, select **GitHub Actions** as the source.
   Do not select a branch/folder Jekyll build or create another Streamlit app.
3. Commit and push the academy files and `academy-pages.yml` to `main`.
4. Open **Actions → Deploy Evidence Academy**. Wait for the job to succeed.
   If needed, choose **Run workflow → main**. A first attempt made before
   enabling Pages can be rerun after changing the setting.
5. Open the URL from the deployment job. Confirm the header shows 37 chapters,
   open N36, answer a practice question, refresh, and check retained progress.
   Open one original Evidence figure and a discussion prompt as well.

Subsequent changes to `docs/academy/**` on `main` trigger deployment
automatically. The workflow checks out the academy directory without LFS and
publishes **only `index.html`**, never the repository, research outputs or local
scratch files. The existing Streamlit app and availability workflow are unchanged.

This workflow owns this repository's GitHub Pages site. If another Pages site
is added later, combine the sites deliberately instead of deploying over it.
No new repository, HF bundle, API token or availability watcher is required.

Official setup reference:
[GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Files and local preview

- `source.html`: editable, self-contained academy fragment with embedded lesson
  data and figures. Preserve the approved scientific content when editing.
- `index.html`: exported standalone document used for deployment. It contains
  its own display wrapper and browser-local state bridge; it is not an LFS pointer.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m http.server 8502 --bind 127.0.0.1 --directory docs/academy
```

Open <http://127.0.0.1:8502/>. Stop the preview with Ctrl+C.
Downloading `index.html` and opening it directly also renders the lessons;
browser persistence is most predictable on a stable HTTP(S) origin.

`index.html` was exported from `source.html` using the visualization renderer.
For later edits, regenerate the standalone export from the fragment; updating
the fragment alone does not change the published page. Keep the exported file
in the same commit and test it in an ordinary browser before pushing. The
renderer is a development tool, not a deployment/runtime dependency.

Progress is stored locally in the browser and is not a graded or authenticated
supervisor record. Discussion controls display copyable prompts; no AI service
or account is needed to read the academy. Reset uses an in-page confirmation.
Figures and lessons require no runtime GitHub/HF fetch. The original source
paths displayed within lessons identify repository evidence; they are not
automatic downloads. Existing third-party/painting rights qualifications still
apply to embedded figures.
