import io
import datetime
from dateutil import tz
import pandas as pd
import streamlit as st

# -------------------------------------------------------------------------
# Session State Initialization
# -------------------------------------------------------------------------
# We use Streamlit's session_state to persist data across interactions within the app
if "matching_transactions" not in st.session_state:
    st.session_state.matching_transactions = None
if "non_matching_transactions" not in st.session_state:
    st.session_state.non_matching_transactions = None
def filter_transactions_by_month_year(dataframe, month, year, datetime_column='date/time'):
    """
    Cleans and filters transactions for a specific month and year, handling timezone issues.
    
    Parameters:
        dataframe (pd.DataFrame): The DataFrame containing the transactions.
        month (int): The month to filter by (1-12).
        year (int): The year to filter by (e.g., 2024).
        datetime_column (str): The name of the column containing date/time values.
        
    Returns:
        pd.DataFrame: Filtered DataFrame containing transactions from the specified month and year.
    """
    # Handle timezone abbreviations by removing them
    dataframe[datetime_column] = dataframe[datetime_column].str.replace(r" [A-Z]{3,4}$", "", regex=True)
    
    # Convert to datetime
    dataframe[datetime_column] = pd.to_datetime(dataframe[datetime_column], errors='coerce')
    
    # Filter the data for the specified month and year
    filtered_df = dataframe[
        (dataframe[datetime_column].dt.month == month) & 
        (dataframe[datetime_column].dt.year == year)
    ]
    
    return filtered_df

def filter_out_orders(df: pd.DataFrame, type_column: str = "type") -> pd.DataFrame:
    """
    Returns a new DataFrame from df that excludes rows where the `type` column is 'Order'.

    :param df: The original DataFrame containing Amazon unified transaction data.
    :param type_column: The name of the column that indicates transaction type.
    :return: A filtered DataFrame without rows of type 'Order'.
    """
    # Check if the type column exists
    if type_column not in df.columns:
        raise ValueError(f"Column '{type_column}' not found in DataFrame.")

    # Filter out rows where df[type_column] == 'Order'
    filtered_df = df[df[type_column] != "Order"]

    return filtered_df

def validate_date_in_target(df: pd.DataFrame, date_column: str, report_name: str) -> pd.DataFrame:
    """
    Convert the specified date_column in the DataFrame to datetime.
    If errors occur, return an empty DataFrame and display an error.
    
    :param df: The input DataFrame.
    :param date_column: Column name that contains date information.
    :param report_name: Name of the report (for error messages).
    :return: The DataFrame with the date_column converted to datetime 
             or an empty DataFrame on error.
    """
    try:
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error processing dates in {report_name}: {e}")
        return pd.DataFrame()


def combine_reports(reports: list) -> pd.DataFrame:
    """
    Combine multiple DataFrames into one using pandas.concat().
    
    :param reports: A list of pandas DataFrames to concatenate.
    :return: A single concatenated DataFrame.
    """
    return pd.concat(reports, ignore_index=True)


def read_text_or_csv(uploaded_file) -> pd.DataFrame:
    """
    Read a text or CSV file into a pandas DataFrame.
    Uses 'python' engine to automatically detect delimiters in CSV/TSV files.
    
    :param uploaded_file: The file uploaded by the user (Streamlit file-like object).
    :return: The resulting pandas DataFrame.
    """
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        return df
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return pd.DataFrame()


def read_dynamic_header_report(uploaded_file, search_string: str = "date/time") -> pd.DataFrame:
    """
    Read a CSV (or text-based) report, dynamically detecting the header row by a given search string.
    
    :param uploaded_file: The file uploaded by the user (Streamlit file-like object).
    :param search_string: The string to search for in lines to identify the header row.
    :return: The resulting pandas DataFrame with correct headers.
    """
    try:
        # Decode the uploaded file content
        content = uploaded_file.read().decode('utf-8-sig')
        lines = content.splitlines()

        # Find the line index where the search_string occurs
        header_row = next(i for i, line in enumerate(lines) if search_string in line.lower())

        # Read the CSV from the detected header row onward
        df = pd.read_csv(io.StringIO(content), skiprows=header_row)
        return df
    except Exception as e:
        st.error(f"An error occurred while processing the uploaded file: {e}")
        return pd.DataFrame()


