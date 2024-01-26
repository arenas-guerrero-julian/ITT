import pymongo
import pandas as pd
import polars as pl


def get_mongo_data(config, rml_rule, references):
    mongo_url = config.get_mongo_url(rml_rule['source_name'])

    client = pymongo.MongoClient(mongo_url)
    mdb = client.get_default_database()

    mapping_collection = rml_rule['logical_source_value']
    collection = mdb.get_collection(mapping_collection)

    mongo_df = pd.DataFrame(list(collection.find(projection=references)))
    mongo_df = mongo_df.astype(str)

    return pl.from_pandas(mongo_df)