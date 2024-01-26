__author__ = "Julián Arenas-Guerrero"
__credits__ = ["Julián Arenas-Guerrero"]

__license__ = "Apache-2.0"
__maintainer__ = "Julián Arenas-Guerrero"
__email__ = "arenas.guerrero.julian@outlook.com"


from falcon.uri import encode_value

from .utils import *
from .constants import *
from .data_source.relational_database import get_sql_data
from .data_source.mongo_database import get_mongo_data
from .data_source.data_file import get_file_data
from .data_source.python_data import get_ram_data
from .fnml.fnml_executer import execute_fnml


def _add_references_in_join_condition(rml_rule, references, parent_references):
    references_join, parent_references_join = get_references_in_join_condition(rml_rule, 'object_join_conditions')

    references.update(set(references_join))
    parent_references.update(set(parent_references_join))

    return references, parent_references


def _preprocess_data(data, rml_rule, references, config):
    # deal with ORACLE
    if rml_rule['source_type'] == RDB:
        if config.get_database_url(rml_rule['source_name']).lower().startswith(ORACLE.lower()):
            data = normalize_oracle_identifier_casing(data, references)

    # data to str
    l = []
    for column_name in data.columns:
        l.append(pl.col(column_name).cast(pl.Utf8))
    data = data.with_columns(l)

    data = remove_null_values_from_dataframe(data, config, references)

    # remove duplicates
    data = data.unique()

    return data


def _get_data(config, rml_rule, references, python_source=None):

    if rml_rule['source_type'] == RDB:
        data = get_sql_data(config, rml_rule, references)
    elif rml_rule['source_type'] == MONGO:
        data = get_mongo_data(config, rml_rule, references)
    elif rml_rule['source_type'] in FILE_SOURCE_TYPES:
        data = get_file_data(rml_rule, references)
    elif rml_rule['source_type'] in IN_MEMORY_TYPES:
        data = get_ram_data(rml_rule, references, python_source)

    data = _preprocess_data(data, rml_rule, references, config)

    return data


def _get_references_in_rml_rule(rml_rule, rml_df, fnml_df, only_subject_map=False):
    references = []
    if rml_rule['subject_map_type'] == RML_TEMPLATE:
        references.extend(get_references_in_template(rml_rule['subject_map_value']))
    elif rml_rule['subject_map_type'] == RML_REFERENCE:
        references.append(rml_rule['subject_map_value'])

    if not only_subject_map:
        if rml_rule['predicate_map_type'] == RML_TEMPLATE:
            references.extend(get_references_in_template(rml_rule['predicate_map_value']))
        elif rml_rule['predicate_map_type'] == RML_REFERENCE:
            references.append(rml_rule['predicate_map_value'])
        if rml_rule['object_map_type'] == RML_TEMPLATE:
            references.extend(get_references_in_template(rml_rule['object_map_value']))
        elif rml_rule['object_map_type'] == RML_REFERENCE:
            references.append(rml_rule['object_map_value'])
        if rml_rule['graph_map_type'] == RML_TEMPLATE:
            references.extend(get_references_in_template(rml_rule['graph_map_value']))
        elif rml_rule['graph_map_type'] == RML_REFERENCE:
            references.append(rml_rule['graph_map_value'])

    if rml_rule['subject_map_type'] == RML_QUOTED_TRIPLES_MAP and pd.isna(rml_rule['subject_join_conditions']):
        parent_rml_rule = get_rml_rule(rml_df, rml_rule['subject_map_value'])
        references.extend(_get_references_in_rml_rule(parent_rml_rule, rml_df, fnml_df))
    if rml_rule['object_map_type'] == RML_QUOTED_TRIPLES_MAP and pd.isna(rml_rule['object_join_conditions']):
        parent_rml_rule = get_rml_rule(rml_df, rml_rule['object_map_value'])
        references.extend(_get_references_in_rml_rule(parent_rml_rule, rml_df, fnml_df))

    references_subject_join, parent_references_subject_join = get_references_in_join_condition(rml_rule, 'subject_join_conditions')
    references.extend(references_subject_join)
    references_object_join, parent_references_object_join = get_references_in_join_condition(rml_rule, 'object_join_conditions')
    references.extend(references_object_join)

    # extract FNML references
    if len(fnml_df):
        for position in ['subject', 'predicate', 'object', 'graph']:
            if rml_rule[f'{position}_map_type'] == RML_EXECUTION:
                references.extend(get_references_in_fnml_execution(fnml_df, rml_rule[f'{position}_map_value']))

    return references


