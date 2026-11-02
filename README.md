# LLM4VKG Matcher Improvement

This project explores improvements to matching relational database schemas with ontology concepts using LLM4VKG.

## Data acquisition

Clone this repository to obtain the local CMT scenario in `dataset/`; no separate download is needed for EDA.

| File | Description |
| --- | --- |
| `dataset/dump.sql` | PostgreSQL dump (`cmt_structured` schema). |
| `dataset/ontology.ttl` | CMT ontology in RDF/Turtle. |
| `dataset/ontology.owl` | CMT ontology in OWL/XML. |

The three files match the [LLM4VKG `cmt_structured` scenario](https://github.com/HomuraT/LLM4VKG/tree/f107bd9b737aa37c69ad55c4b9f3435137122b32/datasets/rodi/cmt_structured). Additional scenarios are available in the [LLM4VKG datasets](https://github.com/HomuraT/LLM4VKG/tree/main/datasets/rodi).

## Exploratory data analysis (EDA)

Run all cells in **[docs/EDA.ipynb](docs/EDA.ipynb)** from the project directory or `docs/`, using Python with `pandas`, `matplotlib`, `rdflib` and `IPython`. The notebook reads the dump without executing SQL. It covers:

- schema completeness, missing values and primary/foreign key integrity;
- ontology classes and properties, graph sizes and relation types;
- preprocessing, resource estimates and conclusions.

**Findings:** 32 tables, 5,386 rows, 20 empty tables and 19.46% NULL values. Full EDA can run on a CPU; missing values and empty tables need interpretation before preprocessing.

The analysis covers only the bundled scenario. Its diagnostic record graph is not a materialized VKG. Reproducing the paper's evaluation additionally requires matching query pairs, scenario configuration and mappings.

## License and attribution

- Project code and documentation: [MIT](LICENSE).
- CMT dataset (`cmt_structured`): [MIT, as distributed by RODI](https://github.com/chrpin/rodi/blob/64ae74ba2b9d21e98733e0ddfbd3a1ffae73706a/LICENSE). Copyright (c) 2015 Christoph Pinkel, fluid Operations AG. Redistribution requires preserving the original copyright and license notice.

## References

- Xiao et al. (2025). [*LLM4VKG: Leveraging Large Language Models for Virtual Knowledge Graph Construction*](https://doi.org/10.24963/ijcai.2025/525). [Authors' implementation](https://github.com/HomuraT/LLM4VKG).
- [RODI: Relational-to-Ontology Mapping Quality Benchmark](https://github.com/chrpin/rodi).
