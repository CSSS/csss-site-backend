from datetime import date
from enum import Enum
from typing import assert_never


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
            assert_never()


def step_semesters(semester_start_date: date, num_semesters: int) -> date:
    """
    step forwards or backwards in time some number of semesters. Translates the date.
    """
    current = current_semester(semester_start_date)
    new_semester = Semester((num_semesters + current.value) % 3)
    new_year = semester_start_date.year + (num_semesters + current.value) // 3
    return get_semester_start(new_year, new_semester)


def current_semester_start(the_date: date) -> date:
    if the_date.month >= 9:
        return date(year=the_date.year, month=9, day=1)
    elif the_date.month >= 5:
        return date(year=the_date.year, month=5, day=1)
    elif the_date.month >= 1:
        return date(year=the_date.year, month=1, day=1)


def current_semester(the_date: date) -> Semester:
    if the_date.month >= 9:
        return Semester.Fall
    elif the_date.month >= 5:
        return Semester.Summer
    elif the_date.month >= 1:
        return Semester.Spring
    else:
        # TODO: apparently static typecheckers exist in python!?
        assert_never()


def get_semester_start(year: int, semester: Semester):
    match semester:
        case Semester.Fall:
            return date(year, month=9, day=1)
        case Semester.Summer:
            return date(year, month=5, day=1)
        case Semester.Spring:
            return date(year, month=1, day=1)