def _materialize_template(results_df, template, config, position, columns_alias='', termtype=RML_IRI, language_tag='',
                          datatype=''):
    references = get_references_in_template(template)

    # Curly braces that do not enclose column names MUST be escaped by a backslash character (“\”).
    # This also applies to curly braces within column names.
    template = template.replace('\\{', '{').replace('\\}', '}')

    if termtype.strip() == RML_IRI:
        results_df = results_df.with_columns(pl.lit('<').alias(position))
    elif termtype.strip() == RML_LITERAL:
        results_df = results_df.with_columns(pl.lit('"').alias(position))
    elif termtype.strip() == RML_BLANK_NODE:
        results_df = results_df.with_columns(pl.lit('_:').alias(position))

    for reference in references:
        if 'reference_results' in results_df.columns:
            results_df = results_df.drop('reference_results')

        results_df = results_df.with_columns(pl.col(columns_alias + reference).alias("reference_results"))

        try:
            for v in results_df.get_column('reference_results').sample(10, seed=0):
                float(v)
        except:
            if termtype.strip() == RML_IRI:
                results_df = results_df.with_columns(pl.col("reference_results").apply(lambda x: encode_value(x), skip_nulls=False).alias("reference_results"))
            elif termtype.strip() == RML_LITERAL:
                # TODO: this can be avoided for most cases (if '\\' in data_value)
                results_df = results_df.with_columns(pl.col("reference_results").str.replace('\n', '\\n').str.replace('\t', '\\t').str.replace('\b', '\\b').str.replace('\f', '\\f').str.replace('\r', '\\r').str.replace('"', '\\"').str.replace("'", "\\'"))

        splitted_template = template.split('{' + reference + '}')
        results_df = results_df.with_columns(pl.concat_str([pl.col(position)+splitted_template[0], pl.col('reference_results')]).alias(position))
        template = str('{' + reference + '}').join(splitted_template[1:])
    if template:
        # add what remains in the template after the last reference
        results_df = results_df.with_columns(pl.concat_str(pl.col(position) + template).alias(position))

    if termtype.strip() == RML_IRI:
        results_df = results_df.with_columns(pl.concat_str(pl.col(position) + '>').alias(position))
    elif termtype.strip() == RML_LITERAL:
        results_df = results_df.with_columns(pl.concat_str(pl.col(position) + '"').alias(position))
        if pd.notna(language_tag):
            results_df = results_df.with_columns(pl.concat_str(pl.col(position) + '@' + language_tag).alias(position))
        elif pd.notna(datatype):
            results_df = results_df.with_columns(pl.concat_str(pl.col(position) + '^^<' + datatype + '>').alias(position))

    return results_df


def _materialize_reference(results_df, reference, config, position, columns_alias='', termtype=RML_LITERAL, language_tag='', datatype=''):
    results_df = results_df.with_columns(pl.col(columns_alias + reference).alias("reference_results"))

    if termtype.strip() == RML_LITERAL:
        # Natural Mapping of SQL Values (https://www.w3.org/TR/r2rml/#natural-mapping)
        if datatype == XSD_BOOLEAN:
            results_df = results_df.with_columns(pl.col("reference_results").str.to_lowercase())
        elif datatype == XSD_DATETIME:
            results_df = results_df.with_columns(pl.col("reference_results").str.replace_all(' ', 'T'))
        # Make integers not end with .0
        elif datatype == XSD_INTEGER:
            results_df = results_df.with_columns(pl.col("reference_results").str.replace_all('.0', ''))

        try:
            for v in results_df.get_column('reference_results').sample(10, seed=0):
                float(v)
        except:
            results_df = results_df.with_columns(pl.col("reference_results").str.replace('\n', '\\n').str.replace('\t', '\\t').str.replace('\b', '\\b').str.replace('\f', '\\f').str.replace('\r', '\\r').str.replace('"', '\\"').str.replace("'", "\\'"))

        results_df = results_df.with_columns(pl.concat_str('"'+pl.col('reference_results')+'"').alias(position))
        if pd.notna(language_tag):
            results_df = results_df.with_columns(pl.concat_str(pl.col(position) + '@' + language_tag).alias(position))
        elif pd.notna(datatype):
            results_df = results_df.with_columns(pl.concat_str(pl.col(position) + '^^<' + datatype + '>').alias(position))
    elif termtype.strip() == RML_IRI:
        # it is assumed that the IRI values will be correct, and they are not percent encoded
        results_df = results_df.with_columns(pl.col("reference_results").apply(lambda x: x.strip(), skip_nulls=False).alias("reference_results"))
        results_df = results_df.with_columns(pl.concat_str('<' + pl.col('reference_results') + '>').alias(position))
    elif termtype.strip() == RML_BLANK_NODE:
        results_df = results_df.with_columns(pl.concat_str('_:' + pl.col('reference_results')).alias(position))

    return results_df


