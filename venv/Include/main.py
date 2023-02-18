from pyngrok import ngrok

from flask import render_template, url_for
from flask import Flask
from flask import g
from flask import request, redirect, flash

from datetime import datetime
import os
import time

import pandas as pd
import math
import statistics

app = Flask(__name__)
ngrok.set_auth_token("282Ami4SOEgAdCoQ39M0Uj2NWqz_2689qKfQNXscuXnqPrrC")
port = 5000
# Open a ngrok tunnel to the HTTP server
public_url = ngrok.connect(port).public_url
print(" * ngrok tunnel \"{}\" -> \"http://127.0.0.1:{}\"".format(public_url, port))
#run_with_ngrok(app)

# List of dics that will hold all the data got to do with the cigarettes
cig_products = []

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def upload_file():
    uploaded_files = request.files.getlist('files')

    # First File will be Sales, second will be Product Listing
    now = datetime.now()
    new_filename = now.strftime("%d-%m-%Y_%H-%M")

    sales_file_name = "sales " + new_filename + ".csv"
    stock_file_name = "stock " + new_filename + ".csv"

    for file in uploaded_files:
        if file.filename == "sales.csv":
            file.filename = sales_file_name
            file.save("./File_Uploads/"+file.filename)
        if file.filename == "stock.csv":
            file.filename = stock_file_name
            file.save("./File_Uploads/" + file.filename)
        else:
            pass

    # Get other form data such as order type and how many weeks of sales are being uploaded
    order_Type = request.form.get('orderType')
    weeks_Of_Sales = request.form.get('weeksOfSales')


    cig_products.clear()
    getCigarettes(sales_file_name, stock_file_name, order_Type, weeks_Of_Sales)

    return render_template("cigaretteTable.html", cig_products = cig_products)


# Args 1 is sales, args 2 is stock file names
def getCigarettes(sales_file_name, stock_file_name, order_Type, weeks_Of_Sales):
    # Adding the Sales Number to the cig_products dictionary for each product within the cig_products list
    # by reading the sales CSV file using pandas and extracting the barcode(ProductUOM2) and the sales number (Textbox51) Columns
    columns_to_extract = ["ProductCategory", "ProductName", "Textbox51", "ProductUOM2"]
    sales_dataframe = pd.read_csv("./File_Uploads/"+sales_file_name, usecols=columns_to_extract)
    sales_dataframe_length = len(sales_dataframe.index)

    for product in range(sales_dataframe_length):
        if sales_dataframe['ProductCategory'][product] == 'CIGARETTES' or sales_dataframe['ProductCategory'][
            product] == 'TOBACCO':
            # if it's the blas cards, don't add to list
            if sales_dataframe['ProductUOM2'][product] == 4030700134282:
                continue
            cig_products.append({
                'Category': sales_dataframe['ProductCategory'][product],
                'ProductName': sales_dataframe['ProductName'][product],
                'BarCode': math.trunc(sales_dataframe['ProductUOM2'][product]),
                'Sales': math.trunc(sales_dataframe['Textbox51'][product]),
                'AverageSales': 0,
                'CurrentStock': 0,
                'CaseSize': 0,
                'CasesToOrder': 0,
                'Supplier': '',
                'CaseCost': 0,
                'salesFileOne': sales_dataframe['Textbox51'][product],
                'salesFileTwo': 0,
                'salesFileThree': 0
            })

        # Finally adding the current stock, case size, supplier, and case cost to the main cig_products list
        columns_to_extract2 = ["ProductCategory", "ProductName", "StockLevel1", "ProductId", "CaseSize1", "LastDocketSupplier", "CaseCost1"]
        stock_dataframe = pd.read_csv("./File_Uploads/"+stock_file_name, usecols=columns_to_extract2)
        stock_dataframe_length = len(stock_dataframe.index)

        # Adding products data to the main products list from the sales CSV file
        for product2 in range(len(cig_products)):
            for stock_product in range(stock_dataframe_length):
                if stock_dataframe['ProductId'][stock_product] == cig_products[product2]['BarCode']:
                    cig_products[product2]['CurrentStock'] = stock_dataframe['StockLevel1'][stock_product]
                    cig_products[product2]['CaseSize'] = stock_dataframe['CaseSize1'][stock_product]
                    cig_products[product2]['Supplier'] = stock_dataframe['LastDocketSupplier'][stock_product]
                    cig_products[product2]['CaseCost'] = stock_dataframe['CaseCost1'][stock_product]


    # Sort cig_products based on sales from least to most into 3 groups
    sorted_cig_products = sorted(cig_products, key=lambda k: k['Sales'])
    no_groups = 3
    group_size = math.ceil(len(sorted_cig_products) / no_groups)

    # This list will have 3 subset lists 0-2
    cig_products_grouped = []

    # Group sorted_cig_products list into 3 seprate lists based on order
    for i in range(0, no_groups):
        cig_products_grouped.append(sorted_cig_products[0:(int(group_size))])
        sorted_cig_products = sorted_cig_products[int(group_size):]

    best_sellers = cig_products_grouped[2]
    avg_sellers = cig_products_grouped[1]
    least_sellers = cig_products_grouped[0]

    # Determine best seller stock
    for best_seller_product in range(len(best_sellers)):
        Cases_To_Order = 0
        currentStock_Placeholder = best_sellers[best_seller_product]['CurrentStock']

        while (((currentStock_Placeholder - best_sellers[best_seller_product]['Sales']) / best_sellers[best_seller_product]['Sales']) * 100 < 23):
            Cases_To_Order += 1
            currentStock_Placeholder += best_sellers[best_seller_product]['CaseSize']
        for product in range(len(cig_products)):
            if cig_products[product]['BarCode'] == best_sellers[best_seller_product]['BarCode']:
                cig_products[product]['CasesToOrder'] = Cases_To_Order

    # Determine average seller stock
    for avg_sellers_product in range(len(avg_sellers)):
        Cases_To_Order = 0
        currentStock_Placeholder = avg_sellers[avg_sellers_product]['CurrentStock']

        while (((currentStock_Placeholder - avg_sellers[avg_sellers_product]['Sales']) / avg_sellers[avg_sellers_product]['Sales']) * 100 < 17):
            Cases_To_Order += 1
            currentStock_Placeholder += avg_sellers[avg_sellers_product]['CaseSize']
        for product in range(len(cig_products)):
            if cig_products[product]['BarCode'] == avg_sellers[avg_sellers_product]['BarCode']:
                cig_products[product]['CasesToOrder'] = Cases_To_Order

    # Determine least seller stock
    for least_sellers_product in range(len(least_sellers)):
        Cases_To_Order = 0
        currentStock_Placeholder = least_sellers[least_sellers_product]['CurrentStock']

        while (((currentStock_Placeholder - least_sellers[least_sellers_product]['Sales']) / least_sellers[least_sellers_product]['Sales']) * 100 < 6):
            Cases_To_Order += 1
            currentStock_Placeholder += least_sellers[least_sellers_product]['CaseSize']
        for product in range(len(cig_products)):
            if cig_products[product]['BarCode'] == least_sellers[least_sellers_product]['BarCode']:
                cig_products[product]['CasesToOrder'] = Cases_To_Order

if __name__ == '__main__':
    app.run()
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER