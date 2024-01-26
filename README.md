# Intermediate Triple Table

**ITT** is a virtual knowledge graph system implementing the _Intermediate Triple Table_ architecture. It allows to access heterogeneous data as a knowledge graph using the **[R2RML](https://www.w3.org/TR/r2rml/)** and **[RML](https://w3id.org/rml/core/spec)** mapping languages.

## Installation

To install `itt` execute the following:

```bash
pip install git+https://github.com/arenas-guerrero-julian/itt.git
```

## Execution

You can run **ITT** via command line:

```bash
python3 -m itt path/to/config.ini path/to/query.rq
```

The query result set is written to `itt_result.csv`.

The configuration file is similar to that of [Morph-KGC](https://github.com/morph-kgc/morph-kgc):

```ini
[DataSource1]
mappings: /path/to/mapping/mapping_file.rml.ttl
db_url: mysql://username:password@server:port/database
```

**ITT** uses [ConnectorX](https://github.com/sfu-db/connector-x) to access relational databases and the connection URLs must be formatted according to this engine. For Postgres the format is _postgres://username:password@server:port/database_ and for MySQL the format is _mysql://username:password@server:port/database_. See the details [here](https://sfu-db.github.io/connector-x/databases.html). For Mongo the connection URL format is _mongodb://localhost:27017/database_.

## License :unlock:

**ITT** is available under the **[Apache License 2.0](https://github.com/arenas-guerrero-julian/ITT/blob/main/LICENSE)**.

## Author & Contact :mailbox_with_mail:

- **[Julián Arenas-Guerrero](https://github.com/arenas-guerrero-julian/) - [julian.arenas.guerrero@upm.es](mailto:julian.arenas.guerrero@upm.es)**

*[Universidad Politécnica de Madrid](https://www.upm.es/internacional)*.
