from dataclasses import dataclass, fields
from typing import Optional

from vivcpy.enums import (
    ColorOfBerrySkin,
    CountryOrRegion,
    Species,
    Utilization,
)


@dataclass(frozen=True)
class Variety:
    prime_name: str
    variety_number_vivc: int

    color_of_berry_skin: Optional[ColorOfBerrySkin] = None
    country_or_region_of_origin_of_the_variety: Optional[CountryOrRegion] = None
    species: Optional[Species] = None
    pedigree_as_given_by_breeder_bibliography: Optional[str] = None
    pedigree_confirmed_by_markers: Optional[str] = None
    prime_name_of_parent_1: Optional[str] = None
    prime_name_of_parent_2: Optional[str] = None
    parent_offspring_relationship: Optional[str] = None
    offspring: Optional[str] = None
    breeder: Optional[str] = None
    breeder_institute_code: Optional[str] = None
    breeder_contact_address: Optional[str] = None
    year_of_selection: Optional[int] = None
    year_of_protection: Optional[str] = None
    year_of_crossing: Optional[int] = None
    formation_of_seeds: Optional[str] = None
    sex_of_flowers: Optional[str] = None
    taste: Optional[str] = None
    chlorotype: Optional[str] = None
    loci_for_resistance: Optional[str] = None

    utilization: Optional[list[Utilization]] = None
