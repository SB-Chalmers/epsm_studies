# Historical study archives

On 14 October 2026, the maintainer archived the existing named study and legacy
workflow implementations pending later decisions. Generic protocol records and
workflow infrastructure remain active. Historical files are retained for
inspection; executing, repairing or reproducing the old studies is not required.
Commands and support statements inside preserved files describe their original
state and are not current instructions or compatibility promises.

| Collection | Contents and status |
| --- | --- |
| [2026-10-14](2026-10-14/) | Formerly importable `epsm_studies.legacy_workflows` source and resources; original root README and package metadata are copied for context. `ARCHIVE.json` records the source commit and SHA256 checksums. |
| [workflows_2026_10_14](workflows_2026_10_14/) | Earlier preservation of Workflows source, tests, campaign configurations, examples and documentation. This collection and its original manifest remain byte-identical. |
| [Data harmonisation evidence](../imports/epsm_data_harmonisation/) | Historical fitting, validation and cohort evidence. It remains at its existing path because Data provenance refers to these records. This is archived evidence, not an active study package. Its contents and `TRANSFER.json` remain byte-identical. |

All collections are excluded from package builds and normal pytest discovery.
The active package retains only the generic `PaperStudy` protocol abstraction.
The archival operation does not claim scientific validation or successful
reproduction of the preserved studies.
