# Chair Library

One file per office chair model, with facts taken from the maker (sizes, adjustments, materials, warranty), every shop listing seen, reviews (labelled independent, seller or paid ad), pros and cons, and what is still unknown.

Made to be reused: for chair comparisons, and later for a website. The block at the top of each file (between the `---` lines) holds the key facts in a fixed form that a website can read.

## How to use

- New chair: send Claude the link and say "chair-info" (for example `/chair-info https://officebusters.ph/products/...`).
- All Office Busters swivel chairs: "chair-info all Office Busters chairs". It works in batches of 5.
- Compare: "compare chairs/okamura-sulato-c331zr.md with chairs/xpanse-f7.md".

## Folder

- `index.md`: list of all chair files
- `template.md`: the layout every chair file follows
- `chairs/`: the chair files

## Online

Private copy on GitHub (once the repository is created).
