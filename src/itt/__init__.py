__author__ = "Julián Arenas-Guerrero"
__credits__ = ["Julián Arenas-Guerrero"]
__copyright__ = "Copyright © 2020 Julián Arenas-Guerrero"

__license__ = "Apache-2.0"
__maintainer__ = "Julián Arenas-Guerrero"
__email__ = "arenas.guerrero.julian@outlook.com"


import sys
import logging
import multiprocessing as mp
import polars as pl

from rdflib import Graph
from pyoxigraph import Store
from io import BytesIO
from itertools import repeat

from .args_parser import load_config_from_command_line
from .mapping.mapping_parser import retrieve_mappings
from .data_source.relational_database import setup_oracle
from .materializer import _materialize_mapping_group_to_df
from .args_parser import load_config_from_argument
from .constants import RML_TRIPLES_MAP_CLASS


def materialize_set(config, python_source=None):
    config = load_config_from_argument(config)

    # parallelization when running as a library is only enabled for Linux see #94
    if 'linux' not in sys.platform:
        logging.info(
            f'Parallelization is not supported for {sys.platform} when running as a library. '
            f'If you need to speed up your data integration pipeline, please run through the command line.')
        config.set_number_of_processes('1')

    setup_oracle(config)

    rml_df, fnml_df = retrieve_mappings(config)

    # keep only asserted mapping rules
    asserted_mapping_df = rml_df.loc[rml_df['triples_map_type'] == RML_TRIPLES_MAP_CLASS]
    mapping_groups = [group for _, group in asserted_mapping_df.groupby(by='mapping_partition')]

    """
    if config.is_multiprocessing_enabled():
        logging.debug(f'Parallelizing with {config.get_number_of_processes()} cores.')

        pool = mp.Pool(config.get_number_of_processes())
        triples = set().union(
            *pool.starmap(_materialize_mapping_group_to_df, zip(mapping_groups, repeat(rml_df), repeat(fnml_df), repeat(config), repeat(python_source))))
        pool.close()
        pool.join()
    else:
        triples = set()
        for mapping_group in mapping_groups:
            triples.update(_materialize_mapping_group_to_df(mapping_group, rml_df, fnml_df, config, python_source))
    """

    if config.is_multiprocessing_enabled():
        pool = mp.Pool(config.get_number_of_processes())
        map_group_dfs = pool.starmap(_materialize_mapping_group_to_df,
                                     zip(mapping_groups, repeat(rml_df), repeat(fnml_df), repeat(config)))
        pool.close()
        pool.join()
    else:
        map_group_dfs = []
        for mapping_group in mapping_groups:
            map_group_dfs.append(_materialize_mapping_group_to_df(mapping_group, rml_df, fnml_df, config))

    triple_table_df = pl.concat(map_group_dfs)
    triple_table_df = triple_table_df.with_columns(pl.concat_str([pl.col("s"), pl.col("p"), pl.col("o"), ], separator=" ",).alias("triple"),)

    triples = set(triple_table_df.get_column('triple').to_list())

    return triples


def materialize(config, python_source=None):
    triples = materialize_set(config, python_source)

    graph = Graph()
    rdf_ntriples = '.\n'.join(triples)
    if rdf_ntriples:
        # only add final dot if at least one triple was generated
        rdf_ntriples += '.'
        graph.parse(data=rdf_ntriples, format='nquads')

    return graph


def materialize_oxigraph(config, python_source=None):
    triples = materialize_set(config, python_source)

    graph = Store()
    rdf_ntriples = '.\n'.join(triples)
    if rdf_ntriples:
        # only add final dot if at least one triple was generated
        rdf_ntriples += '.'
        graph.bulk_load(BytesIO(rdf_ntriples.encode()), 'application/n-quads')

    return graph
