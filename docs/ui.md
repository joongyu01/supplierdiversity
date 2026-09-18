# K-Petro 정부권장정책 구매지원 UI

`site/portal.css` is the shared presentation layer for the directory, offers, contract catalog, and notices. The existing page scripts and generated dataset schemas remain in place. The header uses the K-Petro logo from `joongyu01/good-station-board/client/public/logo.png`; the CI green, light background, soft cards, and navigation treatment follow that project.

- Keep business-list collection and generated files under `site/data/` separate from UI edits.
- Offers support category buttons, classification search, supplier filters, removable filter chips, and URL restoration of selected filters.
- The home page is the offer finder; navigation then leads to contract prices, businesses.html, and certification notices. Internal business-number links explicitly target businesses.html.
- Catalog buttons display all distinct collected item names, with a local name filter and exact-name results across every matching data chunk.
- Offer data arrives in a small bootstrap and hash-named batches. Registry search uses each completed index group. Partial results must never claim that no supplier exists.
- Current-status dialogs hand off to official lookup services and clearly state that they do not automatically validate certifications.
- Internal ERP source files, derived records, and purchase amounts/counts/shares/rankings must never enter public assets. Only general category names may be reused. Displayed supplier/product coverage is from the public datasets.
- Do not remove HTML entry points, requirements files, or collection configuration when updating collectors. These were restored unchanged from commit `9c42607` where applicable after their removal in `5331f07` broke deployment. HTML was then restyled.

Validation: desktop and mobile flows for category selection, search, URL restoration, clearing individual filters, real business details, catalog selection, notice search, asset loading and console errors. Screenshots and browser check scripts stay under ignored `private/ui/`.
