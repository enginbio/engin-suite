# References

```{note}
Generated from `sources.yaml` by `scripts/evidence/render.py`. Do not edit
by hand — CI fails when this file drifts from the register (`D23`).
```

Every substantive claim in a public document should resolve to a row here.
Where the evidence *contradicts* or *supersedes* what a document said, the row
stays after the document is corrected — that record is the point of keeping a
register rather than a bibliography.

## Works cited

| id | work | year | type | stability |
|---|---|---|---|---|
| `2019-goldrick-indpensim` | [Modern day monitoring and control challenges outlined on an industrial-scale benchmark fermentation process](https://doi.org/10.1016/j.compchemeng.2019.05.037)<br/>Goldrick, S., et al. — *Computers & Chemical Engineering* | 2019 | paper | doi |
| `2025-sun-master-efp` | [Multi-scale trend decomposition mixture of experts and time series retrieval-augmented modeling for erythromycin fermentation process](https://doi.org/10.1016/j.neucom.2025.131701)<br/>Sun, Yifei, Yan, Xuefeng — *Neurocomputing 657* | 2025 | paper | doi |
| `2025-zenodo-erythromycin-efp` | [Erythromycin fermentation process dataset](https://doi.org/10.5281/zenodo.14619074)<br/>Yan, Xuefeng, Sun, Yifei — *Zenodo* | 2025 | dataset | doi |
| `2026-cf-xarray-units` | [Units — cf_xarray documentation](https://cf-xarray.readthedocs.io/en/latest/units.html)<br/>cf_xarray contributors — *cf-xarray.readthedocs.io* | 2026 | software | url |
| `2026-frictionless-detector` | [Detector — Frictionless Framework documentation](https://framework.frictionlessdata.io/docs/framework/detector.html)<br/>Frictionless Data — *framework.frictionlessdata.io* | 2026 | software | url |
| `2026-numfocus-fiscal-sponsorship` | [Overview: NumFOCUS Projects — fiscal sponsorship requirements](https://numfocus.org/information-fiscal-sponsorship)<br/>NumFOCUS — *numfocus.org* | 2026 | web | url |
| `2026-zenodo-cho-k1-cultivations` | [Dataset Based on Chinese Hamster Ovary (CHO) Cultivations including Turbidity, Permittivity, O2 and CO2 Measurements](https://doi.org/10.5281/zenodo.20829178)<br/>Uhlendorff, S., Fulek, R., Eimler, J., Pein-Hackelbusch, M., Frahm, B. — *Zenodo* | 2026 | dataset | doi |

## Claims

| document | claim | source | strength |
|---|---|---|---|
| `DECISIONS.md` | NumFOCUS fiscal sponsorship requires a leadership body of at least three people not sharing a common affiliation, an OSI licence, a Code of Conduct, and an active community of reasonable size (D25). | `2026-numfocus-fiscal-sponsorship` | supports |
| `docs/benchmarks.md` | IndPenSim is a simulation validated against industrial data, not measurements from a real plant — placing it at D12 tier 2, not tier 3. | `2019-goldrick-indpensim` | supports |
| `docs/benchmarks.md` | 406 industrial fed-batch production batches, hourly, with a product-potency target, licensed CC-BY-4.0. | `2025-zenodo-erythromycin-efp` | supports |
| `docs/methods/real-data-calibration.md` | `hx` is the dataset's target column (chemical potency) — taken from the authors' own run_EFP.py, which defaults --target to hx. | `2025-sun-master-efp` | supports |
| `docs/methods/real-data-calibration.md` | The dataset's authors report considerably better prediction than this baseline using an architecture built for the purpose. | `2025-sun-master-efp` | partially supports |
| `packages/engin-core/src/engin_core/convention.py` | cf_xarray's vocabulary is geoscience-specific and reports n/a across the board on bioprocess data, so the CF *mechanism* was adopted and the package was not. | `2026-cf-xarray-units` | supports |
| `packages/engin-core/src/engin_core/loaders.py` | frictionless `field_confidence` is a type-casting tolerance, not semantic confidence, and it maps nothing to a domain vocabulary — so it does not serve D11's ingest need. | `2026-frictionless-detector` | supports |

## Components

**4 of 12 audited.** `unaudited` is the honest
default, not an oversight — reducing it is the programme this register exists
to serve.

| component | package | stance | standard implementation | evidence |
|---|---|---|---|---|
| Gaussian-process titer forecast | `engin-core` | standard | scikit-learn GaussianProcessRegressor | — |
| Split-conformal calibration | `engin-core` | wrapped | MAPIE (cross-check) + sd-normalized multiplier | — |
| Data convention over xarray/pandas | `engin-core` | bespoke-justified | none exists | `2026-cf-xarray-units` |
| Ingest layer / schema inference | `engin-core` | bespoke-justified | none exists | `2026-frictionless-detector` |
| Techno-economic coupling | `engin-core` | **unaudited** | BioSTEAM (behind the [tea] extra) | — |
| Mechanistic fed-batch simulator | `engin-core` | **unaudited** | none claimed | — |
| Expected-improvement recommender | `engin-core` | **unaudited** | BoTorch / Ax / BayBE | — |
| Host-capability knowledge base and scoring | `engin-host` | **unaudited** | unknown | — |
| Route-as-graph embedding | `engin-pathway` | **unaudited** | PyTorch Geometric (M1 upgrade) | — |
| Protein fitness ridge head | `engin-protein` | **unaudited** | unknown | — |
| Monomer featurization | `engin-materials` | **unaudited** | RDKit | — |
| Graph embedding | `engin-graph` | **unaudited** | PyTorch Geometric | — |

## Known weaknesses in this register

These are cited by a public document but exist only as web pages, so the
evidence can change or vanish without notice. Each says why no durable
copy was used; `accessed` records when it was last read.

- **`2026-cf-xarray-units`** (accessed 2026-08-11) — Library documentation, as above. The evaluation that rejected cf_xarray was run against the library itself; this is the reference for what it claims.
- **`2026-frictionless-detector`** (accessed 2026-08-11) — Library documentation. The claim is about what this software does, and the documentation is where it says so; there is no paper to cite instead.
- **`2026-numfocus-fiscal-sponsorship`** (accessed 2026-08-11) — An organisation's own statement of its requirements. It exists only as a web page and can change without notice, which is exactly why `accessed` is recorded and D25 names re-checking as a trigger.
