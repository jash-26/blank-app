import streamlit as st
import pandas as pd
import altair as alt

def run():
    st.title("Amazon Inventory Ledger")

    # File uploader
    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            # Load the uploaded CSV file
            data = pd.read_csv(uploaded_file)

            # Ensure required columns exist
            required_columns = {"ASIN", "Event Type", "Quantity", "MSKU", "Title"}
            if not required_columns.issubset(data.columns):
                st.error(f"Missing required columns: {required_columns - set(data.columns)}")
                return

            # Load the ASIN-to-SKU mapping file
            try:
                mapping_file_path = "mappings/asin_to_sku_mapping.csv"
                asin_to_sku_mapping = pd.read_csv(mapping_file_path, sep="\t")
                
                # Ensure the mapping file has the required columns
                mapping_required_columns = {"ASIN", "Internal_SKU"}
                if not mapping_required_columns.issubset(asin_to_sku_mapping.columns):
                    st.error(f"Mapping file is missing required columns: {mapping_required_columns - set(asin_to_sku_mapping.columns)}")
                    return
            except FileNotFoundError:
                st.error("Mapping file not found. Please ensure the file is available at 'mappings/updated_asin_to_sku_mapping.csv'.")
                return

            # Display the uploaded data
            st.subheader("Uploaded Data")
            st.dataframe(data)

            # User filters
            st.subheader("Filter Options")
            asin_filter = st.multiselect("Select ASIN(s) to filter", data["ASIN"].unique())
            if asin_filter:
                data = data[data["ASIN"].isin(asin_filter)]

            # Process data to get required outputs
            st.subheader("Processed Data")

            # Separate pivot tables for event types
            non_receipt_events = data[data["Event Type"] != "Receipts"]
            non_receipt_pivot = non_receipt_events.pivot_table(
                index="ASIN",
                columns="Event Type",
                values="Quantity",
                aggfunc="sum",
                fill_value=0
            ).reset_index()

            # Summing quantities for non-receipt event types
            non_receipt_pivot["Sum_Quantity_Non_Receipts"] = non_receipt_pivot.drop(columns=["ASIN"]).sum(axis=1)

            # Filtering rows where 'Event Type' is 'Receipts'
            receipts = data[data["Event Type"] == "Receipts"]
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
                non_receipt_pivot
                .merge(sum_receipts, on="ASIN", how="left")
                .merge(msku_data, on="ASIN", how="left")
                .merge(title_data, on="ASIN", how="left")
            )

            # Merge with ASIN-to-SKU mapping
            final_data = final_data.merge(asin_to_sku_mapping, on="ASIN", how="left")

            # Add a verification column to ensure all non-receipt events sum correctly
            final_data["Verified_Non_Receipts_Sum"] = (
                final_data["Sum_Quantity_Non_Receipts"] ==
                final_data.drop(columns=["ASIN", "Sum_Quantity_Non_Receipts", "Sum_Quantity_Receipts", "Related_MSKUs", "Related_Titles", "Internal_SKU"]).sum(axis=1)
            )

            # Display the processed data
            st.dataframe(final_data)

            # Summary statistics
            st.subheader("Summary Statistics")
            st.metric("Total ASINs", final_data["ASIN"].nunique())
            st.metric("Total Non-Receipt Quantity", final_data["Sum_Quantity_Non_Receipts"].sum())
            st.metric("Total Receipt Quantity", final_data["Sum_Quantity_Receipts"].sum())

            # Visualization
            st.subheader("Data Visualization")
            chart = alt.Chart(final_data).mark_bar().encode(
                x="ASIN:N",
                y="Sum_Quantity_Non_Receipts:Q",
                tooltip=["ASIN", "Sum_Quantity_Non_Receipts", "Sum_Quantity_Receipts", "Internal_SKU"]
            ).properties(title="Non-Receipt Quantities by ASIN", width=700, height=400)
            st.altair_chart(chart)

            # Export to Excel
            import io
            from openpyxl import Workbook
            from openpyxl.styles import Font

            def generate_excel(dataframe):
                output = io.BytesIO()
                workbook = Workbook()
                sheet = workbook.active
                sheet.title = "Processed Data"
                for col_num, column_title in enumerate(dataframe.columns, 1):
                    sheet.cell(row=1, column=col_num, value=column_title).font = Font(bold=True)
                for row_num, row_data in enumerate(dataframe.itertuples(index=False), 2):
                    for col_num, value in enumerate(row_data, 1):
                        sheet.cell(row=row_num, column=col_num, value=value)
                workbook.save(output)
                output.seek(0)
                return output

            excel_data = generate_excel(final_data)
            st.download_button(
                label="Download Processed Data as Excel",
                data=excel_data,
                file_name="processed_data_with_sku.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            st.error(f"An error occurred while processing the file: {e}")
    else:
        st.write("Please upload a CSV file to proceed.")

if __name__ == "__main__":
    run()