def _materialize_fnml_execution(results_df, fnml_execution, fnml_df, config, position, columns_alias='', termtype=RML_LITERAL, language_tag='', datatype=''):
    # TODO: handle column_alias?

    results_df = execute_fnml(results_df, fnml_df, fnml_execution, config)
    results_df = results_df.rename({fnml_execution: position})

    if termtype.strip() == RML_LITERAL:
        # Natural Mapping of SQL Values (https://www.w3.org/TR/r2rml/#natural-mapping)
        if datatype == XSD_BOOLEAN:
            results_df = results_df.with_columns(pl.col(position).str.to_lowercase())
        elif datatype == XSD_DATETIME:
            results_df = results_df.with_columns(pl.col(position).str.replace(' ', 'T'))

        results_df = results_df.with_columns(pl.col("reference_results").str.replace('\n', '\\n').str.replace('\t', '\\t').str.replace('\b', '\\b').str.replace('\f', '\\f').str.replace('\r', '\\r').str.replace('"', '\\"').str.replace("'", "\\'"))

        results_df = results_df.with_columns(pl.concat_str('"' + pl.col(position) + '"').alias(position))

        if pd.notna(language_tag):
            results_df = results_df.with_columns(pl.concat_str(pl.col(position) + '@' + language_tag).alias(position))
        elif pd.notna(datatype):
            results_df = results_df.with_columns(pl.concat_str(pl.col(position) + '^^<' + datatype + '>').alias(position))
    elif termtype.strip() == RML_IRI:
        # it is assumed that the IRI values will be correct, and they are not percent encoded
        results_df = results_df.with_columns(pl.col(position).apply(lambda x: x.strip(), skip_nulls=False).alias(position))
        results_df = results_df.with_columns(pl.concat_str('<' + pl.col(position) + '>').alias(position))
    elif termtype.strip() == RML_BLANK_NODE:
        results_df = results_df.with_columns(pl.concat_str('_:' + pl.col(position)).alias(position))

    return results_df


def _materialize_constant(results_df, constant, position, termtype=RML_IRI, language_tag='', datatype=''):
    complete_constant = ''
    if termtype.strip() == RML_IRI:
        complete_constant = '<' + constant + '>'
    elif termtype.strip() == RML_LITERAL:
        complete_constant = '"' + constant + '"'

        if pd.notna(language_tag):
            complete_constant = complete_constant + '@' + language_tag
        elif pd.notna(datatype):
            complete_constant = complete_constant + '^^<' + datatype + '>'
        else:
            complete_constant = complete_constant
    elif termtype.strip() == RML_BLANK_NODE:
        complete_constant = '_:' + constant

    results_df = results_df.with_columns(pl.lit(complete_constant).alias(position))

    return results_df


def _materialize_join_rml_rule_terms(results_df, rml_rule, parent_triples_map_rule, config):
    if rml_rule['subject_map_type'] == RML_TEMPLATE:
        results_df = _materialize_template(results_df, rml_rule['subject_map_value'], config, 's', termtype=rml_rule['subject_termtype'])
    elif rml_rule['subject_map_type'] == RML_CONSTANT:
        results_df = _materialize_constant(results_df, rml_rule['subject_map_value'], 's', termtype=rml_rule['subject_termtype'])
    elif rml_rule['subject_map_type'] == RML_REFERENCE:
        results_df = _materialize_reference(results_df, rml_rule['subject_map_value'], config, 's', termtype=rml_rule['subject_termtype'])
    if rml_rule['predicate_map_type'] == RML_TEMPLATE:
        results_df = _materialize_template(results_df, rml_rule['predicate_map_value'], config, 'p')
    elif rml_rule['predicate_map_type'] == RML_CONSTANT:
        results_df = _materialize_constant(results_df, rml_rule['predicate_map_value'], 'p')
    elif rml_rule['predicate_map_type'] == RML_REFERENCE:
        results_df = _materialize_reference(results_df, rml_rule['predicate_map_value'], config, 'p', termtype=RML_IRI)
    if parent_triples_map_rule['subject_map_type'] == RML_TEMPLATE:
        results_df = _materialize_template(results_df, parent_triples_map_rule['subject_map_value'], config, 'o', termtype=parent_triples_map_rule['subject_termtype'], columns_alias='parent_')
    elif parent_triples_map_rule['subject_map_type'] == RML_CONSTANT:
        results_df = _materialize_constant(results_df, parent_triples_map_rule['subject_map_value'], 'o', termtype=parent_triples_map_rule['subject_termtype'])
    elif parent_triples_map_rule['subject_map_type'] == RML_REFERENCE:
        results_df = _materialize_reference(results_df, parent_triples_map_rule['subject_map_value'], config, 'o', termtype=parent_triples_map_rule['subject_termtype'], columns_alias='parent_')

    return results_df


