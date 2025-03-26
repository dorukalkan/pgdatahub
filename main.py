import os
import pandas as pd
import json
import re
import psycopg2 as ps
import logging
from datetime import datetime
from contextlib import closing
import sys


# configure logging at the module level
logger = logging.getLogger(__name__)

# map turkish characters to english characters
TR_MAPPING = str.maketrans("ıİğĞüÜşŞöÖçÇ", "iIgGuUsSoOcC")

# map pandas dtypes to sql data types
DTYPE_MAPPING = {
    # numeric types
    "int8": "SMALLINT",
    "int16": "SMALLINT",
    "int32": "INTEGER",
    "int64": "BIGINT",
    "uint8": "SMALLINT",
    "uint16": "INTEGER",
    "uint32": "BIGINT",
    "uint64": "BIGINT",
    "float16": "REAL",
    "float32": "REAL",
    "float64": "DOUBLE PRECISION",
    "decimal": "NUMERIC",
    # date and time types
    "datetime64[ns]": "TIMESTAMP",
    "datetime64[us]": "TIMESTAMP",
    "datetime64[ms]": "TIMESTAMP",
    "datetime64[s]": "TIMESTAMP",
    "datetime64[D]": "DATE",
    "timedelta64[ns]": "INTERVAL",
    "timedelta64[us]": "INTERVAL",
    "timedelta64[ms]": "INTERVAL",
    "timedelta64[s]": "INTERVAL",
    "timedelta64[D]": "INTERVAL",
    # boolean type
    "bool": "BOOLEAN",
    # string types
    "object": "VARCHAR",
    "string": "VARCHAR",
    "category": "VARCHAR",
    # binary types
    "bytes": "BYTEA",
    # default fallback
    "default": "VARCHAR",
}


# find csv and excel files in current working directory
def find_data_files():
    """Find all CSV, Excel, and JSON files in the current working directory."""
    data_files = []
    excel_extensions = [".xlsx", ".xls", ".xlsm", ".xlsb", ".odf", ".ods", ".odt"]

    # get all files in current directory
    all_files = os.listdir(os.getcwd())
    logger.debug("All files in directory: %s", all_files)

    for f in all_files:
        # skip config files
        if f.lower() in ["config.json", "config.template.json"]:
            logger.debug("Skipping config file: %s", f)
            continue

        # check file extension
        if (
            f.endswith(".csv")
            or f.endswith(".json")
            or any(f.endswith(ext) for ext in excel_extensions)
        ):
            data_files.append(f)
            logger.debug("Found data file: %s", f)

    logger.info("Found %d data files: %s", len(data_files), data_files)
    return data_files


# configure a new directory for datasets
def configure_data_dir(data_files, data_directory):
    """Create a new directory for datasets and move data files into it.

    Args:
        data_files (list): List of data file names to move
        data_directory (str): Name of the directory to create and move files to
    """
    try:
        os.makedirs(data_directory, exist_ok=True)
        logger.info("Directory %s created", data_directory)
    except OSError as e:
        logger.error("Error creating directory: %s", e)

    for f in data_files:
        try:
            file_path = os.path.join(os.getcwd(), f)
            destination = os.path.join(data_directory, f)
            os.rename(file_path, destination)
            logger.info("Moved '%s' to %s", f, data_directory)
        except Exception as e:
            logger.error("Error moving file %s: %s", f, e)


