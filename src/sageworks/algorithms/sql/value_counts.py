"""SQL based Value Counts: Compute Value Counts for all columns in a DataSource using SQL"""
import logging
import pandas as pd

# SageWorks Imports
from sageworks.artifacts.data_sources.data_source_abstract import DataSourceAbstract
from sageworks.utils.pandas_utils import shorten_values
from sageworks.utils.trace_calls import trace_calls

# SageWorks Logger
log = logging.getLogger("sageworks")


@trace_calls
def value_counts(data_source: DataSourceAbstract) -> dict[dict]:
    """Compute 'value_counts' for all the string columns in a DataSource
    Args:
        data_source: The DataSource that we're computing value_counts on
    Returns:
        dict(dict): A dictionary of value counts for each column in the form
             {'col1': {'value_1': X, 'value_2': Y, 'value_3': Z,...},
              'col2': ...}
    """

    # For every column in the table that is string, compute the value_counts
    data_source.log.info("Computing value_counts for all string columns...")
    value_count_dict = dict()
    for column, data_type in zip(data_source.column_names(), data_source.column_types()):
        if data_type in ["string", "boolean"]:
            # Combined query to get both top and bottom counts
            query = (
                f'(SELECT "{column}", count(*) as count '
                f"FROM {data_source.table_name} "
                f'GROUP BY "{column}" ORDER BY count DESC LIMIT 20) '
                f"UNION ALL "
                f'(SELECT "{column}", count(*) as count '
                f"FROM {data_source.table_name} "
                f'GROUP BY "{column}" ORDER BY count ASC LIMIT 20)'
            )
            result_df = data_source.query(query)

            # Convert Int64 (nullable) to int32 so that we can serialize to JSON
            result_df["count"] = result_df["count"].astype("int32")

            # If the column is boolean, convert the values to True/False strings (for JSON)
            if result_df[column].dtype == "boolean":
                result_df[column] = result_df[column].astype("string")

            # Convert any NA values to 'NaN' so that we can serialize to JSON
            result_df.fillna("NaN", inplace=True)

            # If all of our counts equal 1 we can drop most of them
            if result_df["count"].sum() == result_df.shape[0]:
                result_df = result_df.iloc[:5]

            # Shorten any long string values
            result_df = shorten_values(result_df)

            # Convert the result_df into a dictionary
            value_count_dict[column] = dict(zip(result_df[column], result_df["count"]))

    # Return the value_count data
    return value_count_dict


if __name__ == "__main__":
    """Exercise the SQL Value Counts Functionality"""
    from pprint import pprint
    from sageworks.artifacts.data_sources.data_source import DataSource

    # Setup Pandas output options
    pd.set_option("display.max_colwidth", 50)
    pd.set_option("display.max_columns", 15)
    pd.set_option("display.width", 1000)

    # Retrieve a Data Source
    my_data = DataSource("abalone_data")

    # Verify that the Athena Data Source exists
    assert my_data.exists()

    # What's my SageWorks UUID
    print(f"UUID: {my_data.uuid}")

    # Get sample rows for this DataSource
    my_value_counts = value_counts(my_data)
    print("\nValue Counts")
    pprint(my_value_counts)