def _materialize_rml_rule_terms(results_df, rml_rule, fnml_df, config):
    if rml_rule['subject_map_type'] == RML_TEMPLATE:
        results_df = _materialize_template(results_df, rml_rule['subject_map_value'], config, 's', termtype=rml_rule['subject_termtype'])
    elif rml_rule['subject_map_type'] == RML_CONSTANT:
        results_df = _materialize_constant(results_df, rml_rule['subject_map_value'], 's', termtype=rml_rule['subject_termtype'])
    elif rml_rule['subject_map_type'] == RML_REFERENCE:
        results_df = _materialize_reference(results_df, rml_rule['subject_map_value'], config, 's', termtype=rml_rule['subject_termtype'])
    elif rml_rule['subject_map_type'] == RML_EXECUTION:
        results_df = _materialize_fnml_execution(results_df, rml_rule['subject_map_value'], fnml_df, config, 's', termtype=rml_rule['subject_termtype'])
    if rml_rule['predicate_map_type'] == RML_TEMPLATE:
        results_df = _materialize_template(results_df, rml_rule['predicate_map_value'], config, 'p')
    elif rml_rule['predicate_map_type'] == RML_CONSTANT:
        results_df = _materialize_constant(results_df, rml_rule['predicate_map_value'], 'p')
    elif rml_rule['predicate_map_type'] == RML_REFERENCE:
        results_df = _materialize_reference(results_df, rml_rule['predicate_map_value'], config, 'p', termtype=RML_IRI)
    elif rml_rule['predicate_map_type'] == RML_EXECUTION:
        results_df = _materialize_fnml_execution(results_df, rml_rule['predicate_map_value'], fnml_df, config, 'p', termtype=RML_IRI)
    if rml_rule['object_map_type'] == RML_TEMPLATE:
        results_df = _materialize_template(results_df, rml_rule['object_map_value'], config, 'o', termtype=rml_rule['object_termtype'], language_tag=rml_rule['object_language'], datatype=rml_rule['object_datatype'])
    elif rml_rule['object_map_type'] == RML_CONSTANT:
        results_df = _materialize_constant(results_df, rml_rule['object_map_value'], 'o', termtype=rml_rule['object_termtype'], language_tag=rml_rule['object_language'], datatype=rml_rule['object_datatype'])
    elif rml_rule['object_map_type'] == RML_REFERENCE:
        results_df = _materialize_reference(results_df, rml_rule['object_map_value'], config, 'o', termtype=rml_rule['object_termtype'], language_tag=rml_rule['object_language'], datatype=rml_rule['object_datatype'])
    elif rml_rule['object_map_type'] == RML_EXECUTION:
        results_df = _materialize_fnml_execution(results_df, rml_rule['object_map_value'], fnml_df, config, 'o', termtype=rml_rule['object_termtype'], language_tag=rml_rule['object_language'], datatype=rml_rule['object_datatype'])

    return results_df


def _merge_data(data, parent_data, rml_rule, join_condition):
    d = {}
    for col in parent_data.columns:
        d[col] = 'parent_'+col
    parent_data = parent_data.rename(d)

    child_join_references, parent_join_references = get_references_in_join_condition(rml_rule, join_condition)
    parent_join_references = ['parent_' + reference for reference in parent_join_references]

    data = data.join(parent_data, how='inner', left_on=child_join_references, right_on=parent_join_references)
    data = data.with_columns(pl.col(child_join_references[0]).alias(parent_join_references[0]))

    return data


