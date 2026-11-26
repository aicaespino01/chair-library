# Chair Library

One file per office chair model, with facts taken from the maker (sizes, adjustments, materials, warranty), every shop listing seen, reviews (labelled independent, seller or paid ad), pros and cons, and what is still unknown.

Made to be reused: for chair comparisons, and later for a website. The block at the top of each file (between the `---` lines) holds the key facts in a fixed form that a website can read.

## How to use

- New chair: send Claude the link and say "chair-info" (for example `/chair-info https://officebusters.ph/products/...`).
- All Office Busters swivel chairs: "chair-info all Office Busters chairs". It works in batches of 5.
- Compare: "compare chairs/okamura-sulato-c331zr.md with chairs/xpanse-f7.md".

## Website

Double-click `Chair Website.html` to open it (photos need internet). It works on a phone screen too.

- **All chairs:** search, sort and filter every chair, as photos or as a table. "Date modified" sorts by the last time each chair file was changed (from the upload history), newest or oldest first.
- **Chair page:** one page per chair file, with everything in that file. Chairs not confirmed yet show a **How to identify this chair** box near the top: the photo or question that settles the model, written for anyone. It comes from the chair file's "How to identify it" section, or, if the file has none, from the label/model lines of "Missing info".
- **Sort and filter extras:** "Date added" (first upload of the chair file) and "Date modified" sorts; filter "Only chairs with our own photos (no shop photos)" keeps chairs with photos in `photos/`.
- **ChairTok:** the switch at the top turns the site into a simple TikTok-style photo feed (swipe up for the next chair, swipe sideways for more photos, double-tap to like, Info for all the facts). It shows every chair that has a video (20 now), plus confirmed chairs with our own photos. Chairs with a video in `videos/` play it like a TikTok (starts muted: tap "Tap for sound"). ChairTok is the default view when the site is opened from its plain address; once someone switches back to the library, that phone remembers it, like day/night mode. Links to a chair page (#chair/...) always open the normal page. Direct link: https://aicaespino01.github.io/chair-library/Chair%20Website.html#chairtok
- **Compare:** up to 3 chairs side by side.
- **Find my chair:** type your height (and desk height, budget, weight if you like); every chair is ranked by fit, with the reasons.
- **In store:** for a shop visit, on the phone. Type the code from the sticker under the seat and the matching chairs show up with the price logged and how much is still good value; a chair that is new to the library can be saved there (code, brand, price asked, branch, measured seat height, notes) and sent to yourself. Saved chairs stay on that phone only.
- **Model tiers:** one 4-level scale for Okamura, Itoki, Kokuyo, Plus, Uchida and Steelcase: 1 Flagship, 2 Middle, 3 Standard (the baseline: a normal office task chair), 4 Economy (below the baseline). A tier comes from the maker's own class word (for example Okamura's "ミドルクラス") or, if there is none, the list price of a new chair, with bands set from Okamura's own labelled chairs. Every chair whose model is known shows a tier badge on its card, chair page, the table, Compare and the ChairTok Info panel. The **Tiers** page (`#tiers`) shows the ladder for all brands, or one brand at a time, with the maker's words, prices, sources and your chairs under each series. "Reference only" rows (Contessa II, Kokuyo Bezel, Steelcase Gesture) are not in the library and not seen at Office Busters Philippines. Sort "Model tier: highest first" and filter "Model tier" (for example "Tier 3 or higher" = Standard and above) are on All chairs. In Find my chair the tier only breaks ties between chairs with the same match %. Condition, age and price never change a tier.
- **Japan price and value:** each chair shows the price of a new one in Japan with a rough peso estimate, and a value rating (price here as a % of that), with the reasons. The yen-to-peso rate and the value limits are in `website/settings.json`.

The website is built from the chair files, so never edit it by hand. After adding or changing chair files, rebuild it from this folder with `node website/build.js` (chair-info does this for you).

## Folder

- `Chair Website.html`: the website (built from `chairs/`)
- `index.html`: opens the website at the online link; `.nojekyll` makes GitHub show the files as they are
- `sw.js`, `manifest.webmanifest`, `icon-*.png`: keep the website on the phone so it opens with no signal, and give it a proper icon on the home screen. Change `CACHE` in `sw.js` if those files change.
- `website/`: `build.js` and `template.html`, which make the website, and `settings.json` (yen-to-peso rate, value limits)
- `videos/`: the ChairTok videos (`<chair id>.mp4` plus a `.jpg` cover), and `feed.json` (feed order and format). Made by `python3 website/make_videos.py` in 11 formats (salesman, brain rot, nervous salesperson, who's-that-chair mystery, nature documentary, AI-slop parody, 360° spin, breaking news, POV, dating profile, dad jokes). Facts come from the chair files; jokes and hype are for fun. All music is generated by the script (no songs). Chairs with no own photo get a cartoon chair marked "no photo yet". The chair-to-format list is `PLAN` in the script; after changing it or a chair file, run the script, then `node website/build.js`.
- `tiers/`: `scale.md` (the shared 4-level scale, why it is built this way, and notes such as Feego vs Escudo) and one file per brand (`okamura.md`, `itoki.md`, `kokuyo.md`, `plus.md`, `uchida.md`, `steelcase.md`) with that brand's Ladder table and sources. A chair gets the tier of the series its model line starts with (Matches column); chairs not identified get none. To add a series, add a row and rebuild.
- `index.md`: list of all chair files
- `template.md`: the layout every chair file follows
- `chairs/`: the chair files

## Online

- Website: https://aicaespino01.github.io/chair-library/ (updates about a minute after each upload)
- On a phone: open that link, tap Share, then "Add to Home Screen". Open it once on wifi before a shop visit, and on the **In store** page tap "Keep all pictures too", so everything works inside a shop with no signal.
- Files: https://github.com/aicaespino01/chair-library (public: only shop and maker information, no personal or clinic data)
