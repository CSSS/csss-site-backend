from sqlalchemy import Column, DateTime, Integer, String
# from sqlalchemy.orm import relationship

from database import Base


class UserSession(Base):
    __tablename__ = "user_session"

    # note: a primary key is required for every database table
    id = Column(Integer, primary_key=True)

    issue_time = Column(DateTime, nullable=False)
    session_id = Column(String(512), nullable=False)  # the space needed to store 256 bytes in base64
    computing_id = Column(
        String(32), nullable=False
    )  # technically a max of 8 digits https://www.sfu.ca/computing/about/support/tips/sfu-userid.html
    # TODO: link to the user's table entry & remove the computing_id column (it already exists in the User table)


class User(Base):
    # user is a reserved word in postgres
    # see: https://stackoverflow.com/questions/22256124/cannot-create-a-database-table-named-user-in-postgresql
    __tablename__ = "site_user"

    # note: a primary key is required for every database table
    id = Column(Integer, primary_key=True)

    # TODO: (#13) add two new columns for storing the initial date & last date logged in.
    # When running the migration, you'll want to decide on some random date to be the default for users who've logged
    # before but haven't

    computing_id = Column(
        String(32), nullable=False
    )  # technically a max of 8 digits https://www.sfu.ca/computing/about/support/tips/sfu-userid.html
