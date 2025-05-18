from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Baffle:
    name: str
    length_mm: float
    material: Optional[str] = None
    color: Optional[str] = None

    def get_properties(self) -> dict:
        return {
            "name": self.name,
            "length_mm": self.length_mm,
            "material": self.material,
            "color": self.color
        }

@dataclass
class BaffleRow:
    name: str
    length_mm: float
    max_baffle_length_mm: float = 2000  # Default maximum baffle length
    baffles: List[Baffle] = None

    def __post_init__(self):
        self.baffles = []
        self._split_row_into_baffles()

    def _split_row_into_baffles(self) -> None:
        """Splits the row into multiple baffles if needed"""
        num_baffles = -1
        if self.length_mm % self.max_baffle_length_mm == 0:
            num_baffles = int(self.length_mm / self.max_baffle_length_mm)
        else:
            num_baffles = int(self.length_mm // self.max_baffle_length_mm) + 1

        for i in range(num_baffles):
            start = i * self.max_baffle_length_mm
            end = min(start + self.max_baffle_length_mm, self.length_mm)
            baffle_name = f"Baffle_{i+1}"
            new_baffle = Baffle(
                name=baffle_name,
                length_mm=end - start,
                material="DefaultMaterial",
                color="DefaultColor"
            )
            self.baffles.append(new_baffle)

    def add_baffle(self, baffle: Baffle) -> None:
        self.baffles.append(baffle)

@dataclass
class BaffleLayout:
    name: str
    space: 'Space'  # Forward reference to Space class
    rows: List[BaffleRow] = None

    def __post_init__(self):
        self.rows = []

    def add_row(self, row: BaffleRow) -> None:
        self.rows.append(row)

@dataclass
class Space:
    name: str
    space_type: str  # 'room', 'office', 'kitchen', etc.
    description: Optional[str] = None
    layouts: List[BaffleLayout] = None

    def __post_init__(self):
        self.layouts = []

    def add_layout(self, layout: BaffleLayout) -> None:
        self.layouts.append(layout)

@dataclass
class Area:
    name: str
    spaces: List[Space] = None

    def __post_init__(self):
        self.spaces = []

    def add_space(self, space: Space) -> None:
        self.spaces.append(space)

    def get_total_area(self) -> float:
        """Calculates and returns total area of all spaces in this area"""
        # Implement actual area calculation logic here
        pass

@dataclass
class Floor:
    name: str
    areas: List[Area] = None

    def __post_init__(self):
        self.areas = []

    def add_area(self, area: Area) -> None:
        self.areas.append(area)

    def get_total_spaces(self) -> int:
        """Returns total number of spaces on this floor"""
        return sum(len(area.spaces) for area in self.areas)

@dataclass
class Building:
    name: str
    address: str
    floors: List[Floor] = None

    def __post_init__(self):
        self.floors = []

    def add_floor(self, floor: Floor) -> None:
        self.floors.append(floor)

    def get_total_floors(self) -> int:
        """Returns total number of floors in the building"""
        return len(self.floors)

    def get_total_spaces(self) -> int:
        """Returns total number of spaces in the building"""
        return sum(floor.get_total_spaces() for floor in self.floors)
