"""Pydantic request/response contracts for the estimator API.

Field names must match the downstream model service exactly (Task 1's
<HouseFeatures>).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class HouseFeatures(BaseModel):
    square_footage: float = Field(gt=0, le=100_000, description="square footage")
    bedrooms: int = Field(ge=0, le=20, description="bedrooms")
    bathrooms: float = Field(ge=0, le=20, description="bathrooms")
    year_built: int = Field(ge=1800, le=2026, description="year built")
    lot_size: float = Field(gt=0, le=1_000_000, description="lot size")
    distance_to_city_center: float = Field(ge=0, le=1000, description="distance to city center")
    school_rating: float = Field(ge=0, le=10, description="school rating")


class EstimateResponse(BaseModel):
    id: str
    inputs: HouseFeatures
    prediction: float
    created_at: str


class EstimateListResponse(BaseModel):
    estimates: list[EstimateResponse]
