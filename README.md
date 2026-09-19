# Sprint Sarthi

Sprint Sarthi is a human-governed AI Scrum Master that converts architecture documents into a traceable, estimated, dependency-aware, Sprint-ready backlog.

## Run

```bash
git pull origin main
SPRINT_SARTHI_HOST=YOUR_EC2_PUBLIC_IP bash run.sh
```

Open `http://YOUR_EC2_PUBLIC_IP`. Allow inbound TCP ports `80` and `8000` in the EC2 security group.

For Windows/macOS/Linux local Docker:

```bash
bash run.sh
```

Stop the containers with:

```bash
docker compose down
```