# read the data files to a dictionary of dataframes
def create_df_dict(data_files, data_directory):
    """Read data files and create a dictionary of pandas DataFrames.

    Args:
        data_files (list): List of data file names to process
        data_directory (str): Directory containing the data files

    Returns:
        dict: Dictionary mapping file names to their corresponding DataFrames
    """
    # get the path to datasets
    data_path = os.path.join(os.getcwd(), data_directory)
    logger.info("Data path is: %s", data_path)

    # iterate over files and create a dictionary of dataframes
    df = {}
    error_count = 0

    for f in data_files:
        try:
            file_path = os.path.join(data_path, f)
            file_extension = os.path.splitext(f)[1].lower()

            if file_extension == ".csv":
                df[f] = pd.read_csv(file_path)
                logger.info("Successfully loaded CSV: %s", f)

            elif file_extension in [
                ".xlsx",
                ".xls",
                ".xlsm",
                ".xlsb",
                ".odf",
                ".ods",
                ".odt",
            ]:
                try:
                    # read all sheets in the Excel file
                    excel_data = pd.read_excel(file_path, sheet_name=None)

                    if len(excel_data) == 1:
                        # if there's only one sheet, use the original filename
                        df[f] = list(excel_data.values())[0]
                        logger.info(
                            "Successfully loaded Excel file with single sheet: %s", f
                        )
                    else:
                        # if there are multiple sheets, create separate dataframes for each
                        base_name = os.path.splitext(f)[0]
                        for sheet_name, sheet_df in excel_data.items():
                            # create a clean sheet name
                            clean_sheet_name = clean_text(sheet_name)
                            # create a new key for this sheet
                            new_key = f"{base_name}_{clean_sheet_name}.xlsx"
                            df[new_key] = sheet_df
                            logger.info(
                                "Successfully loaded sheet '%s' from Excel file: %s",
                                sheet_name,
                                f,
                            )

                except Exception as e:
                    logger.error("Error loading Excel file %s: %s", f, str(e))
                    error_count += 1
                    continue

            elif file_extension == ".json":
                try:
                    with open(file_path, "r", encoding="utf-8") as json_file:
                        json_data = json.load(json_file)
                        df[f] = pd.json_normalize(json_data)
                        logger.info("Successfully loaded JSON file: %s", f)
                except json.JSONDecodeError as e:
                    logger.error("Invalid JSON format in file %s: %s", f, str(e))
                    error_count += 1
                    continue
                except Exception as e:
                    logger.error("Error processing JSON file %s: %s", f, str(e))
                    error_count += 1
                    continue

            else:
                logger.warning("Unsupported file type: %s", f)
                error_count += 1
                continue

        except Exception as e:
            logger.error("Error loading %s: %s", f, str(e))
            error_count += 1
        logger.debug("Finished processing: %s", f)

    logger.info("Data loading completed with %d errors", error_count)
    return df


# clean and standardize text
def clean_text(text):
    """Clean and standardize text by removing special characters and normalizing.

    Args:
        text (str): Text to clean

    Returns:
        str: Cleaned text with standardized format
    """
    # remove the file extension
    if "." in text and not text.startswith("."):
        base_name = text.split(".")[0]
    else:
        base_name = text

    # replace dots in column names with underscores
    text = base_name.replace(".", "_")

    # replace turkish characters and lower all characters
    text = text.translate(TR_MAPPING).lower()

    # replace special characters with underscores
    text = re.sub(r"[^a-zA-Z0-9_]", "_", text)

    # ensure there is only one underscore between words
    text = re.sub(r"_+", "_", text)

    # remove leading and trailing underscores
    text = text.strip("_")

    # prefix with col_ if it starts with a number
    if text and text[0].isdigit():
        text = "col_" + text

    return text


# clean each file name and update dataframe keys accordingly
def clean_file_names(data_files, dataframe):
    """Clean file names and update DataFrame dictionary keys accordingly.

    Args:
        data_files (list): List of original file names
        dataframe (dict): Dictionary of DataFrames to update

    Returns:
        list: List of cleaned file names
    """
    cleaned_files = []
    for f in data_files:
        clean_name = clean_text(f)
        cleaned_files.append(clean_name)
        dataframe[clean_name] = dataframe.pop(f)
    data_files = cleaned_files
    logger.info("Cleaned file names: %s", data_files)
    return data_files


# clean column headers in each dataframe and define table schemas
def process_dataframes(dataframes_dict):
    """Process DataFrames to clean column headers and create SQL table schemas.

    Args:
        dataframes_dict (dict): Dictionary of DataFrames to process

    Returns:
        dict: Dictionary mapping table names to their SQL schemas
    """
    schemas = {}
    for file_name, df in dataframes_dict.items():
        # clean column headers
        df.columns = [clean_text(col) for col in df.columns]
        # get sql type for each column
        col_types = df.dtypes.replace(DTYPE_MAPPING)
        # pair column names with their sql types
        col_pairs = zip(df.columns, col_types)
        # create the table schema
        schemas[file_name] = ", ".join(f"{col} {type}" for col, type in col_pairs)
        logger.info("Schema created for table %s: %s", file_name, schemas[file_name])
    return schemas


