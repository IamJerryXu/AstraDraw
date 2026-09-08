# AstraDraw branding

Original vector artwork for the AstraDraw repository: a snowy paper-and-pencil wordmark, five navigation chips, and a small section divider.

The palette draws on the publicly visible colors of [jerrysnow.me](https://jerrysnow.me/): ink blue, icy blue, with cream and coral accents. No website images or third-party icons are copied.

All visible lettering is converted to SVG paths from **Comic Neue Bold**, so the appearance does not depend on fonts installed on the reader’s device. Comic Neue is by Craig Rozynski and Hrant Papazian, distributed under the SIL Open Font License 1.1. The source font and its original license are in `fonts/`, from [Google Fonts](https://github.com/google/fonts/tree/main/ofl/comicneue).

The SVGs contain no scripts, external resources, embedded bitmap images, or `foreignObject` content. English navigation labels keep the outlined assets compact; README links supply the surrounding Chinese context.

`build_brand.py` reproduces the artwork with Python and `fonttools`. It is an optional maintenance file; using the repository does not require running it.

## Homepage illustrations

`../workflow-kawaii.png` and `../closing-kawaii.png` were generated with OpenAI image generation on 2026-09-08 for this README. They are original raster illustrations, not editable vectors or scientific diagrams. The original PNG files are retained without re-encoding.

- **Workflow:** six illustrated stations, Read → Collect → Explore → Check → Edit → Refine, with a return arrow from Refine to Edit. A reading robot, reference binder, blue-scarf mouse, reviewing owl, editable canvas and selection magnifier carry the story. White background; navy outlines, ice blue, cream and coral accents.
- **Closing:** a robot and blue-scarf mouse sit on a blue pencil, holding a completed diagram; a paper airplane leads toward the next drawing. No text, with the same colors and hand-drawn sticker treatment.

These illustrations follow the approved public Kawaii collection's visual direction. Private reference libraries and source PPT screenshots are not included. Generated artwork does not establish exclusive rights or grant a license for unrelated assets in this repository.
