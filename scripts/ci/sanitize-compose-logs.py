import re
import sys


TOKEN_PATH = re.compile(r"(?P<prefix>/(?:api/projects/by-token|p)/)[^/?\s]+")
SECRET_FIELD = re.compile(
    r'(?i)(?P<prefix>\b(?:recovery_key|creator_token|share_token|voter_hash|recovery_key_hash|creator_credential_hash|share_token_hash)\b["\s:=]+)[^,}\s]+',
)
HEX_SECRET = re.compile(r"(?i)\b[0-9a-f]{64}\b")

for line in sys.stdin:
    line = TOKEN_PATH.sub(r"\g<prefix>[REDACTED]", line)
    line = SECRET_FIELD.sub(r"\g<prefix>[REDACTED]", line)
    line = HEX_SECRET.sub("[REDACTED]", line)
    sys.stdout.write(line)
