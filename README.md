# Sprint Sarthi

Sprint Sarthi is a human-governed AI Scrum Master that converts architecture documents into a traceable, estimated, dependency-aware, Sprint-ready backlog.

## Run

```bash
git pull origin main
SPRINT_SARTHI_HOST=YOUR_EC2_PUBLIC_IP bash run.sh
```

Open `http://YOUR_EC2_PUBLIC_IP`. Allow inbound TCP port `80` in the EC2 security group.

On the EC2 machine, configure its firewall once:

```bash
bash ec2-firewall.sh
```

In the AWS EC2 Security Group, add inbound rules for TCP `22` (SSH) and TCP `80` (frontend). The API is private inside Docker and is accessed through the UI. Do not allow all ports.

For Windows/macOS/Linux local Docker:

```bash
bash run.sh
```

Stop the containers with:

```bash
docker compose down
```
