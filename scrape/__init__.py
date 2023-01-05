# Module for scraping the job board
__author__ = "Matteo Golin"

# Imports
import json
import time
import csv
from progress.bar import PixelBar
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By

from .job import Job, JobFactory

# Constants
CREDS_FILE = "./config.json"
JOB_POSTINGS = "https://mysuccess.carleton.ca/myAccount/co-op/coopjobs.htm"
CSV_OUTPUT = "./shortlist.csv"


class Driver:

    def __init__(self):
        self.username, self.password = self.load_credentials()
        self.driver = Chrome()
        self.driver.implicitly_wait(4)

    @staticmethod
    def load_credentials() -> tuple[str, str]:

        """Creates basic authentication header for request."""

        with open(CREDS_FILE, 'r') as file:
            credentials = json.load(file)["credentials"]
            username: str = "CUNET\\" + credentials["username"]
            password: str = credentials["password"]

        return username, password

    def login(self, url) -> None:

        """Logs in to the URL, expecting the Carleton SOO Federated Portal."""

        self.driver.get(url)
        self.driver.find_element(By.ID, "userNameInput").send_keys(self.username)
        self.driver.find_element(By.ID, "passwordInput").send_keys(self.password)
        self.driver.find_element(By.ID, "submitButton").click()

    def shortlist(self) -> None:

        """Get the job postings board and enter the shortlist."""

        self.driver.get("https://mysuccess.carleton.ca/myAccount/co-op/coopjobs.htm")
        time.sleep(1.5)

        quick_searches = self.driver.find_elements(By.CSS_SELECTOR, "td.full")
        quick_search_text = [q.text for q in quick_searches]

        if "Shortlist" in quick_search_text:
            quick_searches[quick_search_text.index("Shortlist")].find_element(By.TAG_NAME, "a").click()

    def scrape_jobs(self) -> None:

        """Returns a list of the job postings information on the shortlist."""

        buttons = self.driver.find_elements(By.CSS_SELECTOR, 'a[role="button"]')

        job_links = []
        for button in buttons:
            if button.text not in ["Apply", "New Search"]:
                job_links.append(button)

        # Visit each job page and scrape
        main_tab = self.driver.current_window_handle  # So driver can return
        bar = PixelBar("Scraping Jobs", max=len(job_links))

        with open(CSV_OUTPUT, 'w', encoding="UTF8", newline="") as file:

            writer = csv.writer(file)
            writer.writerow(Job.csv_headers())  # Headers

            for link in job_links:

                # Switch to job posting tab
                link.click()
                self.driver.switch_to.window(self.driver.window_handles[-1])

                # Scrape the job abd write to the CSV
                current_job = JobFactory(self.driver.page_source).make_job()
                writer.writerow(current_job.to_csv_row())

                # Close job posting tab and return to main tab
                self.driver.close()
                self.driver.switch_to.window(main_tab)
                bar.next()

        bar.finish()
