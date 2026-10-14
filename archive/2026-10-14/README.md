# epsm_studies

Named EPSM research protocols, paper-specific implementations and historical study
archives. Reusable designs, optimisation and execution belong to `epsm_workflows`.

```python
from epsm_studies import PaperStudy

study = PaperStudy(
    name="renovation-alternatives",
    question="Which physical renovation sequences improve energy and carbon?",
    configuration={"max_depth": 2, "assessment_period_years": 50},
    sources={"catalogue": "reviewed-release-id"},
    plan_ids=("prepared-workflow-plan-id",),
)
study.save("outputs/renovation-alternatives/protocol.json")
```

These illustrative values are explicit protocol choices, not scientific defaults.
Changing the question or assumptions creates another protocol identity.
`configuration` and `sources` return independent copies for inspection; editing
those copies does not change the protocol or its identity. Construct another
`PaperStudy` to record changed assumptions.

## Historical Workflows transfer

`archive/workflows_2026_10_14/` preserves tracked source, tests, configurations,
examples and documentation from Workflows commit
`1e49fa212f26ed80e6c2dce173cf5caa87a8b5b2`. `ARCHIVE.json` lists SHA256 checksums.
Simulation outputs and external raw datasets are not copied.

`src/epsm_studies/legacy_workflows/` contains the corresponding importable historical
implementations. Old Workflows study imports delegate here for compatibility. Install
the legacy extra and original prerequisites to use them. New protocols use the reusable
Workflows API; the archive is not a second evolving architecture.

The transfer includes national stock exploration, MF revisions, cohort transfer,
archetype diagnosis, the surrogate campaign and weather-imputation study sources.
Old assumptions and source hashes remain inspectable. Running them against newer
packages does not automatically reproduce or validate a previous scientific result.

## Data validation transfer

`imports/epsm_data_harmonisation/` retains historical LoD2 fitting/validation,
frozen-baseline and cohort-profile evidence transferred from Data. `TRANSFER.json`
records original relative paths and verified checksums. Current construction defaults
and original source evidence remain owned by Data.
