# EPSM Studies

<!-- EPSM introduction: Pocket CAD -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/welcome/epsm_studies-dark.png">
  <img src="docs/assets/welcome/epsm_studies.png" width="160" height="160" alt="EPSM Studies — A study report with one highlighted result bar; experiment documentation and evidence.">
</picture>

Turn a research question into a study you can revisit. EPSM Studies helps you
author portable protocols, retain execution results and compare energy outputs.
Reusable study and reporting tools sit alongside the research evidence and
historical archives.

**[Explore the EPSM platform →](https://github.com/SB-Chalmers/epsm/blob/main/docs/platform.md)**
<!-- /EPSM introduction -->

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)](https://github.com/SB-Chalmers/epsm_studies/actions/workflows/ci.yml) [![Releases](https://img.shields.io/badge/releases-GitHub-181717?logo=github&logoColor=white)](https://github.com/SB-Chalmers/epsm_studies/releases) [![Issues](https://img.shields.io/badge/issues-GitHub-181717?logo=github&logoColor=white)](https://github.com/SB-Chalmers/epsm_studies/issues)

## Getting started

Requires Python 3.11+ and Git.

```sh
git clone https://github.com/SB-Chalmers/epsm_studies.git
cd epsm_studies
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

```python
from epsm_studies import PaperStudy

study = PaperStudy(
    name="renovation-alternatives",
    question="Which renovation choices improve energy and climate impact?",
)
study.save("outputs/renovation-alternatives/protocol.json")
```

Protocol records need no simulation engines or database. For study execution,
install compatible Workflows and EPSM packages through the `workflows` extra;
the [study platform guide](docs/study-platform.md) covers setup and result archives.

## Documentation

- [Detailed guide](docs/guide.md)
- [Study authoring and result archives](docs/study-platform.md)
- [Examples](examples/README.md)
- [Engine comparison fixtures](examples/engine_comparison/README.md)
- [Archive index](archive/README.md)

## License

[MIT](LICENSE).

## People and support

Developed at Chalmers University of Technology as part of the EPSM research platform.

**Funding**: Swedish Energy Agency (Project ID: P2024-04053)

**Partners**:

- Lindholmen Science Park AB
- Sinom AB
- Stiftelsen Chalmers Industriteknik

**Team**:

- **Lead Developer**: Sanjay Somanath
- **Principal Investigator**: Alexander Hollberg
- **Contributors**: Yinan Yu, Dag Wästberg

<p align="center">
  <img src="docs/assets/welcome/logos.png" width="100%" alt="Chalmers University of Technology, Chalmers Industriteknik, Sinom, Lindholmen Science Park and Swedish Energy Agency logos">
</p>
