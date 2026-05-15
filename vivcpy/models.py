from dataclasses import dataclass, fields
from typing import Optional

from vivcpy.enums import (
    ColorOfBerrySkin,
    CountryOrRegion,
    FormationOfSeeds,
    Species,
    SexOfFlowers,
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
    offspring: Optional[bool] = None
    breeder: Optional[str] = None
    breeder_institute_code: Optional[str] = None
    breeder_contact_address: Optional[str] = None
    year_of_crossing: Optional[int] = None
    year_of_selection: Optional[int] = None
    year_of_protection: Optional[str] = None
    formation_of_seeds: Optional[FormationOfSeeds] = None
    sex_of_flowers: Optional[SexOfFlowers] = None
    taste: Optional[str] = None
    chlorotype: Optional[str] = None
    loci_for_resistance: Optional[list[str]] = None

    utilization: Optional[list[Utilization]] = None

    synonyms: Optional[list[str]] = None

    def __and__(self, other: "Variety") -> "Variety":
        """Merge two varieties, keeping self's values where set and falling back to other's."""
        if (
            self.prime_name != other.prime_name
            or self.variety_number_vivc != other.variety_number_vivc
        ):
            raise ValueError(
                f"Cannot merge varieties with different identity: "
                f"'{self.prime_name}' ({self.variety_number_vivc}) vs "
                f"'{other.prime_name}' ({other.variety_number_vivc})"
            )
        return Variety(
            **{
                f.name: (
                    getattr(self, f.name)
                    if getattr(self, f.name) is not None
                    else getattr(other, f.name)
                )
                for f in fields(self)
            }
        )
