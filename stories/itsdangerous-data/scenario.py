# The intended use, from the README: sign a user's id and name, send it away, get it back, trust it.
from itsdangerous import URLSafeSerializer

auth_s = URLSafeSerializer("secret key", "auth")
token = auth_s.dumps({"id": 5, "name": "itsdangerous"})
data = auth_s.loads(token)
assert data == {"id": 5, "name": "itsdangerous"}
