__author__ = "Julián Arenas-Guerrero"
__credits__ = ["Julián Arenas-Guerrero"]

__license__ = "Apache-2.0"
__maintainer__ = "Julián Arenas-Guerrero"
__email__ = "arenas.guerrero.julian@outlook.com"


import time
import duckdb

import multiprocessing as mp
import polars as pl

from itertools import repeat

from .args_parser import load_config_from_command_line
from .materializer import _materialize_mapping_group_to_df
from .data_source.relational_database import setup_oracle
from .mapping.mapping_simplifier import simplify_mapping
from .mapping.mapping_parser import retrieve_mappings
from .constants import RML_TRIPLES_MAP_CLASS
from .utils import prepare_output_files
from .sparql_translator import sparql_to_sql, get_sparql_parser


if __name__ == "__main__":
    #mp.set_start_method('spawn')

    config, sparql_query = load_config_from_command_line()

    setup_oracle(config)

    rml_df, fnml_df = retrieve_mappings(config)

    prepare_output_files(config, rml_df)

    # keep only asserted mapping rules
    asserted_mapping_df = rml_df.loc[rml_df['triples_map_type'] == RML_TRIPLES_MAP_CLASS]

    sparql_parser = get_sparql_parser()

    start_time = time.time()
    asserted_mapping_df = simplify_mapping(asserted_mapping_df, sparql_query, sparql_parser)

    # materialize
    mapping_groups = [group for _, group in asserted_mapping_df.groupby(by='mapping_partition')]

    if config.is_multiprocessing_enabled():
        pool = mp.Pool(config.get_number_of_processes())
        map_group_dfs = pool.starmap(_materialize_mapping_group_to_df, zip(mapping_groups, repeat(rml_df), repeat(fnml_df), repeat(config)))
        pool.close()
        pool.join()
    else:
        map_group_dfs = []
        for mapping_group in mapping_groups:
            map_group_dfs.append(_materialize_mapping_group_to_df(mapping_group, rml_df, fnml_df, config))

    if map_group_dfs:
        triple_table_df = pl.concat(map_group_dfs)

        #print(sparql_to_sql(sparql_query))
        #print(len(duckdb.sql(sparql_to_sql(sparql_query)).df()))
        #duckdb.sql(sparql_to_sql(sparql_query)).show()
        res_df = duckdb.sql(sparql_to_sql(sparql_query, sparql_parser)).pl()
        res_df.write_csv('itt_result.csv', separator='\t')
        print(res_df)

        print(int((time.time()-start_time)*1000))
    else:
        print("Empty query result set.")
