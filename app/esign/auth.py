from abc import ABC, abstractmethod

import jwt

from app.esign.exception import InvalidAuthenticationCreds


class AbstractAuthentication(ABC):
    @abstractmethod
    def has_access(self, token: str) -> dict:
        """Check the jwt token"""


class NoAuthentication(AbstractAuthentication):
    def has_access(self, _: str) -> dict:
        return {}


class Auth0Authentication(AbstractAuthentication):
    def __init__(self, audience: str, domain: str):
        self.audience = audience
        self.domain = domain
        self.algorithms = ["RS256"]
        self.jwks_url = f"https://{self.domain}/.well-known/jwks.json"
        self.issuer = f"https://{self.domain}/"
        self.jwks_client = jwt.PyJWKClient(self.jwks_url)

    def verify(self, token: str) -> dict:
        signing_key = self.jwks_client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=self.algorithms,
            audience=self.audience,
            issuer=self.issuer,
        )

    def has_access(self, token: str) -> dict:
        try:
            return self.verify(token)
        except jwt.PyJWTError as exc:
            raise InvalidAuthenticationCreds(additional_message=str(exc))
