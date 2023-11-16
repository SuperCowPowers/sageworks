"""Script that loops through all endpoints and checks if they are ready"""
import logging

# SageWorks Imports
from sageworks.views.artifacts_text_view import ArtifactsTextView
from sageworks.artifacts.endpoints.endpoint import Endpoint

# Setup logging
log = logging.getLogger("sageworks")

# Create a instance of the ArtifactsTextView
artifacts_text_view = ArtifactsTextView()

# Get all the endpoints
endpoints = artifacts_text_view.endpoints_summary()
for end_name in endpoints["Name"]:
    end = Endpoint(end_name)
    if end.ready():
        log.debug(f"Endpoint {end_name} is ready!")
    else:
        log.important(f"Endpoint {end_name} is not ready...Calling make_ready.... ")
        end.make_ready()
