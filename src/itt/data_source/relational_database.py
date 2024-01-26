__author__ = "Julián Arenas-Guerrero"
__credits__ = ["Julián Arenas-Guerrero"]

__license__ = "Apache-2.0"
__maintainer__ = "Julián Arenas-Guerrero"
__email__ = "arenas.guerrero.julian@outlook.com"


import logging
import pandas as pd
import polars as pl

from ..constants import *


# PostgresSQL data types: https://www.postgresql.org/docs/14/datatype.html
# Oracle data types: https://docs.oracle.com/cd/A58617_01/server.804/a58241/ch5.htm
# MySQL data types: https://dev.mysql.com/doc/refman/8.0/en/data-types.html
SQL_RDF_DATATYPE = {
    'BINARY': XSD_HEX_BINARY,
    'VARBINARY': XSD_HEX_BINARY,
    'BLOB': XSD_HEX_BINARY,
    'BFILE': XSD_HEX_BINARY,
    'RAW': XSD_HEX_BINARY,
    'LONG RAW': XSD_HEX_BINARY,

    'INTEGER': XSD_INTEGER,
    'INT': XSD_INTEGER,
    'SMALLINT': XSD_INTEGER,
    'INT8': XSD_INTEGER,
    'INT4': XSD_INTEGER,
    'BIGINT': XSD_INTEGER,
    'BIGSERIAL': XSD_INTEGER,
    'SMALLSERIAL': XSD_INTEGER,
    'INT2': XSD_INTEGER,
    'SERIAL2': XSD_INTEGER,
    'SERIAL4': XSD_INTEGER,
    'SERIAL8': XSD_INTEGER,

    'DECIMAL': XSD_DECIMAL,
    'NUMERIC': XSD_DECIMAL,

    'FLOAT': XSD_DOUBLE,
    'FLOAT8': XSD_DOUBLE,
    'REAL': XSD_DOUBLE,
    'DOUBLE': XSD_DOUBLE,
    'DOUBLE PRECISION': XSD_DOUBLE,
    'NUMBER': XSD_DOUBLE,

    'BOOL': XSD_BOOLEAN,
    'TINYINT': XSD_BOOLEAN,
    'BOOLEAN': XSD_BOOLEAN,

    'DATE': XSD_DATE,
    'TIME': XSD_TIME,
    'DATETIME': XSD_DATETIME,
    'TIMESTAMP': XSD_DATETIME
}


def _replace_query_enclosing_characters(sql_query, db_dialect):
    dialect_sql_query = ''

    if db_dialect in [MYSQL, MARIADB]:
        dialect_sql_query = sql_query   # the query already uses backticks as enclosed characters
    elif db_dialect == MSSQL:
        # replace backticks with square brackets
        square_brackets = ['[', ']']
        num_enclosing_char = 0
        for char in sql_query:
            if char == '`':
                dialect_sql_query = dialect_sql_query + square_brackets[num_enclosing_char % 2]
                num_enclosing_char += 1
            else:
                dialect_sql_query = dialect_sql_query + char
    elif db_dialect == DATABRICKS:
        # remove all backticks
        dialect_sql_query = sql_query.replace('`', '')
    else:
        # replace backticks with double quotes
        dialect_sql_query = sql_query.replace('`', '"')

    return dialect_sql_query


def _relational_db_connection(config, source_name):
    connect_args = eval(config.get_connect_args(source_name)) if config.has_connect_args(source_name) else {}

    db_connection = create_engine(config.get_database_url(source_name), connect_args=connect_args, poolclass=NullPool)
    db_dialect = db_connection.dialect.name.upper()

    return db_connection, db_dialect


def _build_sql_query(rml_rule, references):
    """
    Build a query for MYSQL using backticks '`' as enclosing character. This character will later be replaced with the
    one corresponding one to the dialect that applies. It also takes care of schema-qualified names.
    """

    if rml_rule['logical_source_type'] == RML_QUERY:
        query = rml_rule['logical_source_value']
    elif rml_rule['logical_source_type'] == RML_TABLE_NAME and len(references) > 0:
        query = 'SELECT ' # + 'DISTINCT ' # TODO: is this more efficient?
        # replacements of `.` to deal with schema-qualified names (see issue #89)
        for reference in references:
            query = f"{query}`{reference.replace('.', '`.`')}`, "
        query = f"{query[:-2]} FROM `{rml_rule['logical_source_value'].replace('.', '`.`')}` WHERE "
        for reference in references:
            query = f"{query}`{reference.replace('.', '`.`')}` IS NOT NULL AND "
        query = query[:-5]
    else:
        query = None

    return query


def get_sql_data(config, rml_rule, references):
    db_url = config.get_database_url(rml_rule['source_name'])
    sql_query = _build_sql_query(rml_rule, references)

    if db_url.startswith('postgresql'):
        sql_query = sql_query.replace('`', '"')

    return pl.read_database(sql_query, db_url, engine='connectorx')


def setup_oracle(config):
    if config.is_oracle_client_config_dir_provided() or config.is_oracle_client_lib_dir_provided():
        import cx_Oracle

    if config.is_oracle_client_config_dir_provided() and config. is_oracle_client_lib_dir_provided():
        cx_Oracle.init_oracle_client(lib_dir=config.get_oracle_client_lib_dir(),
                                     config_dir=config.get_oracle_client_config_dir())
    elif config.is_oracle_client_config_dir_provided():
        cx_Oracle.init_oracle_client(config_dir=config.get_oracle_client_config_dir())
    elif config.is_oracle_client_lib_dir_provided():
        cx_Oracle.init_oracle_client(lib_dir=config.get_oracle_client_lib_dir())
