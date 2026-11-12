# The base image tag sets the synapseclient version.
# The digest pins the image. Update the tag and the digest together.
FROM ghcr.io/sage-bionetworks/synapsepythonclient:v4.15.0@sha256:aec697e90ac2c78cefc6b5768544e1e1da431d42ba4d2638cfca3f4628b07ac5

# Copy Python script
COPY src/register_json_schemas.py /usr/local/bin/register_json_schemas.py

# Set working directory to GitHub workspace
WORKDIR /github/workspace

# Set entrypoint to Python script
ENTRYPOINT ["python", "/usr/local/bin/register_json_schemas.py"]
