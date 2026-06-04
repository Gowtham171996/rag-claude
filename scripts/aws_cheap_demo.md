# Minimal AWS Demo — EC2 Spot Instance (~€0.50 for 30 min)

Instead of the full Fargate+ALB+Terraform stack, spin up ONE EC2 spot instance,
run docker compose on it, demo, terminate. Total cost < €1.

## Cost breakdown
Instance: t3.xlarge (4 vCPU, 16 GB RAM) spot price ≈ $0.05/hr
30 minutes = $0.025
Data transfer: < $0.01
Total: < €0.05  ✅ well within €10 budget

t3.xlarge has 16GB RAM — enough to run Ollama (qwen3.5:4b needs ~5GB)
without a GPU. Inference is slower on CPU but fine for a demo.

---

## Step 1 — Get AWS keys

1. Go to https://console.aws.amazon.com
2. Create a free account (credit card required for identity — you won't be charged for this)
3. In the console: IAM → Users → Create User
   Name: rag-demo-user
4. Attach policies (minimum needed for this script):
   - AmazonEC2FullAccess
   - AmazonS3FullAccess (for ECR image if needed)
5. Users → rag-demo-user → Security credentials → Create access key
   Select: "Command Line Interface (CLI)"
   Download the CSV — it contains:
     AWS_ACCESS_KEY_ID=AKIA...
     AWS_SECRET_ACCESS_KEY=...

6. Install AWS CLI: https://aws.amazon.com/cli/
7. Configure:
   aws configure
   # paste your Access Key ID, Secret Access Key
   # Region: eu-central-1 (Frankfurt — cheapest for Europe)
   # Output: json

## Step 2 — Budget alarm (IMPORTANT — do this first)
aws budgets create-budget --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget '{
    "BudgetName": "rag-demo-limit",
    "BudgetLimit": {"Amount": "10", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[{
    "Notification": {"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80},
    "Subscribers": [{"SubscriptionType":"EMAIL","Address":"bcgowtham17@gmail.com"}]
  }]'

## Step 3 — Launch spot instance and run the stack

# Find the latest Ubuntu 22.04 AMI in eu-central-1
AMI=$(aws ec2 describe-images \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
            "Name=state,Values=available" \
  --query "sort_by(Images,&CreationDate)[-1].ImageId" \
  --output text --region eu-central-1)

# Create a key pair (to SSH in if needed)
aws ec2 create-key-pair --key-name rag-demo-key \
  --query "KeyMaterial" --output text > rag-demo-key.pem
chmod 400 rag-demo-key.pem

# Launch spot instance with a bootstrap script
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI \
  --instance-type t3.xlarge \
  --key-name rag-demo-key \
  --instance-market-options '{"MarketType":"spot"}' \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":30}}]' \
  --user-data '#!/bin/bash
    apt-get update -y
    apt-get install -y docker.io git
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    systemctl start docker
    git clone https://github.com/Gowtham171996/rag-claude.git /app
    cd /app
    echo "API_KEY=demo-key-123" > .env
    echo "ANTHROPIC_API_KEY=" >> .env
    echo "OLLAMA_MODEL=qwen3.5:4b" >> .env
    echo "OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b" >> .env
    docker-compose up -d' \
  --region eu-central-1 \
  --query "Instances[0].InstanceId" --output text)

echo "Instance launched: $INSTANCE_ID"

# Get the public IP (wait ~60s for it to boot)
sleep 60
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text --region eu-central-1)

echo "Demo URL: http://$PUBLIC_IP:8000/docs"
echo "Health:   http://$PUBLIC_IP:8000/api/v1/health"

## Step 4 — Open port 8000
SG=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query "Reservations[0].Instances[0].SecurityGroups[0].GroupId" \
  --output text --region eu-central-1)

aws ec2 authorize-security-group-ingress \
  --group-id $SG \
  --protocol tcp --port 8000 --cidr 0.0.0.0/0 \
  --region eu-central-1

## Step 5 — Wait for models to pull (~5 min on first run, then demo)
# Watch logs:
# ssh -i rag-demo-key.pem ubuntu@$PUBLIC_IP "docker logs rag-ollama -f"

## Step 6 — TERMINATE IMMEDIATELY after demo (stops all billing)
aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region eu-central-1
echo "Instance terminated. Billing stopped."

---

## Keys summary

| Key | Where to get it | Needed for |
|-----|----------------|------------|
| AWS_ACCESS_KEY_ID | IAM → Users → Security credentials | All AWS CLI commands |
| AWS_SECRET_ACCESS_KEY | Same CSV download | All AWS CLI commands |
| ANTHROPIC_API_KEY | console.anthropic.com → API Keys | Claude fallback LLM (optional) |
| API_KEY | You set this yourself | X-API-Key header in your RAG API |

## Total AWS charges for this approach: < €0.10
## Terminate the instance = billing stops immediately.
