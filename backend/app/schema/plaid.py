"""Request and response schemas for the /plaid routes."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

# Plaid public tokens are about 60 characters, the cap only bounds abuse.
PublicToken = Annotated[str, StringConstraints(min_length=1, max_length=500)]
InstitutionName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class ExchangeRequest(BaseModel):
    """What the frontend gets from Plaid Link's onSuccess. No user id: the owner is
    always the logged-in user."""

    model_config = ConfigDict(extra="forbid")

    public_token: PublicToken
    institution_name: InstitutionName  # display only, Link's metadata.institution.name


class LinkTokenOut(BaseModel):
    link_token: str
    expiration: str  # ISO 8601, straight from Plaid
