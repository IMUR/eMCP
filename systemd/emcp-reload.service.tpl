[Unit]
Description=Reload eMCP docker-compose stack
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=__EMCP_ROOT__
ExecStart=/usr/bin/docker compose up -d --remove-orphans
ExecStartPost=/usr/bin/docker restart emcp-server
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
