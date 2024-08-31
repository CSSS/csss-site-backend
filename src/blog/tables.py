from constants import COMPUTING_ID_LEN
from database import Base
from officers import models
from sqlalchemy import Column, DateTime, ForeignKey, String, Text


# blog table
class BlogPosts(Base):
    # table name
    __tablename__ = "blog_posts"

    # title of post ( meant to be an unique key but for simplicity,
    # using already defined primay_key )
    title = Column(String(128), primary_key=True, nullable=False)

    # computing id
    # TODO: add foreign key
    computing_id = Column(String(COMPUTING_ID_LEN),
        ForeignKey("officer_info.computing_id"),
        nullable=False)

    # dates of creation and last edit
    date_created = Column(DateTime, nullable=False)
    last_edited = Column(DateTime, nullable=False)

    # storing the html content
    html_content = Column(Text, nullable=False)

    # tags for the respective post
    # TODO: consider implementing limits for tag size and count
    post_tags = Column(String(128))
