import streamlit as st
import pandas as pd

def run():
    # Title
    st.title("ASIN Data Processing App")

    # File uploader
    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            # Load the uploaded CSV file
            data = pd.read_csv(uploaded_file)

            # Display the uploaded data
            st.subheader("Uploaded Data")
            st.dataframe(data)

            # Process data to get required outputs
            st.subheader("Processed Data")

            # Filtering rows where 'Event Type' is not 'Receipts'
            non_receipts = data[data["Event Type"] != "Receipts"]

            # Sum of Quantity for each ASIN (Event Type not 'Receipts')
            sum_non_receipts = non_receipts.groupby("ASIN")["Quantity"].sum().reset_index()
            sum_non_receipts.columns = ["ASIN", "Sum_Quantity_Non_Receipts"]

            # Filtering rows where 'Event Type' is 'Receipts'
            receipts = data[data["Event Type"] == "Receipts"]

            # Sum of Quantity for each ASIN (Event Type is 'Receipts')
            sum_receipts = receipts.groupby("ASIN")["Quantity"].sum().reset_index()
            sum_receipts.columns = ["ASIN", "Sum_Quantity_Receipts"]

            # Get all unique MSKUs for each ASIN
            msku_data = data.groupby("ASIN")["MSKU"].apply(lambda x: ", ".join(x.unique())).reset_index()
            msku_data.columns = ["ASIN", "Related_MSKUs"]

            # Get all unique Titles for each ASIN
            title_data = data.groupby("ASIN")["Title"].apply(lambda x: ", ".join(x.unique())).reset_index()
            title_data.columns = ["ASIN", "Related_Titles"]

            # Merge all results into a single DataFrame
            final_data = (
                sum_non_receipts
                .merge(sum_receipts, on="ASIN", how="left")
                .merge(msku_data, on="ASIN", how="left")
                .merge(title_data, on="ASIN", how="left")
            )

            # Display the processed data
            st.dataframe(final_data)

            # Option to download the processed data
            csv = final_data.to_csv(index=False)
            st.download_button(
                label="Download Processed Data",
                data=csv,
                file_name="processed_data.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"An error occurred while processing the file: {e}")
    else:
        st.write("Please upload a CSV file to proceed.")


if __name__ == "__main__":
    run()