def _materialize_rml_rule(rml_rule, rml_df, fnml_df, config, data=None, parent_join_references=set(), nest_level=0, python_source=None):
    references = set(_get_references_in_rml_rule(rml_rule, rml_df, fnml_df))

    references_subject_join, parent_references_subject_join = get_references_in_join_condition(rml_rule, 'subject_join_conditions')
    references_object_join, parent_references_object_join = get_references_in_join_condition(rml_rule, 'object_join_conditions')
    references.update(parent_join_references)

    if rml_rule['subject_map_type'] == RML_QUOTED_TRIPLES_MAP or rml_rule['object_map_type'] == RML_QUOTED_TRIPLES_MAP:
        if data is None:
            data = _get_data(config, rml_rule, references, python_source)

        if rml_rule['subject_map_type'] == RML_TEMPLATE:
            data = _materialize_template(data, rml_rule['subject_map_value'], config, 's', termtype=rml_rule['subject_termtype'])
        elif rml_rule['subject_map_type'] == RML_CONSTANT:
            data = _materialize_constant(data, rml_rule['subject_map_value'], 's', termtype=rml_rule['subject_termtype'])
        elif rml_rule['subject_map_type'] == RML_REFERENCE:
            data = _materialize_reference(data, rml_rule['subject_map_value'], config, 's', termtype=rml_rule['subject_termtype'])

        if rml_rule['object_map_type'] == RML_TEMPLATE:
            data = _materialize_template(data, rml_rule['object_map_value'], config, 'o', termtype=rml_rule['object_termtype'], language_tag=rml_rule['object_language'], datatype=rml_rule['object_datatype'])
        elif rml_rule['object_map_type'] == RML_CONSTANT:
            data = _materialize_constant(data, rml_rule['object_map_value'], 'o', termtype=rml_rule['object_termtype'], language_tag=rml_rule['object_language'], datatype=rml_rule['object_datatype'])
        elif rml_rule['object_map_type'] == RML_REFERENCE:
            data = _materialize_reference(data, rml_rule['object_map_value'], config, 'o', termtype=rml_rule['object_termtype'], language_tag=rml_rule['object_language'], datatype=rml_rule['object_datatype'])

        if rml_rule['predicate_map_type'] == RML_TEMPLATE:
            data = _materialize_template(data, rml_rule['predicate_map_value'], config, 'p')
        elif rml_rule['predicate_map_type'] == RML_CONSTANT:
            data = _materialize_constant(data, rml_rule['predicate_map_value'], 'p')
        elif rml_rule['predicate_map_type'] == RML_REFERENCE:
            data = _materialize_reference(data, rml_rule['predicate_map_value'], config, 'p', termtype=RML_IRI)

    # elif pd.notna(rml_rule['object_parent_triples_map']):
    elif rml_rule['object_map_type'] == RML_PARENT_TRIPLES_MAP:

        references.update(references_object_join)
        # parent_triples_map_rule = get_rml_rule(rml_df, rml_rule['object_parent_triples_map'])
        parent_triples_map_rule = get_rml_rule(rml_df, rml_rule['object_map_value'])
        parent_references = set(_get_references_in_rml_rule(parent_triples_map_rule, rml_df, fnml_df, only_subject_map=True))

        # add references used in the join condition
        references, parent_references = _add_references_in_join_condition(rml_rule, references, parent_references)

        if data is None:
            data = _get_data(config, rml_rule, references, python_source)

        parent_data = _get_data(config, parent_triples_map_rule, parent_references, python_source)
        merged_data = _merge_data(data, parent_data, rml_rule, 'object_join_conditions')
        data = _materialize_join_rml_rule_terms(merged_data, rml_rule, parent_triples_map_rule, config)
    else:

        if data is None:
            data = _get_data(config, rml_rule, references, python_source)

        data = _materialize_rml_rule_terms(data, rml_rule, fnml_df, config)

    data = data.select(pl.col(['s', 'p', 'o']))

    return data


def _materialize_mapping_group_to_df(mapping_group_df, rml_df, fnml_df, config, python_source=None):

    triples_rules_dfs = []
    for i, rml_rule in mapping_group_df.iterrows():
        triples_rules_dfs.append(_materialize_rml_rule(rml_rule, rml_df, fnml_df, config, python_source=python_source))
        logging.debug(f'Materialized mapping rule {rml_rule["triples_map_id"]}.')

    triples_rules_df = pl.concat(triples_rules_dfs)
    triples_rules_df = triples_rules_df.with_columns(pl.Series(name="row_hash", values=triples_rules_df.hash_rows(seed=42)))

    triples_rules_df = triples_rules_df.unique(subset='row_hash')
    triples_rules_df = triples_rules_df.drop('row_hash')

    return triples_rules_df
