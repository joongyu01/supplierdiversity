# K-Petro 정부권장정책 구매지원 UI

`site/portal.css` is the shared presentation layer for the directory, offers, contract catalog, and notices. The existing page scripts and generated dataset schemas remain in place. The header uses the K-Petro logo from `joongyu01/good-station-board/client/public/logo.png`; the CI green, light background, soft cards, and navigation treatment follow that project.

- Keep business-list collection and generated files under `site/data/` separate from UI edits.
- Offers support category buttons, classification search, supplier filters, removable filter chips, and URL restoration of selected filters.
- The home page is the offer finder; navigation then leads to contract prices, businesses.html, and certification notices. Internal business-number links explicitly target businesses.html.
- Catalog buttons include all distinct collected item names. The default view shows one responsive row with an expand/collapse button; searching reveals every matching name. Exact-name results span every matching data chunk.
- Offer data arrives in a small bootstrap and hash-named batches. Registry search uses each completed index group. Partial results must never claim that no supplier exists.
- Current-status dialogs hand off to official lookup services and clearly state that they do not automatically validate certifications.
- Internal ERP source files, derived records, and purchase amounts/counts/shares/rankings must never enter public assets. Only general category names may be reused. Displayed supplier/product coverage is from the public datasets.
- Do not remove HTML entry points, requirements files, or collection configuration when updating collectors. These were restored unchanged from commit `9c42607` where applicable after their removal in `5331f07` broke deployment. HTML was then restyled.

Validation: desktop and mobile flows for category selection, search, URL restoration, clearing individual filters, real business details, catalog selection, notice search, asset loading and console errors. Screenshots and browser check scripts stay under ignored `private/ui/`.

Brand asset: `site/assets/kpetro-logo-transparent.png` is the transparent header variant of the preserved original `kpetro-logo.png`, edited with the built-in image generation tool. Edit brief: remove the white background, preserve the original K-Petro symbol, Korean lettering, proportions, and gray/green colors; use PNG alpha with no white matte. The header uses normal compositing.

The offers category column and every page footer display “© 2026 Joongyu Shin. All rights reserved.” and “Developed by Joongyu Shin.” The credit sits below the category card, outside its scroll area.

Cache consistency: deployment runs `scripts/version_site_assets.py` before publishing. Every local CSS/JS reference in HTML receives a content-hash `v` parameter, so a new page cannot silently reuse an earlier stylesheet after layout changes. Run the same script after asset edits when preparing a local preview. The category card and credits share one sticky grid column; only the category list scrolls.
