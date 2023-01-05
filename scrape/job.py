# Job data class for representing postings
__author__ = "Matteo Golin"

# Imports
from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag
import datetime as dt

# Constants
WFH_KEYWORDS: list[str] = ["work from home", "virtual work", "remote work", "hybrid work", "hybrid"]
DEADLINE_FORMAT = "%B %d @%I:%M%p"
FIELD_TITLES = [
    "position title",
    "number of positions",
    "location of work",
    "indicate working arrangements",
    "working from home",
    "duration",
    "salary",
    "work term start",
    "work term end",
    "job description",
    "security screening",
]


# Class
@dataclass
class Job:
    title: str
    company: str
    division: str
    deadline: dt.datetime
    positions: int
    location: str
    wfh: bool
    working_arrangements: str
    duration_in_months: int
    salary: float | None
    hours_per_week: float | None
    description: str
    security_screening: bool

    @property
    def duration_in_days(self) -> dt.timedelta:
        return self.term[1] - self.term[0]

    @property
    def earnings(self):

        """Returns the total money that would be made during the work term."""

        # 4 weeks per month
        return self.salary * self.hours_per_week * 4 * self.duration_in_months

    def __repr__(self):

        if not self.salary:
            salary_repr = "Salary: Not available."
        else:
            salary_repr = f"Total earnings: ${self.earnings:,.2f} at ${self.salary:.2f}/hr"

        if not self.hours_per_week:
            hour_repr = "Hours Weekly: Not available."
        else:
            hour_repr = f"Hours Weekly: {self.hours_per_week}"

        spacer = "-" * 50 + "\n"

        return f"{spacer}{self.title}\n" \
               f"{self.company}, {self.location}\n{spacer}" \
               f"APPLICATION DEADLINE: {self.deadline.strftime(DEADLINE_FORMAT)}\n" \
               f"{salary_repr}\n" \
               f"{hour_repr}\n" \
               f"Remote Work: {'Yes' if self.wfh else 'No'}"

    @classmethod
    def csv_headers(cls) -> list[str]:

        """Returns a list of formatted property names belonging to the Job class"""

        headers: list[str] = []
        for header in cls.__annotations__.keys():

            if header == "wfh":
                headers.append(header.upper())
            else:
                header = " ".join(header.split("_"))  # No underscores
                headers.append(header.capitalize())

        return headers

    def to_csv_row(self) -> list:
        return list(self.__dict__.values())


