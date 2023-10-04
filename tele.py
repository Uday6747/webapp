import mysql.connector
from tabulate import tabulate
from mysql.connector import Error
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import requests
import asyncio
import time
from telegram import Bot, Update
from telegram.ext import Updater, Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext

# Your MySQL and other configurations
# ...
# MySQL conn settings
mysql_host = "bd1v22ah0w7d16zc6bfk-mysql.services.clever-cloud.com"
mysql_user = "usbc9fjuh5g4zyfq"
mysql_password = "LPaXas79XrZzRNjkzGZC"
mysql_database = "bd1v22ah0w7d16zc6bfk"

# Chrome WebDriver options
chrome_options = Options()
chrome_options.add_argument("--headless")

# Student login credentials

# Initialize the Telegram bot
telegram_bot_token = "6541876774:AAETncZQD6Tq9hrkt0rF_RM2upnSyaq6sa8"
bot = Bot(token=telegram_bot_token)

global cursor
global conn
global first_time_insert_permanent
global driver

# Conversation states
USERNAME, PASSWORD, TRACKING = range(3)

# Global variables to store user input
user_data = {}
session = requests.Session()

    # Initialize the Chrome WebDriver
driver = webdriver.Chrome(options=chrome_options)
first_time_insert_permanent = True
# Initialize the MySQL conn
def sqlconn():
    try:
        conn = mysql.connector.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database
        )
        cursor = conn.cursor()

        # Create the permanent and temporary tables if they don't exist
        create_permanent_table_query = """
        CREATE TABLE IF NOT EXISTS permanent_attendance_data (
            Sl_No VARCHAR(255),
            Subject VARCHAR(255) PRIMARY KEY,
            Held VARCHAR(255),
            Attend VARCHAR(255),
            Percent VARCHAR(255)
        );
        """

        create_temporary_table_query = """
        CREATE TABLE IF NOT EXISTS temporary_attendance_data (
            Sl_No VARCHAR(255),
            Subject VARCHAR(255) PRIMARY KEY,
            Held VARCHAR(255),
            Attend VARCHAR(255),
            Percent VARCHAR(255)
        );
        """
        # Create the attendance_log table if it doesn't exist
        create_log_table_query = """
        CREATE TABLE IF NOT EXISTS attendance_log (
            Log_ID INT AUTO_INCREMENT PRIMARY KEY,
            Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Subject VARCHAR(255),
            New_Held VARCHAR(255),
            New_Attend VARCHAR(255),
            New_Percent VARCHAR(255)
        );
        """
        cursor.execute(create_log_table_query)
        conn.commit()

        cursor.execute(create_permanent_table_query)
        cursor.execute(create_temporary_table_query)
        conn.commit()
    except Error as e:
        print(f"Error connecting to MySQL: {e}")

def webpage():
    login_url = 'http://103.138.0.69/ecap/'
    driver.get(login_url)
    username_field = driver.find_element(By.ID, 'txtId2')
    password_field = driver.find_element(By.ID, 'txtPwd2')
    username_field.send_keys(user_data['username'])  # Use the stored username
    password_field.send_keys(user_data['password']) 
    login_button = driver.find_element(By.ID, 'imgBtn2')
    login_button.click()

    # Step 2: Navigate to the attendance page
    attendance_link_text = 'ATTENDANCE'  # Replace with the correct link text
    driver.find_element(By.LINK_TEXT, attendance_link_text).click()
    driver.switch_to.frame(0)

async def start(update, context):
    user_data.clear()
    await update.message.reply_text("Welcome to the attendance tracking bot! Please enter your username:")
    sqlconn()
    return USERNAME

async def username(update, context):
    user_data['username'] = update.message.text
    print("Username:", user_data['username'])
    await update.message.reply_text("Great! Now enter your password:")
    return PASSWORD

async def password(update, context):
    user_data['password'] = update.message.text
    print("Password:", user_data['password'])
    await update.message.reply_text("Thanks! You are now logged in. Use /track to start tracking attendance.")
    return ConversationHandler.END

