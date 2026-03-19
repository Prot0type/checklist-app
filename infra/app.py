#!/usr/bin/env python3
from __future__ import annotations

import os

import aws_cdk as cdk

from checklist_infra.config import InfrastructureConfig
from checklist_infra.stack import ChecklistAppStack


app = cdk.App()
config = InfrastructureConfig.from_app(app)

stack_environment = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION", config.aws_region),
)

ChecklistAppStack(
    app,
    config.stack_name,
    config=config,
    env=stack_environment,
    description="Checklist app infrastructure for the EC2 worker and DynamoDB tables.",
)

app.synth()
