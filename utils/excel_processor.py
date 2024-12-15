# utils/excel_processor.py

import pandas as pd
import re
from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

from utils.validators import format_datetime, is_date

def process_excel(file_path, timezone):
    """
    Processes an Excel file for XMLTV conversion, handling various data formats and potential errors.

    Args:
        file_path (str): Path to the Excel file.
        timezone (ZoneInfo): Timezone for datetime localization.

    Returns:
        tuple: (display_df, internal_df)
            - display_df (pd.DataFrame): DataFrame for display in the application.
            - internal_df (pd.DataFrame): DataFrame for XMLTV conversion.

    Raises:
        ValueError: If the Excel file has an incorrect number of columns or no rows starting with a date.
        Exception: If other errors occur during processing.
    """
    try:
        # Read Excel file without headers
        df = pd.read_excel(file_path, header=None)
        logging.debug(f"Excel file loaded: {file_path}")
        logging.debug(f"First 5 rows before filtering:\n{df.head()}")

        # Filter rows starting with a date
        df = df[df[0].apply(is_date)].copy()

        if df.empty:
            logging.debug("No rows starting with a date.")
            raise ValueError("No rows starting with a date.")

        logging.debug(f"Number of rows after filtering: {len(df)}")
        logging.debug(f"First 5 rows after filtering:\n{df.head()}")

        # Reset index after filtering
        df.reset_index(drop=True, inplace=True)

        # Check and select columns
        required_columns = 7  # Date, Time, Title, Category, EPZ, P/R, Description
        actual_columns = df.shape[1]
        if actual_columns < required_columns:
            raise ValueError(f"Excel file must have at least {required_columns} columns, but only has {actual_columns}.")
        elif actual_columns > required_columns:
            logging.warning(f"Excel file has {actual_columns} columns. Only the first {required_columns} columns will be used.")
            df = df.iloc[:, :required_columns]

        # Name columns for easier work
        df.columns = ['Date', 'Time', 'Title', 'Category', 'EPZ', 'P/R', 'Description']

        # Rename 'EPZ' to 'episode-num'
        df.rename(columns={'EPZ': 'episode-num'}, inplace=True)

        # Check if 'episode-num' column exists after renaming
        if 'episode-num' not in df.columns:
            raise ValueError("Renaming column 'EPZ' to 'episode-num' failed.")

        # Correct Date format in 'Date' column
        df['Date'] = df['Date'].astype(str).str.strip()
        df['Date'] = df['Date'].apply(lambda x: x + '.' if not x.endswith('.') else x)
        
        # Correct Time format in 'Time' column
        df['Time'] = df['Time'].astype(str).str.strip()
        df['Time'] = df['Time'].apply(lambda x: x if ":" in x else x.replace(".", ":"))


        # Create 'start' time
        df['start'] = df.apply(lambda row: format_datetime(row['Date'], row['Time']), axis=1)

        # Create 'stop' time as the 'start' time of the next row
        df['stop'] = df['start'].shift(-1)

        # If 'stop' time is not available (last program), set to 07:00 the next day
        for i in range(len(df)):
            if pd.isna(df.at[i, 'stop']):
                start_dt = pd.to_datetime(df.at[i, 'start'])
                next_day = start_dt + timedelta(days=1)
                stop_dt = next_day.replace(hour=7, minute=0, second=0)
                df.at[i, 'stop'] = stop_dt

        # Check if 'start' and 'stop' times are correctly formatted
        for idx, row in df.iterrows():
            if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+\d{2}:\d{2}$', str(row['start'])):  # Updated regex for datetime format
                raise ValueError(f"Incorrect 'start' time format in row {idx + 2}: {row['start']}")
            if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+\d{2}:\d{2}$', str(row['stop'])):  # Updated regex for datetime format
                raise ValueError(f"Incorrect 'stop' time format in row {idx + 2}: {row['stop']}")

        # Create new columns for display
        df['DATE'] = pd.to_datetime(df['start']).dt.strftime('%d.%m.%Y.')
        df['START TIME'] = pd.to_datetime(df['start']).dt.strftime('%H:%M')
        df['STOP TIME'] = pd.to_datetime(df['stop']).dt.strftime('%H:%M')
        df['NAZIV EMISIJE'] = df['Title']
        df['EPISODE NUMBER'] = df['episode-num']
        df['P/R'] = df['P/R']
        df['CATEGORY'] = df['Category']
        df['OPIS emisije'] = df['Description']

        # Create display_df with correct column mapping
        display_df = pd.DataFrame({
            'DATE': df['DATE'],
            'START TIME': df['START TIME'],
            'NAZIV EMISIJE': df['Title'],
            'CATEGORY': df['Category'],
            'EPISODE NUMBER': df['episode-num'],
            'P/R': df['P/R'],
            'OPIS emisije': df['Description']
        })

        # Create internal DataFrame with all necessary data for XMLTV
        internal_df = df[['start', 'stop', 'Title', 'Description', 'Category', 'episode-num']].copy()
        internal_df.rename(columns={'Title': 'title', 'Description': 'desc'}, inplace=True)

        logging.debug(f"display_df:\n{display_df.head()}")
        logging.debug(f"internal_df:\n{internal_df.head()}")

        return display_df, internal_df

    except Exception as e:
        logging.error("An error occurred during Excel file processing:", exc_info=True)
        raise e
