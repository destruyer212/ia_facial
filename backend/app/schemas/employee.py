from pydantic import BaseModel, Field


class OrgAreaPublic(BaseModel):
    code: str
    name: str
    sort_order: int = 0


class OrgPositionPublic(BaseModel):
    area_code: str
    code: str
    name: str
    sort_order: int = 0


class EmployeeCatalogResponse(BaseModel):
    areas: list[OrgAreaPublic]
    positions: list[OrgPositionPublic]


class NextEmployeeCodeResponse(BaseModel):
    area_code: str
    area_name: str
    position_code: str
    position_name: str
    employee_code: str = Field(description="Formato AREA-CARGO-CORRELATIVO")
    correlativo: int
