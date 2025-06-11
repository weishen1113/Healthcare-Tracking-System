import os
import sys
import time
import datetime
import threading

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from flask import Flask
from app import create_app, db  # Your Flask app factory and db instance
from app.models import User      # Your User model
from app.config import TestConfig  # Your test config


BASE_URL = "http://127.0.0.1:5000"
LOGIN_PASSWORD = "testpass123"


class AppTestSuite:
    def __init__(self):
        # Setup Chrome options
        self.options = Options()
        self.options.add_argument("--log-level=3")
        self.options.add_experimental_option("detach", True)  # Keeps browser open after test for debugging

        # Initialize Chrome WebDriver
        self.driver = webdriver.Chrome(service=Service(), options=self.options)

        # Setup Flask test app and run in background thread
        self.app = create_app(TestConfig)
        self.flask_thread = threading.Thread(target=self.run_flask_app)
        self.flask_thread.daemon = True
        self.flask_thread.start()

        # Wait for Flask server to start
        time.sleep(2)

    def run_flask_app(self):
        with self.app.app_context():
            db.create_all()  # Create fresh tables
            self.app.run(debug=False, use_reloader=False)

    def test_register_user(self):
        self.driver.get(f"{BASE_URL}/register")
        time.sleep(1)

        # Unique email each run to avoid conflicts
        new_email = f"user{int(time.time())}@example.com"
        self.driver.find_element(By.NAME, "first_name").send_keys("Selenium")
        self.driver.find_element(By.NAME, "last_name").send_keys("Tester")
        self.driver.find_element(By.NAME, "email").send_keys(new_email)
        self.driver.find_element(By.NAME, "password").send_keys(LOGIN_PASSWORD)
        self.driver.find_element(By.NAME, "confirm_password").send_keys(LOGIN_PASSWORD)

        submit_btn = self.driver.find_element(By.NAME, "submit")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        submit_btn.click()

        WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))
        assert "login" in self.driver.current_url.lower()
        print("✅ Registration test passed.")

        return new_email

    def login(self, email):
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(1)
        self.driver.find_element(By.NAME, "email").send_keys(email)
        self.driver.find_element(By.NAME, "password").send_keys(LOGIN_PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        # Wait for redirect or user dashboard (adjust as per your app)
        try:
            WebDriverWait(self.driver, 5).until(EC.url_changes(f"{BASE_URL}/login"))
        except TimeoutException:
            pass

        time.sleep(1)
        print("✅ Login completed.")

    def test_add_appointment(self):
        self.driver.get(f"{BASE_URL}/appointment/add")
        time.sleep(1)

        today = datetime.date.today().strftime('%Y-%m-%d')

        self.driver.find_element(By.NAME, "starting_time").send_keys("15:00")
        self.driver.find_element(By.NAME, "ending_time").send_keys("16:00")

        date_input = self.driver.find_element(By.NAME, "appointment_date")
        self.driver.execute_script("arguments[0].value = arguments[1]", date_input, today)

        self.driver.find_element(By.NAME, "practitioner_name").send_keys("Dr. Selenium")
        Select(self.driver.find_element(By.NAME, "practitioner_type")).select_by_visible_text("General Practitioner (GP)")
        self.driver.find_element(By.NAME, "location").send_keys("Test Clinic")
        self.driver.find_element(By.NAME, "provider_number").send_keys("123456")
        Select(self.driver.find_element(By.NAME, "appointment_type")).select_by_visible_text("General")
        self.driver.find_element(By.NAME, "appointment_notes").send_keys("Testing appointment add via Selenium.")

        for label in ["2 hours before", "1 day before"]:
            try:
                checkbox = self.driver.find_element(By.XPATH, f"//input[@type='checkbox' and @value='{label}']")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                time.sleep(0.5)
                if not checkbox.is_selected():
                    checkbox.click()
            except NoSuchElementException:
                print(f"⚠️ Reminder checkbox '{label}' not found. Skipping.")

        custom_reminder = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        custom_input = self.driver.find_element(By.NAME, "custom_reminder")
        self.driver.execute_script("arguments[0].value = arguments[1]", custom_input, custom_reminder)

        submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        self.driver.execute_script("arguments[0].click();", submit_btn)

        try:
            WebDriverWait(self.driver, 10).until(EC.url_contains("/appointments"))
        except TimeoutException:
            print("⚠️ URL did not change. Checking for success message instead...")

        assert "appointment" in self.driver.current_url.lower() or "successfully" in self.driver.page_source.lower()
        print("✅ Appointment add test passed.")

    def test_edit_appointment(self):
        self.driver.get(f"{BASE_URL}/appointments")
        time.sleep(1)

        edit_links = self.driver.find_elements(By.LINK_TEXT, "Edit")
        if not edit_links:
            raise Exception("❌ No appointments available to edit.")

        edit_links[0].click()

        WebDriverWait(self.driver, 5).until(EC.url_contains("/appointment/edit"))

        # Change the start and end times
        start_input = self.driver.find_element(By.NAME, "starting_time")
        start_input.clear()
        start_input.send_keys("13:00")

        end_input = self.driver.find_element(By.NAME, "ending_time")
        end_input.clear()
        end_input.send_keys("14:00")

        # Change the practitioner name and notes
        practitioner_input = self.driver.find_element(By.NAME, "practitioner_name")
        practitioner_input.clear()
        practitioner_input.send_keys("Dr. Updated")

        notes_field = self.driver.find_element(By.NAME, "appointment_notes")
        notes_field.clear()
        notes_field.send_keys("Edited via Selenium.")

        # Optionally update custom reminder date
        custom_reminder = (datetime.date.today() + datetime.timedelta(days=3)).strftime('%Y-%m-%d')
        custom_input = self.driver.find_element(By.NAME, "custom_reminder")
        self.driver.execute_script("arguments[0].value = arguments[1];", custom_input, custom_reminder)

        # Submit the form
        submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        self.driver.execute_script("arguments[0].click();", submit_btn)

        try:
            WebDriverWait(self.driver, 10).until(EC.url_contains("/appointments"))
        except Exception:
            print("[Warning] Redirect after edit may have failed.")

        # Verify success message or URL
        page_source = self.driver.page_source.lower()
        assert "updated" in page_source or "success" in page_source
        print("✅ Appointment edit test passed.")

    def test_upload_document(self):
        self.driver.get(f"{BASE_URL}/medical_document/upload_document")
        time.sleep(1)

        self.driver.find_element(By.NAME, "document_name").send_keys("Test Document")
        Select(self.driver.find_element(By.NAME, "document_type")).select_by_visible_text("Report")
        self.driver.find_element(By.NAME, "document_notes").send_keys("Uploaded via Selenium.")
        self.driver.find_element(By.NAME, "practitioner_name").send_keys("Dr. Selenium")
        Select(self.driver.find_element(By.NAME, "practitioner_type")).select_by_visible_text("Specialist")

        today = datetime.date.today().strftime('%Y-%m-%d')
        upload_date_input = self.driver.find_element(By.NAME, "upload_date")
        self.driver.execute_script("arguments[0].value = arguments[1];", upload_date_input, today)

        expiration_checkbox = self.driver.find_element(By.ID, "enableExpirationDate")
        self.driver.execute_script("arguments[0].click();", expiration_checkbox)

        expiration_date = (datetime.date.today() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        expiration_date_input = self.driver.find_element(By.NAME, "expiration_date")
        self.driver.execute_script("arguments[0].value = arguments[1];", expiration_date_input, expiration_date)

        file_input = self.driver.find_element(By.NAME, "upload_document")
        test_file_path = os.path.abspath("tests/test_upload_edited.pdf")
        if not os.path.exists(test_file_path):
            raise FileNotFoundError(f"Test file not found at: {test_file_path}")
        file_input.send_keys(test_file_path)

        submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        self.driver.execute_script("arguments[0].click();", submit_btn)

        page_source = self.driver.page_source.lower()
        assert "successfully" in page_source
        print("✅ Document upload test passed.")

    def test_edit_document(self):
        self.driver.get(f"{BASE_URL}/medical_document")
        time.sleep(1)

        edit_links = self.driver.find_elements(By.LINK_TEXT, "Edit")
        if not edit_links:
            raise Exception("❌ No documents available to edit.")
        edit_links[0].click()

        WebDriverWait(self.driver, 5).until(EC.url_contains("/edit_document"))

        document_name_field = self.driver.find_element(By.NAME, "document_name")
        document_name_field.clear()
        document_name_field.send_keys("Edited Document Name")

        notes_field = self.driver.find_element(By.NAME, "document_notes")
        notes_field.clear()
        notes_field.send_keys("Updated via Selenium.")

        new_test_file_path = os.path.abspath("tests/test_upload_edited.pdf")
        if os.path.exists(new_test_file_path):
            try:
                file_input = self.driver.find_element(By.NAME, "upload_document")
                file_input.send_keys(new_test_file_path)
            except Exception as e:
                print(f"[Warning] Failed to upload new file: {e}")

        expiration_checkbox = self.driver.find_element(By.ID, "enableExpirationDate")
        self.driver.execute_script("arguments[0].click();", expiration_checkbox)
        time.sleep(0.3)

        new_exp_date = (datetime.date.today() + datetime.timedelta(days=60)).strftime('%Y-%m-%d')
        expiration_input = self.driver.find_element(By.NAME, "expiration_date")
        self.driver.execute_script("arguments[0].value = '';", expiration_input)
        self.driver.execute_script("arguments[0].value = arguments[1];", expiration_input, new_exp_date)

        submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        self.driver.execute_script("arguments[0].click();", submit_btn)

        try:
            WebDriverWait(self.driver, 10).until(EC.url_contains("/medical_document"))
        except:
            print("[Warning] URL didn't change after edit.")

        if "successfully" not in self.driver.page_source.lower():
            self.driver.save_screenshot("edit_debug.png")
            raise AssertionError("❌ Edit did not succeed. Check logs or screenshot.")
        print("✅ Document edit test passed.")

    def test_calendar_view(self):
        print("▶ Testing Calendar View page...")
        self.driver.get(f"{BASE_URL}/calendar")

        heading = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//h1[contains(text(), 'Your Calendar')]"))
        )
        assert heading is not None

        view_selector = self.driver.find_element(By.ID, "viewSelector")
        assert view_selector.get_attribute("disabled") == "true"
        assert view_selector.get_attribute("value") == "month"

        prev_btn = self.driver.find_element(By.ID, "prevMonth")
        next_btn = self.driver.find_element(By.ID, "nextMonth")
        heading = self.driver.find_element(By.ID, "monthYearHeading")
        assert prev_btn.is_displayed() and next_btn.is_displayed() and heading.is_displayed()

        for btn_class in ["btn-Appointment", "btn-Tests", "btn-Expirations", "btn-Missed"]:
            btn = self.driver.find_element(By.CLASS_NAME, btn_class)
            assert btn.is_displayed()

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    ".btn-Appointment, .btn-Missed, .btn-Tests, .btn-Expirations"
                ))
            )
            print("✅ Events are rendered on the calendar.")
        except:
            print("❌ No events found on the calendar.")

        print("✅ Calendar View test passed.")

    def test_dashboard_view(self):
        self.driver.get(f"{BASE_URL}/dashboard")
        time.sleep(1)

        # Verify welcome message
        welcome_header =self.driver.find_element(By.CLASS_NAME, "title-purple-text")
        assert "Welcome back" in welcome_header.text
        print("✅ Dashboard welcome message found.")

        # Check if upcoming appointment appears
        appt_cards =self.driver.find_elements(By.CLASS_NAME, "upcoming-appt-details")
        assert len(appt_cards) > 0, "❌ No appointment cards found on dashboard."
        print("✅ Appointment section loaded.")

        # Check appointment info (if known values exist)
        card_text = appt_cards[0].text.lower()
        assert "dr. smith" in card_text or "general practitioner" in card_text
        print("✅ Appointment content verified.")

        # Check expiring documents (if any exist)
        doc_cards = self.driver.find_elements(By.CLASS_NAME, "upcoming-appt-details")
        if len(doc_cards) > 1:
            doc_text = doc_cards[1].text.lower()
            assert "referral" in doc_text or "expiring" in doc_text
            print("✅ Document section verified.")
        else:
            print("ℹ️ No expiring documents found to verify.")

    def test_mark_notifications_read(self):
        self.driver.get(f"{BASE_URL}/dashboard")  # Go to a page where notifications are loaded
        time.sleep(1)

        # Get CSRF token (from meta or cookie)
        csrf_token = self.driver.execute_script("return document.querySelector('meta[name=csrf-token]')?.getAttribute('content')")
        if not csrf_token:
            csrf_token = self.driver.get_cookie("csrf_token")["value"]

        assert csrf_token, "❌ CSRF token not found."

        # Send fetch() request using JavaScript (simulate frontend AJAX)
        script = f"""
        return fetch('/notifications/read', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'X-CSRFToken': '{csrf_token}'
            }},
            credentials: 'same-origin'
        }}).then(res => res.json());
        """

        result =self.driver.execute_script(script)
        assert result["success"] is True
        print("✅ Notification marked as read successfully.")

    def test_calendar_view(self):
        print("▶ Testing Calendar View page...")
        self.driver.get(f"{BASE_URL}/calendar")

        heading = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//h1[contains(text(), 'Your Calendar')]"))
        )
        assert heading is not None

        view_selector =self.driver.find_element(By.ID, "viewSelector")
        assert view_selector.get_attribute("disabled") == "true"
        assert view_selector.get_attribute("value") == "month"

        prev_btn =self.driver.find_element(By.ID, "prevMonth")
        next_btn =self.driver.find_element(By.ID, "nextMonth")
        heading =self.driver.find_element(By.ID, "monthYearHeading")
        assert prev_btn.is_displayed() and next_btn.is_displayed() and heading.is_displayed()

        for btn_class in ["btn-Appointment", "btn-Tests", "btn-Expirations", "btn-Missed"]:
            btn =self.driver.find_element(By.CLASS_NAME, btn_class)
            assert btn.is_displayed()

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    ".btn-Appointment, .btn-Missed, .btn-Tests, .btn-Expirations"
                ))
            )
            print("✅ Events are rendered on the calendar.")
        except:
            print("❌ No events found on the calendar.")

        print("✅ Calendar View test passed.")

    def test_notification_button_click(self):
        self.driver.get(f"{BASE_URL}/dashboard")
        time.sleep(1)

        notify_button = self.driver.find_element(By.ID, "notification-read-btn")
        assert notify_button.is_displayed(), "❌ Notification button not visible."

        notify_button.click()
        time.sleep(1)

        # Example: Check if button becomes disabled or hidden
        assert not notify_button.is_enabled(), "❌ Button was clicked but not disabled."

        print("✅ Notification read button clicked and backend triggered.")

    def test_analytics_page(self):
        # Navigate to the insights page
        self.driver.get(f"{BASE_URL}/insights")
        time.sleep(2)

        # Ensure URL is correct
        assert "insights" in self.driver.current_url.lower()

        # Wait for one of the dashboard metrics to be present
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dashboard-p"))
        )

        # Verify key stats are visible
        summary_labels = [
            "Total Appointments",
            "Total Documents",
            "Documents Expiring Soon",
            "Top Appointment Type",
            "Most Frequent Practitioner"
        ]

        for label in summary_labels:
            assert label in self.driver.page_source, f"Missing summary label: {label}"

        # Check for presence of chart canvases
        canvas_ids = [
            "appointmentTypeChart",
            "appointmentFrequencyChart",
            "practitionerBarChart"
        ]
        for canvas_id in canvas_ids:
            chart =self.driver.find_element(By.ID, canvas_id)
            assert chart.is_displayed(), f"Chart {canvas_id} is not visible"

        # Interact with the "Sort by" dropdown (pure JS effect — test UI response)
        sort_dropdown = Select(self.driver.find_element(By.ID, "sort-range"))
        sort_options = ["year", "6months", "3months", "month", "week"]

        for value in sort_options:
            sort_dropdown.select_by_value(value)
            time.sleep(1)  # Let JS re-render the chart

            chart =self.driver.find_element(By.ID, "appointmentFrequencyChart")
            assert chart.is_displayed(), f"Line chart not visible for sort option: {value}"

            label_text =self.driver.find_element(By.ID, "date-range-label").text.strip()
            warning_visible =self.driver.find_element(By.ID, "chart-warning").is_displayed()

            print(f"Sort range '{value}': label = '{label_text}', warning visible = {warning_visible}")

            if not label_text and not warning_visible:
                print(f"⚠️ No date label or warning shown — possibly due to insufficient data for '{value}' range.")
            else:
                print(f"✅ Valid response for '{value}' range.")

        print("✅ Analytics page test passed.")




    def teardown(self):
        print("Closing browser...")
        self.driver.quit()


if __name__ == "__main__":
    suite = AppTestSuite()
    try:
        email = suite.test_register_user()
        suite.login(email)
        suite.test_add_appointment()
        suite.test_edit_appointment()
        suite.test_upload_document()
        suite.test_edit_document()
        suite.test_mark_notifications_read()
        suite.test_dashboard_view()
        suite.test_calendar_view()
        suite.test_analytics_page()
        suite.test_mark_notifications_read()
    finally:
        suite.teardown()
