import asyncio
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import asyncpg
import sqlalchemy

sys.path.append(str(Path(__file__).parent.parent.resolve()))

from auth.crud import site_user_exists
from auth.tables import SiteUserDB
from data import semesters
from database import SQLALCHEMY_TEST_DATABASE_URL, DatabaseSessionManager
from officers.constants import OfficerPosition
from officers.types import OfficerInfoDB, OfficerTermDB

# This loads officer data from the https://github.com/CSSS/csss-site database into the provided database

DB_PASSWORD = os.environ.get("DB_PASSWORD")
# NOTE: pass either SQLALCHEMY_DATABASE_URL or SQLALCHEMY_TEST_DATABASE_URL
DB_TARGET = os.environ.get("DB_TARGET")


async def main():
    conn = await asyncpg.connect(
        user="postgres",
        password=DB_PASSWORD,
        database="postgres",
        host="sfucsss.org",  # NOTE: this should point to the old sfucsss.org server (made initially by jace)
        port=5432,
    )

    # officer data in order of oldest term first
    officer_data = await conn.fetch(
        """
        SELECT *
        FROM about_officer
        ORDER BY elected_term_id ASC
        """
    )
    print(len(officer_data))

    officer_956 = next(officer for officer in officer_data if officer["id"] == 956)

    def get_key(officer):
        if officer["id"] == 966:
            # something weird happened w/ the start date which caused it to not be the same as the other 2.
            # here, we update it to be the same as it used to
            return (officer_956["start_date"], officer["sfu_computing_id"], officer["position_name"])
        else:
            return (officer["start_date"], officer["sfu_computing_id"], officer["position_name"])

    # group by (officer.start_date, officer.sfu_computing_id, officer.position_name)
    unique_terms = {}
    for officer in officer_data:
        key = get_key(officer)
        if key not in unique_terms:
            unique_terms[key] = (officer["id"], 1)
        else:
            # if there is a term with the same start date, position, and computing_id, take only the last instance.
            unique_terms[key] = (officer["id"], unique_terms[key][1] + 1)

    # computing num_semesters
    num_semesters_map = {}
    consolidated_officer_data = [
        officer
        for officer in officer_data
        # include only latest info in a term
        if unique_terms[get_key(officer)][0] == officer["id"]
    ]
    for officer in consolidated_officer_data:
        # add num_semesters
        key = get_key(officer)
        num_semesters_map[key] = unique_terms[key][1]

    # Jace's many terms as sysadmin is a bit unusual, so we want to concatenate it into a single long officer term
    last_term_jace = None
    for officer in consolidated_officer_data:
        if officer["full_name"] == "Jace Manshadi":
            last_term_jace = officer
    num_semesters_jace = sum(
        [
            num_semesters_map[get_key(officer)]
            for officer in consolidated_officer_data
            if officer["full_name"] == "Jace Manshadi"
        ]
    )
    num_semesters_map[
        (last_term_jace["start_date"], last_term_jace["sfu_computing_id"], last_term_jace["position_name"])
    ] = num_semesters_jace

    consolidated_officer_data = [
        officer for officer in consolidated_officer_data if officer["full_name"] != "Jace Manshadi"
    ] + [last_term_jace]
    await conn.close()

    # print("\n\n".join([str(x) for x in consolidated_officer_data[100:]]))

    sessionmanager = DatabaseSessionManager(DB_TARGET, {"echo": False}, check_db=False)
    await DatabaseSessionManager.test_connection(DB_TARGET)
    async with sessionmanager.session() as db_session:
        # NOTE: keep an eye out for bugs with legacy officer position names, as any not in OfficerPosition should be considered inactive
        position_name_map = {
            "SFSS Council Representative": OfficerPosition.SFSS_COUNCIL_REPRESENTATIVE,
            "Frosh Chair": OfficerPosition.FROSH_WEEK_CHAIR,
            "General Election Officer": OfficerPosition.ELECTIONS_OFFICER,
            "First Year Representative": OfficerPosition.FIRST_YEAR_REPRESENTATIVE,
            "Director of Communications": OfficerPosition.DIRECTOR_OF_COMMUNICATIONS,
            "By-Elections Officer": OfficerPosition.ELECTIONS_OFFICER,
            "Director of Education Events": OfficerPosition.DIRECTOR_OF_EDUCATIONAL_EVENTS,
            "Director of Multi-media": OfficerPosition.DIRECTOR_OF_MULTIMEDIA,
            "Systems Administrator": OfficerPosition.SYSTEM_ADMINISTRATOR,
            "Elections Officer": OfficerPosition.ELECTIONS_OFFICER,
            "Executive at Large 1": OfficerPosition.EXECUTIVE_AT_LARGE,
            "Director of Resources": OfficerPosition.DIRECTOR_OF_RESOURCES,
            "Frosh Week Chair": OfficerPosition.FROSH_WEEK_CHAIR,
            "First Year Representative 1": OfficerPosition.FIRST_YEAR_REPRESENTATIVE,
            "First Year Representative 2": OfficerPosition.FIRST_YEAR_REPRESENTATIVE,
            "Executive at Large 2": OfficerPosition.EXECUTIVE_AT_LARGE,
            "Executive at Large": OfficerPosition.EXECUTIVE_AT_LARGE,
            "Director of Archives": OfficerPosition.DIRECTOR_OF_ARCHIVES,
            "By-Election Officer": OfficerPosition.ELECTIONS_OFFICER,
            "co-Frosh Chair 2": OfficerPosition.FROSH_WEEK_CHAIR,
            "Treasurer": OfficerPosition.TREASURER,
            "Assistant Director of Events": OfficerPosition.ASSISTANT_DIRECTOR_OF_EVENTS,
            "Director of Events": OfficerPosition.DIRECTOR_OF_EVENTS,
            "President": OfficerPosition.PRESIDENT,
            "Executive at Large [Surrey]": OfficerPosition.EXECUTIVE_AT_LARGE,
            "Webmaster": OfficerPosition.WEBMASTER,
            "co-Frosh Chair 1": OfficerPosition.FROSH_WEEK_CHAIR,
            "Vice-President": OfficerPosition.VICE_PRESIDENT,
        }

        for officer in consolidated_officer_data:
            print(f"* doing {officer} ...")

            if officer["id"] == 855:
                # some weird position truman had that didn't exist, but is stored in the db?
                continue
            elif officer["id"] == 883:
                # ditto with jasper
                continue

            if not await site_user_exists(db_session, officer["sfu_computing_id"]):
                # if computing_id has not been created as a site_user yet, add them
                db_session.add(
                    SiteUserDB(
                        computing_id=officer["sfu_computing_id"],
                        first_logged_in=datetime.now(UTC),
                        last_logged_in=datetime.now(UTC),
                    )
                )

            # use the most up to date officer info
            # --------------------------------

            new_officer_info = OfficerInfoDB(
                computing_id=officer["sfu_computing_id"],
                legal_name=officer["full_name"],
                phone_number=str(officer["phone_number"]),
                discord_id=officer["discord_id"],
                discord_name=officer["discord_username"],
                discord_nickname=officer["discord_nickname"],
                google_drive_email=officer["gmail"],
                github_username=officer["github_username"],
            )

            existing_officer_info = await db_session.scalar(
                sqlalchemy.select(OfficerInfoDB).where(OfficerInfoDB.computing_id == new_officer_info.computing_id)
            )
            if existing_officer_info is None:
                db_session.add(new_officer_info)
            else:
                await db_session.execute(
                    sqlalchemy.update(OfficerInfoDB)
                    .where(OfficerInfoDB.computing_id == new_officer_info.computing_id)
                    .values(new_officer_info.to_update_dict())
                )

            # now, create an officer term
            # --------------------------------

            corrected_position_name = (
                position_name_map[officer["position_name"]]
                if officer["position_name"] in position_name_map
                else officer["position_name"]
            )
            position_length = OfficerPosition.length_in_semesters(corrected_position_name)
            num_semesters = num_semesters_map[get_key(officer)]

            if position_length is not None:
                if (
                    (officer["start_date"].date() < (date.today() - timedelta(days=365)))
                    and (officer["start_date"].date() > (date.today() - timedelta(days=365 * 5)))
                    and officer["id"] != 867  # sometimes people only run partial terms (elected_term_id=20222)
                    and officer["id"] != 942  # sometimes people only run partial terms
                ):
                    # over the past few years, the semester length should be as expected
                    if not (position_length == num_semesters):
                        print(num_semesters)
                        print(officer["start_date"].date())
                        print(date.today() - timedelta(days=365))
                    assert position_length == num_semesters
                computed_end_date = semesters.step_semesters(
                    semesters.current_semester_start(officer["start_date"]),
                    position_length,
                )
            else:
                computed_end_date = semesters.step_semesters(
                    semesters.current_semester_start(officer["start_date"]),
                    num_semesters,
                )

            new_officer_term = OfficerTermDB(
                computing_id=officer["sfu_computing_id"],
                position=corrected_position_name,
                start_date=officer["start_date"],
                end_date=computed_end_date,
                nickname=None,
                favourite_course_0=officer["course1"],
                favourite_course_1=officer["course2"],
                favourite_pl_0=officer["language1"],
                favourite_pl_1=officer["language2"],
                biography=officer["bio"],
                photo_url=officer["image"],
            )
            db_session.add(new_officer_term)

        # data lgtm!
        await db_session.commit()

    print("successfully loaded data!")


asyncio.run(main())
