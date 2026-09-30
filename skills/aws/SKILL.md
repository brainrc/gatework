---
name: aws
description: AWS account safety, CLI usage, and review checklists for IAM, networking, S3, KMS, EKS, and cost. Use when a change or task involves AWS resources, IAM policies, the aws CLI, or AWS-specific Terraform.
---

# aws

## Account safety
- Never rely on the default profile. Every command names `--profile <p>` (or runs with an
  `AWS_PROFILE` the user confirmed) and `--region`.
- Before the first AWS call in a work item, run `aws sts get-caller-identity --profile <p>` and
  show the account ID and role to the user. Record it in `state.targets.aws`.
- Read-only calls (`describe-*`, `list-*`, `get-*`) are fine against the approved account.
  Anything that creates, modifies, deletes, invokes, starts, or stops needs explicit approval
  and is normally done through IaC instead.
- Never print or copy credentials, session tokens, or `~/.aws/credentials`. SSO login is the user's job.

## IAM review
- No `"Action": "*"` / `"Resource": "*"` pairs; scope `Resource` to ARNs; use `Condition` keys
  (`aws:SourceArn`, `aws:PrincipalOrgID`, `aws:RequestedRegion`) for cross-service and cross-account access.
- `iam:PassRole` restricted to specific role ARNs. Watch for `iam:*`, `sts:AssumeRole` on `*`,
  and `kms:*`: CRITICAL unless justified.
- Trust policies: specific principals; OIDC trust (GitHub Actions, EKS IRSA/Pod Identity)
  pinned to `sub` claims (repo/branch, namespace/service account).
- Prefer managed identities (IRSA / Pod Identity / instance profiles) over access keys.

## Networking
- Security groups: no `0.0.0.0/0` or `::/0` ingress except public load balancers on 80/443;
  reference SGs instead of CIDRs inside the VPC.
- Public subnets only for LBs/NAT; databases and workloads private. VPC endpoints for S3/ECR/STS
  where egress cost or isolation matters.

## Data
- S3: Block Public Access on, bucket policy denies non-TLS (`aws:SecureTransport`), SSE-KMS or
  SSE-S3, versioning for anything important, lifecycle rules for logs.
- RDS/DynamoDB: encryption, deletion protection, backups/PITR, not publicly accessible.
- KMS: key policies least-privilege, rotation enabled, `prevent_destroy` on keys.

## Cost callouts (mention in plan.md)
NAT gateways, cross-AZ traffic, provisioned IOPS, large instance classes, always-on
EKS node groups, CloudWatch log retention "never expire", data transfer to the internet.
