from pydantic import BaseModel


class SiteConfigResponse(BaseModel):
    admin_enabled: bool
