# Application to analyze shortlisted co-op job postings
__author__ = "Matteo Golin"

# Imports
import chromedriver_autoinstaller
from scrape import Driver, check_for_credentials

# Constants
URL = "https://mysuccess.carleton.ca/Shibboleth.sso/Login?entityID=http://cufed.carleton.ca/adfs/services/trust&target=https://mysuccess.carleton.ca/secure/sso.htm"


# Main
def main():

    # Check for credentials
    check_for_credentials()

    # Ensure up-to-date driver
    chromedriver_autoinstaller.install()

    driver = Driver()
    driver.login(URL)
    driver.shortlist()
    driver.scrape_jobs()


if __name__ == "__main__":
    main()
