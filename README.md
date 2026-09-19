# Sprint Sarthi

Sprint Sarthi is a human-governed AI Scrum Master that converts architecture documents into a traceable, estimated, dependency-aware, Sprint-ready backlog.

## Run

```bash
git pull origin main
SPRINT_SARTHI_HOST=YOUR_EC2_PUBLIC_IP bash run.sh
```

Open `http://YOUR_EC2_PUBLIC_IP`. Allow inbound TCP ports `80` and `8000` in the EC2 security group.

On the EC2 machine, configure its firewall once:

```bash
bash ec2-firewall.sh
```

In the AWS EC2 Security Group, add inbound rules for TCP `22` (SSH), TCP `80` (frontend), and TCP `8000` (API). Use your own IP for SSH; use your own IP for the API when possible. Do not allow all ports.

For Windows/macOS/Linux local Docker:

```bash
bash run.sh
```

Stop the containers with:

```bash
docker compose down
```
