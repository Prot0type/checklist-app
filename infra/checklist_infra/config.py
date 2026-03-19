from __future__ import annotations

from dataclasses import dataclass

import aws_cdk as cdk


@dataclass(frozen=True, slots=True)
class InfrastructureConfig:
    project_name: str
    environment_name: str
    aws_region: str
    github_repository: str
    github_branch: str
    instance_type: str
    instance_volume_size_gib: int
    checklist_table_name: str
    match_data_table_name: str
    ubuntu_ami_ssm_parameter: str

    @classmethod
    def from_app(cls, app: cdk.App) -> "InfrastructureConfig":
        context = app.node.try_get_context("checklist") or {}
        return cls(
            project_name=context.get("projectName", "checklist-app"),
            environment_name=context.get("environmentName", "prod"),
            aws_region=context.get("awsRegion", "us-west-2"),
            github_repository=context.get("githubRepository", "Prot0type/checklist-app"),
            github_branch=context.get("githubBranch", "main"),
            instance_type=context.get("instanceType", "t4g.small"),
            instance_volume_size_gib=int(context.get("instanceVolumeSizeGiB", 16)),
            checklist_table_name=context.get("checklistTableName", "Checklist"),
            match_data_table_name=context.get("matchDataTableName", "MatchData"),
            ubuntu_ami_ssm_parameter=context.get(
                "ubuntuAmiSsmParameter",
                "/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id",
            ),
        )

    @property
    def stack_name(self) -> str:
        project = "".join(part.capitalize() for part in self.project_name.replace("_", "-").split("-"))
        environment = "".join(part.capitalize() for part in self.environment_name.replace("_", "-").split("-"))
        return f"{project}{environment}Stack"
