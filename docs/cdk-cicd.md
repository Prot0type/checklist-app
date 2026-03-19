# CDK And CI/CD

This repo now includes:

- a Python CDK app under `infra/`
- GitHub Actions CI in `.github/workflows/ci.yml`
- GitHub Actions deploy automation in `.github/workflows/deploy.yml`

## What CDK Manages

The current stack provisions:

- a single-AZ VPC with one public subnet and no NAT gateway
- a `t4g.small` Ubuntu 24.04 ARM EC2 worker
- the EC2 instance role with `AmazonSSMManagedInstanceCore`
- the `Checklist` DynamoDB table
- the `MatchData` DynamoDB table

The instance is tagged for automation:

- `Project=checklist-app`
- `Environment=prod`
- `Component=worker`

## What The Deploy Workflow Does

On pushes to `main` or on manual dispatch:

1. assumes the GitHub OIDC role in AWS
2. bootstraps and deploys the CDK stack
3. finds the worker instance by tags
4. starts it if it was stopped
5. waits for SSM to come online
6. updates the app checkout on the server
7. installs the app and reruns the t4g smoke test
8. writes `/etc/checklist-app/checklist-app.env`
9. stops the instance again if the workflow had to start it

## GitHub Configuration

The workflows are currently wired to:

- role ARN: `arn:aws:iam::637423363389:role/Checklist-App-GitHub-OIDC-Role`
- branch trust model: `main`
- AWS region: `us-west-2`

## Optional GitHub Secrets

If these repo secrets are set, the deploy workflow will write them into the server env file and enable the monitor service:

- `DISCORD_BOT_TOKEN`
- `DISCORD_CHANNEL_ID`

If they are not set, the app still deploys and smoke-tests, but the monitor service is not enabled automatically.

## Local Infra Commands

From the repo root:

```bash
python -m pip install -r infra/requirements.txt
npm install --global aws-cdk
cd infra
cdk synth
```

For the first deploy in an account/region:

```bash
cd infra
cdk bootstrap aws://ACCOUNT_ID/us-west-2
cdk deploy --all --require-approval never
```
