# AstraDraw branding

Original vector artwork for the AstraDraw repository: a snowy paper-and-pencil wordmark, navigation chips, handwritten Chinese introduction, origin-story note, matching section headings, and a blue wave divider.

The palette draws on the publicly visible colors of [jerrysnow.me](https://jerrysnow.me/): ink blue, icy blue, with cream and coral accents. No website images or third-party icons are copied.

All visible lettering is converted to SVG paths, so the appearance does not depend on fonts installed on the reader’s device.

- **Comic Neue Bold** supplies Latin lettering. It is by Craig Rozynski and Hrant Papazian, distributed under the SIL Open Font License 1.1. The source font and license are in `fonts/`, from [Google Fonts](https://github.com/google/fonts/tree/main/ofl/comicneue).
- **LXGW WenKai Medium** supplies the Chinese introduction and section headings. Source: [LXGW WenKai](https://github.com/lxgw/LxgwWenKai/tree/50f4b182415a8c33d9a456df220b66a284e2509b/fonts/TTF), under SIL OFL 1.1 (`fonts/LXGW-OFL.txt`). The included derivative is reduced to the used characters and renamed **AstraDraw WenKai Subset**.
- **ZCOOL KuaiLe** was used in the earlier cream-and-tape note; the current icy-blue note uses WenKai to match the page. The old font subset is retained for that earlier variant. Source: [Google Fonts](https://github.com/google/fonts/tree/main/ofl/zcoolkuaile), under SIL OFL 1.1 (`fonts/ZCOOL-OFL.txt`). The included derivative is reduced to the used characters and renamed **AstraDraw KuaiLe Subset**.

The subsets are only for rebuilding this artwork, not general-purpose Chinese fonts. Their original copyright and license records are retained. To add new text, provide the original upstream fonts with `build_brand.py --cjk-source FONT --quote-source FONT`; this refreshes the used character sets and then rebuilds the SVGs.

The SVGs contain no scripts, external resources, embedded bitmap images, or `foreignObject` content. English navigation labels keep the outlined assets compact; README links supply the surrounding Chinese context.

`build_brand.py` reproduces the artwork with Python and `fonttools`. It is an optional maintenance file; using the repository does not require running it.

## Homepage illustrations

`../workflow-kawaii.png` and `../closing-kawaii.png` were generated with OpenAI image generation on 2026-09-08 for this README. They are original raster illustrations, not editable vectors or scientific diagrams. The original PNG files are retained without re-encoding.

- **Workflow:** six illustrated stations, Read → Collect → Explore → Check → Edit → Refine, with a return arrow from Refine to Edit. A reading robot, reference binder, blue-scarf mouse, reviewing owl, editable canvas and selection magnifier carry the story. White background; navy outlines, ice blue, cream and coral accents.
- **Closing:** a robot and blue-scarf mouse sit on a blue pencil, holding a completed diagram; a paper airplane leads toward the next drawing. No text, with the same colors and hand-drawn sticker treatment.

These illustrations follow the approved public Kawaii collection's visual direction. Private reference libraries and source PPT screenshots are not included. Generated artwork does not establish exclusive rights or grant a license for unrelated assets in this repository.
