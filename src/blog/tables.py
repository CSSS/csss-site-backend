from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, Text

from constants import COMPUTING_ID_LEN
from database import Base


# blog table
class BlogPostsDB(Base):
    # table name
    __tablename__ = "blog_posts"

    __table_args__ = (
        CheckConstraint(
            "computing_id ~ '^[a-z0-9]+$' AND computing_id = lower(computing_id)", name="computing_id_format"
        ),
    )

    # title of post ( meant to be an unique key but for simplicity,
    # using already defined primay_key )
    title = Column(String(128), primary_key=True, nullable=False)

    # computing id
    computing_id = Column(
        String(COMPUTING_ID_LEN),
        ForeignKey("officer_info.computing_id"),
        nullable=False,
    )

    # dates of creation and last edit
    date_created = Column(DateTime(timezone=True), nullable=False)
    last_edited = Column(DateTime(timezone=True), nullable=False)

    # storing the html content
    html_content = Column(Text, nullable=False)

    # tags for the respective post
    # TODO: consider implementing limits for tag size and count
    post_tags = Column(String(128))
