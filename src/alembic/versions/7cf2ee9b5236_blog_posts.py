"""blog_posts

Revision ID: 7cf2ee9b5236
Revises: 43f71e4bd6fc
Create Date: 2024-08-31 02:48:49.791153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7cf2ee9b5236'
down_revision: Union[str, None] = '43f71e4bd6fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('blog_posts',
    sa.Column('title', sa.String(length=128), nullable=False),
    sa.Column('computing_id', sa.String(length=32), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=False),
    sa.Column('last_edited', sa.DateTime(), nullable=False),
    sa.Column('html_content', sa.Text(), nullable=False),
    sa.Column('post_tags', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('title'),
    sa.ForeignKeyConstraint(['computing_id'],['officer_info.computing_id'])
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('blog_posts')
    # ### end Alembic commands ###
