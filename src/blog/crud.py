import logging
from datetime import date, datetime

import sqlalchemy
from sqlalchemy import func

import database
from blog.models import BlogPosts


async def create_new_entry(
    db_session: database.DBSession,
    title:str, computing_id:str, post_tags: str, html_content:str,
    date_created:date, last_edited: date
):
    """ To create a new blog entry """

    #TODO

async def fetch_by_title(
    db_session: database.DBSession,
    title: str
) -> tuple[str, str, datetime, list[str] | None] | None:
    """ Returns the blog entry with the matching title """
    # returns title, html, date, and list of tags

    query = sqlalchemy.select(BlogPosts)
    # query will only return an entry if the title is an exact
    # match ( as title is the unique key)
    # should be only one result to return
    query = query.where(BlogPosts.title == title)

    # should return the one entry with an unique title
    post = await db_session.scalar(query)

    # picking out the specific fields we want returned
    return post.html_content, post.last_edited, post.post_tags


async def fetch_by_date_and_tag(
    db_session: database.DBSession,
    last_edited: date,
    tags:str
) -> (str, str | None) | None:
    """" Returns blog entries sorted by date of last edit and containing matching tags """
    # returns title and html

    query = sqlalchemy.select(BlogPosts)
    # checks for matching tags first
    # then sort by date of last edit
    query = query.where(BlogPosts.post_tags in tags).where(BlogPosts.last_edited).order_by(BlogPosts.last_edited.desc())
    # .all() should return a list of all the posts
    post = await db_session(query).all()

    # now what
    return post


async def update_entry(
    db_session: database.DBSession,
    title:str,
    html_content:str,
    last_edited: func.now(),
):
    """ To update html contents of an existing entry """

    #TODO
