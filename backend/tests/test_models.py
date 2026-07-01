"""ORM mapper configuration sanity check.

Regression test for a real bug found via live curl/Playwright testing:
several models declared plain BigInteger FK-like columns (e.g.
RefreshToken.user_id, Course.station_id) without an actual `ForeignKey(...)`,
while their sibling model declared a `relationship()` expecting one.
SQLAlchemy configures the *entire* mapper registry lazily on first ORM use
(e.g. `Session.get(Place, id)` in POST /v1/places/{id}/report), so a single
missing ForeignKey anywhere in the registry breaks ORM access everywhere,
even for routes that never touch the broken model directly. Every other
test in this suite mocks the DB session, so this was never caught until a
real request against the live DB hit `sqlalchemy.exc.NoForeignKeysError`.
"""
from sqlalchemy.orm import configure_mappers

import app.models  # noqa: F401  — import to register all mapped classes


def test_all_orm_relationships_configure_without_error():
    configure_mappers()