# save dataframe to csv
def save_df_to_csv(clean_file_name, dataframe_dict):
    """Save DataFrames to CSV files.

    Args:
        clean_file_name (str): Name of the file to save
        dataframe_dict (dict): Dictionary of DataFrames to save
    """
    for clean_file_name, df in dataframe_dict.items():
        df.to_csv(
            f"{clean_file_name}.csv",
            header=df.columns,
            index=False,
            encoding="utf-8",
        )
        logger.info("%s saved successfully", clean_file_name)

    return


# get database credentials
def load_config():
    """Load database configuration from config.json file.

    Returns:
        dict: Database connection parameters
    """
    with open("config.json", "r") as f:
        config = json.load(f)
    return config["database"]


# connect to db, create tables, insert values
def import_to_postgres(table_schema, conn_dict):
    """Import data into PostgreSQL database by creating tables and inserting values.

    Args:
        table_schema (dict): Dictionary mapping table names to their schemas
        conn_dict (dict): Database connection parameters
    """
    with closing(ps.connect(**conn_dict)) as conn:
        with conn.cursor() as cur:
            try:
                # wrap all operations in a single transaction
                for file_name, schema in table_schema.items():
                    # use proper sql parameter substitution where possible
                    cur.execute(
                        "CREATE TABLE IF NOT EXISTS %s (%s)",
                        (ps.extensions.AsIs(file_name), ps.extensions.AsIs(schema)),
                    )

                    with open(f"{file_name}.csv", "r", encoding="utf-8") as my_file:
                        QUERY = f"""
                        COPY {file_name} FROM STDIN WITH
                            CSV
                            HEADER
                            DELIMITER AS ','
                            ENCODING 'UTF8'
                        """
                        cur.copy_expert(sql=QUERY, file=my_file)

                conn.commit()
                logger.info("All tables created and data imported successfully")
            except Exception as e:
                conn.rollback()
                logger.error("Failed to import data: %s", str(e))
                raise


def move_processed_files(processed_files):
    """Move processed CSV files to processed_data directory.

    Args:
        processed_files (list): List of processed file names to move
    """
    processed_dir = "processed_data"
    try:
        os.makedirs(processed_dir, exist_ok=True)
        logger.info("Created processed datasets directory: %s", processed_dir)

        for file_name in processed_files:
            csv_file = f"{file_name}.csv"
            source = os.path.join(os.getcwd(), csv_file)
            destination = os.path.join(processed_dir, csv_file)
            os.rename(source, destination)
            logger.info("Moved processed file '%s' to %s", csv_file, processed_dir)
    except Exception as e:
        logger.error("Error moving processed files: %s", str(e))
        raise


# main
def main():
    """Main function to execute the data import process.
    Orchestrates the entire workflow from finding files to database import.
    """
    logger.info("Starting data import process")

    try:
        data_dir = "unprocessed_data"
        data_files = find_data_files()
        if not data_files:
            raise ValueError("No data files found to process")

        configure_data_dir(data_files, data_dir)
        df_dict = create_df_dict(data_files, data_dir)

        if not df_dict:
            raise ValueError("Failed to process any data files")

        datasets = clean_file_names(list(df_dict.keys()), df_dict)
        schemas = process_dataframes(df_dict)
        save_df_to_csv(datasets, df_dict)

        # load credentials from config file
        db_config = load_config()
        import_to_postgres(schemas, db_config)

        # move processed csv files to processed_data directory
        move_processed_files(datasets)

        logger.info("All datasets have been imported successfully")
    except Exception as e:
        logger.error("Script failed: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    # logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                f"data_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            ),
            logging.StreamHandler(),
        ],
    )
    main()
