# Intermediate Triple Table

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.11096736.svg)](https://doi.org/10.5281/zenodo.11096736)

**ITT** is a virtual knowledge graph system implementing the _Intermediate Triple Table_ architecture. It allows to access heterogeneous data as a knowledge graph using the **[R2RML](https://www.w3.org/TR/r2rml/)** and **[RML](https://w3id.org/rml/core/spec)** mapping languages.

## Installation ⚙️

To install **ITT** execute the following:

```bash
pip install git+https://github.com/arenas-guerrero-julian/itt.git
```

## Execution 🚀

You can run **ITT** via command line:

```bash
python3 -m itt path/to/config.ini path/to/query.rq
```

The query result set is written to `itt_result.csv`.

The configuration file is similar to that of [Morph-KGC](https://github.com/morph-kgc/morph-kgc):

```ini
[DataSource1]
mappings: /path/to/mapping/mapping_file.rml.ttl
db_url: mysql://username:password@host:port/database
```

**ITT** uses [ConnectorX](https://github.com/sfu-db/connector-x) to access relational databases and the connection URLs must be formatted according to this engine. For Postgres the format is _postgresql://username:password@host:port/database_ and for MySQL the format is _mysql://username:password@host:port/database_. See the details [here](https://sfu-db.github.io/connector-x/databases.html).

For MongoDB the connection URL format is _mongodb://localhost:27017/database_. Example config file for MongoDB:

```ini
[DataSource1]
mappings: /path/to/mapping/mapping_file.rml.ttl
mongo_url: mongodb://localhost:27017/database
```

## License :unlock:

**ITT** is available under the **[Apache License 2.0](https://github.com/arenas-guerrero-julian/ITT/blob/main/LICENSE)**.

## Author & Contact :mailbox_with_mail:

- **[Julián Arenas-Guerrero](https://github.com/arenas-guerrero-julian/) - [julian.arenas.guerrero@upm.es](mailto:julian.arenas.guerrero@upm.es)**

*[Universidad Politécnica de Madrid](https://www.upm.es/internacional)*.

## Citing :speech_balloon:

If you used ITT in your work, please cite the **[Knowledge-Based Systems paper](https://doi.org/10.1016/j.knosys.2025.113179)**:

```bib
@article{arenas2025itt,
  title = {Intermediate triple table: A general architecture for virtual knowledge graphs},
  author = {Julián Arenas-Guerrero and Oscar Corcho and María S. Pérez},
  journal = {Knowledge-Based Systems},
  publisher = {Elsevier},
  pages = {113179},
  year = {2025},
  issn = {0950-7051},
  doi = {10.1016/j.knosys.2025.113179},
}
```
