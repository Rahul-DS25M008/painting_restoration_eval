# Trustworthiness cosmetic pass 04

- Title moved another 3 CSS pixels left (cumulative -6 pixels).
- Added a decorative faceless Zhongli portrait on the left canvas. CSS perspective projects its edges onto the inset quadrilateral (52,133), (113,151), (113,470), (52,470) in the 1672 × 941 room. The background and plaque border are unchanged.
- Candidate evidence now displays the exact reference collage, clipped in CSS from the approved reference. This is decorative reference artwork, not a preview of the selected record. Its existing evidence action still opens the selected record.
- Added the reference caption below the existing connector: “The candidate, its damage, and restoration for inspection.”

Assets:

- `streamlit_assets/rooms/trustworthiness_zhongli.png`: generated using the built-in imagegen tool; copied into the project.
- `streamlit_assets/rooms/trustworthiness_evidence_reference.png`: unchanged copy of `approved_current/08_trustworthiness_final.png`, displayed only through the evidence-panel crop.

## Final image generation prompt

Use case: stylized-concept. Asset type: narrow vertical museum canvas artwork for a web gallery. Create a custom faceless full-length portrait of Zhongli from Genshin Impact, unmistakable through his swept dark brown hair with amber tips and signature elegant long brown-and-black coat, geometric gold trim, fitted waistcoat, amber diamond details, dark trousers and gloves. Face deliberately featureless, softly shaded warm neutral oval: no eyes, nose or mouth. Mature dignified upright pose, arms close to body, slim elongated silhouette. Warm sepia oil painting on aged parchment canvas, restrained ochre, umber and bronze-gold palette, soft antique museum lighting. Extremely tall narrow composition: artwork aspect ratio 1:5, complete figure from hair to boots, no clipping, minimal background, no text or symbols outside clothing, no added frame. Flat front-facing rectangular artwork only, no room mockup or perspective; the website will fit and perspective-warp it into a narrow angled plaque. Preserve generous head/foot margins and keep the silhouette narrow enough to fit the full width.

## Verification

All four fast presentation tests pass. Browser click verification confirmed that the reference collage opens “Candidate evidence · original recorded images” for the current p256/HINT mixed-damage candidate, with Clean, Damaged, and Restored images. Scientific data and calculation code are unchanged.
