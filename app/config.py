import base64
import json
import os
from pathlib import Path

from pydantic import BaseModel, BaseSettings, PrivateAttr, validator


class AuthSettings(BaseModel):
    api_keys: list[str] | None = None

    @validator("api_keys", pre=True)
    def parse_api_keys(cls, api_keys_value):
        if not api_keys_value:
            return None
        return json.loads(api_keys_value)


class GotenbergSettings(BaseModel):
    url: str = "http://localhost:3000"

    # Config for retry, moved here to control it inside tests. All values in seconds
    min_wait: float = 3.0
    max_wait: float = 5.0
    max_timeout: float = 30.0
    max_attempt: int = 5


class DocGenSettings(BaseModel):
    use_pypdftk: bool = True
    tmp_dir_path: Path = Path("doc_gen_tmp")


class AwsSettings(BaseModel):
    access_key_id: str | None = None
    secret_access_key: str | None = None


class StorageSettings(BaseModel):
    endpoint_url: str | None = None
    main_bucket_name: str = "dev-doc-mgmt.coverwhale.com"


class DynamoStorageSettings(BaseModel):
    endpoint_url: str | None = None
    expiration_date_in_seconds: int = 15552000  # 60 sec * 60 min * 24 hours * 180 days
    documents_table_name: str = "Documents"
    envelopes_table_name: str = "Envelopes"
    envelope_callbacks_table_name: str = "EnvelopeCallbacks"


class DocuSignSettings(BaseSettings):
    client_id: str | None
    impersonated_user_id: str | None
    account_id: str | None
    authorization_server: str | None = "account-d.docusign.com"
    host: str | None = "https://demo.docusign.net/restapi"
    webhook_url: str | None = None
    connect_secret_key: str | None = "None"
    pool_max_size: int | None = 4
    min_wait: float = 3.0
    max_wait: float = 5.0
    max_timeout: float = 30.0
    max_attempt: int = 5

    private_key_encoded: str | None
    _private_key: str | None = PrivateAttr(default=None)

    @property
    def private_key(self) -> str:
        if self.private_key_encoded is None:
            raise ValueError("private_key_encoded environment variable is absent")

        if self._private_key is None:
            self._private_key = base64.b64decode(self.private_key_encoded).decode()  # noqa: WPS601

        return self._private_key


class AuthDocuSignSettings(BaseModel):
    domain: str | None = None
    api_audience: str | None = None

    @property
    def is_auth0_enabled(self) -> bool:
        return bool(self.domain and self.api_audience)


class Settings(BaseSettings):
    auth: AuthSettings = AuthSettings()
    gotenberg: GotenbergSettings = GotenbergSettings()
    doc_gen: DocGenSettings = DocGenSettings()
    storage: StorageSettings = StorageSettings()
    dynamo_storage: DynamoStorageSettings = DynamoStorageSettings()
    aws_settings: AwsSettings = AwsSettings()
    docu_sign: DocuSignSettings = DocuSignSettings()
    auth_docu_sign: AuthDocuSignSettings = AuthDocuSignSettings()

    app_version: str = "v0.0.1-develop"

    class Config:
        env_nested_delimiter = "__"
        env_file = os.getenv("ENV_FILE_NAME", ".env")


settings = Settings()