async def track(update, context):
    await update.message.reply_text("Tracking attendance...")
    first_time_insert_permanent = True
    webpage()
    # Initialize a session for making HTTP requests
    conn = mysql.connector.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database
        )
    cursor = conn.cursor()
        
    while True:
        if "stop tracking" in update.message.text.lower():  # Check for a specific message
            await update.message.reply_text("Tracking stopped.")
            return ConversationHandler.END  # End the conversation and stop tracking
        # Step 3: Select the desired radio button and click the "Show" button
        radio_button = driver.find_element(By.ID, "radTillNow")
        radio_button.click()
        show_button = driver.find_element(By.ID, 'btnShow')
        show_button.click()

        # Delete temporary data from the table
        delete_temporary_data_query = "DELETE FROM temporary_attendance_data"
        cursor.execute(delete_temporary_data_query)
        conn.commit()

        # Step 4: Extract and process table data
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        table = soup.find('table', class_='cellBorder')

        if table:
            rows = table.find_all('tr', class_='reportData1')
            table_class = table.find_all('tr', class_='reportHeading2WithBackground')

            if table_class:
                table_heading = table_class[0]
                heading_columns = table_heading.find_all('td')
                heading = [col.text.strip() for col in heading_columns]

            for row in rows:
                columns = row.find_all('td')
                data = [column.text.strip() for column in columns]

                if data:
                    data_tuple = tuple(data)
                    insert_data_query = """
                    INSERT INTO temporary_attendance_data (Sl_No, Subject, Held, Attend, Percent)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_data_query, data_tuple)
                    conn.commit()

            if table_class:
                table_heading = table_class[-1]
                heading_columns = table_heading.find_all('td')
                result = [col.text.strip() for col in heading_columns]
                total_tuple = tuple(result)

                if True:
                    insert_total_query = """
                    INSERT INTO temporary_attendance_data (Sl_No, Subject, Held, Attend, Percent)
                    VALUES (8, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_total_query, total_tuple)
                    conn.commit()

            if first_time_insert_permanent:
                # Fetch and insert data into the permanent table here (outside the loop)
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                table = soup.find('table', class_='cellBorder')

                if table:
                    rows = table.find_all('tr', class_='reportData1')
                    table_class = table.find_all('tr', class_='reportHeading2WithBackground')

                    if table_class:
                        table_heading = table_class[0]
                        heading_columns = table_heading.find_all('td')
                        heading = [col.text.strip() for col in heading_columns]

                for row in rows:
                    columns = row.find_all('td')
                    data = [column.text.strip() for column in columns]

                    if data:
                        data_tuple = tuple(data)
                        insert_data_query = """
                        INSERT INTO permanent_attendance_data (Sl_No, Subject, Held, Attend, Percent)
                        VALUES (%s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_data_query, data_tuple)
                        conn.commit()

                if table_class:
                    table_heading = table_class[-1]
                    heading_columns = table_heading.find_all('td')
                    result = [col.text.strip() for col in heading_columns]
                    total_tuple = tuple(result)

                    if True:
                        insert_total_query = """
                        INSERT INTO permanent_attendance_data (Sl_No, Subject, Held, Attend, Percent)
                        VALUES (8, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_total_query, total_tuple)
                        conn.commit()

                first_time_insert_permanent = False

            # Compare temporary data with permanent data
            compare_query = """
            SELECT t.Subject, t.Held, t.Attend, t.Percent
            FROM temporary_attendance_data t
            LEFT JOIN permanent_attendance_data p ON t.Subject = p.Subject
            WHERE p.Subject IS NULL OR t.Held != p.Held OR t.Attend != p.Attend OR t.Percent != p.Percent
            """
            cursor.execute(compare_query)
            changes = cursor.fetchall()

            if changes:
                message = "Attendance changes:\n"
                for change in changes:
                    subject, held, attend, percent = change
                    message += f"Subject: {subject}, Held: {held}, Attend: {attend}, Percent: {percent}\n"


                # Update the permanent data table with the temporary data
                update_query = """
                REPLACE INTO permanent_attendance_data (Subject, Held, Attend, Percent)
                SELECT Subject, Held, Attend, Percent FROM temporary_attendance_data
                """
                cursor.execute(update_query)
                conn.commit()
                for change in changes:
                    print(change)
                    subject, perm_held, perm_attend, perm_percent = change
                    
                    # Insert the change into the attendance_log table
                    log_insert_query = """
                    INSERT INTO attendance_log (Subject, New_Held, New_Attend, New_Percent)
                    VALUES (%s, %s, %s, %s)
                    """
                    log_data = (subject, perm_held, perm_attend,perm_percent)
                    cursor.execute(log_insert_query, log_data)
                    conn.commit()

            # Delete data from the temporary table
            delete_temporary_data_query = "DELETE FROM temporary_attendance_data"
            cursor.execute(delete_temporary_data_query)
            conn.commit()

        print("Hello")
        # Wait for 20 seconds before retrieving data again
        time.sleep(20)

    await update.message.reply_text("Tracking stopped. Use /log to view the log.")
    return ConversationHandler.END

async def log(update, context):
    # Fetch and display the attendance log
    # ...
    global driver
    await update.message.reply_text("Attendance log:")
    # Display the log here
    
    conn = mysql.connector.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database
        )
    cursor = conn.cursor()
    # Connect to the MySQL database
    try:
        if conn.is_connected():
            cursor = conn.cursor()

            # Replace 'your_table_name' with the name of your SQL table
            table_name = 'attendance_log'

            # Execute a SELECT query to fetch data from the table
            query = f'SELECT * FROM {table_name}'
            cursor.execute(query)

            # Fetch all rows from the result
            rows = cursor.fetchall()

            # Get column names
            column_names = [desc[0] for desc in cursor.description]

            # Convert SQL data to a list of tuples
            data = [tuple(row) for row in rows]

            # Convert the data to a table string using tabulate
            table_string = tabulate([column_names] + data, tablefmt="grid")

            # Send the table string as a reply
            await update.message.reply_text(table_string)

    except mysql.connector.Error as e:
        print(f"Error: {e}")

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL conn is closed")

async def stop(update, context):
    await update.message.reply_text("Tracking stopped.")
    return ConversationHandler.END


if __name__ == '__main__':
    print("Starting Bot .....")
    loop = asyncio.get_event_loop()
    app = Application.builder().token(telegram_bot_token).build()
    app.add_handler(CommandHandler('track', track))
    app.add_handler(CommandHandler('log', log))
    app.add_handler(CommandHandler('stop', stop))
    # Create a ConversationHandler and add it to the application
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password)],
            TRACKING: [CommandHandler('track', track)]
        },
        fallbacks=[]
    )
    
    app.add_handler(conv_handler)
    # Start polling for Telegram updates
    app.run_polling(poll_interval=1)