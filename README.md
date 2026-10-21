# epsm_studies

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)](https://github.com/SB-Chalmers/epsm_studies/actions/workflows/ci.yml) [![Releases](https://img.shields.io/badge/releases-GitHub-181717?logo=github&logoColor=white)](https://github.com/SB-Chalmers/epsm_studies/releases) [![Issues](https://img.shields.io/badge/issues-GitHub-181717?logo=github&logoColor=white)](https://github.com/SB-Chalmers/epsm_studies/issues)

Author portable EPSM studies, record research protocols, retain execution results
and compare energy outputs. Studies keeps research evidence and historical
archives alongside reusable study and reporting APIs.

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
