from datetime import date, datetime

from data.semesters import current_semester, current_semester_start, step_semesters


def test_semesters():
    start1 = current_semester_start(date(year=2022, month=11, day=1))
    start2 = current_semester_start(date(year=1022, month=7, day=30))
    start3 = current_semester_start(date(year=2322, month=1, day=12))

    assert start1.month == 9
    assert start2.month == 5
    assert start3.month == 1

    assert step_semesters(start1, -3).month == 9
    assert step_semesters(start1, -3).year == start1.year - 1

    assert step_semesters(start1, -2).month == 1
    assert step_semesters(start1, -2).year == start1.year

    assert step_semesters(start1, -1).month == 5
    assert step_semesters(start1, -1).year == start1.year

    assert step_semesters(start1, 0).month == 9
    assert step_semesters(start1, 0).year == start1.year

    assert step_semesters(start1, 1).month == 1
    assert step_semesters(start1, 1).year == start1.year + 1

    assert step_semesters(start1, 2).month == 5
    assert step_semesters(start1, 2).year == start1.year + 1

    assert step_semesters(start1, 3).month == 9
    assert step_semesters(start1, 3).year == start1.year + 1

    assert step_semesters(start3, -4).month == 9
    assert step_semesters(start3, -4).year == start3.year - 2

    assert str(current_semester(start1)) == "fall"
