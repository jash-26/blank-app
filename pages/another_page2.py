import pandas as pd
import streamlit as st

def run():
    st.title("Amazon Sales Report Processor")

    # File uploaders
    fulfillment_file = st.file_uploader("Upload Fulfillment Report:", type=["csv"])
    combined_transactions_file = st.file_uploader("Upload Combined Transactions Report:", type=["csv"])

    if st.button("Process Reports"):
        if not fulfillment_file or not combined_transactions_file:
            st.error("Please upload both the fulfillment and combined transactions reports.")
            return

        try:
            # Load data
            fulfillment_df = pd.read_csv(fulfillment_file)
            combined_transactions_df = pd.read_csv(combined_transactions_file)

            # Clean and debug column names
            fulfillment_df.columns = fulfillment_df.columns.str.strip()
            combined_transactions_df.columns = combined_transactions_df.columns.str.strip()

            st.write("Fulfillment Report Columns:", fulfillment_df.columns)
            st.write("Combined Transactions Report Columns:", combined_transactions_df.columns)

            # Ensure the required columns exist
            if 'amazon-order-id' not in fulfillment_df.columns or 'order id' not in combined_transactions_df.columns:
                st.error("Required columns not found in the uploaded files. Check the column names.")
                return

            # Filter matching and non-matching transactions
            matching_transactions = combined_transactions_df[
                combined_transactions_df['order id'].isin(fulfillment_df['amazon-order-id'])
            ]
            non_matching_transactions = combined_transactions_df[
                ~combined_transactions_df['order id'].isin(fulfillment_df['amazon-order-id'])
            ]

            # Display results
            st.write("Matching Transactions", matching_transactions)
            st.write("Non-Matching Transactions", non_matching_transactions)

            # Provide download links
            csv_matching = matching_transactions.to_csv(index=False)
            csv_non_matching = non_matching_transactions.to_csv(index=False)

            st.download_button(
                label="Download Matching Transactions",
                data=csv_matching,
                file_name="matching_transactions.csv",
                mime="text/csv"
            )
            st.download_button(
                label="Download Non-Matching Transactions",
                data=csv_non_matching,
                file_name="non_matching_transactions.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error(f"An error occurred while processing the reports: {e}")

if __name__ == "__main__":
    run()
