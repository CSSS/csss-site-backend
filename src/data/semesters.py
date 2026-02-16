from datetime import date
from enum import Enum
from typing import assert_never

JANUARY = 1
MAY = 5
SEPTEMBER = 9


class Semester(Enum):
    """semester numbers are assigned by their order in the year"""

    Fall = 2
    Summer = 1
    Spring = 0

    def __str__(self):
        if self.value == 0:
            return "spring"
        elif self.value == 1:
            return "summer"
        elif self.value == 2:
            return "fall"
        else:
            assert_never(self.value)


def step_semesters(semester_start_date: date, num_semesters: int) -> date:
    """
    step forwards or backwards in time some number of semesters. Translates the date.
    """
    current = current_semester(semester_start_date)
    new_semester = Semester((num_semesters + current.value) % 3)
    new_year = semester_start_date.year + (num_semesters + current.value) // 3
    return get_semester_start(new_year, new_semester)


def current_semester_start(the_date: date) -> date:
    if the_date.month >= SEPTEMBER:
        return date(year=the_date.year, month=SEPTEMBER, day=1)
    elif the_date.month >= MAY:
        return date(year=the_date.year, month=MAY, day=1)
    elif the_date.month >= JANUARY:
        return date(year=the_date.year, month=JANUARY, day=1)
    else:
        raise AssertionError("unreachable")


def current_semester(the_date: date) -> Semester:
    if the_date.month >= SEPTEMBER:
        return Semester.Fall
    elif the_date.month >= MAY:
        return Semester.Summer
    elif the_date.month >= JANUARY:
        return Semester.Spring
    else:
        raise AssertionError("unreachable")


def get_semester_start(year: int, semester: Semester):
    match semester:
        case Semester.Fall:
            return date(year, month=SEPTEMBER, day=1)
        case Semester.Summer:
            return date(year, month=MAY, day=1)
        case Semester.Spring:
            return date(year, month=JANUARY, day=1)