def run():
    """
    Main Streamlit application to process Amazon sales reports. 
    The user can upload several reports (Fulfillment, Unified Transaction, 
    Standard Orders Deferred Transaction, Invoiced Orders Deferred Transaction), 
    which are validated and combined. The combined data is then split into 
    matching and non-matching transactions (based on Fulfillment Report 
    order IDs) and summed for certain financial columns.
    """
    # ---------------------------------------------------------------------
    # Page Title and Instructions
    # ---------------------------------------------------------------------
    st.title("Amazon Sales Report Processor")
    st.write(
        "Upload your Amazon sales reports, specify the target month and year, "
        "and process them for accounting."
    )
    user_selected_date = st.date_input(
        "Select a date (we'll use only the month/year)",
        value=datetime.date(2024, 11, 1)
    )
    
    # 2. Extract the month/year from user-selected date
    target_month = user_selected_date.month
    target_year = user_selected_date.year
    # ---------------------------------------------------------------------
    # File Uploaders
    # ---------------------------------------------------------------------
    fulfillment_file = st.file_uploader("Upload Fulfillment Report:", type=["txt"])
    unified_transaction_file = st.file_uploader(
        "Upload Unified Transaction Report:", type=["csv", "xls", "xlsx"]
    )
    standard_orders_file = st.file_uploader(
        "Upload Standard Orders Deferred Transaction Report:", type=["csv", "xls", "xlsx"]
    )
    invoiced_orders_file = st.file_uploader(
        "Upload Invoiced Orders Deferred Transaction Report:", type=["csv", "xls", "xlsx"]
    )

    # ---------------------------------------------------------------------
    # Process the reports when the user clicks the "Process Reports" button
    # ---------------------------------------------------------------------
    if st.button("Process Reports"):
        if not all([fulfillment_file, unified_transaction_file, standard_orders_file, invoiced_orders_file]):
            st.error("Please upload all required reports.")
            return

        try:
            # -------------------------------------------------------------
            # Fulfillment Report
            # -------------------------------------------------------------
            st.subheader("Processing Fulfillment Report")
            fulfillment_df = read_text_or_csv(fulfillment_file)
            if fulfillment_df.empty:
                st.error("Fulfillment Report is empty or could not be processed.")
                return
            st.write("Fulfillment Report preview:", fulfillment_df.head())

            # Validate/convert date column for Fulfillment Report
            # Assumes the date is in the 3rd column (index = 2)
            try:
                date_col_name = fulfillment_df.columns[2]
                fulfillment_df = validate_date_in_target(
                    df=fulfillment_df, 
                    date_column=date_col_name, 
                    report_name="Fulfillment Report"
                )
            except Exception as e:
                st.error(f"Error processing Fulfillment Report date column: {e}")
                return

            # -------------------------------------------------------------
            # Unified Transaction Report
            # -------------------------------------------------------------
            st.subheader("Processing Unified Transaction Report")
            unified_transaction_df = read_dynamic_header_report(unified_transaction_file, search_string="date/time")
            if not unified_transaction_df.empty:
                st.write(unified_transaction_df.head())

            # -------------------------------------------------------------
            # Standard Orders Deferred Transaction Report
            # -------------------------------------------------------------
            st.subheader("Processing Standard Orders Deferred Transaction Report")
            standard_orders_df = read_dynamic_header_report(standard_orders_file, search_string="date/time")
            if not standard_orders_df.empty:
                st.write(standard_orders_df.head())

            # -------------------------------------------------------------
            # Invoiced Orders Deferred Transaction Report
            # -------------------------------------------------------------
            st.subheader("Processing Invoiced Orders Deferred Transaction Report")
            invoiced_orders_df = read_dynamic_header_report(invoiced_orders_file, search_string="date/time")
            if not invoiced_orders_df.empty:
                st.write(invoiced_orders_df.head())

            # -------------------------------------------------------------
            # Combine the Unified, Standard Orders, and Invoiced Orders
            # into one transactions DataFrame
            # -------------------------------------------------------------
            combined_transactions = combine_reports([
                unified_transaction_df, 
                standard_orders_df, 
                invoiced_orders_df
            ])
            st.write("Combined Transactions preview:", combined_transactions.head())

            # -------------------------------------------------------------
            # Provide a download link for the combined data
            # -------------------------------------------------------------
            csv_combined = combined_transactions.to_csv(index=False)
            st.download_button(
                label="Download Processed Data",
                data=csv_combined,
                file_name="processed_data.csv",
                mime="text/csv"
            )

            # -------------------------------------------------------------
            # Identify matching and non-matching transactions
            # -------------------------------------------------------------
            transaction_order_id_column = "order id"
            fulfillment_order_id_column = "amazon-order-id"
            type_column = "type"
            valid_types = ["Order"]  # Extend if needed, e.g., ["Order", "Liquidation"]

            # Validate columns exist
            required_combined_cols = [transaction_order_id_column, type_column]
            if all(col in combined_transactions.columns for col in required_combined_cols) and \
               fulfillment_order_id_column in fulfillment_df.columns:

                # Fulfillment order IDs
                fulfillment_order_ids = fulfillment_df[fulfillment_order_id_column]

                # Matching transactions based on 'order id' in Fulfillment and type
                matching_transactions = combined_transactions[
                    (combined_transactions[transaction_order_id_column].isin(fulfillment_order_ids)) &
                    (combined_transactions[type_column].isin(valid_types))
                ]

                # Non-matching transactions are everything else
                non_matching_transactions = combined_transactions[
                    ~(
                        (combined_transactions[transaction_order_id_column].isin(fulfillment_order_ids)) &
                        (combined_transactions[type_column].isin(valid_types))
                    )
                ]

                # Store in session state
                st.session_state.processed_data = combined_transactions
                st.session_state.matching_transactions = matching_transactions
                st.session_state.non_matching_transactions = non_matching_transactions

                st.write("Matching Transactions:", matching_transactions)
                st.write("Non-Matching Transactions:", non_matching_transactions)

                # ---------------------------------------------------------
                # Identify unexpected columns and sum known financial columns
                # ---------------------------------------------------------
                columns_to_sum = [
                    "product sales",
                    "product sales tax",
                    "shipping credits",
                    "shipping credits tax",
                    "gift wrap credits",
                    "giftwrap credits tax",
                    "Regulatory Fee",
                    "Tax On Regulatory Fee",
                    "promotional rebates",
                    "promotional rebates tax",
                    "marketplace withheld tax",
                    "selling fees",
                    "fba fees",
                    "other transaction fees",
                    "other",
                    "total",
                ]

                # Identify columns appearing after "product sales"
                if "product sales" in matching_transactions.columns:
                    columns_after_product_sales = matching_transactions.columns[
                        matching_transactions.columns.get_loc("product sales") + 1 :
                    ]
                    unexpected_columns = [
                        col for col in columns_after_product_sales if col not in columns_to_sum
                    ]

                    if unexpected_columns:
                        st.warning(
                            f"The following unexpected columns were found after 'product sales': "
                            f"{', '.join(unexpected_columns)}. These columns are not currently "
                            "accounted for in the calculations."
                        )
                else:
                    st.warning("Column 'product sales' is missing from the transactions.")

                # Convert columns_to_sum to numeric and sum them
                for col in columns_to_sum:
                    if col in matching_transactions.columns:
                        matching_transactions[col] = pd.to_numeric(matching_transactions[col], errors='coerce')
                    else:
                        st.warning(f"Column '{col}' is missing from the report.")

                summed_values = matching_transactions[columns_to_sum].sum(numeric_only=True)
                st.subheader("Summed Column Values")
                st.write("Matching Order Sales/Charges:", summed_values)

                non_order_transactions_df = filter_out_orders(unified_transaction_df)
                non_order_transactions_df = filter_transactions_by_month_year(non_order_transactions_df,11,2024)
                st.download_button(
                    "Download unified transaction that are not orders for target month",
                    data=non_order_transactions_df.to_csv(index=False),
                    file_name="filtered_unified_transactions.csv",
                    mime="text/csv",
                )
                
            else:
                st.error("Required columns not found in one or both DataFrames.")

            st.success("Reports processed successfully!")

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")

    # ---------------------------------------------------------------------
    # Provide download buttons for Non-Matching and Matching transactions
    # if they exist in session_state
    # ---------------------------------------------------------------------
    if st.session_state.non_matching_transactions is not None:
        csv_non_matching = st.session_state.non_matching_transactions.to_csv(index=False)
        st.download_button(
            "Download Non-Matching Transactions",
            data=csv_non_matching,
            file_name="non_matching_transactions.csv",
            mime="text/csv",
        )

    if st.session_state.matching_transactions is not None:
        csv_matching = st.session_state.matching_transactions.to_csv(index=False)
        st.download_button(
            "Download Matching Transactions",
            data=csv_matching,
            file_name="matching_transactions.csv",
            mime="text/csv",
        )
    
    

# Run the Streamlit app
if __name__ == "__main__":
    run()
