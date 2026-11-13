# Chair Library

One file per office chair model, with facts taken from the maker (sizes, adjustments, materials, warranty), every shop listing seen, reviews (labelled independent, seller or paid ad), pros and cons, and what is still unknown.

Made to be reused: for chair comparisons, and later for a website. The block at the top of each file (between the `---` lines) holds the key facts in a fixed form that a website can read.

## How to use

- New chair: send Claude the link and say "chair-info" (for example `/chair-info https://officebusters.ph/products/...`).
- All Office Busters swivel chairs: "chair-info all Office Busters chairs". It works in batches of 5.
- Compare: "compare chairs/okamura-sulato-c331zr.md with chairs/xpanse-f7.md".

## Website

Double-click `Chair Website.html` to open it (photos need internet). It works on a phone screen too.

- **All chairs:** search, sort and filter every chair, as photos or as a table.
- **Chair page:** one page per chair file, with everything in that file.
- **Compare:** up to 3 chairs side by side.
- **Find my chair:** type your height (and desk height, budget, weight if you like); every chair is ranked by fit, with the reasons.

The website is built from the chair files, so never edit it by hand. After adding or changing chair files, rebuild it from this folder with `node website/build.js` (chair-info does this for you).

## Folder

- `Chair Website.html`: the website (built from `chairs/`)
- `index.html`: opens the website at the online link; `.nojekyll` makes GitHub show the files as they are
- `website/`: `build.js` and `template.html`, which make the website
- `index.md`: list of all chair files
- `template.md`: the layout every chair file follows
- `chairs/`: the chair files

## Online

- Website: https://aicaespino01.github.io/chair-library/ (updates about a minute after each upload)
- Files: https://github.com/aicaespino01/chair-library (public: only shop and maker information, no personal or clinic data)
