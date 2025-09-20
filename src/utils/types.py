
from sqlalchemy import Dialect
from sqlalchemy.types import Text, TypeDecorator


class StringList(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect: Dialect) -> str:
        if value is None:
            return ""
        if not isinstance(value, list):
            raise ValueError("Must be a list")

        return ",".join(value)

    def process_result_value(self, value, dialect: Dialect) -> list[str]:
        if value is None or value == "":
            return []
        return value.split(",")


