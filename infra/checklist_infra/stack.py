from __future__ import annotations

from aws_cdk import CfnOutput, RemovalPolicy, Stack, Tags
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct

from checklist_infra.config import InfrastructureConfig


class ChecklistAppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, config: InfrastructureConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=1,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                )
            ],
        )

        security_group = ec2.SecurityGroup(
            self,
            "WorkerSecurityGroup",
            vpc=vpc,
            description="Outbound-only security group for the checklist worker instance.",
            allow_all_outbound=True,
        )

        checklist_table = dynamodb.Table(
            self,
            "ChecklistTable",
            table_name=config.checklist_table_name,
            partition_key=dynamodb.Attribute(
                name="checklist_name",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=False
            ),
        )

        match_data_table = dynamodb.Table(
            self,
            "MatchDataTable",
            table_name=config.match_data_table_name,
            partition_key=dynamodb.Attribute(
                name="match_url",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=False
            ),
        )

        instance_role = iam.Role(
            self,
            "WorkerInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="Allows the checklist worker to use SSM and read/write the app tables.",
        )
        instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
        )
        checklist_table.grant_read_write_data(instance_role)
        match_data_table.grant_read_write_data(instance_role)

        user_data = ec2.UserData.for_linux()
        self._add_bootstrap_commands(user_data, config)

        machine_image = ec2.GenericSSMParameterImage(
            parameter_name=config.ubuntu_ami_ssm_parameter,
            os=ec2.OperatingSystemType.LINUX,
        )

        worker_instance = ec2.Instance(
            self,
            "WorkerInstance",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=security_group,
            role=instance_role,
            instance_type=ec2.InstanceType(config.instance_type),
            machine_image=machine_image,
            user_data=user_data,
            require_imdsv2=True,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/sda1",
                    volume=ec2.BlockDeviceVolume.ebs(
                        config.instance_volume_size_gib,
                        delete_on_termination=True,
                        encrypted=True,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                    ),
                )
            ],
        )

        Tags.of(self).add("Project", config.project_name)
        Tags.of(self).add("Environment", config.environment_name)
        Tags.of(worker_instance).add("Component", "worker")
        Tags.of(worker_instance).add("Name", f"{config.project_name}-{config.environment_name}-worker")

        CfnOutput(self, "ChecklistTableName", value=checklist_table.table_name)
        CfnOutput(self, "MatchDataTableName", value=match_data_table.table_name)
        CfnOutput(self, "WorkerInstanceId", value=worker_instance.instance_id)
        CfnOutput(self, "WorkerPublicDnsName", value=worker_instance.instance_public_dns_name)

    def _add_bootstrap_commands(self, user_data: ec2.UserData, config: InfrastructureConfig) -> None:
        repo_url = f"https://github.com/{config.github_repository}.git"
        app_dir = "/opt/checklist-app"
        env_file = "/etc/checklist-app/checklist-app.env"

        user_data.add_commands(
            "set -euxo pipefail",
            "export DEBIAN_FRONTEND=noninteractive",
            "apt-get update",
            "apt-get install -y git",
            "mkdir -p /opt",
            f"if [ ! -d {app_dir}/.git ]; then git clone {repo_url} {app_dir}; fi",
            f"cd {app_dir}",
            f"git fetch origin {config.github_branch}",
            f"git checkout {config.github_branch}",
            f"git reset --hard origin/{config.github_branch}",
            "bash ops/rebuild_t4g.sh",
            (
                "CHECKLIST_AWS_REGION='{region}' "
                "CHECKLIST_TABLE_NAME='{checklist_table}' "
                "MATCH_DATA_TABLE_NAME='{match_table}' "
                "CHECKLIST_CSV_DIRECTORY='{app_dir}/checklist_csvs' "
                "CHECKLIST_LOG_DIRECTORY='/var/log/checklist-app' "
                "bash ops/render_server_env.sh '{env_file}'"
            ).format(
                region=config.aws_region,
                checklist_table=config.checklist_table_name,
                match_table=config.match_data_table_name,
                app_dir=app_dir,
                env_file=env_file,
            ),
            "cp ops/checklist-app-monitor.service /etc/systemd/system/checklist-app-monitor.service",
            "systemctl daemon-reload",
        )