# Job factory
class JobFactory:

    def __init__(self, page_source: str):

        self.html = BeautifulSoup(page_source, features="html.parser")
        job_inf, self.app_inf, self.comp_inf = self.__get_tables()

        # Check for missing fields and remove them from list
        self.fields = FIELD_TITLES.copy()
        self.__set_page_fields(job_inf)

        # Only select the side of the table with data
        self.job_inf = job_inf.select('td[width="75%"]')

    def __set_page_fields(self, raw_job_inf: Tag) -> None:

        """Removes the fields not contained by the job posting from the fields list."""

        page_fields = raw_job_inf.select('td[style="width: 25%;"]')
        page_fields = [f.get_text(strip=True).lower() for f in page_fields]
        page_fields = " ".join(page_fields)

        for field in self.fields:
            if field.lower() not in page_fields:
                self.fields.remove(field)

    def __get_tables(self) -> tuple[Tag, Tag, Tag]:
        """
        Returns the three tables containing job information in the order:
        1. Job posting information
        2. Application information
        3. Company information
        """

        tables = self.html.select(".table.table-bordered")

        job_posting_info = tables[1]
        application_info = tables[2]
        company_info = tables[3]

        return job_posting_info, application_info, company_info

    def __get_company_info(self) -> tuple[str, str]:

        """Returns company title and division."""

        info_cells = self.comp_inf.select('td[width="75%"]')

        company = info_cells[1].get_text(strip=True)
        division = info_cells[2].get_text(strip=True)

        return company, division

    def __get_application_deadline(self) -> dt.datetime:

        """Returns the application deadline as a datetime object."""

        # Parse
        raw_deadline = self.app_inf.select("#npPostingApplicationInfoDeadlineDate")[0]
        parsed_deadline = raw_deadline.get_text(strip=True).replace("\n", "")
        parsed_deadline = " ".join(parsed_deadline.split())

        # Convert to datetime
        deadline = dt.datetime.strptime(parsed_deadline, "%B %d, %Y %I:%M %p")
        return deadline

    def __get_salary_hours(self) -> tuple[float | None, float | None]:

        """Returns the salary as a tuple of the pay rate and hours per week."""

        index = self.fields.index(FIELD_TITLES[6])
        parsed_salary = self.job_inf[index].get_text(strip=True).replace("$", "")

        # Convert to floating point numbers
        salary = []
        for word in parsed_salary.split():
            try:
                salary.append(float(word))
            except ValueError:
                continue

        # Found an hourly salary
        if len(salary) == 2 and 0.0 not in salary:

            if salary[0] > 40.0:  # The salary is monthly
                salary[0] /= (4 * salary[1])  # Divide by 4 weeks times the hourly amount

            return salary[0], salary[1]

        # Found no salary
        return None, None

    def __get_working_arrangements(self) -> str:

        """Returns the working arrangements of the position."""

        arrangements_index = self.fields.index(FIELD_TITLES[3])
        arrangements = self.job_inf[arrangements_index].get_text(strip=True)

        if FIELD_TITLES[4] in self.fields:
            wfh_index = self.fields.index(FIELD_TITLES[4])
            wfh_arrangements = self.job_inf[wfh_index].get_text(strip=True)
            return f"{arrangements}. {wfh_arrangements}."

        return f"{arrangements}."

    def __get_duration(self) -> int:

        """Returns the duration of the work term."""

        index = self.fields.index(FIELD_TITLES[5])
        parsed_duration = self.job_inf[index].get_text(strip=True)

        # I only care if the duration is available in a 4-month term
        if "4" in parsed_duration:
            return 4

        # Pick the first duration if there are multiple above 4
        for word in parsed_duration.split():
            try:
                return int(word)
            except ValueError:
                continue

        # No duration
        return 0

    def __get_security_screening(self) -> bool:

        """Returns True if security screening is required for the position."""

        index = self.fields.index(FIELD_TITLES[10])
        screening = self.job_inf[index].get_text(strip=True)

        if "no" in screening.lower() or "other" in screening.lower():
            return False

        return True

    def __verify_wfh(self, description: str, location: str, arrangements: str) -> bool:

        """Returns True if mention of WFH is in any other fields."""

        if "virtual" in location.lower() or FIELD_TITLES[4] in self.fields:
            return True

        # Process text
        description = description.lower()
        arrangements = arrangements.lower()

        for keyword in WFH_KEYWORDS:
            if keyword in description or keyword in arrangements:
                return True

        return False

    def make_job(self) -> Job:

        """Returns the job posting data within the Job class."""

        # Easy scrapes
        # Indexes
        title_index = self.fields.index(FIELD_TITLES[0])
        positions_index = self.fields.index(FIELD_TITLES[1])
        location_index = self.fields.index(FIELD_TITLES[2])
        description_index = self.fields.index(FIELD_TITLES[9])

        # Parsing
        title = self.job_inf[title_index].get_text(strip=True)
        positions = int(self.job_inf[positions_index].get_text(strip=True))
        location = self.job_inf[location_index].get_text(strip=True)
        description = self.job_inf[description_index].get_text(strip=True)

        # Scrapes handled by functions
        arrangements = self.__get_working_arrangements()
        company, division = self.__get_company_info()
        deadline = self.__get_application_deadline()
        salary, hours = self.__get_salary_hours()
        duration = self.__get_duration()
        screening = self.__get_security_screening()

        # Verify work from home that could have been stated outside the designated field
        wfh = self.__verify_wfh(description, location, arrangements)

        return Job(
            title=title,
            company=company,
            division=division,
            deadline=deadline,
            salary=salary,
            hours_per_week=hours,
            location=location,
            positions=positions,
            duration_in_months=duration,
            description=description,
            security_screening=screening,
            wfh=wfh,
            working_arrangements=arrangements,
        )


# Main
def main():

    with open("test.txt", 'r') as file:
        factory = JobFactory(file.read())
        job = factory.make_job()
        print(job)
        print(Job.csv_headers())


if __name__ == '__main__':
    main()
